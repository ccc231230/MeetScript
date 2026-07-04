"""API Key model for external API authentication."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ApiKey(Base, UUIDMixin):
    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    scopes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rate_limit: Mapped[int] = mapped_column(Integer, default=100)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
