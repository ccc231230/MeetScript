"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    meetings,
    tasks,
    subtitles,
    translations,
    models,
    token_usage,
    api_keys,
    exports,
    search,
    sse,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(subtitles.router, tags=["subtitles"])
api_router.include_router(translations.router, tags=["translations"])
api_router.include_router(models.router, prefix="/model-configs", tags=["model-configs"])
api_router.include_router(token_usage.router, prefix="/token-usage", tags=["token-usage"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(sse.router, tags=["sse"])
