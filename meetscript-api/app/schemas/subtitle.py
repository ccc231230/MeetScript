"""Subtitle schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SubtitleOut(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    speaker_label: str
    language: str
    start_time_ms: int
    end_time_ms: int
    text: str
    is_candidate: bool
    confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}


class SubtitleListOut(BaseModel):
    items: list[SubtitleOut]
    total: int
    page: int
    page_size: int


class SubtitleUpdate(BaseModel):
    speaker_label: Optional[str] = None
    text: Optional[str] = None
    is_candidate: Optional[bool] = None


class SubtitleExportRequest(BaseModel):
    meeting_id: uuid.UUID
    format: str = Field(default="srt")  # srt / vtt / json / txt
    language: Optional[str] = None
    speaker_filter: Optional[str] = None
