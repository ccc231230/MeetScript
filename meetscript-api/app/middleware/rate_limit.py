"""Middleware: rate limiting using Redis sliding-window counters."""

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.services.cache_service import cache_service

logger = structlog.get_logger()
settings = get_settings()

# Paths exempt from rate limiting
EXEMPT_PATHS = {
    "/api/v1/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Default rate limits by path prefix
PATH_LIMITS = {
    "/api/v1/auth/login": 10,
    "/api/v1/auth/refresh": 10,
    "/api/v1/auth/register": 5,
    "/api/v1/meetings/upload/": 30,
    "/api/v1/search/": 60,
    "/api/v1/sse/": 0,  # SSE has its own connection limits
    "default": 100,
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based sliding-window rate limiter.

    Uses a 1-minute window. Clients exceeding the limit receive HTTP 429.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path
        method = request.method

        # Skip exempt paths
        if path in EXEMPT_PATHS:
            return await call_next(request)

        # Determine user/client identity
        # Prefer JWT user_id, fall back to client IP
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            user_id = request.client.host if request.client else "anonymous"

        # Determine rate limit for this path
        limit = PATH_LIMITS.get("default", 100)
        for prefix, path_limit in PATH_LIMITS.items():
            if path.startswith(prefix) and prefix != "default":
                limit = path_limit
                break

        # SSE endpoints are handled separately
        if limit == 0:
            return await call_next(request)

        # Check rate limit
        endpoint_key = f"{method}:{path}"
        is_under_limit = await cache_service.check_rate_limit(
            str(user_id), endpoint_key, limit=limit,
        )

        if not is_under_limit:
            logger.warning(
                "rate_limit_exceeded",
                user_id=str(user_id),
                path=path,
                method=method,
                limit=limit,
            )
            return Response(
                content='{"detail":"Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
