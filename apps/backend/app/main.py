import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.api_v1.api import api_router
from app.jobs.cleanup import cleanup_expired_artifacts
from app.observability import init_observability

_cleanup_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover - integration path
    global _cleanup_task
    # Startup
    interval_minutes = getattr(settings, "CLEANUP_INTERVAL_MINUTES", 24 * 60)
    try:
        _cleanup_task = asyncio.create_task(_run_cleanup_periodically(interval_minutes))
    except Exception:
        _cleanup_task = None
    # Yield control to application
    try:
        yield
    finally:
        # Shutdown
        if _cleanup_task is not None:
            _cleanup_task.cancel()
            try:
                await _cleanup_task
            except Exception:
                pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Synthetic Data Platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# Observability (Prometheus /metrics and OpenTelemetry tracing if configured)
init_observability(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "message": "Synthetic Data Platform API is running"}


async def _run_cleanup_periodically(interval_minutes: int) -> None:
    # Sleep a bit after startup to avoid contention
    await asyncio.sleep(5)
    interval = max(1, int(interval_minutes)) * 60
    while True:
        try:
            # Run sync cleanup in a thread to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, cleanup_expired_artifacts)
        except Exception:
            # Best-effort only; ignore errors
            pass
        await asyncio.sleep(interval)



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)