"""ASR (Automatic Speech Recognition) Celery task."""

import asyncio
import logging
import os
import subprocess
import tempfile
import traceback
import uuid
from pathlib import Path
from typing import Optional

from app.core.celery_app import app
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.services.asr_service import asr_service
from app.core.redis_client import _redis_instances, close_redis_connections
from app.services.cache_service import cache_service
from app.services.file_service import file_service
from app.services.meeting_service import meeting_service
from app.services.model_registry import model_registry
from app.services.subtitle_service import subtitle_service
from app.services.task_service import task_service
from app.services.token_service import token_service

logger = logging.getLogger(__name__)
settings_ = get_settings()


async def _mark_failed(meeting_id: str, task_id: Optional[str], error: str) -> None:
    """Mark task as DLQ and meeting as failed."""
    async with get_session_factory()() as db:
        mid = uuid.UUID(meeting_id)
        await meeting_service.update_status(db, mid, "failed")
        if task_id:
            await task_service.mark_task_dlq(db, task_id, error)
        else:
            existing = await task_service.get_meeting_tasks(
                db, mid, task_type="asr",
            )
            for t in existing.get("items", []):
                if t.status in ("running", "pending", "retrying"):
                    await task_service.mark_task_dlq(db, t.id, error)
        await db.commit()


async def _run_asr(meeting_id: str, audio_url: Optional[str], request_id: str) -> dict:
    """Core ASR processing logic, separate from Celery task wrapper."""
    mid = uuid.UUID(meeting_id)
    local_path = None
    audio_path = None

    try:
        # Close stale Redis connections from previous asyncio.run() calls
        await close_redis_connections()

        # Release any stale lock from previous attempts
        await cache_service.release_task_lock(meeting_id, "asr")

        # ── Step 0: create / re-use the task record ────────────────
        async with get_session_factory()() as db0:
            existing = await task_service.get_meeting_tasks(
                db0, mid, task_type="asr",
            )
            task_obj = None
            if existing.get("items"):
                task_obj = existing["items"][0]

            if task_obj is None:
                task_obj = await task_service.create_task(db0, mid, "asr")
            else:
                task_obj.celery_task_id = request_id
                await task_service.update_task_status(
                    db0, task_obj.id, "running", progress=5,
                    celery_task_id=request_id,
                )

            await db0.commit()
            task_id = task_obj.id
            logger.warning(f"[ASR] Task record ready: {task_id}")

        # ── Step 1: gather meeting info ────────────────────────────
        async with get_session_factory()() as db:
            meeting = await meeting_service.get_meeting(db, mid)
            if not meeting:
                raise ValueError(f"Meeting {meeting_id} not found")
            logger.warning(
                f"[ASR] Meeting found: {meeting.title}, "
                f"lang={meeting.source_language}, file={meeting.file_path}",
            )

            # Resolve model from registry (fallback to config default)
            model_config = await model_registry.get_active_config(db, "asr")
            model_name = model_config.model_name if model_config else None
            logger.warning(
                "[ASR] Using model: %s",
                model_name or settings_.DEFAULT_ASR_MODEL,
            )

            if not audio_url:
                logger.warning("[ASR] No audio_url provided, downloading from MinIO")
                await task_service.update_task_status(
                    db, task_id, "running", progress=8,
                )
                await db.commit()

                file_data = await file_service.download_file(meeting.file_path)
                logger.warning(
                    f"[ASR] Downloaded {len(file_data)} bytes from MinIO",
                )
                suffix = os.path.splitext(meeting.file_path)[1] or ".mp4"
                with tempfile.NamedTemporaryFile(
                    suffix=suffix, delete=False,
                ) as tmp:
                    local_path = tmp.name
                    tmp.write(file_data)

                await task_service.update_task_status(
                    db, task_id, "running", progress=10,
                )
                await db.commit()

                # Extract audio from video to reduce upload size
                upload_path = local_path
                video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
                if Path(local_path).suffix.lower() in video_exts:
                    audio_path = os.path.join(
                        tempfile.gettempdir(),
                        f"asr_audio_{meeting_id[:8]}.wav",
                    )
                    logger.warning(
                        "[ASR] Extracting audio from video (%d bytes) "
                        "to reduce upload size...",
                        len(file_data),
                    )
                    subprocess.run(
                        [
                            "ffmpeg", "-y",
                            "-i", local_path,
                            "-vn",
                            "-acodec", "pcm_s16le",
                            "-ar", "16000",
                            "-ac", "1",
                            audio_path,
                        ],
                        capture_output=True, text=True, timeout=300, check=True,
                    )
                    audio_size = os.path.getsize(audio_path)
                    logger.warning(
                        "[ASR] Audio extracted: %d bytes (reduced %d bytes)",
                        audio_size, len(file_data) - audio_size,
                    )
                    upload_path = audio_path

                audio_url = await asr_service.upload_audio_to_dashscope(upload_path)
                logger.warning(
                    f"[ASR] Uploaded to DashScope: {audio_url[:80]}...",
                )

                await task_service.update_task_status(
                    db, task_id, "running", progress=13,
                )
                await db.commit()

            await task_service.update_task_status(
                db, task_id, "running", progress=15,
            )

            submit_result = await asr_service.submit_transcription(
                audio_url=audio_url,
                source_language=meeting.source_language,
                enable_diarization=True,
                model_name=model_name,
            )
            logger.warning(
                f"[ASR] Submitted transcription: "
                f"task_id={submit_result.get('task_id')}",
            )

            await task_service.update_task_status(
                db, task_id, "running", progress=20,
            )
            await db.commit()

        # ── Step 2: poll for completion ────────────────────────────
        logger.warning("[ASR] Polling for completion...")
        final_result = await asr_service.wait_for_completion(
            submit_result["task_id"],
            poll_interval=10,
            max_wait=1800,
        )
        logger.warning(
            f"[ASR] ASR completed: "
            f"{len(final_result.get('results', []))} segments",
        )

        # ── Step 3: persist subtitles + token usage ────────────────
        async with get_session_factory()() as db:
            asr_results = final_result.get("results", [])
            subtitles = await subtitle_service.create_subtitles_from_asr(
                db, mid, asr_results, language=meeting.source_language,
            )

            usage = final_result.get("usage", {})
            await token_service.record_usage(
                db,
                user_id=meeting.user_id,
                operation_type="asr",
                tokens_input=usage.get("input_tokens", 0),
                tokens_output=usage.get("output_tokens", 0),
                model_name=settings_.DEFAULT_ASR_MODEL,
                meeting_id=mid,
                request_id=final_result.get("request_id"),
                custom_cost=token_service.calculate_asr_cost(
                    meeting.duration_seconds or 0,
                ),
            )

            await task_service.update_task_status(
                db, task_id, "completed", progress=100,
            )
            await meeting_service.update_status(db, mid, "completed")
            await db.commit()

            logger.warning(
                f"[ASR] Done: {len(subtitles)} subtitles saved",
            )
            return {
                "meeting_id": meeting_id,
                "subtitle_count": len(subtitles),
                "segments": len(asr_results),
            }

    except Exception as exc:
        logger.warning(f"[ASR] Error: {exc}\n{traceback.format_exc()}")
        raise
    finally:
        if local_path:
            try:
                os.unlink(local_path)
            except OSError:
                pass
        if audio_path:
            try:
                os.unlink(audio_path)
            except OSError:
                pass


@app.task(
    bind=True,
    name="process_asr",
    queue="priority_high",
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    autoretry_for=(Exception,),
)
def process_asr(self, meeting_id: str, audio_url: Optional[str] = None):
    """ASR processing task with speaker diarization.

    1. Download audio from MinIO to local temp file (if no public URL)
    2. Upload to DashScope file storage to get a publicly accessible URL
    3. Submit async ASR job to Paraformer
    4. Poll until completion
    5. Create subtitle records from results
    6. Record token usage
    """
    logger.warning(
        f"[ASR] Task started: meeting={meeting_id}, "
        f"retry={self.request.retries}/{self.max_retries}",
    )
    try:
        result = asyncio.run(_run_asr(meeting_id, audio_url, self.request.id))
        _redis_instances.clear()
        return result
    except Exception as exc:
        logger.warning(
            f"[ASR] Exception caught: {exc}\n{traceback.format_exc()}",
        )
        # Always release the lock so future manual retries can proceed
        try:
            asyncio.run(
                cache_service.release_task_lock(meeting_id, "asr"),
            )
        finally:
            _redis_instances.clear()

        if self.request.retries >= self.max_retries:
            logger.warning(f"[ASR] Max retries reached, marking as failed")
            try:
                asyncio.run(
                    _mark_failed(meeting_id, task_id=None, error=str(exc)),
                )
            finally:
                _redis_instances.clear()
            return None
        logger.warning(f"[ASR] Retrying in {self.default_retry_delay}s")
        raise self.retry(exc=exc)
