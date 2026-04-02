# Research: Monorepo Structure + FastAPI Layered Architecture

**Researcher:** Claude  
**Date:** 2026-04-02  
**Scope:** Monorepo layout, FastAPI layered architecture, extensions/lifespan pattern, fastcrud integration  
**Requirements:** INFRA-01, D-01, D-02, D-04

---

## 1. Monorepo Layout (Dify Enterprise Pattern)

### 1.1 Root Structure

Dify uses a flat monorepo with clear top-level separation. Adapted for PAPERY:

```
PAPERY/
├── backend/                 # Python FastAPI service
│   ├── app/                 # Application code (FLAT — no src/ nesting)
│   ├── migrations/          # Alembic migrations
│   ├── scripts/             # Seed data, bootstrap utilities
│   ├── tests/               # Pytest test suite
│   ├── pyproject.toml       # uv/Poetry config + dependencies
│   ├── uv.lock              # Lock file
│   ├── alembic.ini          # Alembic config
│   ├── Dockerfile           # Production multi-stage
│   ├── Dockerfile.dev       # Dev (quick build, hot-reload)
│   └── .env.example         # Template env vars
├── frontend/                # Next.js application
│   ├── src/
│   ├── package.json
│   └── ...
├── docker/                  # Docker Compose files (NOT inside backend/)
│   ├── docker-compose.yaml           # Full stack (prod)
│   ├── docker-compose.middleware.yaml # DB + Redis + MinIO only (dev)
│   └── middleware.env.example
├── scripts/                 # Root-level automation scripts
├── Makefile                 # Dev environment management
├── .env.example             # Single root env template
├── CLAUDE.md
├── README.md
└── ...
```

### 1.2 Key Decision: `backend/app/` NOT `backend/src/app/`

Per D-02, use flat structure matching Dify's `api/` pattern. The `src/` nesting from v0 is removed:
- **Before (v0):** `backend/src/app/main.py` — extra nesting, no benefit
- **After (v1):** `backend/app/main.py` — simpler imports, Dify-aligned

Python path: the `backend/` directory is the working directory. Imports use `app.` prefix:
```python
from app.core.config import settings
from app.models.user import User
```

### 1.3 Makefile Targets (Adapted from Dify)

```makefile
.PHONY: dev-setup prepare-docker prepare-api prepare-web dev-clean

dev-setup: prepare-docker prepare-api prepare-web
    @echo "Dev environment ready!"

prepare-docker:
    @cp -n docker/middleware.env.example docker/middleware.env 2>/dev/null || true
    @cd docker && docker compose -f docker-compose.middleware.yaml up -d

prepare-api:
    @cp -n backend/.env.example backend/.env 2>/dev/null || true
    @cd backend && uv sync --dev
    @cd backend && uv run alembic upgrade head

prepare-web:
    @cp -n frontend/.env.example frontend/.env.local 2>/dev/null || true
    @cd frontend && pnpm install

dev-clean:
    @cd docker && docker compose -f docker-compose.middleware.yaml down -v

lint:
    @uv run --project backend --dev ruff format ./backend
    @uv run --project backend --dev ruff check --fix ./backend

test:
    @uv run --project backend --dev pytest backend/tests/

migrate:
    @cd backend && uv run alembic upgrade head

seed:
    @cd backend && uv run python scripts/seed.py
```

---

## 2. FastAPI Layered Architecture

### 2.1 Layer Flow (INFRA-01)

```
HTTP Request
    |
    v
[Router Layer]        backend/app/api/v1/*.py
    |                 - Path definitions, response models
    |                 - Thin: validates input, calls service, returns response
    v
[Dependencies]        backend/app/api/dependencies.py
    |                 - Auth (JWT decode, user loading)
    |                 - DB session injection
    |                 - Rate limiting
    v
[Service Layer]       backend/app/services/*.py        [NEW — v0 lacked this]
    |                 - Business logic orchestration
    |                 - Calls multiple CRUDs, external APIs
    |                 - Transaction boundaries
    v
[CRUD Layer]          backend/app/crud/*.py
    |                 - fastcrud instances (pure data access)
    |                 - No business logic, no HTTP concerns
    v
[Schema Layer]        backend/app/schemas/*.py
    |                 - Pydantic v2 models
    |                 - Read/Create/Update/Delete/Internal variants
    v
[Model Layer]         backend/app/models/*.py
    |                 - SQLAlchemy 2.0 ORM (mapped_column)
    |                 - Mixins: UUID, Timestamp, SoftDelete
    v
[Database]            PostgreSQL via asyncpg
```

### 2.2 Why Add a Service Layer (vs v0)

v0 put business logic directly in routers. Problems:
- Routers became fat (auth + validation + business logic + CRUD calls)
- Hard to test business logic in isolation
- No reuse across endpoints

Service layer benefits:
- Routers stay thin (HTTP concern only)
- Services are testable without HTTP
- Transaction boundaries live in service methods
- Services can orchestrate multiple CRUDs

### 2.3 Import Direction (Strict DAG — No Cycles)

```
routers  -> dependencies, services, schemas
services -> crud, schemas, models, core
crud     -> models, schemas, core.db
models   -> core.db.base (mixins only)
schemas  -> nothing internal (pure Pydantic)
core     -> core siblings only
```

---

## 3. Flat `backend/app/` Structure (D-02)

```
backend/app/
├── __init__.py
├── main.py                      # FastAPI app instantiation + lifespan
│
├── api/                         # HTTP interface
│   ├── __init__.py              # Top-level /api router
│   ├── dependencies.py          # Depends() providers (auth, db, rate limit)
│   └── v1/                      # API version 1
│       ├── __init__.py          # Aggregates all v1 routers
│       ├── auth.py
│       ├── users.py
│       └── ...
│
├── core/                        # Cross-cutting infrastructure
│   ├── __init__.py
│   ├── config/                  # Modular Pydantic Settings (D-15)
│   │   ├── __init__.py          # Exports composed AppConfig
│   │   ├── app.py               # APP_NAME, DEBUG, ENVIRONMENT
│   │   ├── database.py          # POSTGRES_* + pool config
│   │   ├── redis.py             # REDIS_CACHE_*, REDIS_QUEUE_*, REDIS_RATE_LIMIT_*
│   │   ├── minio.py             # MINIO_*
│   │   ├── security.py          # SECRET_KEY, JWT settings
│   │   ├── email.py             # SMTP_*
│   │   └── cors.py              # CORS_ORIGINS
│   ├── security.py              # JWT encode/decode, bcrypt, OAuth2 scheme
│   ├── logger.py                # Structured logging
│   └── exceptions/              # Custom HTTP exceptions
│       ├── __init__.py
│       └── http.py              # 401, 403, 404, 409, 429
│
├── extensions/                  # Service initializers (Dify-inspired)
│   ├── __init__.py
│   ├── ext_database.py          # SQLAlchemy async engine + session factory
│   ├── ext_redis.py             # Redis connections (3 logical namespaces)
│   └── ext_minio.py             # MinIO client + bucket init
│
├── models/                      # SQLAlchemy ORM models
│   ├── __init__.py              # Import all models (Alembic discovery)
│   ├── base.py                  # DeclarativeBase + mixins (UUID, Timestamp, SoftDelete)
│   ├── user.py
│   └── ...
│
├── schemas/                     # Pydantic v2 schemas
│   ├── __init__.py
│   ├── base.py                  # Shared base schemas (APIResponse, PaginatedResponse)
│   ├── user.py                  # UserRead, UserCreate, UserCreateInternal, UserUpdate
│   └── ...
│
├── crud/                        # fastcrud repository instances
│   ├── __init__.py
│   ├── crud_users.py
│   └── ...
│
├── services/                    # Business logic
│   ├── __init__.py
│   ├── user_service.py
│   └── ...
│
└── middleware/                   # HTTP middleware
    ├── __init__.py
    └── cache.py                 # Cache-Control headers
```

---

## 4. FastAPI Lifespan + Extensions Pattern

### 4.1 Dify's Pattern (Flask → FastAPI Adaptation)

Dify uses `extensions/ext_*.py` modules, each with `init_app(app)` function. They are initialized in order during `create_app()`. We adapt this for FastAPI's lifespan pattern.

### 4.2 Extension Module Contract

Each extension file in `backend/app/extensions/` follows this contract:

```python
# backend/app/extensions/ext_database.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

# Module-level singletons (initialized during lifespan)
engine = None
async_session_factory = None

async def init() -> None:
    """Called during app startup."""
    global engine, async_session_factory
    engine = create_async_engine(
        str(settings.database.ASYNC_DATABASE_URI),
        pool_size=settings.database.POOL_SIZE,
        max_overflow=settings.database.MAX_OVERFLOW,
        pool_recycle=settings.database.POOL_RECYCLE,
        pool_pre_ping=settings.database.POOL_PRE_PING,
        echo=settings.app.DEBUG,
    )
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

async def shutdown() -> None:
    """Called during app shutdown."""
    global engine
    if engine:
        await engine.dispose()

async def get_session() -> AsyncSession:
    """Dependency for route handlers."""
    async with async_session_factory() as session:
        yield session
```

### 4.3 Lifespan Wiring in main.py

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.extensions import ext_database, ext_redis, ext_minio
from app.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — order matters
    await ext_database.init()
    await ext_redis.init()
    await ext_minio.init()

    yield

    # Shutdown — reverse order
    await ext_minio.shutdown()
    await ext_redis.shutdown()
    await ext_database.shutdown()

app = FastAPI(
    title="PAPERY API",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api")
```

### 4.4 Why This Pattern

- **Explicit ordering:** Extensions init in defined sequence (DB before Redis, etc.)
- **Module-level singletons:** Accessed anywhere via `from app.extensions.ext_database import async_session_factory`
- **Testable:** Can mock extensions or init with test configs
- **Dify-aligned:** Same mental model as Dify's `init_app()` pattern, adapted for async

---

## 5. fastcrud Integration

### 5.1 Core Concept

fastcrud eliminates CRUD boilerplate. You instantiate `FastCRUD` with a model and get typed `create`, `get`, `get_multi`, `update`, `delete`, `exists` methods.

### 5.2 Class Signature

```python
from fastcrud import FastCRUD

class FastCRUD(
    Generic[
        ModelType,          # SQLAlchemy model
        CreateSchemaType,   # Pydantic create schema
        UpdateSchemaType,   # Pydantic update schema
        UpdateSchemaInternalType,  # Internal update (computed fields)
        DeleteSchemaType,   # Soft delete trigger schema
        SelectSchemaType,   # Response/select schema
    ]
)
```

### 5.3 CRUD Instance Definition

```python
# backend/app/crud/crud_users.py
from fastcrud import FastCRUD
from app.models.user import User
from app.schemas.user import (
    UserCreateInternal,
    UserUpdate,
    UserUpdateInternal,
    UserDelete,
    UserRead,
)

CRUDUser = FastCRUD[
    User,
    UserCreateInternal,
    UserUpdate,
    UserUpdateInternal,
    UserDelete,
    UserRead,
]
crud_users = CRUDUser(User)
```

### 5.4 Key Methods

```python
# Create
user = await crud_users.create(db=session, object=UserCreateInternal(...))

# Get single (kwargs filtering)
user = await crud_users.get(db=session, email="test@example.com", is_deleted=False)

# Get multiple (paginated)
result = await crud_users.get_multi(
    db=session,
    offset=0,
    limit=20,
    sort_columns=["created_at"],
    sort_orders=["desc"],
    is_deleted=False,
    schema_to_select=UserRead,
    return_total_count=True,
)

# Update
await crud_users.update(db=session, object=UserUpdate(name="New"), id=user_id)

# Soft delete (auto-detected if model has is_deleted column)
await crud_users.delete(db=session, id=user_id)

# Check existence
exists = await crud_users.exists(db=session, email="test@example.com")
```

### 5.5 Advanced Filtering

```python
# Comparison operators via double-underscore suffix
users = await crud_users.get_multi(
    db=session,
    age__gt=18,                    # age > 18
    created_at__lt=cutoff_date,    # created before cutoff
    username__ne="admin",          # not admin
)
```

### 5.6 Soft Delete Configuration

fastcrud auto-detects soft delete columns. Defaults:
- `is_deleted_column="is_deleted"` — boolean flag
- `deleted_at_column="deleted_at"` — timestamp
- `updated_at_column="updated_at"` — auto-updated

Custom column names:
```python
crud_users = FastCRUD(User, is_deleted_column="archived", deleted_at_column="archived_at")
```

When `delete()` is called, if the model has the `is_deleted` column, it sets `is_deleted=True` + `deleted_at=now()` instead of hard deleting.

### 5.7 Usage in Service Layer

```python
# backend/app/services/user_service.py
from app.crud.crud_users import crud_users
from app.schemas.user import UserCreate, UserCreateInternal, UserRead

class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, data: UserCreate) -> UserRead:
        # Business logic: hash password, generate UUID, etc.
        internal = UserCreateInternal(
            **data.model_dump(),
            hashed_password=hash_password(data.password),
            uuid=uuid4(),
        )
        user = await crud_users.create(
            db=db, object=internal, schema_to_select=UserRead, return_as_model=True
        )
        return user
```

---

## 6. Schema Separation Pattern (v0 → v1 Carry Forward)

| Suffix | Purpose | Example |
|--------|---------|---------|
| `Read` | Public API response (safe fields) | `UserRead` — no password hash |
| `ReadInternal` | Internal use (all fields) | `UserReadInternal` — includes hash |
| `Create` | Public create request | `UserCreate` — name, email, password |
| `CreateInternal` | Service creates (computed fields added) | `UserCreateInternal` — adds uuid, hashed_pw |
| `Update` | Partial update (all Optional) | `UserUpdate` — name?, email? |
| `UpdateInternal` | Service update (computed fields) | `UserUpdateInternal` — adds updated_at |
| `Delete` | Soft delete trigger | `UserDelete` — sets is_deleted, deleted_at |

---

## 7. Model Mixins (v0 → v1 Carry Forward)

```python
# backend/app/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, Boolean, Integer
from datetime import datetime
import uuid as uuid_pkg

class Base(DeclarativeBase):
    pass

class UUIDMixin:
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        default=uuid_pkg.uuid4, unique=True, index=True
    )

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=datetime.utcnow
    )

class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
```

All models inherit: `Base, UUIDMixin, TimestampMixin, SoftDeleteMixin`

Dual-ID strategy (INFRA-14): `id` (int autoincrement, internal FK) + `uuid` (public API identifier).

---

## 8. Implementation Checklist

- [ ] Create root `Makefile` with `dev-setup`, `dev-clean`, `lint`, `test`, `migrate`, `seed`
- [ ] Create `backend/app/` flat structure with all directories
- [ ] Create `backend/app/main.py` with lifespan pattern
- [ ] Create `backend/app/extensions/` with `ext_database.py`, `ext_redis.py`, `ext_minio.py`
- [ ] Create `backend/app/models/base.py` with `Base` + 3 mixins
- [ ] Create `backend/app/schemas/base.py` with `APIResponse`, `PaginatedResponse`
- [ ] Create `backend/app/crud/__init__.py` — verify fastcrud works with SQLAlchemy 2.0 async
- [ ] Create `backend/app/services/__init__.py` — establish service layer pattern
- [ ] Create `backend/app/api/v1/__init__.py` — router aggregator
- [ ] Create `backend/app/api/dependencies.py` — DB session dependency
- [ ] Create `docker/docker-compose.middleware.yaml` for dev
- [ ] Create `.env.example` at root

---

*Research complete. Ready for planning phase.*
