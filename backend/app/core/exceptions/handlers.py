"""Exception handlers for the FastAPI application.

All exception handler functions live here. ``register_exception_handlers``
is the single wiring function that ``main.py`` calls to install them.
"""

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from app.core.exceptions import HTTP_STATUS_ERROR_CODE_MAP, PaperyHTTPException
from app.schemas.error import ErrorResponse

logger = logging.getLogger(__name__)


def _get_request_id(request: Request) -> str:
    """Safely get request_id from request.state, with fallback."""
    return getattr(request.state, "request_id", "unknown")


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle all HTTP exceptions → consistent ErrorResponse with request_id.

    If the exception is a ``PaperyHTTPException``, its ``error_code`` is used
    directly. Otherwise, the status code is mapped via
    ``HTTP_STATUS_ERROR_CODE_MAP`` (fallback: ``HTTP_<status>``).
    """
    if isinstance(exc, PaperyHTTPException):
        error_code = exc.error_code
    else:
        error_code = HTTP_STATUS_ERROR_CODE_MAP.get(exc.status_code, f"HTTP_{exc.status_code}")

    message = exc.detail if isinstance(exc.detail, str) else "An error occurred"

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error_code=error_code,
            message=message,
            detail=None,
            request_id=_get_request_id(request),
        ).model_dump(),
        headers=getattr(exc, "headers", None),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic request validation errors → consistent ErrorResponse."""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            success=False,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            detail=exc.errors(),
            request_id=_get_request_id(request),
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions → 500 ErrorResponse. Never expose stack traces."""
    logger.error(
        "Unhandled exception: %s",
        exc,
        exc_info=True,
        extra={"request_id": _get_request_id(request)},
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            detail=None,
            request_id=_get_request_id(request),
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application.

    Call this once after ``app = FastAPI(...)`` in ``main.py``.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
