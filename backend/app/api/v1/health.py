"""Health check endpoints — liveness (/health) and readiness (/ready)."""

import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.configs import settings
from app.core.db import session as db_session
from app.extensions import ext_minio, ext_redis

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe — returns immediately. No dependency checks."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """Readiness probe — deep check of all dependencies.

    Checks PostgreSQL, Redis (cache), and MinIO connectivity.
    Returns 200 if all pass, 503 if any fail.
    Per-service timeout: 2.5 seconds.
    """
    checks: dict[str, str] = {}
    healthy = True

    # PostgreSQL check
    try:
        if db_session.engine is None:
            raise RuntimeError("Database engine not initialized")
        async with asyncio.timeout(2.5):
            async with db_session.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
        healthy = False
        logger.warning("Readiness check failed for postgres: %s", exc)

    # Redis check (cache client)
    try:
        if ext_redis.cache_client is None:
            raise RuntimeError("Redis cache client not initialized")
        async with asyncio.timeout(2.5):
            await ext_redis.cache_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        healthy = False
        logger.warning("Readiness check failed for redis: %s", exc)

    # MinIO check (sync SDK — must use run_in_executor)
    try:
        if ext_minio.client is None:
            raise RuntimeError("MinIO client not initialized")
        loop = asyncio.get_running_loop()
        async with asyncio.timeout(2.5):
            await loop.run_in_executor(None, ext_minio.client.list_buckets)
        checks["minio"] = "ok"
    except Exception as exc:
        checks["minio"] = f"error: {exc}"
        healthy = False
        logger.warning("Readiness check failed for minio: %s", exc)

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if healthy else "unhealthy",
            "checks": checks,
        },
    )
