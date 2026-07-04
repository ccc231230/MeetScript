"""Subtitle retrieval routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.schemas.subtitle import SubtitleListOut, SubtitleOut
from app.services.subtitle_service import subtitle_service

router = APIRouter()


@router.get("/meetings/{meeting_id}/subtitles", response_model=SubtitleListOut)
async def get_subtitles(
    meeting_id: str,
    format: str = Query("json", pattern="^(json|vtt|srt)$"),
    lang: str = Query("zh"),
    speaker: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await subtitle_service.get_meeting_subtitles(
        db,
        uuid.UUID(meeting_id),
        language=lang if lang else None,
        speaker_label=speaker,
        page=page,
        page_size=page_size,
    )

    if format == "srt":
        from fastapi.responses import PlainTextResponse
        srt_content = subtitle_service.generate_srt(result["items"])
        return PlainTextResponse(content=srt_content, media_type="text/plain")
    elif format == "vtt":
        from fastapi.responses import PlainTextResponse
        vtt_content = subtitle_service.generate_vtt(result["items"])
        return PlainTextResponse(content=vtt_content, media_type="text/vtt")

    return SubtitleListOut(
        items=[SubtitleOut.model_validate(s) for s in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
