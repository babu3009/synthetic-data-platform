"""Startup/shutdown events shim (Phase 0)."""

from fastapi import FastAPI


def register_events(app: FastAPI) -> None:
    @app.on_event("startup")
    async def _startup():  # noqa: D401
        # Placeholder for future initialization (metrics, tracing, etc.)
        return None

    @app.on_event("shutdown")
    async def _shutdown():  # noqa: D401
        # Placeholder for cleanup logic.
        return None
