# Phase 1: Backend Core Infrastructure — Synthesized Research

**Date:** 2026-04-02
**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-09, INFRA-11, INFRA-14, INFRA-15

---

## 1. Monorepo Structure

### Layout

```
PAPERY/
├── backend/                 # Python FastAPI service
│   ├── app/                 # Application code (FLAT — no src/ nesting)
│   │   ├── main.py          # FastAPI app + lifespan
│   │   ├── api/v1/          # Route handlers (thin)
│   │   ├── core/config/     # Modular Pydantic Settings
│   │   ├── extensions/      # ext_database, ext_redis, ext_minio (singletons)
│   │   ├── models/          # SQLAlchemy ORM + mixins
│   │   ├── schemas/         # Pydantic v2 (Read/Create/Update/Delete variants)
│   │   ├── crud/            # fastcrud instances (pure data access)
│   │   ├── services/        # Business logic orchestration
│   │   └── middleware/       # HTTP middleware
│   ├── migrations/          # Alembic (committed to git)
│   ├── tests/               # pytest suite
│   ├── scripts/             # Seed data, bootstrap
│   ├── pyproject.toml       # uv config + tool configs (ruff, mypy, pytest)
│   ├── uv.lock              # Committed to git
│   └── .python-version      # "3.12"
├── frontend/                # Next.js (Phase 2+)
├── docker/
│   ├── docker-compose.yaml              # Full stack (prod/CI)
│   ├── docker-compose.middleware.yaml   # DB+Redis+MinIO only (daily dev)
│   ├── middleware.env.example
│   └── volumes/             # Bind mounts (gitignored)
├── Makefile                 # Root-level automation
├── .pre-commit-config.yaml
└── .env.example             # Single source of truth for env vars
```

**Key decision:** `backend/app/` NOT `backend/src/app/` — simpler imports, Dify-aligned. All imports use `app.` prefix: `from app.core.config import settings`.

---

## 2. FastAPI Layered Architecture (INFRA-01)

### Layer Flow

```
HTTP Request → Router → Dependencies → Service → CRUD → Model → PostgreSQL
```

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Router | `api/v1/*.py` | Path defs, response models, thin (no business logic) |
| Dependencies | `api/dependencies.py` | Auth (JWT), DB session, rate limiting |
| Service | `services/*.py` | Business logic, transaction boundaries, multi-CRUD orchestration |
| CRUD | `crud/*.py` | fastcrud instances, pure data access |
| Schema | `schemas/*.py` | Pydantic v2 models (Read/Create/Update/Delete/Internal) |
| Model | `models/*.py` | SQLAlchemy 2.0 ORM, mixins |

**Why add Service layer (vs v0):** v0 put business logic in routers, making them fat and untestable. Services are testable without HTTP, reusable across endpoints, and own transaction boundaries.

### Import Direction (Strict DAG — no cycles)

```
routers  → dependencies, services, schemas
services → crud, schemas, models, core
crud     → models, schemas, core.db
models   → core.db.base (mixins only)
schemas  → nothing internal (pure Pydantic)
```

### Extensions Pattern (Dify-inspired Lifespan)

Each `ext_*.py` exports module-level singletons + `init()`/`shutdown()`:

```python
# backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    await ext_database.init()   # startup: order matters
    await ext_redis.init()
    await ext_minio.init()
    yield
    await ext_minio.shutdown()  # shutdown: reverse order
    await ext_redis.shutdown()
    await ext_database.shutdown()
```

Singletons imported anywhere: `from app.extensions.ext_database import async_session_factory`

---

## 3. Database Layer (INFRA-02, INFRA-14, INFRA-15)

### Engine & Session

```python
engine = create_async_engine(
    settings.database.ASYNC_DATABASE_URI,
    pool_size=20, max_overflow=10, pool_recycle=3600,
    pool_pre_ping=True, pool_timeout=30, echo=settings.app.DEBUG,
)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False  # CRITICAL: prevents MissingGreenlet
)
```

| Decision | Choice | Why |
|----------|--------|-----|
| Driver | `asyncpg` | Fastest async PG driver |
| `expire_on_commit` | `False` | Avoids `MissingGreenlet` errors post-commit in async |
| Pool pre-ping | `True` | Catches dead connections (~1ms overhead, worth it) |

### Dual ID Strategy (INFRA-14)

- `id` (BigInteger, auto-increment): internal FKs, JOINs — fast, compact
- `uuid` (UUID v4): public API identifier — prevents enumeration

**API contract:** Incoming requests use `uuid`. Internal queries use `id`. API responses expose `uuid`, never `id`. FKs reference `id` (int), not uuid.

### Base Model + Mixins

```python
class Base(DeclarativeBase):
    __abstract__ = True
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

class UUIDMixin:
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_pkg.uuid4, unique=True, nullable=False, index=True
    )

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class SoftDeleteMixin:  # INFRA-15
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, index=True
    )
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

**Usage:** `class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin)`

**Soft delete gotcha:** Use `deleted_at` (timestamp), not a boolean `is_deleted` column. Partial unique indexes need `WHERE deleted_at IS NULL` for unique-with-soft-delete.

### Alembic Async Migrations

```bash
cd backend && alembic init -t async migrations
```

- Use `NullPool` for migration scripts (short-lived, no pooling needed)
- Set `compare_type=True` + `compare_server_default=True` in `context.configure()`
- **CRITICAL:** Barrel-import ALL models in `models/__init__.py` before `target_metadata` — otherwise autogenerate misses them
- File template: `%%(year)d_%%(month).2d_%%(day).2d_%%(rev)s_%%(slug)s`
- Migration files committed to git

### fastcrud Integration

```python
crud_users = FastCRUD(
    User,
    is_deleted_column="deleted_at",   # uses timestamp, not boolean
    deleted_at_column="deleted_at",
    updated_at_column="updated_at",
)
```

- `delete()` → sets `deleted_at = now()` (no SQL DELETE)
- `get()`/`get_multi()` → auto-filters `deleted_at IS NULL`
- Supports `__gt`, `__lt`, `__ne` operators for advanced filtering
- `return_total_count=True` for paginated queries

### Schema Separation Pattern

| Suffix | Purpose | Example |
|--------|---------|---------|
| `Read` | Public API response (safe fields) | No password hash, no `id` |
| `CreateInternal` | Service creates (adds computed fields) | Adds uuid, hashed_pw |
| `Update` | Partial update (all Optional) | |
| `Delete` | Soft delete trigger | Sets deleted_at |

---

## 4. Redis Namespace Isolation (INFRA-03)

### Three Separate Clients, Isolated by DB Number

| Namespace | DB | Purpose |
|-----------|-----|---------|
| Cache | 0 | Response caching, session data |
| Queue | 1 | ARQ task queue |
| Rate Limit | 2 | Per-user/IP rate counters |

**Why separate clients (not SELECT)?** `SELECT` changes db on a connection — unsafe with connection pools since coroutines share the pool.

### Client Configuration

```python
pool = aioredis.ConnectionPool(
    host=host, port=port, db=db, password=password or None,
    max_connections=20,
    decode_responses=True,       # Return str not bytes
    health_check_interval=30,    # Ping every 30s
    socket_timeout=5.0,
    socket_connect_timeout=5.0,
    retry_on_timeout=True,
)
```

### Extension Pattern

- `init()`: Create 3 clients, `ping()` each (fail-fast if unreachable)
- `shutdown()`: `aclose()` each (not `close()` — `aclose()` is async-native in redis-py 5.x)
- **Library:** `redis[hiredis]>=5.2.0` (hiredis = C parser, 10x faster)

---

## 5. MinIO Presigned URLs (INFRA-04)

### Key Facts

- MinIO SDK is **synchronous only** (uses urllib3) — no async SDK exists
- Presigned URL generation is **local crypto signing** (no network call) — safe to call synchronously
- Bucket operations (`make_bucket`, `bucket_exists`) are network calls — only at startup

### Presigned URL Defaults

| Operation | Method | Default Expiry | Max |
|-----------|--------|----------------|-----|
| Download | `presigned_get_object` | 1 hour | 7 days |
| Upload | `presigned_put_object` | 30 minutes | 7 days |

### Async Consideration

For large server-side uploads, wrap sync calls with `run_in_executor`:
```python
await loop.run_in_executor(None, partial(upload_file, object_name, data, content_type))
```

For presigned URLs: sync is fine (no I/O).

### Extension Pattern

- `init()`: Create `Minio` client, auto-create bucket if not exists
- `shutdown()`: No-op (urllib3 manages connections internally)

---

## 6. Pydantic Settings Config (INFRA-09)

### Composition via Multiple Inheritance

```python
class AppSettings(AppConfig, DatabaseConfig, RedisConfig, MinioConfig,
                  SecurityConfig, EmailConfig, CorsConfig, AdminConfig):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8",
        extra="ignore", case_sensitive=True,
    )
```

**Rules:**
- `model_config` on ROOT class ONLY (avoids MRO conflicts)
- `extra="ignore"` — unknown vars don't error
- `case_sensitive=True` — UPPER_CASE exclusively
- NO `env_prefix` — explicit naming (`POSTGRES_*`, `REDIS_CACHE_*`)
- Singleton: `settings = AppSettings()` in `__init__.py` — validates at import

### Startup Validation

```python
@model_validator(mode="after")
def validate_startup(self) -> Self:
    # SECRET_KEY: reject placeholders, enforce >= 32 chars
    # Non-local: reject placeholder passwords for POSTGRES_PASSWORD, MINIO_SECRET_KEY
    # Production: require SMTP_HOST
```

### Key Patterns

| Pattern | Decorator | Use |
|---------|-----------|-----|
| CSV → list | `@field_validator("CORS_ORIGINS", mode="before")` | Parse `"a,b,c"` → `["a","b","c"]` |
| Computed URL | `@computed_field` + `@property` | `ASYNC_DATABASE_URI` with `quote_plus()` |
| Cross-field validation | `@model_validator(mode="after")` | Environment-dependent checks |

### Env Loading Priority (First Wins)

Init kwargs → Environment variables → `.env` file → Secrets dir → Defaults

---

## 7. Docker Compose Dev Environment (INFRA-11)

### Split Strategy

| File | Purpose | When |
|------|---------|------|
| `docker-compose.middleware.yaml` | DB + Redis + MinIO only | **Daily dev** (app runs locally) |
| `docker-compose.yaml` | Full stack | CI, staging, production |

Both are **standalone** (not overrides). Middleware file uses `env_file: [./middleware.env]`.

### Service Definitions

| Service | Image | Port | Healthcheck |
|---------|-------|------|-------------|
| PostgreSQL 17 | `postgres:17-alpine` | 5432 | `pg_isready -U <user> -d <db>` |
| Redis 7 | `redis:7-alpine` | 6379 | `redis-cli ping \| grep PONG` |
| MinIO | `minio/minio:latest` | 9000/9001 | `curl -f localhost:9000/minio/health/live` |

**Key patterns:**
- `restart: unless-stopped` — survives reboot
- Bind-mount volumes at `docker/volumes/` (gitignored)
- `${VAR:-default}` for host-side substitution
- `condition: service_healthy` for `depends_on` in full-stack compose
- Redis uses `REDISCLI_AUTH` env to suppress `-a password` warning in healthcheck
- PG uses `command:` to pass tuning params (`max_connections`, `shared_buffers`)

### Networking

| Context | PostgreSQL | Redis | MinIO |
|---------|-----------|-------|-------|
| Local dev | `localhost:5432` | `localhost:6379` | `localhost:9000` |
| Full stack | `db:5432` | `redis:6379` | `minio:9000` |

### Dockerfile.dev (Backend)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

Use `python:3.12-slim` (not Alpine — avoids musl/wheel issues). Deps cached separately for fast rebuilds.

---

## 8. Dev Tooling (uv + Makefile + Linting)

### uv Package Manager

**Mode:** `package = false` (app, not library)

```toml
[tool.uv]
package = false
default-groups = ["dev"]
```

**Key commands:** `uv sync --dev` (install), `uv run pytest` (execute), `uv lock` (resolve). `uv.lock` committed to git.

**Dependency groups:** Use `[dependency-groups]` (PEP 735), not `[project.optional-dependencies]`.

### Core Dependencies

```toml
dependencies = [
    "fastapi>=0.115.0", "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.35", "asyncpg>=0.30.0", "alembic>=1.14.0",
    "pydantic>=2.10.0", "pydantic-settings>=2.6.0",
    "redis[hiredis]>=5.2.0", "minio>=7.2",
    "fastcrud>=0.16.0", "python-multipart>=0.0.18",
    "python-jose[cryptography]>=3.3.0", "passlib[bcrypt]>=1.7.4", "httpx>=0.28.0",
]
```

### Ruff Config (Key Ignores for FastAPI)

```toml
[tool.ruff.lint]
ignore = [
    "B008",    # FastAPI Depends() in function defaults is idiomatic
    "RUF012",  # SQLAlchemy mutable class vars
    "S105",    # False positives in config schemas
]
```

Enable: `ASYNC` (async mistakes), `UP` (pyupgrade to 3.12+), `S` (security), `PT` (pytest style).

### Mypy Config

- `plugins = ["pydantic.mypy"]` — needed for BaseModel typing
- SQLAlchemy mypy plugin is **DEPRECATED** — do NOT use it. `Mapped[]` works natively.
- `ignore_missing_imports = true` for `fastcrud.*`
- Start with `strict = false`, tighten over time

### pytest Config

```toml
asyncio_mode = "auto"    # auto-detect async tests
markers = ["slow", "integration"]
```

### Makefile Targets

| Target | Action |
|--------|--------|
| `dev-setup` | Start Docker middleware + install deps + run migrations |
| `dev-clean` | Stop Docker middleware, remove volumes |
| `lint` | `ruff format` + `ruff check --fix` |
| `type-check` | `mypy` |
| `test` / `test-cov` | pytest with optional coverage |
| `migrate` / `migrate-new MSG='...'` | Alembic upgrade / new revision |

---

## 9. Testing Strategy

### Unit Tests (No External Services)

| Service | Mock Strategy |
|---------|---------------|
| Redis | `fakeredis[aioredis]` — drop-in replacement, no Docker needed |
| MinIO | `unittest.mock.MagicMock` — presigned URLs are pure computation |
| Database | Per-test session with rollback for isolation |

### Integration Tests

| Service | Strategy |
|---------|----------|
| Redis | Real Redis, `db=15` (never conflicts with app db 0/1/2), `flushdb()` per test |
| MinIO | Real MinIO, `test-*` bucket prefix, cleanup after test |
| Database | Ephemeral `papery_test` DB, created per session, `Base.metadata.create_all` |

### Ephemeral Test Database

- Create/drop per pytest session (not per test)
- Use `AUTOCOMMIT` isolation for `CREATE/DROP DATABASE` (can't run inside transaction)
- `pg_terminate_backend` prevents "database in use" errors
- Each test gets own session with rollback

---

## 10. Critical Gotchas

| Pitfall | Mitigation |
|---------|------------|
| `MissingGreenlet` after commit | `expire_on_commit=False` on session factory |
| Alembic misses models | Barrel-import ALL models in `models/__init__.py` |
| `CREATE DATABASE` inside transaction | `isolation_level="AUTOCOMMIT"` for admin connection |
| UUID FK performance | FKs use int `id`, never UUID — no UUID joins |
| `server_default` vs `default` | Use `server_default=func.now()` for DB-level defaults |
| Soft delete + unique constraints | Partial unique index: `WHERE deleted_at IS NULL` |
| fastcrud `is_deleted_column` | Pass `"deleted_at"` (timestamp), not `"is_deleted"` (boolean) |
| Redis `SELECT` with pools | Use separate clients per namespace, not `SELECT` |
| Redis `close()` vs `aclose()` | Use `aclose()` in redis-py 5.x (async-native) |
| MinIO SDK is sync | OK for presigned URLs (no I/O); use `run_in_executor` for uploads |
| `model_config` MRO conflict | Declare `model_config` on root AppSettings ONLY |
| Pydantic `env_prefix` | NOT used — explicit naming per service prefix |
| Alpine Docker images | Use `slim` to avoid musl/wheel compilation issues |

---

## Validation Architecture

### INFRA-01: FastAPI Layered Architecture
- **Verify:** App starts with `uvicorn app.main:app`
- **Verify:** `GET /docs` returns Swagger UI
- **Verify:** Lifespan initializes all extensions (check logs for Redis ping, MinIO bucket, DB engine)
- **Verify:** Import DAG has no cycles (ruff + mypy pass)

### INFRA-02: PostgreSQL + SQLAlchemy + Alembic
- **Verify:** `alembic upgrade head` creates tables successfully
- **Verify:** `alembic revision --autogenerate` detects model changes
- **Verify:** Session dependency injects correctly in route handlers
- **Verify:** Connection pool stats visible in debug logs (`echo=True`)

### INFRA-03: Redis Namespace Isolation
- **Verify:** Three separate Redis clients connect to db 0, 1, 2
- **Verify:** `ping()` succeeds for all three during startup
- **Verify:** Data written to cache (db=0) is NOT visible from queue (db=1)
- **Verify:** `fakeredis` tests pass without real Redis running

### INFRA-04: MinIO Presigned URLs
- **Verify:** Bucket auto-created on startup if missing
- **Verify:** `presigned_get_object` returns signed URL string
- **Verify:** Upload via presigned PUT URL succeeds (integration test)
- **Verify:** Download via presigned GET URL returns correct file

### INFRA-09: Pydantic Settings Config
- **Verify:** App crashes on startup with placeholder `SECRET_KEY`
- **Verify:** `ASYNC_DATABASE_URI` computed correctly with special chars in password
- **Verify:** `CORS_ORIGINS` parses CSV string from env var
- **Verify:** Real env vars override `.env` file values

### INFRA-11: Docker Compose Dev Environment
- **Verify:** `make dev-setup` starts middleware + installs deps + runs migrations
- **Verify:** All healthchecks pass (`docker compose ps` shows "healthy")
- **Verify:** Backend connects to `localhost:5432/6379/9000` successfully
- **Verify:** `make dev-clean` tears down containers and volumes

### INFRA-14: Dual ID Strategy
- **Verify:** Models have both `id` (BigInteger PK) and `uuid` (UUID, unique, indexed)
- **Verify:** API responses contain `uuid`, never `id`
- **Verify:** ForeignKey columns reference `id` (int), not `uuid`

### INFRA-15: Soft Delete Mixin
- **Verify:** `crud.delete()` sets `deleted_at` timestamp (no SQL DELETE)
- **Verify:** `crud.get()` excludes soft-deleted records by default
- **Verify:** `is_deleted` property returns `True` when `deleted_at` is set
- **Verify:** Partial unique indexes work with `WHERE deleted_at IS NULL`

---

## RESEARCH COMPLETE
