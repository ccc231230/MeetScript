"""User management routes."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id

router = APIRouter()


@router.get("/me")
async def get_current_user(user_id: str = Depends(get_current_user_id)):
    """Return the currently authenticated user's profile."""
    return {"user_id": user_id, "message": "User profile endpoint (stub)"}
