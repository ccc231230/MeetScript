"""Export routes for subtitles and translations."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.schemas.subtitle import SubtitleExportRequest
from app.services.subtitle_service import subtitle_service

router = APIRouter()


@router.post("")
async def export_data(
    meeting_id: str = Query(...),
    format: str = Query("json", pattern="^(srt|vtt|json|txt|csv)$"),
    lang: str = Query("zh"),
    export_type: str = Query("subtitles", pattern="^(subtitles|translations)$"),
    speaker: str = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Export subtitles or translations in the requested format."""
    result = await subtitle_service.get_meeting_subtitles(
        db,
        uuid.UUID(meeting_id),
        language=lang,
        speaker_label=speaker,
        page_size=50000,  # Get all for export
    )
    subtitles = result["items"]

    if not subtitles:
        return {"message": "No data to export", "download_url": None}

    # Generate export
    from fastapi.responses import PlainTextResponse

    if format == "srt":
        content = subtitle_service.generate_srt(subtitles)
        return PlainTextResponse(content=content, media_type="text/plain",
                                 headers={"Content-Disposition": f"attachment; filename=meeting_{meeting_id}.srt"})
    elif format == "vtt":
        content = subtitle_service.generate_vtt(subtitles)
        return PlainTextResponse(content=content, media_type="text/vtt",
                                 headers={"Content-Disposition": f"attachment; filename=meeting_{meeting_id}.vtt"})
    elif format == "txt":
        content = subtitle_service.generate_txt(subtitles)
        return PlainTextResponse(content=content, media_type="text/plain",
                                 headers={"Content-Disposition": f"attachment; filename=meeting_{meeting_id}.txt"})
    else:
        content = subtitle_service.generate_json(subtitles)
        return PlainTextResponse(content=content, media_type="application/json",
                                 headers={"Content-Disposition": f"attachment; filename=meeting_{meeting_id}.json"})
