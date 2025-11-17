import asyncio
import logging
import traceback
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.api_v1.api import api_router
from app.jobs.cleanup import cleanup_expired_artifacts
from app.observability import init_observability

# Configure logging at module level
configure_logging(level=settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "INFO")
logger = logging.getLogger(__name__)

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
    # Seed admin if missing
    try:
        from app.db.session import AsyncSessionLocal
        from app.db.models import User, UserRole, UserStatus
        from app.security.passwords import hash_password
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL.lower()))
            admin = res.scalar_one_or_none()
            if not admin:
                admin = User(
                    email=settings.ADMIN_EMAIL.lower(),
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                    status=UserStatus.APPROVED,
                    organization="admin",
                )
                db.add(admin)
                await db.commit()
    except Exception:
        # best effort seeding only
        pass
    # Yield control to application
    try:
        yield
    finally:
        # Shutdown
        if _cleanup_task is not None:
            _cleanup_task.cancel()
            try:
                await _cleanup_task
            except BaseException:
                pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Synthetic Data Platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)


# Exception handlers for comprehensive error logging
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions and log errors (4xx as warning, 5xx as error)."""
    log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
    
    logger.log(
        log_level,
        f"HTTP {exc.status_code} | {request.method} {request.url.path} | {exc.detail}",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": exc.status_code,
            "detail": exc.detail,
            "client": request.client.host if request.client else None,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors and log them."""
    logger.warning(
        f"Validation Error | {request.method} {request.url.path} | {exc.errors()}",
        extra={
            "method": request.method,
            "url": str(request.url),
            "errors": exc.errors(),
            "body": exc.body,
            "client": request.client.host if request.client else None,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions with full traceback logging."""
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    
    logger.error(
        f"UNHANDLED EXCEPTION | {request.method} {request.url.path} | {type(exc).__name__}: {str(exc)}\n{tb_str}",
        extra={
            "method": request.method,
            "url": str(request.url),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": tb_str,
            "client": request.client.host if request.client else None,
        },
        exc_info=True
    )
    
    # Don't expose internal error details to client in production
    detail = "Internal server error"
    if settings.DEBUG if hasattr(settings, "DEBUG") else False:
        detail = f"{type(exc).__name__}: {str(exc)}"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail},
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
# Static serving for uploaded avatars
app.mount("/storage/uploads/avatars", StaticFiles(directory="storage/uploads/avatars"), name="avatars")

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
    try:
        while True:
            try:
                # Run sync cleanup in a thread to avoid blocking the event loop
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, cleanup_expired_artifacts)
            except Exception:
                # Best-effort only; ignore errors
                pass
            await asyncio.sleep(interval)
    except BaseException:
        # Graceful task cancellation on shutdown/reload
        return



if __name__ == "__main__":
    import uvicorn
    import multiprocessing

    # Fix for Windows multiprocessing issues with uvicorn reload
    multiprocessing.freeze_support()

    uvicorn.run(app, host="0.0.0.0", port=8000)