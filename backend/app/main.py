"""PAPERY backend — FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_v1_router
from app.configs import settings
from app.core.db import session as db_session
from app.core.exceptions.handlers import register_exception_handlers
from app.extensions import ext_minio, ext_redis
from app.middleware.request_id import RequestIDMiddleware

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
register_exception_handlers(app)


# --- Routes ---
app.include_router(api_v1_router)
