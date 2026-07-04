"""Translation record model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Translation(Base, UUIDMixin):
    __tablename__ = "translations"

    subtitle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subtitles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(128), nullable=False)
    token_count_input: Mapped[int] = mapped_column(Integer, default=0)
    token_count_output: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    translation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
