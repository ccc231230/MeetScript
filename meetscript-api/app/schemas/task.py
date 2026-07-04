"""Task schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskOut(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    task_type: str
    celery_task_id: Optional[str]
    priority: int
    status: str
    progress: int
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskListOut(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    page_size: int


class TaskRetryResponse(BaseModel):
    task_id: uuid.UUID
    new_celery_task_id: str
    status: str


class TaskLogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
