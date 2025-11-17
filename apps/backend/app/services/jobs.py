from __future__ import annotations

from typing import Optional
from uuid import UUID

from typing import Optional, Any

from app.core.config import settings


def get_redis_connection() -> Optional[Any]:
    """Create a Redis connection from settings. Returns None if Redis unavailable."""
    try:
        import redis
        kwargs = {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "decode_responses": False,
            "socket_connect_timeout": 2,
            "socket_timeout": 2,
        }
        if settings.REDIS_PASSWORD:
            kwargs["password"] = settings.REDIS_PASSWORD
        conn = redis.Redis(**kwargs)
        conn.ping()  # Test connection
        return conn
    except Exception:
        return None


def get_queue(name: str = "default") -> Any:
    """Get queue, returns fake queue if Redis unavailable."""
    conn = get_redis_connection()
    if conn is None:
        # Return fake queue
        class _FakeJob:
            def __init__(self):
                self.id = "fake-job-id"
        class _FakeQueue:
            def __init__(self, qname: str):
                self.name = qname
            def enqueue(self, func, *args, **kwargs):
                return _FakeJob()
        return _FakeQueue(name)
    else:
        from rq import Queue
        return Queue(name, connection=conn)


def enqueue_flat_request(request_id: UUID) -> str:
    """Enqueue a flat-generation request; returns job id."""
    from app.worker import run_flat_request  # local import to avoid worker import cycles

    q = get_queue("flat")
    job = q.enqueue(run_flat_request, str(request_id))
    return job.id
