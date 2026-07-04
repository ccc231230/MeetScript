"""Main meeting processing Celery chain orchestrator."""

import uuid
from typing import Optional

from celery import chain, group
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import app
from app.core.database import get_session_factory


async def _get_db() -> AsyncSession:
    """Get an async DB session for use in Celery tasks."""
    factory = get_session_factory()
    return factory()


@app.task(bind=True, name="process_meeting", queue="priority_high")
def process_meeting(self, meeting_id: str):
    """Orchestrate the full meeting processing pipeline using Celery Chain.

    Pipeline: Audio Preprocess → ASR → Subtitle → Translation → Summary
    """
    try:
        # Fan-out: Audio Preprocess → (on completion, triggers ASR → Translation → Summary)
        audio_result = process_audio.delay(meeting_id)

        return {
            "meeting_id": meeting_id,
            "audio_task_id": audio_result.id,
        }

    except Exception as exc:
        if self.request.retries >= self.max_retries:
            _mark_meeting_failed(meeting_id, str(exc))
            return
        raise self.retry(exc=exc)


def _mark_meeting_failed(meeting_id: str, error: str):
    """Mark meeting as failed (sync helper for Celery task)."""
    import asyncio

    async def _mark():
        from app.services.meeting_service import meeting_service

        async with await _get_db() as db:
            try:
                await meeting_service.update_status(db, uuid.UUID(meeting_id), "failed")
                await db.commit()
            except Exception:
                await db.rollback()

    asyncio.run(_mark())


# Import sub-tasks so Celery discovers them
from app.tasks.audio_task import process_audio  # noqa: E402, F401
from app.tasks.asr_task import process_asr  # noqa: E402, F401
from app.tasks.translation_task import process_translation  # noqa: E402, F401
from app.tasks.summary_task import process_summary  # noqa: E402, F401
from app.tasks.export_task import process_export  # noqa: E402, F401

# Aliases for the chain components
process_subtitles = process_asr  # Subtitle generation is part of ASR task flow
