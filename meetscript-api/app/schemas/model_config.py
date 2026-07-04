"""Model configuration schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelConfigCreate(BaseModel):
    model_type: str = Field(description="asr / translation / summary")
    provider: str
    model_name: str
    api_key_encrypted: str
    endpoint_url: Optional[str] = None
    parameters: Optional[dict] = None
    is_active: bool = True


class ModelConfigUpdate(BaseModel):
    model_name: Optional[str] = None
    api_key_encrypted: Optional[str] = None
    endpoint_url: Optional[str] = None
    parameters: Optional[dict] = None
    is_active: Optional[bool] = None


class ModelConfigOut(BaseModel):
    id: uuid.UUID
    model_type: str
    provider: str
    model_name: str
    endpoint_url: Optional[str]
    parameters: Optional[dict]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
