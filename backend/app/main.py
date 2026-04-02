import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.extensions import ext_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize and shutdown extensions."""
    logger.info("Starting PAPERY backend v%s [%s]", settings.APP_VERSION, settings.ENVIRONMENT)
    await ext_database.init()
    # await ext_redis.init()    # Plan 04
    # await ext_minio.init()    # Plan 04
    logger.info("All extensions initialized")
    yield
    # await ext_minio.shutdown()   # Plan 04
    # await ext_redis.shutdown()   # Plan 04
    await ext_database.shutdown()
    logger.info("All extensions shut down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.api.v1.health import router as health_router  # noqa: E402

app.include_router(health_router, prefix="/api/v1", tags=["health"])
