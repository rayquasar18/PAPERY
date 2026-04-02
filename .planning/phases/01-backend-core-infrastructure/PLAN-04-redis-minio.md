---
plan: "04"
title: "Redis & MinIO Extensions"
phase: 1
wave: 3
depends_on: ["01", "03"]
requirements:
  - INFRA-03
  - INFRA-04
files_modified:
  - backend/app/extensions/ext_redis.py
  - backend/app/extensions/ext_minio.py
  - backend/app/main.py
autonomous: true
estimated_tasks: 3
---

# Plan 04 — Redis & MinIO Extensions

## Goal

Implement Redis extension with 3 isolated namespace clients (cache db=0, queue db=1, rate_limit db=2) and MinIO extension with presigned URL generation. Both follow the same init/shutdown pattern as ext_database. Wire both into FastAPI lifespan.

> **Note:** This plan runs in wave 3 (after PLAN-03) because Task 4.3 modifies `main.py`,
> which PLAN-03 Task 3.4 also modifies. Sequential execution avoids file conflicts.

---

## Tasks

### Task 4.1 — Create Redis extension with 3-namespace isolation (INFRA-03)

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 4: Redis Namespace Isolation)
- .planning/phases/01-backend-core-infrastructure/research/03-redis-minio.md
- backend/app/core/config/redis.py (RedisConfig with all 3 namespace configs)
</read_first>

<action>
Create `backend/app/extensions/ext_redis.py`:

```python
"""Redis extension — three isolated namespace clients (cache, queue, rate_limit)."""
import logging

import redis.asyncio as aioredis

from app.core.config import settings

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
```
</action>

<acceptance_criteria>
- `backend/app/extensions/ext_redis.py` contains `import redis.asyncio as aioredis`
- `backend/app/extensions/ext_redis.py` contains `cache_client: aioredis.Redis | None = None`
- `backend/app/extensions/ext_redis.py` contains `queue_client: aioredis.Redis | None = None`
- `backend/app/extensions/ext_redis.py` contains `rate_limit_client: aioredis.Redis | None = None`
- `backend/app/extensions/ext_redis.py` contains `def _create_client(`
- `backend/app/extensions/ext_redis.py` contains `aioredis.ConnectionPool(`
- `backend/app/extensions/ext_redis.py` contains `decode_responses=True`
- `backend/app/extensions/ext_redis.py` contains `health_check_interval=30`
- `backend/app/extensions/ext_redis.py` contains `retry_on_timeout=True`
- `backend/app/extensions/ext_redis.py` contains `await cache_client.ping()`
- `backend/app/extensions/ext_redis.py` contains `await queue_client.ping()`
- `backend/app/extensions/ext_redis.py` contains `await rate_limit_client.ping()`
- `backend/app/extensions/ext_redis.py` contains `await client.aclose()` (not `close()`)
- `backend/app/extensions/ext_redis.py` contains `async def init()`
- `backend/app/extensions/ext_redis.py` contains `async def shutdown()`
</acceptance_criteria>

---

### Task 4.2 — Create MinIO extension with presigned URL generation (INFRA-04)

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 5: MinIO Presigned URLs)
- .planning/phases/01-backend-core-infrastructure/research/03-redis-minio.md
- backend/app/core/config/minio.py (MinioConfig with all settings)
</read_first>

<action>
Create `backend/app/extensions/ext_minio.py`:

```python
"""MinIO extension — S3-compatible file storage with presigned URL support."""
import logging
from datetime import timedelta
from functools import partial

from minio import Minio

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton (initialized in init())
client: Minio | None = None


def init() -> None:
    """Initialize MinIO client and ensure bucket exists.

    Note: MinIO SDK is synchronous (urllib3-based). This is fine because:
    - init() runs once at startup
    - presigned URL generation is local crypto (no network I/O)
    - Only large uploads need run_in_executor wrapping
    """
    global client

    client = Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )

    # Auto-create bucket if it doesn't exist
    bucket = settings.MINIO_BUCKET_NAME
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info("Created MinIO bucket: %s", bucket)
    else:
        logger.info("MinIO bucket exists: %s", bucket)

    logger.info("MinIO client initialized: %s", settings.MINIO_ENDPOINT)


def shutdown() -> None:
    """No-op. MinIO SDK manages connections internally via urllib3."""
    global client
    client = None
    logger.info("MinIO client released")


def presigned_get_url(
    object_name: str,
    expires: int | None = None,
) -> str:
    """Generate a presigned GET URL for downloading an object.

    Args:
        object_name: The object key in the bucket.
        expires: Expiry in seconds. Defaults to MINIO_PRESIGNED_GET_EXPIRY (3600s).

    Returns:
        Presigned URL string.
    """
    if client is None:
        raise RuntimeError("MinIO not initialized. Call ext_minio.init() first.")

    expiry = timedelta(seconds=expires or settings.MINIO_PRESIGNED_GET_EXPIRY)
    return client.presigned_get_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
        expires=expiry,
    )


def presigned_put_url(
    object_name: str,
    expires: int | None = None,
) -> str:
    """Generate a presigned PUT URL for uploading an object.

    Args:
        object_name: The object key in the bucket.
        expires: Expiry in seconds. Defaults to MINIO_PRESIGNED_PUT_EXPIRY (1800s).

    Returns:
        Presigned URL string.
    """
    if client is None:
        raise RuntimeError("MinIO not initialized. Call ext_minio.init() first.")

    expiry = timedelta(seconds=expires or settings.MINIO_PRESIGNED_PUT_EXPIRY)
    return client.presigned_put_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
        expires=expiry,
    )


async def upload_file(
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    """Upload file data to MinIO. Wraps sync call in executor for async safety.

    Args:
        object_name: The object key in the bucket.
        data: File content as bytes.
        content_type: MIME type of the file.
    """
    import asyncio
    import io

    if client is None:
        raise RuntimeError("MinIO not initialized. Call ext_minio.init() first.")

    loop = asyncio.get_running_loop()
    stream = io.BytesIO(data)

    await loop.run_in_executor(
        None,
        partial(
            client.put_object,
            bucket_name=settings.MINIO_BUCKET_NAME,
            object_name=object_name,
            data=stream,
            length=len(data),
            content_type=content_type,
        ),
    )
```
</action>

<acceptance_criteria>
- `backend/app/extensions/ext_minio.py` contains `from minio import Minio`
- `backend/app/extensions/ext_minio.py` contains `client: Minio | None = None`
- `backend/app/extensions/ext_minio.py` contains `def init() -> None:`
- `backend/app/extensions/ext_minio.py` contains `def shutdown() -> None:`
- `backend/app/extensions/ext_minio.py` contains `client.bucket_exists(bucket)`
- `backend/app/extensions/ext_minio.py` contains `client.make_bucket(bucket)`
- `backend/app/extensions/ext_minio.py` contains `def presigned_get_url(`
- `backend/app/extensions/ext_minio.py` contains `client.presigned_get_object(`
- `backend/app/extensions/ext_minio.py` contains `def presigned_put_url(`
- `backend/app/extensions/ext_minio.py` contains `client.presigned_put_object(`
- `backend/app/extensions/ext_minio.py` contains `async def upload_file(`
- `backend/app/extensions/ext_minio.py` contains `asyncio.get_running_loop()`
- `backend/app/extensions/ext_minio.py` contains `loop.run_in_executor(`
- `backend/app/extensions/ext_minio.py` contains `timedelta(seconds=expires or settings.MINIO_PRESIGNED_GET_EXPIRY)`
- `backend/app/extensions/ext_minio.py` contains `timedelta(seconds=expires or settings.MINIO_PRESIGNED_PUT_EXPIRY)`
- `backend/app/extensions/ext_minio.py` does NOT contain `asyncio.get_event_loop()` (deprecated in Python 3.12)
</acceptance_criteria>

---

### Task 4.3 — Wire Redis and MinIO extensions into FastAPI lifespan

<read_first>
- backend/app/main.py (current state after Plan 03 wired ext_database)
- backend/app/extensions/ext_redis.py (created in Task 4.1)
- backend/app/extensions/ext_minio.py (created in Task 4.2)
</read_first>

<action>
Update `backend/app/main.py` to import and call Redis and MinIO extensions in the lifespan.

Add imports at the top:
```python
from app.extensions import ext_database, ext_redis, ext_minio
```

Update the lifespan function to:
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize and shutdown extensions."""
    logger.info("Starting PAPERY backend v%s [%s]", settings.APP_VERSION, settings.ENVIRONMENT)
    # Startup: order matters (database first, then cache, then storage)
    await ext_database.init()
    await ext_redis.init()
    ext_minio.init()  # Sync — MinIO SDK is synchronous
    logger.info("All extensions initialized")
    yield
    # Shutdown: reverse order
    ext_minio.shutdown()  # Sync
    await ext_redis.shutdown()
    await ext_database.shutdown()
    logger.info("All extensions shut down")
```

Note: `ext_minio.init()` and `ext_minio.shutdown()` are called WITHOUT `await` because the MinIO SDK is synchronous.
</action>

<acceptance_criteria>
- `backend/app/main.py` contains `from app.extensions import ext_database, ext_redis, ext_minio`
- `backend/app/main.py` contains `await ext_database.init()`
- `backend/app/main.py` contains `await ext_redis.init()`
- `backend/app/main.py` contains `ext_minio.init()` (no await)
- `backend/app/main.py` contains `ext_minio.shutdown()` (no await)
- `backend/app/main.py` contains `await ext_redis.shutdown()`
- `backend/app/main.py` contains `await ext_database.shutdown()`
- The startup order is: ext_database → ext_redis → ext_minio
- The shutdown order is: ext_minio → ext_redis → ext_database (reverse)
</acceptance_criteria>

---

## Verification

After all tasks complete:
1. `cd backend && uv run python -c "from app.extensions.ext_redis import init, shutdown, cache_client, queue_client, rate_limit_client; print('Redis ext OK')"` outputs "Redis ext OK"
2. `cd backend && uv run python -c "from app.extensions.ext_minio import init, shutdown, presigned_get_url, presigned_put_url; print('MinIO ext OK')"` outputs "MinIO ext OK"
3. `cd backend && uv run ruff check app/extensions/` passes with no errors
4. With Docker middleware running: FastAPI app starts and logs show all 3 Redis pings + MinIO bucket check

## must_haves

- [ ] 3 separate Redis clients for cache (db=0), queue (db=1), rate_limit (db=2) — never use `SELECT` (INFRA-03)
- [ ] Redis clients use `aioredis.ConnectionPool` with `decode_responses=True` and `health_check_interval=30`
- [ ] Redis `shutdown()` uses `aclose()` (not `close()`) for async-native cleanup
- [ ] All 3 Redis clients `ping()` during init (fail-fast on startup)
- [ ] MinIO `init()` creates bucket if not exists (INFRA-04)
- [ ] `presigned_get_url()` returns signed URL with configurable expiry (default 3600s)
- [ ] `presigned_put_url()` returns signed URL with configurable expiry (default 1800s)
- [ ] MinIO `init()`/`shutdown()` are sync (no `await`) — SDK is synchronous
- [ ] `upload_file()` uses `run_in_executor` with `asyncio.get_running_loop()` for async safety
- [ ] Lifespan startup order: database → redis → minio; shutdown: minio → redis → database
