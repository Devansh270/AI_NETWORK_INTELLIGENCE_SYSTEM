import logging
import time
import uuid
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("ainis.errors")


def _error_body(code: str, message: str, request: Request, details=None):
    return {
        "error": message,
        "code": code,
        "timestamp": time.time(),
        "path": str(request.url.path),
        "request_id": getattr(request.state, "request_id", None),
    } | ({"details": details} if details else {})


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(
        "http_exception",
        extra={"path": request.url.path, "status": exc.status_code, "detail": exc.detail},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(f"HTTP_{exc.status_code}", str(exc.detail), request),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("validation_error", extra={"path": request.url.path, "errors": exc.errors()})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            "VALIDATION_ERROR",
            "Request validation failed",
            request,
            details=exc.errors(),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    logger.error(
        "unhandled_exception",
        extra={"path": request.url.path, "error_id": error_id},
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            "INTERNAL_ERROR",
            "An unexpected error occurred",
            request,
            details={"error_id": error_id},
        ),
    )