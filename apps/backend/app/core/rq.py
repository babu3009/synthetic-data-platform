from __future__ import annotations

from typing import Any, Dict
import os
import logging

_queues: Dict[str, Any] = {}
logger = logging.getLogger(__name__)


class SyncJob:
    """Synchronous job that executes immediately."""
    def __init__(self, job_id: str) -> None:
        self._id = job_id
    
    def get_id(self) -> str:
        return self._id


class SyncQueue:
    """Synchronous queue that executes jobs immediately (no Redis/background workers)."""
    def __init__(self, qname: str) -> None:
        self.name = qname
        self.last_enqueued = None
    
    def enqueue(self, func, *args, **kwargs):
        """Execute job synchronously."""
        self.last_enqueued = {"func": func, "args": args, "kwargs": kwargs}
        
        # In test mode, don't execute - just return job
        if os.getenv("PYTEST_CURRENT_TEST"):
            return SyncJob("test-job-id")
        
        # Execute synchronously
        job_id = f"sync-{func.__name__}-{args[0] if args else 'unknown'}"
        logger.info(f"Executing {func.__name__} synchronously (no background workers)")
        try:
            func(*args)
            logger.info(f"Job {job_id} completed successfully")
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            raise
        
        return SyncJob(job_id)


def get_queue(name: str = "default") -> SyncQueue:
    """Return a named synchronous queue.
    
    Caches per name. All jobs execute synchronously.
    Supported names: "low", "default", "high" (priority is ignored in sync mode).
    """
    global _queues
    if name not in _queues:
        _queues[name] = SyncQueue(name)
    return _queues[name]

