from __future__ import annotations

from typing import Any, Optional

from app.core.config import settings

_redis: Any = None
_queue: Any = None


def get_redis_connection() -> Any:
    global _redis
    if _redis is None:
        # Import lazily to avoid optional dependency issues in static analysis
        from redis import Redis  # type: ignore

        _redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=False,
        )
    return _redis


def get_queue(name: str = "default") -> Any:
    global _queue
    if _queue is None:
        from rq import Queue  # type: ignore

        _queue = Queue(name, connection=get_redis_connection())
    return _queue
