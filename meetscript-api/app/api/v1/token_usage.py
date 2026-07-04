"""Token usage routes."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.models.model_config import ModelConfig
from app.models.token_usage import TokenUsage
from app.schemas.token_usage import TokenUsageListOut, TokenUsageOut, TokenUsageStats
from app.utils.token_counter import format_cost

router = APIRouter()


@router.get("", response_model=TokenUsageListOut)
async def get_token_usage(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    operation_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(TokenUsage).where(TokenUsage.user_id == uuid.UUID(user_id))
    if operation_type:
        query = query.where(TokenUsage.operation_type == operation_type)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(TokenUsage.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return TokenUsageListOut(
        items=[TokenUsageOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=TokenUsageStats)
async def get_token_usage_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    period_start = datetime.now(timezone.utc) - timedelta(days=days)
    period_end = datetime.now(timezone.utc)

    query = select(TokenUsage).where(
        TokenUsage.user_id == uuid.UUID(user_id),
        TokenUsage.created_at >= period_start,
        TokenUsage.created_at <= period_end,
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    # Aggregate stats
    total_tokens = sum(i.tokens_total for i in items)
    total_cost = sum(i.cost for i in items)

    by_operation: dict[str, dict] = {}
    by_model: dict[str, dict] = {}

    for item in items:
        # By operation type
        op = item.operation_type
        if op not in by_operation:
            by_operation[op] = {"tokens": 0, "cost": 0.0}
        by_operation[op]["tokens"] += item.tokens_total
        by_operation[op]["cost"] += round(item.cost, 6)

        # By model — use operation_type as proxy if model_config_id is null
        model_key = item.operation_type or "unknown"
        if item.model_config_id:
            # Resolve model name from model_configs table
            cfg_result = await db.execute(
                select(ModelConfig.model_name).where(ModelConfig.id == item.model_config_id)
            )
            cfg_name = cfg_result.scalar_one_or_none()
            if cfg_name:
                model_key = cfg_name

        if model_key not in by_model:
            by_model[model_key] = {"tokens": 0, "cost": 0.0}
        by_model[model_key]["tokens"] += item.tokens_total
        by_model[model_key]["cost"] += round(item.cost, 6)

    return TokenUsageStats(
        total_tokens=total_tokens,
        total_cost=round(total_cost, 4),
        by_operation=by_operation,
        by_model=by_model,
        period_start=period_start,
        period_end=period_end,
    )
