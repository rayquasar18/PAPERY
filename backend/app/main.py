"""PAPERY backend — FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from app.api.v1 import api_v1_router
from app.configs import settings
from app.core.db import session as db_session
from app.extensions import ext_minio, ext_redis
from app.middleware.request_id import RequestIDMiddleware
from app.schemas.error import ErrorResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize and shutdown extensions."""
    logger.info("Starting PAPERY backend v%s [%s]", settings.APP_VERSION, settings.ENVIRONMENT)
    # Startup: order matters (database first, then cache, then storage)
    await db_session.init()
    await ext_redis.init()
    ext_minio.init()  # Sync — MinIO SDK is synchronous
    logger.info("All extensions initialized")
    yield
    # Shutdown: reverse order
    ext_minio.shutdown()  # Sync
    await ext_redis.shutdown()
    await db_session.shutdown()
    logger.info("All extensions shut down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url="/api/v1/openapi.json" if settings.DEBUG else None,
    docs_url="/api/v1/docs" if settings.DEBUG else None,
    redoc_url="/api/v1/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# --- Middleware (order matters: first added = outermost) ---

# CORS must be outermost to handle preflight and add headers to error responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware — sets request.state.request_id for all requests
app.add_middleware(RequestIDMiddleware)


# --- Exception Handlers ---

def _get_request_id(request: Request) -> str:
    """Safely get request_id from request.state, with fallback."""
    return getattr(request.state, "request_id", "unknown")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle all HTTP exceptions → consistent ErrorResponse with request_id.

    Uses FastAPI's built-in HTTPException directly. The handler maps
    status codes to error codes and injects request_id automatically.
    """
    error_code_map: dict[int, str] = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    error_code = error_code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
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


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
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


@app.exception_handler(Exception)
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


# --- Routes ---
app.include_router(api_v1_router)
