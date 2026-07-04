"""PostgreSQL full-text search service."""

import uuid
from typing import Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.models.subtitle import Subtitle


class SearchService:
    """Full-text search using PostgreSQL GIN indexes."""

    @staticmethod
    async def search_subtitles(
        db: AsyncSession,
        keyword: str,
        meeting_id: Optional[str] = None,
        speaker_label: Optional[str] = None,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search subtitles with optional filters. Returns paginated results with highlights."""
        ts_query = func.websearch_to_tsquery("simple", keyword)

        # "simple" config treats CJK text as single token → tsquery never matches.
        # Combine tsquery with ILIKE so both space-separated and CJK languages work.
        ilike_pattern = f"%{keyword}%"

        # Build query
        query = (
            select(
                Subtitle.id,
                Subtitle.meeting_id,
                Meeting.title.label("meeting_title"),
                Subtitle.speaker_label,
                Subtitle.start_time_ms,
                Subtitle.end_time_ms,
                Subtitle.text,
                func.ts_headline(
                    "simple",
                    Subtitle.text,
                    ts_query,
                    "StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=10",
                ).label("headline"),
                func.ts_rank(Subtitle.text_search_vector, ts_query).label("rank"),
            )
            .join(Meeting, Subtitle.meeting_id == Meeting.id)
            .where(
                or_(
                    Subtitle.text_search_vector.op("@@")(ts_query),
                    Subtitle.text.ilike(ilike_pattern),
                )
            )
        )

        if meeting_id:
            query = query.where(Subtitle.meeting_id == meeting_id)
        if speaker_label:
            query = query.where(Subtitle.speaker_label == speaker_label)
        if start_time_ms is not None:
            query = query.where(Subtitle.start_time_ms >= start_time_ms)
        if end_time_ms is not None:
            query = query.where(Subtitle.end_time_ms <= end_time_ms)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        query = query.order_by(text("rank DESC"), Subtitle.start_time_ms)
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        rows = result.all()

        items = [
            {
                "id": row[0],
                "meeting_id": row[1],
                "meeting_title": row[2],
                "speaker_label": row[3],
                "start_time_ms": row[4],
                "end_time_ms": row[5],
                "text": row[6],
                "headline": row[7],
                "rank": float(row[8]) if row[8] else 0.0,
            }
            for row in rows
        ]

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @staticmethod
    async def search_meetings(
        db: AsyncSession,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search meetings by title and description."""
        ts_query = func.websearch_to_tsquery("simple", keyword)
        ilike_pattern = f"%{keyword}%"

        query = (
            select(
                Meeting.id,
                Meeting.title,
                Meeting.description,
                func.ts_headline(
                    "simple",
                    func.coalesce(Meeting.title, "") + " " + func.coalesce(Meeting.description, ""),
                    ts_query,
                    "StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=10",
                ).label("headline"),
                func.ts_rank(Meeting.search_vector, ts_query).label("rank"),
            )
            .where(
                or_(
                    Meeting.search_vector.op("@@")(ts_query),
                    Meeting.title.ilike(ilike_pattern),
                )
            )
        )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(text("rank DESC")).offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        rows = result.all()

        items = [
            {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "headline": row[3],
                "rank": float(row[4]) if row[4] else 0.0,
            }
            for row in rows
        ]

        return {"items": items, "total": total, "page": page, "page_size": page_size}


# Singleton
search_service = SearchService()
