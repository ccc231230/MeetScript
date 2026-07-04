"""Audit logging service for security tracking."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    """Records structured audit logs for all critical operations."""

    @staticmethod
    async def log(
        db: AsyncSession,
        user_id: Optional[uuid.UUID],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        db.add(audit)
        await db.flush()
        return audit

    @staticmethod
    async def query_logs(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Query audit logs with filters."""
        query = select(AuditLog)

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if start_time:
            query = query.where(AuditLog.created_at >= start_time)
        if end_time:
            query = query.where(AuditLog.created_at <= end_time)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    # ── Convenience Loggers ────────────────────────────────────────

    @staticmethod
    async def log_meeting_created(
        db: AsyncSession,
        user_id: uuid.UUID,
        meeting_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        return await AuditService.log(
            db, user_id, "meeting.created", "meeting", str(meeting_id), ip_address
        )

    @staticmethod
    async def log_task_started(
        db: AsyncSession,
        user_id: uuid.UUID,
        task_id: uuid.UUID,
        meeting_id: uuid.UUID,
        task_type: str,
    ) -> AuditLog:
        return await AuditService.log(
            db, user_id, "task.started", "task", str(task_id),
            details={"meeting_id": str(meeting_id), "task_type": task_type},
        )

    @staticmethod
    async def log_api_call(
        db: AsyncSession,
        user_id: uuid.UUID,
        endpoint: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        return await AuditService.log(
            db, user_id, f"api.{endpoint}", "api", endpoint,
            ip_address=ip_address, user_agent=user_agent,
        )


# Singleton
audit_service = AuditService()
