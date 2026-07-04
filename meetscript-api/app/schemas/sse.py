"""SSE (Server-Sent Events) protocol schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaskProgressEvent(BaseModel):
    """SSE event pushed to the frontend during task processing."""

    task_id: str
    meeting_id: str
    task_type: str  # audio_preprocess / asr / translation / summary
    status: str  # pending / running / completed / failed / dlq
    progress: int  # 0-100
    current_step: str  # e.g. "正在进行语音识别 (45%)"
    message: str  # Detailed message
    timestamp: datetime  # ISO 8601
    error_detail: Optional[str] = None  # Set on failure


class MeetingProgressEvent(BaseModel):
    """SSE event for overall meeting processing progress."""

    meeting_id: str
    overall_progress: int  # 0-100
    current_task: Optional[str] = None
    tasks: list[TaskProgressEvent]
    timestamp: datetime
