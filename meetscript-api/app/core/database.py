"""Database connection pool and session management."""

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> str:
    """Return the database URL, ensuring asyncpg driver for async mode."""
    url = settings.DATABASE_URL.get_secret_value()
    # Only add +asyncpg if not already present
    if "+asyncpg" not in url:
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def get_engine() -> AsyncEngine:
    """Create or return the async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        is_dev = settings.ENVIRONMENT == "development"
        engine_kwargs = {
            "echo": settings.DB_ECHO,
            "pool_pre_ping": True,
        }
        if is_dev:
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
            engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        _engine = create_async_engine(get_database_url(), **engine_kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create or return the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_connection() -> None:
    """Gracefully dispose the engine (called on application shutdown)."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
