"""Meeting schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: Optional[str] = Field(default=None, max_length=2048)
    source_language: str = Field(default="zh")
    file_path: Optional[str] = Field(default=None)
    file_type: str
    file_size_bytes: int = 0
    duration_seconds: Optional[int] = None


class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=512)
    description: Optional[str] = Field(default=None, max_length=2048)


class MeetingOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: Optional[str]
    source_language: str
    file_path: str
    file_type: str
    file_size_bytes: int
    duration_seconds: Optional[int]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MeetingListOut(BaseModel):
    items: list[MeetingOut]
    total: int
    page: int
    page_size: int


class UploadSignUrlRequest(BaseModel):
    file_name: str
    content_type: str = "application/octet-stream"
    file_size: int


class UploadSignUrlResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int = 3600


class UploadCompleteRequest(BaseModel):
    object_key: str
    parts: Optional[list[dict]] = None  # [{PartNumber: int, ETag: str}]
