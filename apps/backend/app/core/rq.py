from __future__ import annotations

from typing import Any, Optional, Dict

from app.core.config import settings

_redis: Any = None
_queues: Dict[str, Any] = {}


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
    """Return a named RQ queue. Caches per name.

    Supported names: "low", "default", "high" (but any name is accepted).
    """
    global _queues
    if name not in _queues:
        from rq import Queue  # type: ignore

        _queues[name] = Queue(name, connection=get_redis_connection())
    return _queues[name]
