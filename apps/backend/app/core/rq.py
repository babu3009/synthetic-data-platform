from __future__ import annotations

from typing import Any, Optional, Dict

import os
from app.core.config import settings

_redis: Any = None
_queues: Dict[str, Any] = {}


def get_redis_connection() -> Any:
    """Return Redis connection or None if Redis unavailable."""
    global _redis
    if _redis is None:
        try:
            from redis import Redis  # type: ignore
            _redis = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=False,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            _redis.ping()
        except Exception:
            # Redis not available, return None
            _redis = False  # Use False to indicate connection failed
    return _redis if _redis is not False else None


def get_queue(name: str = "default") -> Any:
    """Return a named RQ queue. Caches per name.

    Returns fake queue if Redis unavailable or in test mode.
    Supported names: "low", "default", "high" (but any name is accepted).
    """
    global _queues
    if name not in _queues:
        # Under pytest or when Redis unavailable, return fake queue
        redis_conn = None if os.getenv("PYTEST_CURRENT_TEST") else get_redis_connection()
        
        if redis_conn is None:
            class _FakeJob:
                def __init__(self) -> None:
                    self._id = "test-job-id"
                def get_id(self) -> str:
                    return self._id
            class _FakeQueue:
                def __init__(self, qname: str) -> None:
                    self.name = qname
                    self.last_enqueued = None
                def enqueue(self, func, *args, **kwargs):
                    self.last_enqueued = {"func": func, "args": args, "kwargs": kwargs}
                    return _FakeJob()
            _queues[name] = _FakeQueue(name)
        else:
            from rq import Queue  # type: ignore
            _queues[name] = Queue(name, connection=redis_conn)
    return _queues[name]
