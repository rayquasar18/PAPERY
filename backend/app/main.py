import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize and shutdown extensions."""
    logger.info("Starting PAPERY backend v%s [%s]", settings.APP_VERSION, settings.ENVIRONMENT)
    # Extensions will be initialized here in subsequent plans:
    # await ext_database.init()
    # await ext_redis.init()
    # await ext_minio.init()
    logger.info("All extensions initialized")
    yield
    # Shutdown in reverse order:
    # await ext_minio.shutdown()
    # await ext_redis.shutdown()
    # await ext_database.shutdown()
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
