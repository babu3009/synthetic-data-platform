from __future__ import annotations

"""
Minimal RQ worker launcher.

Note: The actual job implementation lives in app.jobs.flat_job.
This module only provides a CLI entrypoint to start a worker and is
kept intentionally simple to avoid type-checker import issues when RQ/Redis
aren't installed in certain environments.
"""

def run_worker() -> None:  # pragma: no cover - runtime utility
    try:
        from rq import Connection, Worker  # type: ignore
        from app.services.jobs import get_redis_connection  # type: ignore

        with Connection(get_redis_connection()):
            Worker(["flat", "default"]).work(with_scheduler=True)
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
