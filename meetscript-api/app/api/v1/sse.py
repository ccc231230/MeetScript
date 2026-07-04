"""SSE (Server-Sent Events) real-time task progress endpoint."""

import asyncio
import json

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.core.redis_client import get_redis_client

router = APIRouter()


async def _sse_channel_stream(
    request: Request,
    channels: list[str],
    stop_states: set[str] = None,
) -> str:
    """Generic SSE event generator from Redis Pub/Sub channels."""
    if stop_states is None:
        stop_states = {"completed", "failed", "dlq"}

    redis = await get_redis_client()
    pubsub = redis.pubsub()
    await pubsub.subscribe(*channels)
    try:
        while True:
            # Use get_message with timeout to allow disconnect checks
            message = await pubsub.get_message(timeout=2.0)
            if message is None:
                if await request.is_disconnected():
                    break
                yield ": heartbeat\n\n"
                continue

            if message["type"] == "message":
                data = json.loads(message["data"])
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("status") in stop_states:
                    break
            if await request.is_disconnected():
                break
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(*channels)


@router.get("/tasks/{task_id}/stream")
async def task_progress_stream(task_id: str, request: Request):
    """Subscribe to a single task's progress via Redis Pub/Sub and stream as SSE."""
    return StreamingResponse(
        _sse_channel_stream(request, [f"task_progress:{task_id}"]),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/meetings/{meeting_id}/stream")
async def meeting_progress_stream(
    meeting_id: str,
    request: Request,
    task_id: str = Query(None, description="Optional: also subscribe to a specific task"),
):
    """Subscribe to all task progress events for a meeting, plus optionally a specific task."""
    channels = [f"meeting_progress:{meeting_id}"]
    if task_id:
        channels.append(f"task_progress:{task_id}")

    return StreamingResponse(
        _sse_channel_stream(request, channels),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
