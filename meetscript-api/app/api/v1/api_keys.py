"""API Key management routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyOut
from app.services.api_key_service import api_key_service

router = APIRouter()


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys owned by the current user."""
    keys = await api_key_service.list_keys(db, uuid.UUID(user_id))
    return keys


@router.post("", response_model=ApiKeyCreatedResponse)
async def create_api_key(
    data: ApiKeyCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key. The full key is only returned once."""
    result = await api_key_service.create_key(
        db,
        user_id=uuid.UUID(user_id),
        key_name=data.key_name,
        scopes=data.scopes,
        rate_limit=data.rate_limit,
        expires_in_days=data.expires_in_days,
    )
    return result


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete an API key."""
    success = await api_key_service.delete_key(
        db,
        key_id=uuid.UUID(key_id),
        user_id=uuid.UUID(user_id),
    )
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "deleted"}
