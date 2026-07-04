"""Translation Celery task."""

import uuid
from typing import Optional

from app.core.celery_app import app
from app.core.database import get_session_factory
from app.services.translation_service import translation_service
from app.services.task_service import task_service
from app.services.meeting_service import meeting_service
from app.services.token_service import token_service
from app.services.cache_service import cache_service


@app.task(
    bind=True,
    name="process_translation",
    queue="priority_normal",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    autoretry_for=(Exception,),
)
def process_translation(
    self,
    meeting_id: str,
    target_languages: Optional[list[str]] = None,
):
    """Translate all subtitles for a meeting into target languages.

    Args:
        meeting_id: Meeting UUID.
        target_languages: List of target language codes. Default to ["en", "ja"].
    """
    import asyncio
    from app.core.redis_client import _redis_instances

    if target_languages is None:
        target_languages = ["en", "ja"]

    async def _process():
        async with get_session_factory()() as db:
            try:
                mid = uuid.UUID(meeting_id)
                meeting = await meeting_service.get_meeting(db, mid)
                if not meeting:
                    raise ValueError(f"Meeting {meeting_id} not found")

                results = {}

                for target_lang in target_languages:
                    # Create a task record per language
                    task = await task_service.create_task(db, mid, "translation")
                    task.celery_task_id = self.request.id
                    await task_service.update_task_status(
                        db, task.id, "running", progress=0,
                    )

                    # Get all subtitles for this meeting
                    from app.services.subtitle_service import subtitle_service as ss

                    subtitle_result = await ss.get_meeting_subtitles(
                        db, mid, page_size=10000  # Get all at once
                    )
                    all_subtitles = subtitle_result["items"]

                    if not all_subtitles:
                        await task_service.update_task_status(
                            db, task.id, "completed", progress=100,
                        )
                        results[target_lang] = {"translated": 0, "cached": 0}
                        continue

                    total = len(all_subtitles)
                    translated = 0
                    cached = 0
                    total_tokens_input = 0
                    total_tokens_output = 0

                    for i, sub in enumerate(all_subtitles):
                        result = await translation_service.translate_text(
                            sub.text,
                            target_language=target_lang,
                            source_language=meeting.source_language,
                        )

                        if result["from_cache"]:
                            cached += 1
                        else:
                            translated += 1
                            total_tokens_input += result["tokens_input"]
                            total_tokens_output += result["tokens_output"]

                        # Save translation record to DB
                        from app.models.translation import Translation

                        translation_record = Translation(
                            subtitle_id=sub.id,
                            meeting_id=mid,
                            target_language=target_lang,
                            translated_text=result["translated_text"],
                            model_used=result["model_used"],
                            token_count_input=result["tokens_input"],
                            token_count_output=result["tokens_output"],
                            translation_hash=translation_service.compute_hash(sub.text),
                        )
                        db.add(translation_record)

                        # Update progress
                        progress = int((i + 1) / total * 100)
                        if progress % 10 == 0:  # Update every 10%
                            await task_service.update_task_status(
                                db, task.id, "running", progress=progress,
                            )

                    # Record token usage (accumulated across all subtitles)
                    await token_service.record_usage(
                        db,
                        user_id=meeting.user_id,
                        operation_type="translation",
                        tokens_input=total_tokens_input,
                        tokens_output=total_tokens_output,
                        model_name=result.get("model_used", "anytrans"),
                        meeting_id=mid,
                    )

                    await task_service.update_task_status(
                        db, task.id, "completed", progress=100,
                    )
                    results[target_lang] = {"translated": translated, "cached": cached}

                await meeting_service.update_status(db, mid, "completed")
                await db.commit()

                # Release task lock on success
                await cache_service.release_task_lock(meeting_id, "translation")

                return {"meeting_id": meeting_id, "results": results}

            except Exception as exc:
                await db.rollback()
                # Release lock so retry can proceed
                try:
                    await cache_service.release_task_lock(meeting_id, "translation")
                except Exception:
                    pass
                if self.request.retries >= self.max_retries:
                    async with get_session_factory()() as inner_db:
                        mid = uuid.UUID(meeting_id)
                        tasks = await task_service.get_meeting_tasks(
                            inner_db, mid, task_type="translation",
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
        # Clear Redis instances cache after asyncio.run() closes the event loop.
        # This prevents "Event loop is closed" errors on the next task invocation.
        _redis_instances.clear()
