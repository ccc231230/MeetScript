"""Meeting management routes."""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db, get_user_id_from_api_key
from app.schemas.meeting import (
    MeetingCreate,
    MeetingListOut,
    MeetingOut,
    MeetingUpdate,
    UploadCompleteRequest,
    UploadSignUrlRequest,
    UploadSignUrlResponse,
)
from app.services.file_service import file_service
from app.services.meeting_service import meeting_service
from app.services.audit_service import audit_service
from app.core.config import get_settings

settings = get_settings()

router = APIRouter()


@router.get("", response_model=MeetingListOut)
async def list_meetings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    result = await meeting_service.list_meetings(
        db,
        user_id=uuid.UUID(user_id),
        status=status,
        page=page,
        page_size=page_size,
    )
    return MeetingListOut(**result)


@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
    meeting_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    meeting = await meeting_service.get_meeting(
        db, uuid.UUID(meeting_id), user_id=uuid.UUID(user_id),
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return MeetingOut.model_validate(meeting)


@router.post("/upload/sign-url", response_model=UploadSignUrlResponse)
async def get_upload_sign_url(
    body: UploadSignUrlRequest,
    user_id: str = Depends(get_current_user_id),
):
    result = await file_service.get_upload_url(user_id, body.file_name, body.content_type)
    return UploadSignUrlResponse(**result)


@router.post("/upload/file", response_model=UploadSignUrlResponse)
async def upload_file_direct(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """Upload a file directly through the backend (bypasses presigned URL issues).

    Uses streaming upload to MinIO to avoid loading large files entirely into memory.
    """
    # Validate file size before reading anything
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file.file.seek(0, 2)  # seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # reset to beginning

    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大，最大允许 {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="文件为空，请选择有效的文件",
        )

    # Validate file extension
    ext = os.path.splitext(file.filename or "unknown.bin")[1].lstrip(".").lower()
    if ext not in settings.ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: .{ext}。支持格式: {', '.join(settings.ALLOWED_AUDIO_EXTENSIONS)}",
        )

    try:
        result = await file_service.upload_file_stream(
            user_id,
            file.file,
            file.filename or "upload",
            file.content_type or "application/octet-stream",
            file_size=file_size,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}",
        )

    return UploadSignUrlResponse(
        upload_url=result["url"],
        object_key=result["object_key"],
        expires_in=3600,
    )


@router.post("/upload/complete", status_code=status.HTTP_201_CREATED)
async def complete_upload(
    body: UploadCompleteRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Notify server that a file upload (possibly multipart) has completed."""
    # Validate the object exists in storage
    download_url = await file_service.get_download_url(body.object_key)
    return {"object_key": body.object_key, "download_url": download_url, "status": "ready"}


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    body: MeetingCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    meeting = await meeting_service.create_meeting(
        db,
        user_id=uuid.UUID(user_id),
        title=body.title,
        file_path=body.file_path or f"meetings/{user_id}/{body.title}",
        file_type=body.file_type,
        description=body.description,
        source_language=body.source_language,
        file_size_bytes=body.file_size_bytes,
        duration_seconds=body.duration_seconds,
    )
    await audit_service.log_meeting_created(db, uuid.UUID(user_id), meeting.id)
    await db.commit()
    return MeetingOut.model_validate(meeting)


@router.get("/{meeting_id}/media")
async def get_media(
    meeting_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Stream the meeting's media file for browser playback with Range support."""
    meeting = await meeting_service.get_meeting(
        db, uuid.UUID(meeting_id), user_id=uuid.UUID(user_id),
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    content_type_map = {
        "video": "video/mp4",
        "audio": "audio/mpeg",
    }
    media_type = content_type_map.get(meeting.file_type, "application/octet-stream")

    # Get file size from storage
    file_size = await file_service.get_file_size(meeting.file_path)
    if file_size is None:
        raise HTTPException(status_code=404, detail="Media file not found in storage")

    range_header = request.headers.get("range")

    if range_header:
        return _stream_range(meeting.file_path, media_type, file_size, range_header)
    else:
        return StreamingResponse(
            file_service.stream_file(meeting.file_path),
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )


def _parse_range_header(range_header: str, file_size: int) -> Optional[tuple[int, int]]:
    """Parse HTTP Range header, return (start, end) inclusive."""
    unit, _, range_spec = range_header.partition("=")
    if unit.strip() != "bytes":
        return None
    range_spec = range_spec.split(",")[0].strip()
    try:
        if range_spec.startswith("-"):
            suffix = int(range_spec[1:])
            if suffix <= 0:
                return None
            start = max(0, file_size - suffix)
            end = file_size - 1
        elif range_spec.endswith("-"):
            start = int(range_spec[:-1])
            end = file_size - 1
        else:
            start_str, end_str = range_spec.split("-", 1)
            start = int(start_str)
            end = int(end_str)
    except (ValueError, OverflowError):
        return None
    if start < 0 or start >= file_size or end < start:
        return None
    return (start, min(end, file_size - 1))


def _stream_range(object_key: str, media_type: str, file_size: int, range_header: str) -> StreamingResponse:
    """Stream a byte range of the file."""
    range_parsed = _parse_range_header(range_header, file_size)
    if range_parsed is None:
        return StreamingResponse(
            file_service.stream_file(object_key),
            media_type=media_type,
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    start, end = range_parsed

    async def range_generator():
        offset = 0
        async for chunk in file_service.stream_file(object_key):
            chunk_end = offset + len(chunk) - 1
            # Check if this chunk overlaps with requested range
            if chunk_end < start:
                offset += len(chunk)
                continue
            if offset > end:
                break
            # Calculate slice boundaries
            chunk_start_inner = max(0, start - offset)
            chunk_end_inner = min(len(chunk), end - offset + 1)
            if chunk_start_inner < chunk_end_inner:
                yield chunk[chunk_start_inner:chunk_end_inner]
            offset += len(chunk)

    content_length = end - start + 1

    return StreamingResponse(
        range_generator(),
        media_type=media_type,
        status_code=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        },
    )


@router.post("/{meeting_id}/process")
async def process_meeting(
    meeting_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the meeting processing Celery chain."""
    meeting = await meeting_service.get_meeting(
        db, uuid.UUID(meeting_id), user_id=uuid.UUID(user_id),
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    from app.tasks.process_meeting import process_meeting as process_task

    result = process_task.delay(meeting_id)

    await audit_service.log_task_started(
        db, uuid.UUID(user_id), uuid.UUID(result.id), meeting.id, "full_pipeline",
    )
    await db.commit()

    return {"task_id": result.id, "meeting_id": meeting_id, "status": "processing"}


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    deleted = await meeting_service.delete_meeting(
        db, uuid.UUID(meeting_id), user_id=uuid.UUID(user_id),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await db.commit()


# ── External API Integration ────────────────────────────────────────

from fastapi import UploadFile, File
from pydantic import BaseModel as PydanticBaseModel, Field


class ExternalMeetingCreate(PydanticBaseModel):
    """Meeting creation payload for third-party API integration."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_language: str = Field(default="zh", pattern=r"^(zh|en|ja|ko|fr|de|es)$")
    file_type: str | None = Field(default=None, pattern=r"^(video|audio)$")
    target_languages: list[str] | None = Field(default=None)
    callback_url: str | None = Field(default=None, max_length=2048)


class ExternalMeetingResponse(PydanticBaseModel):
    id: str
    title: str
    status: str
    task_id: str
    message: str


@router.post(
    "/external/submit",
    response_model=ExternalMeetingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a meeting via API Key (third-party integration)",
    description="Submit a meeting file and trigger the full processing pipeline using API key authentication.",
)
async def external_submit_meeting(
    file: UploadFile = File(..., description="Meeting audio/video file"),
    body: ExternalMeetingCreate = Depends(),
    user_id: str = Depends(get_user_id_from_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Third-party API integration endpoint.

    Authenticate with an API key in the Authorization: Bearer header.
    Upload a meeting file and automatically trigger processing.
    """
    import os

    # Validate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    # Validate file extension
    ext = os.path.splitext(file.filename or "unknown.bin")[1].lstrip(".").lower()
    if ext not in settings.ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Allowed: {', '.join(settings.ALLOWED_AUDIO_EXTENSIONS)}",
        )

    # Upload file to storage
    upload_result = await file_service.upload_file(
        user_id,
        await file.read(),
        file.filename or "meeting_upload",
        file.content_type or "application/octet-stream",
    )

    # Determine file type
    file_type = body.file_type or ("video" if ext in {"mp4", "avi", "mov", "mkv", "webm", "flv", "wmv"} else "audio")

    # Create meeting record
    meeting = await meeting_service.create_meeting(
        db,
        user_id=uuid.UUID(user_id),
        title=body.title,
        file_path=upload_result["object_key"],
        file_type=file_type,
        description=body.description,
        source_language=body.source_language,
        file_size_bytes=file_size,
    )

    await audit_service.log_meeting_created(db, uuid.UUID(user_id), meeting.id)

    # Trigger processing pipeline
    from app.tasks.process_meeting import process_meeting as process_task

    celery_result = process_task.delay(str(meeting.id))

    await audit_service.log_task_started(
        db, uuid.UUID(user_id), uuid.UUID(celery_result.id), meeting.id, "external_pipeline",
    )
    await db.commit()

    return ExternalMeetingResponse(
        id=str(meeting.id),
        title=meeting.title,
        status="processing",
        task_id=celery_result.id,
        message="Meeting submitted successfully. Processing has started.",
    )
