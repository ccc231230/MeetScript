"""API Key management routes."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id

router = APIRouter()


@router.get("")
async def list_api_keys(user_id: str = Depends(get_current_user_id)):
    return {"keys": [], "message": "API keys list endpoint (stub)"}


@router.post("")
async def create_api_key(user_id: str = Depends(get_current_user_id)):
    return {"key": "", "message": "Create API key endpoint (stub)"}


@router.delete("/{key_id}")
async def delete_api_key(key_id: str, user_id: str = Depends(get_current_user_id)):
    return {"key_id": key_id, "message": "Delete API key endpoint (stub)"}
