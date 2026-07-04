"""Redis client manager for broker, result backend, and application cache."""

from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

_redis_instances: dict[int, Optional[Redis]] = {}


async def get_redis_client(db: int = settings.REDIS_CACHE_DB) -> Redis:
    """Return a Redis client for the given database index."""
    global _redis_instances
    if db not in _redis_instances or _redis_instances[db] is None:
        _redis_instances[db] = aioredis.from_url(
            f"{settings.REDIS_URL}/{db}",
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_instances[db]  # type: ignore[return-value]


async def close_redis_connections() -> None:
    """Gracefully close all Redis connections."""
    global _redis_instances
    for client in _redis_instances.values():
        if client is not None:
            await client.close()
    _redis_instances = {}


async def get_redis(db: int = settings.REDIS_CACHE_DB) -> Redis:
    """Alias for get_redis_client - returns a Redis client for the given DB index."""
    return await get_redis_client(db)


async def publish_task_progress(task_id: str, event_data: dict) -> None:
    """Publish a task progress event via Redis Pub/Sub for SSE streaming."""
    client = await get_redis_client(db=settings.REDIS_CACHE_DB)
    import json

    await client.publish(f"task_progress:{task_id}", json.dumps(event_data, default=str))
