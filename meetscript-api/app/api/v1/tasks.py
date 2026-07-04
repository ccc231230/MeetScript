"""Task management routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.schemas.task import TaskListOut, TaskOut, TaskRetryResponse
from app.services.task_service import task_service

router = APIRouter()


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, uuid.UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut.model_validate(task)


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, uuid.UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Task logs would be stored in Redis or a dedicated log table.
    # For now return the task status as the "log".
    return {
        "task_id": str(task.id),
        "logs": [
            {
                "timestamp": task.created_at.isoformat() if task.created_at else None,
                "level": "INFO",
                "message": f"Task {task.task_type}: {task.status} (progress: {task.progress}%)",
            }
        ],
    }


@router.post("/{task_id}/retry", response_model=TaskRetryResponse)
async def retry_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed or DLQ task."""
    task = await task_service.get_task(db, uuid.UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ("failed", "dlq"):
        raise HTTPException(status_code=400, detail=f"Cannot retry task in status: {task.status}")

    # Re-submit the task to Celery
    from app.tasks.process_meeting import process_meeting

    celery_result = process_meeting.delay(str(task.meeting_id))

    # Update task status
    await task_service.update_task_status(
        db, task.id, "pending", progress=0, celery_task_id=celery_result.id,
    )
    await db.commit()

    return TaskRetryResponse(
        task_id=task.id,
        new_celery_task_id=celery_result.id,
        status="pending",
    )
