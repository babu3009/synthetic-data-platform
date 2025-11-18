from __future__ import annotations

from typing import Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class SyncJob:
    """Synchronous job that executes immediately."""
    def __init__(self, job_id: str):
        self.id = job_id


class SyncQueue:
    """Synchronous queue that executes jobs immediately (no Redis/background workers)."""
    def __init__(self, qname: str):
        self.name = qname
    
    def enqueue(self, func, *args, **kwargs):
        """Execute job synchronously."""
        import os
        
        # In test mode, don't execute - just return job
        if os.getenv("PYTEST_CURRENT_TEST"):
            return SyncJob("test-job-id")
        
        job_id = f"sync-{func.__name__}-{args[0] if args else 'unknown'}"
        logger.info(f"Executing {func.__name__} synchronously")
        try:
            func(*args)
            logger.info(f"Job {job_id} completed successfully")
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            raise
        return SyncJob(job_id)


def get_queue(name: str = "default") -> SyncQueue:
    """Get synchronous queue (no Redis required)."""
    return SyncQueue(name)


def enqueue_flat_request(request_id: UUID) -> str:
    """Enqueue a flat-generation request; returns job id."""
    from app.worker import run_flat_request  # local import to avoid worker import cycles

    q = get_queue("flat")
    job = q.enqueue(run_flat_request, str(request_id))
    return job.id
