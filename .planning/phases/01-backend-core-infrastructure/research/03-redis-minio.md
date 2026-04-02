# Research: Redis Namespace Isolation + MinIO Presigned URLs

**Date:** 2026-04-02
**Scope:** Redis async client with multi-DB namespaces, MinIO presigned URLs, singleton patterns, testing
**Requirements:** INFRA-03 (Redis 7+), INFRA-04 (MinIO), D-16 (service prefix naming)

---

## 1. Redis Async Client — Multi-DB Namespace Isolation

### 1.1 Design: Three Separate `redis.asyncio.Redis` Instances

Each logical namespace gets its own client + connection pool, isolated by `db` number:

| Namespace | DB | Prefix | Purpose |
|---|---|---|---|
| Cache | 0 | `REDIS_CACHE_*` | Response caching, session data |
| Queue | 1 | `REDIS_QUEUE_*` | ARQ task queue |
| Rate Limit | 2 | `REDIS_RATE_LIMIT_*` | Per-user/IP rate counters |

**Why separate clients (not SELECT)?** `SELECT` changes db on a connection — unsafe with connection pools since multiple coroutines share the pool. Separate pools = zero cross-contamination.

### 1.2 Connection Pool Parameters

```python
import redis.asyncio as aioredis

def _create_redis_client(
    host: str,
    port: int,
    db: int,
    password: str,
    max_connections: int = 20,
) -> aioredis.Redis:
    """Create a redis.asyncio client with its own connection pool."""
    pool = aioredis.ConnectionPool(
        host=host,
        port=port,
        db=db,
        password=password or None,
        max_connections=max_connections,
        decode_responses=True,       # Return str not bytes
        encoding="utf-8",
        health_check_interval=30,    # Ping every 30s on reused connections
        socket_timeout=5.0,          # Read/write timeout
        socket_connect_timeout=5.0,  # Connection establishment timeout
        retry_on_timeout=True,       # Auto-retry on timeout
    )
    return aioredis.Redis(connection_pool=pool)
```

**Key parameter choices:**
- `decode_responses=True` — avoids `.decode()` everywhere; all values returned as `str`
- `health_check_interval=30` — detects dead connections before use (sends PING)
- `max_connections=20` — per-namespace pool size; cache may need more, rate_limit less
- `socket_timeout=5.0` — prevents hanging on network issues
- `retry_on_timeout=True` — resilience for transient failures

### 1.3 Extension Module: `ext_redis.py`

```python
# backend/app/extensions/ext_redis.py
import logging
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level singletons — initialized during lifespan
redis_cache: aioredis.Redis | None = None
redis_queue: aioredis.Redis | None = None
redis_rate_limit: aioredis.Redis | None = None


def _create_client(host: str, port: int, db: int, password: str) -> aioredis.Redis:
    pool = aioredis.ConnectionPool(
        host=host, port=port, db=db,
        password=password or None,
        max_connections=20,
        decode_responses=True,
        health_check_interval=30,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        retry_on_timeout=True,
    )
    return aioredis.Redis(connection_pool=pool)


async def init() -> None:
    global redis_cache, redis_queue, redis_rate_limit

    redis_cache = _create_client(
        settings.REDIS_CACHE_HOST, settings.REDIS_CACHE_PORT,
        settings.REDIS_CACHE_DB, settings.REDIS_CACHE_PASSWORD,
    )
    redis_queue = _create_client(
        settings.REDIS_QUEUE_HOST, settings.REDIS_QUEUE_PORT,
        settings.REDIS_QUEUE_DB, settings.REDIS_QUEUE_PASSWORD,
    )
    redis_rate_limit = _create_client(
        settings.REDIS_RATE_LIMIT_HOST, settings.REDIS_RATE_LIMIT_PORT,
        settings.REDIS_RATE_LIMIT_DB, settings.REDIS_RATE_LIMIT_PASSWORD,
    )

    # Verify connectivity
    await redis_cache.ping()
    await redis_queue.ping()
    await redis_rate_limit.ping()
    logger.info("Redis connections established (cache=db%d, queue=db%d, rate_limit=db%d)",
                settings.REDIS_CACHE_DB, settings.REDIS_QUEUE_DB, settings.REDIS_RATE_LIMIT_DB)


async def shutdown() -> None:
    for name, client in [("cache", redis_cache), ("queue", redis_queue), ("rate_limit", redis_rate_limit)]:
        if client:
            await client.aclose()  # aclose() closes pool + all connections
            logger.info("Redis %s connection closed", name)
```

**Key decisions:**
- `aclose()` (not `close()`) — the async-native cleanup method in redis-py 5.x
- `ping()` on init — fail-fast if Redis is unreachable; app won't start with broken connections
- Module-level singletons — imported anywhere: `from app.extensions.ext_redis import redis_cache`

### 1.4 Dependency Injection for Routes

```python
# backend/app/api/dependencies.py
from app.extensions import ext_redis

async def get_redis_cache() -> aioredis.Redis:
    assert ext_redis.redis_cache is not None, "Redis cache not initialized"
    return ext_redis.redis_cache
```

---

## 2. MinIO — Connection Singleton + Presigned URLs

### 2.1 MinIO Python SDK Facts

- **Library:** `minio` (PyPI) — pure Python, **synchronous only** (uses `urllib3`)
- **No async SDK exists** — use `run_in_executor` for CPU-bound ops or accept sync in async context
- **Presigned URLs are computed locally** (no network call) — safe to call synchronously
- **Bucket operations (`make_bucket`, `bucket_exists`) are network calls** — but only at startup

### 2.2 Extension Module: `ext_minio.py`

```python
# backend/app/extensions/ext_minio.py
import logging
from datetime import timedelta
from minio import Minio
from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton
minio_client: Minio | None = None


async def init() -> None:
    global minio_client
    minio_client = Minio(
        endpoint=settings.MINIO_ENDPOINT,       # "localhost:9000"
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_SSL,           # False for local dev
    )

    # Auto-create bucket if it doesn't exist
    bucket = settings.MINIO_BUCKET
    if not minio_client.bucket_exists(bucket_name=bucket):
        minio_client.make_bucket(bucket_name=bucket)
        logger.info("Created MinIO bucket: %s", bucket)
    else:
        logger.info("MinIO bucket exists: %s", bucket)


async def shutdown() -> None:
    # MinIO client has no persistent connection to close
    # urllib3 pool manager handles connection lifecycle
    logger.info("MinIO client released")
```

### 2.3 Presigned URL Generation

```python
# Presigned GET — client downloads a file (default 1 hour expiry)
def generate_download_url(object_name: str, expires: timedelta = timedelta(hours=1)) -> str:
    assert minio_client is not None
    return minio_client.presigned_get_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        expires=expires,
    )

# Presigned PUT — client uploads a file directly to MinIO (default 30 min)
def generate_upload_url(object_name: str, expires: timedelta = timedelta(minutes=30)) -> str:
    assert minio_client is not None
    return minio_client.presigned_put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        expires=expires,
    )
```

**Key facts about presigned URLs:**
- `presigned_get_object` max expires = 7 days; default in SDK = 7 days (too long — use 1h)
- `presigned_put_object` max expires = 7 days; use 30min for upload tokens
- Both return a full URL string (`http://localhost:9000/bucket/object?X-Amz-...`)
- **No network call** — URL is signed locally using access/secret keys
- Client uses the URL to PUT/GET directly to MinIO (bypasses backend)

### 2.4 Server-Side Upload (Backend Receives File)

```python
from io import BytesIO

def upload_file(object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload file from backend to MinIO. Returns object_name."""
    assert minio_client is not None
    minio_client.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return object_name
```

### 2.5 Async Consideration

MinIO SDK is sync. For routes that upload large files server-side:

```python
import asyncio
from functools import partial

async def async_upload_file(object_name: str, data: bytes, content_type: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(upload_file, object_name, data, content_type)
    )
```

For presigned URL generation: sync is fine (no I/O, just crypto signing).

---

## 3. Config Module Integration

Already defined in `04-config-settings.md` research. Summary:

```python
# backend/app/core/config/redis.py — 3 namespaces × 4 fields = 12 env vars
class RedisConfig(BaseSettings):
    REDIS_CACHE_HOST: str = "localhost"
    REDIS_CACHE_PORT: PositiveInt = 6379
    REDIS_CACHE_DB: int = 0   # ge=0, le=15
    REDIS_CACHE_PASSWORD: str = ""
    REDIS_QUEUE_HOST: str = "localhost"
    REDIS_QUEUE_PORT: PositiveInt = 6379
    REDIS_QUEUE_DB: int = 1
    REDIS_QUEUE_PASSWORD: str = ""
    REDIS_RATE_LIMIT_HOST: str = "localhost"
    REDIS_RATE_LIMIT_PORT: PositiveInt = 6379
    REDIS_RATE_LIMIT_DB: int = 2
    REDIS_RATE_LIMIT_PASSWORD: str = ""

# backend/app/core/config/minio.py
class MinioConfig(BaseSettings):
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "papery"
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "papery-documents"
    MINIO_USE_SSL: bool = False
```

---

## 4. Testing Patterns

### 4.1 Redis — Use `fakeredis` for Unit Tests

```python
# tests/conftest.py
import fakeredis.aioredis
import pytest_asyncio

@pytest_asyncio.fixture
async def mock_redis():
    """In-memory Redis for unit tests — no real Redis needed."""
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.aclose()
```

- `fakeredis[aioredis]` — drop-in replacement for `redis.asyncio.Redis`
- Supports most Redis commands (GET/SET/INCR/EXPIRE/TTL/pipeline)
- Tests run without Docker or real Redis

### 4.2 Redis — Integration Tests with Real Redis

```python
# tests/integration/conftest.py
import redis.asyncio as aioredis

@pytest_asyncio.fixture
async def real_redis():
    """Requires Redis running (docker compose middleware)."""
    client = aioredis.Redis(host="localhost", port=6379, db=15, decode_responses=True)
    await client.flushdb()  # Clean slate for each test
    yield client
    await client.flushdb()
    await client.aclose()
```

Use `db=15` for tests — never conflicts with app databases (0, 1, 2).

### 4.3 MinIO — Unit Tests with Mocking

```python
from unittest.mock import MagicMock, patch

def test_generate_download_url():
    mock_client = MagicMock()
    mock_client.presigned_get_object.return_value = "http://minio:9000/bucket/file?signed"
    with patch("app.extensions.ext_minio.minio_client", mock_client):
        url = generate_download_url("docs/test.pdf")
    assert "signed" in url
    mock_client.presigned_get_object.assert_called_once()
```

### 4.4 MinIO — Integration Tests

```python
@pytest.fixture
def real_minio():
    """Requires MinIO running (docker compose middleware)."""
    client = Minio("localhost:9000", access_key="papery", secret_key="papery_minio_dev", secure=False)
    bucket = "test-papery"
    if not client.bucket_exists(bucket_name=bucket):
        client.make_bucket(bucket_name=bucket)
    yield client, bucket
    # Cleanup: remove all objects + bucket
    for obj in client.list_objects(bucket_name=bucket, recursive=True):
        client.remove_object(bucket_name=bucket, object_name=obj.object_name)
    client.remove_bucket(bucket_name=bucket)
```

---

## 5. Implementation Checklist

- [ ] Create `backend/app/extensions/ext_redis.py` — 3 clients, init/shutdown, ping on startup
- [ ] Create `backend/app/extensions/ext_minio.py` — client init, bucket auto-create, presigned helpers
- [ ] Add `redis[hiredis]>=5.0` to `pyproject.toml` (hiredis = C parser, 10x faster)
- [ ] Add `minio>=7.2` to `pyproject.toml`
- [ ] Add `fakeredis[aioredis]` to dev dependencies
- [ ] Wire `ext_redis.init()` and `ext_minio.init()` in `main.py` lifespan
- [ ] Add Redis + MinIO health check to a `/health` endpoint
- [ ] Write unit tests for presigned URL generation (mock MinIO client)
- [ ] Write unit tests for Redis fallback patterns (fakeredis)
- [ ] Write integration test fixtures using `db=15` (Redis) and `test-*` bucket (MinIO)

## 6. Key Decisions Summary

| Decision | Choice | Rationale |
|---|---|---|
| Redis library | `redis[hiredis]` >= 5.0 | Official, async-native, hiredis for performance |
| Namespace isolation | Separate `db` per client | No `SELECT` needed, pool-safe, zero cross-talk |
| Pool size | 20 per namespace | Reasonable default; cache may need tuning up |
| Health check | `health_check_interval=30` | Detects dead connections before commands fail |
| MinIO SDK | `minio` (sync) | Only official SDK; presigned URLs need no async |
| Presigned expiry | GET=1h, PUT=30min | Short-lived tokens; secure defaults |
| Bucket init | Auto-create on startup | Dev-friendly; production buckets pre-exist |
| Test isolation | `fakeredis` + `db=15` + `test-*` bucket | No infra for unit tests; clean isolation for integration |

---

*Research complete. Ready for implementation.*
