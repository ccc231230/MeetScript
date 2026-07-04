"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import get_settings
from app.core.database import close_db_connection

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: startup and shutdown handlers."""
    # Startup: nothing to init eagerly (lazy connections)
    yield
    # Shutdown: gracefully close connections
    await close_db_connection()
    from app.core.redis_client import close_redis_connections

    await close_redis_connections()


def create_app() -> FastAPI:
    """Factory: build and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise Meeting Minutes Platform - API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Middleware ────────────────────────────────────────────────
    from app.middleware.request_id import RequestIDMiddleware
    from app.middleware.access_log import AccessLogMiddleware
    from app.middleware.rate_limit import RateLimitMiddleware

    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(AccessLogMiddleware)

    # ── Prometheus Metrics ────────────────────────────────────────
    if settings.PROMETHEUS_ENABLED:
        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_instrument_requests_inprogress=True,
        )
        instrumentator.instrument(application).expose(application, endpoint="/metrics")

    # ── Routes ────────────────────────────────────────────────────
    from app.api.v1.router import api_router

    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ── Health Check ──────────────────────────────────────────────
    @application.get("/api/v1/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "version": settings.APP_VERSION}

    return application


app = create_app()
