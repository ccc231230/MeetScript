"""Translation routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.models.translation import Translation
from app.schemas.translation import TranslationListOut, TranslationOut, TranslationRequest, TranslationUpdate
from app.services.translation_service import translation_service

router = APIRouter()


@router.get("/meetings/{meeting_id}/translations", response_model=TranslationListOut)
async def get_translations(
    meeting_id: str,
    lang: str = Query("en"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    query = select(Translation).where(
        Translation.meeting_id == uuid.UUID(meeting_id),
        Translation.target_language == lang,
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Translation.created_at)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return TranslationListOut(
        items=[TranslationOut.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/translations/{translation_id}", response_model=TranslationOut)
async def update_translation(
    translation_id: str,
    body: TranslationUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually edit a translation's text (e.g., post-editing by a human reviewer)."""
    result = await db.execute(
        select(Translation).where(Translation.id == uuid.UUID(translation_id))
    )
    translation = result.scalar_one_or_none()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    if not body.translated_text.strip():
        raise HTTPException(status_code=400, detail="Translated text cannot be empty")

    translation.translated_text = body.translated_text
    await db.flush()
    await db.commit()

    return TranslationOut.model_validate(translation)


@router.post("/translations")
async def request_translation(
    body: TranslationRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Trigger translation for a meeting (async via Celery)."""
    from app.tasks.translation_task import process_translation

    result = process_translation.delay(str(body.meeting_id), body.target_languages)
    return {
        "task_id": result.id,
        "meeting_id": str(body.meeting_id),
        "target_languages": body.target_languages,
        "status": "processing",
    }
