"""Central exception types/handlers placeholder (Phase 0)."""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import status


class BackendError(Exception):
    def __init__(self, message: str, code: str = "backend_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


async def backend_error_handler(request: Request, exc: BackendError):  # noqa: D401
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": exc.message, "code": exc.code},
    )
