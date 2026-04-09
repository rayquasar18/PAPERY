"""Redis client — three isolated namespace clients (cache, queue, rate_limit)."""

import logging

import redis.asyncio as aioredis

from app.configs import settings

logger = logging.getLogger(__name__)

# Module-level singletons (initialized in init())
cache_client: aioredis.Redis | None = None
queue_client: aioredis.Redis | None = None
rate_limit_client: aioredis.Redis | None = None


def _create_client(
    host: str,
    port: int,
    db: int,
    password: str,
    max_connections: int = 20,
) -> aioredis.Redis:
    """Create a Redis async client with connection pool."""
    pool = aioredis.ConnectionPool(
        host=host,
        port=port,
        db=db,
        password=password or None,
        max_connections=max_connections,
        decode_responses=True,
        health_check_interval=30,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        retry_on_timeout=True,
    )
    return aioredis.Redis(connection_pool=pool)


async def init() -> None:
    """Initialize three Redis clients and verify connectivity."""
    global cache_client, queue_client, rate_limit_client

    cache_client = _create_client(
        host=settings.REDIS_CACHE_HOST,
        port=settings.REDIS_CACHE_PORT,
        db=settings.REDIS_CACHE_DB,
        password=settings.REDIS_CACHE_PASSWORD,
    )

    queue_client = _create_client(
        host=settings.REDIS_QUEUE_HOST,
        port=settings.REDIS_QUEUE_PORT,
        db=settings.REDIS_QUEUE_DB,
        password=settings.REDIS_QUEUE_PASSWORD,
    )

    rate_limit_client = _create_client(
        host=settings.REDIS_RATE_LIMIT_HOST,
        port=settings.REDIS_RATE_LIMIT_PORT,
        db=settings.REDIS_RATE_LIMIT_DB,
        password=settings.REDIS_RATE_LIMIT_PASSWORD,
    )

    # Verify connectivity (fail-fast)
    await cache_client.ping()
    logger.info("Redis cache client connected (db=%d)", settings.REDIS_CACHE_DB)

    await queue_client.ping()
    logger.info("Redis queue client connected (db=%d)", settings.REDIS_QUEUE_DB)

    await rate_limit_client.ping()
    logger.info("Redis rate_limit client connected (db=%d)", settings.REDIS_RATE_LIMIT_DB)


async def shutdown() -> None:
    """Close all Redis clients."""
    global cache_client, queue_client, rate_limit_client

    for name, client in [
        ("cache", cache_client),
        ("queue", queue_client),
        ("rate_limit", rate_limit_client),
    ]:
        if client is not None:
            await client.aclose()
            logger.info("Redis %s client closed", name)

    cache_client = None
    queue_client = None
    rate_limit_client = None
