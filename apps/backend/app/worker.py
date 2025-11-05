from __future__ import annotations

"""
Minimal RQ worker launcher.

This module provides a CLI entrypoint to start an RQ worker that listens to
priority queues ("high", "default", "low") and enables the builtin scheduler
loop (with_scheduler=True) so delayed jobs can run if scheduled externally.
"""

def run_worker() -> None:  # pragma: no cover - runtime utility
    try:
        from rq import Connection, Worker  # type: ignore
        from app.core.rq import get_redis_connection  # type: ignore

        # Listen to priority queues in order
        queues = ["high", "default", "low"]
        with Connection(get_redis_connection()):
            Worker(queues).work(with_scheduler=True)
    except Exception:
        # Avoid crashing during static analysis or missing optional deps
        pass


def run_flat_request(request_id_str: str) -> None:  # pragma: no cover - compatibility shim
    """Compatibility wrapper to invoke the flat job directly if needed."""
    try:
        from app.jobs.flat_job import run_flat_job  # type: ignore

        run_flat_job(request_id_str)
    except Exception:
        pass


if __name__ == "__main__":  # pragma: no cover
    run_worker()
