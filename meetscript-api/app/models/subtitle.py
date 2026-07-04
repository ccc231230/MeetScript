"""Subtitle model with full-text search support."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Computed, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Subtitle(Base, UUIDMixin):
    __tablename__ = "subtitles"
    __table_args__ = (
        Index("idx_subtitles_meeting_time", "meeting_id", "start_time_ms"),
        Index("idx_subtitles_meeting_speaker", "meeting_id", "speaker_label"),
        Index("idx_subtitles_text_search", "text_search_vector", postgresql_using="gin"),
    )

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    speaker_label: Mapped[str] = mapped_column(String(64), default="SPEAKER_00", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="zh", nullable=False)
    start_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    text_search_vector: Mapped[str | None] = mapped_column(
        "text_search_vector",
        TSVECTOR,
        Computed("to_tsvector('simple'::regconfig, text)", persisted=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
