"""Translation schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TranslationOut(BaseModel):
    id: uuid.UUID
    subtitle_id: uuid.UUID
    meeting_id: uuid.UUID
    target_language: str
    translated_text: str
    model_used: str
    token_count_input: int
    token_count_output: int
    cost: float
    created_at: datetime

    model_config = {"from_attributes": True}


class TranslationListOut(BaseModel):
    items: list[TranslationOut]
    total: int
    page: int
    page_size: int


class TranslationUpdate(BaseModel):
    translated_text: str


class TranslationRequest(BaseModel):
    meeting_id: uuid.UUID
    target_languages: list[str] = Field(min_length=1)
    model_name: Optional[str] = None


class BatchTranslationOut(BaseModel):
    meeting_id: uuid.UUID
    target_language: str
    translation_count: int
    cached_count: int
    new_count: int
    status: str
