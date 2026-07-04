"""API Key management schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    key_name: str = Field(min_length=1, max_length=128)
    scopes: Optional[list[str]] = None
    rate_limit: int = Field(default=100, ge=1)
    expires_in_days: Optional[int] = Field(default=None, ge=1)


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    key_name: str
    prefix: str
    scopes: Optional[dict]
    rate_limit: int
    expires_at: Optional[datetime]
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyOut):
    api_key: str  # Full key, only shown once


class ApiKeyListOut(BaseModel):
    items: list[ApiKeyOut]
    total: int
