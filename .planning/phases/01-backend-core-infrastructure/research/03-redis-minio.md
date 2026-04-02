# Research: Redis Namespace Isolation & MinIO Presigned URLs

**Scope:** INFRA-03 (Redis 7+ with namespace isolation) and INFRA-04 (MinIO file storage with presigned URLs)
**Date:** 2026-04-02

---

## 1. Redis Async — Multi-DB Namespace Isolation

### 1.1 Architecture Decision

Use **separate Redis databases** (db=0, db=1, db=2) on a single Redis instance for logical isolation. Each namespace gets its own `redis.asyncio.Redis` client with its own connection pool. This prevents key collisions and allows independent `FLUSHDB` per namespace.

| Namespace | DB | Env Prefix | Purpose |
|-----------|----|------------|---------|
| Cache | 0 | `REDIS_CACHE_*` | Response caching, session data |
| Queue | 1 | `REDIS_QUEUE_*` | ARQ task queue broker |
| Rate Limit | 2 | `REDIS_RATE_LIMIT_*` | Per-user/IP rate counters, token blacklist |

### 1.2 Connection Pool Setup

Each namespace needs an independent `ConnectionPool`. Key parameters:

```python
import redis.asyncio as aioredis

pool = aioredis.ConnectionPool(
    host=settings.REDIS_CACHE_HOST,
    port=settings.REDIS_CACHE_PORT,
    db=0,
    password=settings.REDIS_CACHE_PASSWORD,
    max_connections=settings.REDIS_CACHE_MAX_CONNECTIONS or 10,
    decode_responses=True,          # return str not bytes
    health_check_interval=30,       # ping every 30s to detect dead connections
    socket_connect_timeout=5,       # fail fast on connection
    socket_timeout=5,               # fail fast on operations
    retry_on_timeout=True,          # auto-retry on timeout
)
client = aioredis.Redis(connection_pool=pool)
```

**Alternative — `from_url` shorthand** (good for simple setups):
```python
client = aioredis.from_url(
    "redis://:password@localhost:6379/0",
    max_connections=10,
    decode_responses=True,
    health_check_interval=30,
)
```

**Pool sizing guidance:**
- Cache (db=0): 10-20 connections (most traffic)
- Queue (db=1): 5-10 connections (ARQ manages its own pool too)
- Rate Limit (db=2): 5-10 connections (simple INCR/EXPIRE ops)

### 1.3 Singleton Pattern — FastAPI Lifespan

Redis clients must be created at startup and closed at shutdown. Use FastAPI's lifespan context manager:

```python
# backend/app/core/db/redis.py

from dataclasses import dataclass
import redis.asyncio as aioredis

@dataclass
class RedisClients:
    cache: aioredis.Redis
    queue: aioredis.Redis
    rate_limit: aioredis.Redis

# Module-level singleton — set during lifespan
_clients: RedisClients | None = None

def get_redis_cache() -> aioredis.Redis:
    assert _clients is not None, "Redis not initialized"
    return _clients.cache

def get_redis_queue() -> aioredis.Redis:
    assert _clients is not None, "Redis not initialized"
    return _clients.queue

def get_redis_rate_limit() -> aioredis.Redis:
    assert _clients is not None, "Redis not initialized"
    return _clients.rate_limit

async def init_redis(settings) -> RedisClients:
    """Create all three Redis clients. Called in lifespan startup."""
    global _clients
    _clients = RedisClients(
        cache=aioredis.from_url(
            f"redis://{settings.REDIS_CACHE_HOST}:{settings.REDIS_CACHE_PORT}/0",
            password=settings.REDIS_CACHE_PASSWORD or None,
            max_connections=settings.REDIS_CACHE_MAX_CONNECTIONS,
            decode_responses=True,
            health_check_interval=30,
        ),
        queue=aioredis.from_url(
            f"redis://{settings.REDIS_QUEUE_HOST}:{settings.REDIS_QUEUE_PORT}/1",
            password=settings.REDIS_QUEUE_PASSWORD or None,
            max_connections=settings.REDIS_QUEUE_MAX_CONNECTIONS,
            decode_responses=True,
        ),
        rate_limit=aioredis.from_url(
            f"redis://{settings.REDIS_RATE_LIMIT_HOST}:{settings.REDIS_RATE_LIMIT_PORT}/2",
            password=settings.REDIS_RATE_LIMIT_PASSWORD or None,
            max_connections=settings.REDIS_RATE_LIMIT_MAX_CONNECTIONS,
            decode_responses=True,
        ),
    )
    # Verify all connections
    for name, client in [("cache", _clients.cache), ("queue", _clients.queue), ("rate_limit", _clients.rate_limit)]:
        await client.ping()
    return _clients

async def close_redis() -> None:
    """Close all Redis connections. Called in lifespan shutdown."""
    global _clients
    if _clients:
        await _clients.cache.aclose()
        await _clients.queue.aclose()
        await _clients.rate_limit.aclose()
        _clients = None
```

**Lifespan integration:**
```python
# backend/app/core/setup.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_redis(settings)
    init_minio(settings)
    yield
    # Shutdown
    await close_redis()
```

### 1.4 FastAPI Dependency Injection

```python
# backend/app/api/dependencies.py
from app.core.db.redis import get_redis_cache, get_redis_rate_limit

async def redis_cache_dep() -> aioredis.Redis:
    return get_redis_cache()

async def redis_rate_limit_dep() -> aioredis.Redis:
    return get_redis_rate_limit()
```

### 1.5 Key Patterns to Follow

- **Key prefixing by namespace** is NOT needed because we use separate DBs, but consider prefixing keys by feature for clarity: `token_blacklist:{jti}`, `rate:{user_id}:{endpoint}`, `cache:response:{hash}`
- **`aclose()` not `close()`** — `redis.asyncio` requires `aclose()` for proper async cleanup
- **`decode_responses=True`** — return `str` instead of `bytes`; set `False` only if storing binary data (unlikely for cache/rate-limit)
- **Error resilience** — wrap non-critical Redis calls (caching) in try/except; let critical ops (rate limiting) propagate errors

---

## 2. MinIO — File Storage & Presigned URLs

### 2.1 SDK Choice: `minio` (Official Python SDK)

The official `minio` Python package is **synchronous only** (uses `urllib3` internally). It is **thread-safe** — one client instance can be shared across async handlers safely since each call is an independent HTTP request. No need for `run_in_executor` for typical operations (upload/download are I/O but brief for metadata ops like presigned URL generation).

For file upload/download in async context: use `asyncio.to_thread()` to avoid blocking the event loop on large files.

### 2.2 Client Initialization

```python
from minio import Minio

client = Minio(
    endpoint="localhost:9000",       # host:port, no scheme
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False,                    # True for HTTPS in production
)
```

### 2.3 Singleton Pattern

```python
# backend/app/core/db/minio.py

from minio import Minio

_client: Minio | None = None
_bucket_name: str = ""

def init_minio(settings) -> Minio:
    """Initialize MinIO client and ensure bucket exists. Called in lifespan startup."""
    global _client, _bucket_name
    _client = Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    _bucket_name = settings.MINIO_BUCKET_NAME
    # Auto-create bucket on startup
    if not _client.bucket_exists(bucket_name=_bucket_name):
        _client.make_bucket(bucket_name=_bucket_name)
    return _client

def get_minio_client() -> Minio:
    assert _client is not None, "MinIO not initialized"
    return _client

def get_bucket_name() -> str:
    return _bucket_name
```

No `close()` needed — MinIO SDK uses HTTP requests, no persistent connections to clean up.

### 2.4 Presigned URL Generation

**Download URL** (client downloads file directly from MinIO):
```python
from datetime import timedelta

url = client.presigned_get_object(
    bucket_name="papery-documents",
    object_name="projects/{project_uuid}/docs/{file_uuid}.pdf",
    expires=timedelta(hours=1),    # default: 7 days; keep short for security
)
```

**Upload URL** (client uploads file directly to MinIO — bypasses backend for large files):
```python
url = client.presigned_put_object(
    bucket_name="papery-documents",
    object_name="projects/{project_uuid}/docs/{file_uuid}.pdf",
    expires=timedelta(minutes=30),  # short window for uploads
)
```

**Object key convention:**
```
{bucket}/
  projects/{project_uuid}/
    documents/{document_uuid}/{original_filename}
  avatars/{user_uuid}/{filename}
  temp/{upload_uuid}  (for presigned uploads before processing)
```

### 2.5 File Upload Flow (Backend-Proxied, v1)

For v1, use backend-proxied uploads (simpler, validated server-side):

```python
import asyncio
from io import BytesIO

async def upload_file(file_data: bytes, object_name: str, content_type: str) -> str:
    """Upload file to MinIO via asyncio.to_thread to avoid blocking."""
    client = get_minio_client()
    data_stream = BytesIO(file_data)
    await asyncio.to_thread(
        client.put_object,
        bucket_name=get_bucket_name(),
        object_name=object_name,
        data=data_stream,
        length=len(file_data),
        content_type=content_type,
    )
    return object_name
```

### 2.6 Bucket Management on Startup

The `init_minio()` function handles auto-create. Additional considerations:
- **Bucket naming:** single bucket `papery-documents` for v1; split later if needed
- **Bucket policy:** keep private (default); access only via presigned URLs or backend proxy
- **Versioning:** disable for v1 (adds complexity without clear benefit yet)

---

## 3. Config Module Structure

```python
# backend/app/core/config/redis.py

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings

class RedisCacheConfig(BaseSettings):
    REDIS_CACHE_HOST: str = Field(default="localhost")
    REDIS_CACHE_PORT: PositiveInt = Field(default=6379)
    REDIS_CACHE_PASSWORD: str | None = Field(default=None)
    REDIS_CACHE_MAX_CONNECTIONS: PositiveInt = Field(default=10)

class RedisQueueConfig(BaseSettings):
    REDIS_QUEUE_HOST: str = Field(default="localhost")
    REDIS_QUEUE_PORT: PositiveInt = Field(default=6379)
    REDIS_QUEUE_PASSWORD: str | None = Field(default=None)
    REDIS_QUEUE_MAX_CONNECTIONS: PositiveInt = Field(default=5)

class RedisRateLimitConfig(BaseSettings):
    REDIS_RATE_LIMIT_HOST: str = Field(default="localhost")
    REDIS_RATE_LIMIT_PORT: PositiveInt = Field(default=6379)
    REDIS_RATE_LIMIT_PASSWORD: str | None = Field(default=None)
    REDIS_RATE_LIMIT_MAX_CONNECTIONS: PositiveInt = Field(default=5)
```

```python
# backend/app/core/config/minio.py

class MinIOConfig(BaseSettings):
    MINIO_ENDPOINT: str = Field(default="localhost:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")
    MINIO_SECURE: bool = Field(default=False)
    MINIO_BUCKET_NAME: str = Field(default="papery-documents")
    MINIO_PRESIGNED_EXPIRY_HOURS: PositiveInt = Field(default=1)
```

These get composed into the root `AppConfig` via multiple inheritance (D-15).

---

## 4. Testing Patterns

### 4.1 Redis Testing — `fakeredis`

Use `fakeredis[aioredis]` for unit tests (no real Redis needed):

```python
# tests/conftest.py
import fakeredis.aioredis
import pytest_asyncio

@pytest_asyncio.fixture
async def fake_redis():
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.aclose()
```

For integration tests: use real Redis in Docker (via `docker-compose.middleware.yaml`).

### 4.2 MinIO Testing

- **Unit tests:** mock `Minio` client with `unittest.mock.MagicMock` or `pytest-mock`
- **Integration tests:** use real MinIO from `docker-compose.middleware.yaml` with a test bucket
- **Fixture pattern:**
```python
@pytest.fixture
def minio_client():
    client = Minio("localhost:9000", access_key="test", secret_key="test", secure=False)
    bucket = "test-bucket"
    if not client.bucket_exists(bucket_name=bucket):
        client.make_bucket(bucket_name=bucket)
    yield client, bucket
    # Cleanup: remove all objects and bucket
    for obj in client.list_objects(bucket_name=bucket, recursive=True):
        client.remove_object(bucket_name=bucket, object_name=obj.object_name)
    client.remove_bucket(bucket_name=bucket)
```

---

## 5. Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Redis client | `redis.asyncio` (redis-py 5.x) | Native async, well-maintained, de facto standard |
| Namespace isolation | Separate DB numbers (0/1/2) | Simple, no key collision, independent FLUSHDB |
| Pool per namespace | Yes — independent `ConnectionPool` | Prevents one namespace from starving another |
| MinIO SDK | `minio` (official, sync) | Only official option; thread-safe, works fine in async via `to_thread` |
| Presigned URLs | `presigned_get_object` / `presigned_put_object` | Direct client-to-storage download/upload, reduces backend load |
| Large file uploads | `asyncio.to_thread(client.put_object, ...)` | Prevents blocking event loop |
| Unit test Redis | `fakeredis[aioredis]` | Fast, no external deps, mimics real Redis behavior |
| Bucket auto-create | On startup in `init_minio()` | Idempotent, eliminates manual setup step |

---

## 6. Dependencies to Add

```toml
# pyproject.toml
[project.dependencies]
redis = ">=5.0"     # includes redis.asyncio
minio = ">=7.2"     # presigned URL support, type hints

[project.optional-dependencies]
test = [
    "fakeredis[aioredis]>=2.21",
    "pytest-asyncio>=0.23",
]
```

---

*Research completed: 2026-04-02*
*Covers: INFRA-03, INFRA-04 | Does NOT cover: PostgreSQL, SQLAlchemy, Docker, config/env (other researchers)*
