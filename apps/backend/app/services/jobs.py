from __future__ import annotations

from typing import Optional
from uuid import UUID

import redis
from rq import Queue

from app.core.config import settings


def get_redis_connection() -> redis.Redis:
    """Create a Redis connection from settings."""
    kwargs = {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "decode_responses": False,
    }
    if settings.REDIS_PASSWORD:
        kwargs["password"] = settings.REDIS_PASSWORD
    return redis.Redis(**kwargs)


def get_queue(name: str = "default") -> Queue:
    conn = get_redis_connection()
    return Queue(name, connection=conn)


def enqueue_flat_request(request_id: UUID) -> str:
    """Enqueue a flat-generation request; returns job id."""
    from app.worker import run_flat_request  # local import to avoid worker import cycles

    q = get_queue("flat")
    job = q.enqueue(run_flat_request, str(request_id))
    return job.id
