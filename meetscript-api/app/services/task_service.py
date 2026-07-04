"""Task orchestration service with Celery integration and Redis Pub/Sub."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis_client import get_redis
from app.models.task import MeetingTask
from app.services.cache_service import cache_service

settings = get_settings()


class TaskService:
    """Task scheduling, deduplication, priority management, and status tracking."""

    # Priority mapping
    PRIORITIES = {
        "audio_preprocess": 7,
        "asr": 8,
        "subtitle": 6,
        "translation": 5,
        "summary": 3,
        "export": 2,
    }

    # Queue routing
    QUEUE_ROUTING = {
        (7, 8, 6): "priority_high",
        (5,): "priority_normal",
        (3, 2): "priority_low",
    }

    @staticmethod
    def get_queue_for_task(task_type: str) -> str:
        """Determine which Celery queue a task type should route to."""
        for priority_range, queue in TaskService.QUEUE_ROUTING.items():
            if TaskService.PRIORITIES.get(task_type, 5) in priority_range:
                return queue
        return "priority_normal"

    @staticmethod
    async def create_task(
        db: AsyncSession,
        meeting_id: uuid.UUID,
        task_type: str,
        priority: Optional[int] = None,
    ) -> MeetingTask:
        """Create a new task record with deduplication check.

        Raises ValueError if a task of the same type is already active.
        """
        if priority is None:
            priority = TaskService.PRIORITIES.get(task_type, 5)

        # Check deduplication
        is_locked = await cache_service.acquire_task_lock(str(meeting_id), task_type)
        if not is_locked:
            raise ValueError(f"Task {task_type} already in progress for meeting {meeting_id}")

        task = MeetingTask(
            meeting_id=meeting_id,
            task_type=task_type,
            priority=priority,
            status="pending",
            progress=0,
            max_retries=settings.CELERY_TASK_MAX_RETRIES,
        )
        db.add(task)
        await db.flush()
        return task

    @staticmethod
    async def update_task_status(
        db: AsyncSession,
        task_id: uuid.UUID,
        status: str,
        progress: Optional[int] = None,
        celery_task_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[MeetingTask]:
        """Update task status and publish progress via Redis Pub/Sub."""
        result = await db.execute(select(MeetingTask).where(MeetingTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        task.status = status
        if progress is not None:
            task.progress = progress
        if celery_task_id is not None:
            task.celery_task_id = celery_task_id
        if error_message is not None:
            task.error_message = error_message

        if status == "running" and task.started_at is None:
            task.started_at = datetime.now(timezone.utc)
        if status in ("completed", "failed", "dlq"):
            task.completed_at = datetime.now(timezone.utc)

        await db.flush()

        # Publish progress via Redis Pub/Sub for SSE
        await TaskService._publish_progress(task)

        return task

    @staticmethod
    async def mark_task_dlq(
        db: AsyncSession,
        task_id: uuid.UUID,
        error_message: str,
    ) -> Optional[MeetingTask]:
        """Move a task to the Dead Letter Queue after max retries."""
        return await TaskService.update_task_status(
            db, task_id, status="dlq", error_message=error_message
        )

    @staticmethod
    async def increment_retry(
        db: AsyncSession,
        task_id: uuid.UUID,
    ) -> Optional[MeetingTask]:
        """Increment retry count for a task."""
        result = await db.execute(select(MeetingTask).where(MeetingTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        task.retry_count += 1
        task.status = "retrying"

        if task.retry_count >= task.max_retries:
            task.status = "dlq"

        await db.flush()
        await TaskService._publish_progress(task)
        return task

    @staticmethod
    async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Optional[MeetingTask]:
        """Get a task by ID."""
        result = await db.execute(select(MeetingTask).where(MeetingTask.id == task_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_tasks(
        db: AsyncSession,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List all tasks across all meetings owned by a user."""
        from sqlalchemy import func
        from app.models.meeting import Meeting

        query = (
            select(MeetingTask)
            .join(Meeting, MeetingTask.meeting_id == Meeting.id)
            .where(Meeting.user_id == user_id)
        )
        if status:
            query = query.where(MeetingTask.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(MeetingTask.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @staticmethod
    async def get_meeting_tasks(
        db: AsyncSession,
        meeting_id: uuid.UUID,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get paginated tasks for a meeting with optional filters."""
        from sqlalchemy import func

        query = select(MeetingTask).where(MeetingTask.meeting_id == meeting_id)

        if task_type:
            query = query.where(MeetingTask.task_type == task_type)
        if status:
            query = query.where(MeetingTask.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(MeetingTask.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @staticmethod
    async def _publish_progress(task: MeetingTask) -> None:
        """Publish task progress event to Redis Pub/Sub channel."""
        try:
            redis = await get_redis()
            event = {
                "task_id": str(task.id),
                "meeting_id": str(task.meeting_id),
                "task_type": task.task_type,
                "status": task.status,
                "progress": task.progress,
                "current_step": f"Task {task.task_type}: {task.status}",
                "message": task.error_message or f"{task.task_type} is {task.status}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_detail": task.error_message,
            }
            await redis.publish(f"task_progress:{task.id}", json.dumps(event))

            # Also publish to meeting-level channel for overall progress
            await redis.publish(f"meeting_progress:{task.meeting_id}", json.dumps(event))
        except Exception:
            pass  # Pub/Sub failure should not block task updates


# Singleton
task_service = TaskService()
