"""LLM Summary Celery task."""

import uuid

from app.core.celery_app import app
from app.core.database import get_session_factory
from app.services.summary_service import summary_service
from app.services.task_service import task_service
from app.services.meeting_service import meeting_service
from app.services.model_registry import model_registry
from app.services.token_service import token_service
from app.services.cache_service import cache_service


@app.task(
    bind=True,
    name="process_summary",
    queue="priority_low",
    max_retries=3,
    default_retry_delay=120,
    retry_backoff=True,
    retry_backoff_max=600,
    autoretry_for=(Exception,),
)
def process_summary(self, meeting_id: str):
    """Generate meeting summary using LLM (Qwen).

    1. Collect all subtitles as transcript text
    2. Call LLM for structured summary
    3. Record token usage
    """
    import asyncio
    from app.core.redis_client import _redis_instances, close_redis_connections
    import json

    async def _process():
        await close_redis_connections()
        async with get_session_factory()() as db:
            try:
                mid = uuid.UUID(meeting_id)
                meeting = await meeting_service.get_meeting(db, mid)
                if not meeting:
                    raise ValueError(f"Meeting {meeting_id} not found")

                # Create task record
                task = await task_service.create_task(db, mid, "summary")
                task.celery_task_id = self.request.id
                await task_service.update_task_status(db, task.id, "running", progress=10)

                # Collect subtitles as transcript
                from app.services.subtitle_service import subtitle_service as ss

                subtitle_result = await ss.get_meeting_subtitles(
                    db, mid, page_size=10000,
                )
                all_subtitles = subtitle_result["items"]

                if not all_subtitles:
                    await task_service.update_task_status(
                        db, task.id, "completed", progress=100,
                    )
                    await db.commit()
                    return {"meeting_id": meeting_id, "summary": None}

                # Build transcript text
                transcript_parts = []
                for sub in all_subtitles:
                    speaker = sub.speaker_label.replace("SPEAKER_", "")
                    transcript_parts.append(f"[{speaker}] {sub.text}")
                transcript = "\n".join(transcript_parts)

                await task_service.update_task_status(db, task.id, "running", progress=30)

                # Resolve model from registry
                model_config = await model_registry.get_active_config(db, "summary")
                model_name = model_config["model_name"] if model_config else None

                # Call LLM
                result = await summary_service.generate_summary(transcript, model=model_name)

                await task_service.update_task_status(db, task.id, "running", progress=80)

                # Record token usage
                usage = result.get("usage", {})
                await token_service.record_usage(
                    db,
                    user_id=meeting.user_id,
                    operation_type="summary",
                    tokens_input=usage.get("input_tokens", 0),
                    tokens_output=usage.get("output_tokens", 0),
                    model_name=result.get("model_used", "qwen-max"),
                    meeting_id=mid,
                    model_config_id=uuid.UUID(model_config["id"]) if model_config else None,
                    request_id=result.get("request_id"),
                )

                # Store summary in task details (or dedicated table)
                # For now, store as task error_message field (hack) or in Redis
                from app.core.redis_client import get_redis

                redis = await get_redis()
                await redis.setex(
                    f"meeting_summary:{meeting_id}",
                    86400 * 30,  # 30 days
                    json.dumps(result["summary"], ensure_ascii=False),
                )

                await task_service.update_task_status(db, task.id, "completed", progress=100)
                await db.commit()

                return {
                    "meeting_id": meeting_id,
                    "summary": result["summary"],
                    "model_used": result["model_used"],
                }

            except Exception as exc:
                await db.rollback()
                try:
                    await cache_service.release_task_lock(meeting_id, "summary")
                except Exception:
                    pass
                if self.request.retries >= self.max_retries:
                    async with get_session_factory()() as inner_db:
                        mid = uuid.UUID(meeting_id)
                        tasks = await task_service.get_meeting_tasks(
                            inner_db, mid, task_type="summary",
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
