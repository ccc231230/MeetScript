"""Meeting management service."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting


class MeetingService:
    """Meeting CRUD and lifecycle management."""

    @staticmethod
    async def create_meeting(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        file_path: str,
        file_type: str,
        description: Optional[str] = None,
        source_language: str = "zh",
        file_size_bytes: int = 0,
        duration_seconds: Optional[int] = None,
    ) -> Meeting:
        """Create a new meeting record."""
        meeting = Meeting(
            user_id=user_id,
            title=title,
            description=description,
            source_language=source_language,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            duration_seconds=duration_seconds,
            status="uploaded",
        )
        db.add(meeting)
        await db.flush()
        return meeting

    @staticmethod
    async def get_meeting(
        db: AsyncSession,
        meeting_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Meeting]:
        """Get a meeting by ID, optionally scoped to user."""
        query = select(Meeting).where(Meeting.id == meeting_id)
        if user_id:
            query = query.where(Meeting.user_id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_meetings(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List meetings with optional filters."""
        query = select(Meeting)

        if user_id:
            query = query.where(Meeting.user_id == user_id)
        if status:
            query = query.where(Meeting.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Meeting.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    @staticmethod
    async def update_meeting(
        db: AsyncSession,
        meeting_id: uuid.UUID,
        **kwargs,
    ) -> Optional[Meeting]:
        """Update meeting fields."""
        result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = result.scalar_one_or_none()
        if not meeting:
            return None

        for key, value in kwargs.items():
            if hasattr(meeting, key) and value is not None:
                setattr(meeting, key, value)

        await db.flush()
        return meeting

    @staticmethod
    async def update_status(
        db: AsyncSession,
        meeting_id: uuid.UUID,
        status: str,
    ) -> Optional[Meeting]:
        """Update meeting processing status."""
        allowed = {"uploaded", "preprocessing", "processing", "completed", "failed"}
        if status not in allowed:
            raise ValueError(f"Invalid status: {status}. Must be one of {allowed}")

        result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = result.scalar_one_or_none()
        if not meeting:
            return None

        meeting.status = status
        await db.flush()
        return meeting

    @staticmethod
    async def delete_meeting(
        db: AsyncSession,
        meeting_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Delete a meeting (cascades to subtitles, translations, etc.)."""
        query = select(Meeting).where(Meeting.id == meeting_id)
        if user_id:
            query = query.where(Meeting.user_id == user_id)

        result = await db.execute(query)
        meeting = result.scalar_one_or_none()
        if not meeting:
            return False

        await db.delete(meeting)
        await db.flush()
        return True


# Singleton
meeting_service = MeetingService()
