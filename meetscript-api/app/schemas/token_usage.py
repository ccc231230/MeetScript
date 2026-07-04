"""Token usage schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TokenUsageOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    meeting_id: Optional[uuid.UUID]
    model_config_id: Optional[uuid.UUID]
    operation_type: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost: float
    request_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenUsageStats(BaseModel):
    total_tokens: int
    total_cost: float
    by_operation: dict[str, dict]  # {asr: {tokens: N, cost: M}, ...}
    by_model: dict[str, dict]
    period_start: datetime
    period_end: datetime


class TokenUsageListOut(BaseModel):
    items: list[TokenUsageOut]
    total: int
    page: int
    page_size: int
