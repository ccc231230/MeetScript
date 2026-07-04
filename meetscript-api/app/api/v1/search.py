"""Full-text search routes."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.schemas.search import SearchResultOut
from app.services.search_service import search_service

router = APIRouter()


@router.get("/subtitles", response_model=SearchResultOut)
async def search_subtitles(
    q: str = Query(..., min_length=1),
    meeting_id: str = Query(None),
    speaker: str = Query(None),
    time_from: int = Query(None),
    time_to: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await search_service.search_subtitles(
        db,
        keyword=q,
        meeting_id=meeting_id,
        speaker_label=speaker,
        start_time_ms=time_from,
        end_time_ms=time_to,
        page=page,
        page_size=page_size,
    )
    return SearchResultOut(subtitles=result["items"], meetings=None, total=result["total"], page=page, page_size=page_size)


@router.get("/meetings", response_model=SearchResultOut)
async def search_meetings(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await search_service.search_meetings(
        db,
        keyword=q,
        page=page,
        page_size=page_size,
    )
    return SearchResultOut(subtitles=None, meetings=result["items"], total=result["total"], page=page, page_size=page_size)
