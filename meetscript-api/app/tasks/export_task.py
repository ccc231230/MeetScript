"""Export Celery task for subtitle/translation export."""

import uuid
from typing import Optional

from app.core.celery_app import app
from app.core.database import get_session_factory
from app.services.subtitle_service import subtitle_service
from app.services.task_service import task_service
from app.services.file_service import file_service
from app.services.cache_service import cache_service


@app.task(
    bind=True,
    name="process_export",
    queue="priority_low",
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
)
def process_export(
    self,
    meeting_id: str,
    user_id: str,
    export_format: str = "srt",
    language: Optional[str] = None,
    speaker_filter: Optional[str] = None,
):
    """Export subtitles/translations to a file and store in MinIO/OSS.

    Args:
        meeting_id: Meeting UUID.
        user_id: User UUID.
        export_format: srt / vtt / json / txt.
        language: Language filter.
        speaker_filter: Speaker label filter.
    """
    import asyncio
    from app.core.redis_client import _redis_instances
    import io

    async def _process():
        async with get_session_factory()() as db:
            try:
                mid = uuid.UUID(meeting_id)
                uid = uuid.UUID(user_id)

                # Create task record
                task = await task_service.create_task(db, mid, "export")
                task.celery_task_id = self.request.id
                await task_service.update_task_status(db, task.id, "running", progress=10)

                # Get subtitles
                result = await subtitle_service.get_meeting_subtitles(
                    db, mid, language=language, speaker_label=speaker_filter, page_size=10000,
                )
                subtitles = result["items"]

                if not subtitles:
                    await task_service.update_task_status(db, task.id, "completed", progress=100)
                    await db.commit()
                    return {"meeting_id": meeting_id, "format": export_format, "count": 0}

                await task_service.update_task_status(db, task.id, "running", progress=50)

                # Generate export content
                generators = {
                    "srt": subtitle_service.generate_srt,
                    "vtt": subtitle_service.generate_vtt,
                    "json": subtitle_service.generate_json,
                    "txt": subtitle_service.generate_txt,
                }
                generator = generators.get(export_format, subtitle_service.generate_srt)
                content = generator(subtitles)

                # Upload to storage
                object_key = f"exports/{meeting_id}/{meeting_id}_{language or 'all'}.{export_format}"
                content_bytes = content.encode("utf-8")

                await file_service.upload_file(
                    str(uid), content_bytes, f"export.{export_format}",
                )

                # Generate download URL
                download_url = await file_service.get_download_url(object_key, expires=86400)

                await task_service.update_task_status(db, task.id, "completed", progress=100)
                await db.commit()

                return {
                    "meeting_id": meeting_id,
                    "format": export_format,
                    "count": len(subtitles),
                    "download_url": download_url,
                }

            except Exception as exc:
                await db.rollback()
                try:
                    await cache_service.release_task_lock(meeting_id, "export")
                except Exception:
                    pass
                if self.request.retries >= self.max_retries:
                    async with get_session_factory()() as inner_db:
                        mid = uuid.UUID(meeting_id)
                        tasks = await task_service.get_meeting_tasks(
                            inner_db, mid, task_type="export",
                        )
                        for t in tasks.get("items", []):
                            if t.status in ("running", "pending", "retrying"):
                                await task_service.mark_task_dlq(inner_db, t.id, str(exc))
                        await inner_db.commit()
                    return
                raise self.retry(exc=exc)

    try:
        return asyncio.run(_process())
    finally:
        _redis_instances.clear()
