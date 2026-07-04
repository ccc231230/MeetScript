"""Audio preprocessing Celery task."""

import os
import tempfile
import uuid
from datetime import datetime, timezone

from app.core.celery_app import app
from app.core.database import get_session_factory
from app.services.audio_processor import audio_processor
from app.services.file_service import file_service
from app.services.task_service import task_service
from app.services.meeting_service import meeting_service


@app.task(
    bind=True,
    name="process_audio",
    queue="priority_high",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    autoretry_for=(Exception,),
)
def process_audio(self, meeting_id: str):
    """Audio preprocessing task.

    1. Create/update task record
    2. Process audio (extract/transcode/split/quality check)
    3. Upload processed segments to storage
    4. Update meeting duration and status
    """
    import asyncio

    async def _process():
        async with get_session_factory()() as db:
            try:
                mid = uuid.UUID(meeting_id)

                # Create task record
                task = await task_service.create_task(db, mid, "audio_preprocess")
                task.celery_task_id = self.request.id
                await task_service.update_task_status(db, task.id, "running", progress=10)

                # Get meeting info
                meeting = await meeting_service.get_meeting(db, mid)
                if not meeting:
                    raise ValueError(f"Meeting {meeting_id} not found")

                # Update meeting status
                await meeting_service.update_status(db, mid, "preprocessing")
                await task_service.update_task_status(db, task.id, "running", progress=20)
                await db.commit()

                # Download the media file from MinIO to a local temp file
                import asyncio
                loop = asyncio.get_event_loop()
                file_data = await file_service.download_file(meeting.file_path)

                # Write to a temp file so ffmpeg can access it
                suffix = os.path.splitext(meeting.file_path)[1] or ".mp4"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    local_path = tmp.name
                    await loop.run_in_executor(None, lambda: tmp.write(file_data))

                try:
                    # Run audio processing pipeline on the local temp file
                    result = audio_processor.process(local_path, meeting_id)

                    if result.warnings:
                        await task_service.update_task_status(
                            db, task.id, "running", progress=50,
                        )

                    # Update meeting duration
                    if result.original_duration_seconds > 0:
                        await meeting_service.update_meeting(
                            db, mid, duration_seconds=int(result.original_duration_seconds),
                        )

                    await task_service.update_task_status(db, task.id, "running", progress=90)

                    # Store segment metadata
                    segment_data = [
                        {
                            "index": s.index,
                            "file_path": s.file_path,
                            "start_seconds": s.start_seconds,
                            "end_seconds": s.end_seconds,
                            "duration_seconds": s.duration_seconds,
                            "md5_hash": s.md5_hash,
                            "quality_warnings": s.quality_warnings,
                        }
                        for s in result.segments
                    ]

                    # Mark complete
                    await task_service.update_task_status(db, task.id, "completed", progress=100)
                    await meeting_service.update_status(db, mid, "processing")

                    await db.commit()

                    # Fan-out: trigger ASR as the next step in the pipeline
                    from app.tasks.asr_task import process_asr  # noqa: F811
                    process_asr.delay(meeting_id)

                    return {
                        "meeting_id": meeting_id,
                        "segments": len(result.segments),
                        "duration": result.original_duration_seconds,
                        "warnings": result.warnings,
                    }
                finally:
                    # Always clean up the temp file
                    try:
                        os.unlink(local_path)
                    except OSError:
                        pass

            except Exception as exc:
                await db.rollback()
                if self.request.retries >= self.max_retries:
                    async with get_session_factory()() as inner_db:
                        mid = uuid.UUID(meeting_id)
                        await meeting_service.update_status(inner_db, mid, "failed")
                        # Find and mark task as DLQ
                        tasks = await task_service.get_meeting_tasks(
                            inner_db, mid, task_type="audio_preprocess"
                        )
                        for t in tasks.get("items", []):
                            if t.status in ("running", "pending", "retrying"):
                                await task_service.mark_task_dlq(inner_db, t.id, str(exc))
                        await inner_db.commit()
                    return
                raise self.retry(exc=exc)

    return asyncio.get_event_loop().run_until_complete(_process())
