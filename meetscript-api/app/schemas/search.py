"""Search schemas."""

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class SubtitleSearchResult(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    meeting_title: str
    speaker_label: str
    start_time_ms: int
    end_time_ms: int
    text: str
    headline: str  # Highlighted text snippet from ts_headline
    rank: float

    model_config = {"from_attributes": True}


class MeetingSearchResult(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    headline: str  # Highlighted snippet
    rank: float

    model_config = {"from_attributes": True}


class SearchResultOut(BaseModel):
    subtitles: Optional[list[SubtitleSearchResult]] = None
    meetings: Optional[list[MeetingSearchResult]] = None
    total: int
    page: int
    page_size: int
