# Research: Database Layer — PostgreSQL + SQLAlchemy 2.0 Async + Alembic

**Researcher:** Claude
**Date:** 2026-04-02
**Scope:** INFRA-02, INFRA-14, INFRA-15 | Decisions D-05 through D-11

---

## 1. Async Engine & Session Factory

### Engine Setup

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host:5432/papery",
    pool_size=settings.POSTGRES_POOL_SIZE,
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    pool_recycle=settings.POSTGRES_POOL_RECYCLE,
    pool_pre_ping=settings.POSTGRES_POOL_PRE_PING,
    pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
    echo=settings.POSTGRES_ECHO,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # CRITICAL: prevents lazy-load errors after commit
)
```

### Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Driver | `asyncpg` | Fastest async PostgreSQL driver; native prepared statements |
| `expire_on_commit` | `False` | Avoids `MissingGreenlet` errors when accessing attributes post-commit in async |
| Engine disposal | `await engine.dispose()` in FastAPI lifespan `shutdown` | Prevents connection leaks |

### FastAPI Integration (Lifespan Pattern)

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup — engine already created at module level
    yield
    # shutdown — clean up connections
    await engine.dispose()

# Dependency injection for routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## 2. Enterprise Connection Pool Config

All params from env vars via Pydantic Settings. Based on Dify enterprise pattern.

### Config Class (in `backend/app/core/config/database.py`)

```python
class DatabaseConfig(BaseSettings):
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "papery"

    # Pool config — all env-configurable
    POSTGRES_POOL_SIZE: int = Field(default=20, ge=1)
    POSTGRES_MAX_OVERFLOW: int = Field(default=10, ge=0)
    POSTGRES_POOL_RECYCLE: int = Field(default=3600, description="seconds")
    POSTGRES_POOL_PRE_PING: bool = Field(default=True)
    POSTGRES_POOL_TIMEOUT: int = Field(default=30, description="seconds")
    POSTGRES_ECHO: bool = Field(default=False)

    @computed_field
    @property
    def POSTGRES_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
```

### Production Recommendations

| Param | Dev | Prod | Notes |
|-------|-----|------|-------|
| `pool_size` | 5 | 20-30 | Match expected concurrent requests |
| `max_overflow` | 5 | 10-20 | Burst headroom; total max = pool_size + max_overflow |
| `pool_recycle` | 3600 | 3600 | Prevents stale connections (PG default `idle_session_timeout`) |
| `pool_pre_ping` | True | True | Always on — catches dead connections before use |
| `pool_timeout` | 30 | 30 | Raise error rather than hang indefinitely |
| `echo` | True | False | SQL logging only in dev |

---

## 3. Alembic Async Migrations

### Init Command

```bash
cd backend
alembic init -t async migrations
```

This generates an async-ready `env.py` template using `asyncpg`.

### Async `env.py` (Key Parts)

```python
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool  # No pooling for migration scripts

from app.models.base import Base  # Import ALL models via base
target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,           # Detect column type changes
        compare_server_default=True, # Detect default value changes
        render_as_batch=True,        # SQLite compat (not needed but harmless)
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,  # Migration = short-lived, no pool needed
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())
```

### Auto-generate Workflow (D-06)

```bash
# After model changes:
alembic revision --autogenerate -m "add_users_table"
# Review the generated script in migrations/versions/
# Then apply:
alembic upgrade head
```

### Critical: Model Import

All models MUST be imported before `target_metadata` is set, otherwise autogenerate won't detect them. Use a barrel import in `app/models/__init__.py`:

```python
# app/models/__init__.py
from app.models.base import Base
from app.models.user import User
from app.models.project import Project
# ... import every model so metadata registers them
```

### alembic.ini — Key Settings

```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+asyncpg://... (overridden by env.py)
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(rev)s_%%(slug)s
```

Migration files committed to git (D-11). Remove `migrations/versions/` from `.gitignore`.

---

## 4. Dual ID Strategy (INFRA-14)

### Why Dual IDs?

- `id` (int, auto-increment): Fast JOINs, compact indexes, used internally
- `uuid` (UUID v4): Public API identifier, prevents enumeration attacks

### Implementation as Mixin

```python
import uuid as uuid_pkg
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

class UUIDMixin:
    """Public-facing UUID identifier. All API responses use this."""
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid_pkg.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
```

### Base Model with Auto-increment ID

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Abstract base for all models. Provides int PK."""
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
```

### API Contract

- **Incoming requests** (path params, query params): always `uuid`
- **Internal queries** (JOINs, FK references): always `id` (int)
- **API responses**: expose `uuid`, never expose `id`
- **Foreign keys**: use `int` FK to `id` (not UUID FK) for performance

### Index Strategy

```python
# UUID column gets a unique B-tree index (from unique=True + index=True)
# id column gets PK index automatically
# FKs on int id — no composite index needed
```

---

## 5. Soft Delete Mixin (INFRA-15)

### Implementation

```python
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

class SoftDeleteMixin:
    """Soft delete — never physically remove records."""
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,  # Filtered index for queries
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = func.now()
```

### Query Filtering

Two approaches — we choose **explicit filtering** (not `where_criteria` event):

```python
# In every query — explicit is safer, more debuggable
stmt = select(User).where(User.deleted_at.is_(None))

# fastcrud handles this if model has is_deleted column (see §7)
```

**Why not `do_orm_execute` event?** Hidden magic makes debugging harder, and fastcrud already handles soft delete filtering natively.

---

## 6. Complete Base Model

### `backend/app/models/base.py`

```python
import uuid as uuid_pkg
from datetime import datetime

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Abstract base — provides int PK only."""
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
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, index=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

### Usage in Entity Models

```python
class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    # ... FK uses int: tier_id -> tiers.id
    tier_id: Mapped[int | None] = mapped_column(ForeignKey("tiers.id"), nullable=True)
```

---

## 7. fastcrud Integration

### Soft Delete Support

fastcrud natively supports soft delete via two constructor params:

```python
from fastcrud import FastCRUD

crud_users = FastCRUD(
    User,
    is_deleted_column="deleted_at",  # Column name used for soft delete check
    deleted_at_column="deleted_at",  # Column that stores deletion timestamp
    updated_at_column="updated_at",  # Auto-updated on modifications
)
```

**Behavior:**
- `crud_users.delete(db, id=1)` → sets `deleted_at = now()` instead of SQL DELETE
- `crud_users.get(db, id=1)` → auto-filters `deleted_at IS NULL`
- No `is_deleted` boolean column needed — fastcrud checks `deleted_at IS NOT NULL`

### Important Note

Since we use `deleted_at` (timestamp) not a boolean `is_deleted`, configure fastcrud with:
- `is_deleted_column="deleted_at"` — fastcrud treats non-null as "deleted"
- This eliminates the need for a separate boolean column

### Schema Integration

```python
# Schemas exclude id (internal), include uuid (public)
class UserRead(BaseModel):
    uuid: UUID
    email: str
    created_at: datetime
    # No id, no deleted_at, no hashed_password

class UserCreateInternal(BaseModel):
    email: str
    hashed_password: str
    # fastcrud adds created_at/updated_at automatically
```

---

## 8. Ephemeral Test Database (D-10)

### Strategy: Create/Drop Per Test Session

```python
# tests/conftest.py
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

TEST_DB = "papery_test"
ADMIN_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
TEST_URL = f"postgresql+asyncpg://postgres:postgres@localhost:5432/{TEST_DB}"

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create fresh test database for entire test session."""
    admin_engine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        # Terminate existing connections
        await conn.execute(text(
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{TEST_DB}' AND pid <> pg_backend_pid()"
        ))
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB}"))
        await conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    await admin_engine.dispose()

    # Run migrations on test DB
    test_engine = create_async_engine(TEST_URL)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await test_engine.dispose()

    yield

    # Teardown
    admin_engine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(text(
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{TEST_DB}' AND pid <> pg_backend_pid()"
        ))
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB}"))
    await admin_engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    """Per-test session with rollback for isolation."""
    engine = create_async_engine(TEST_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()  # Each test gets clean state
    await engine.dispose()
```

### Key Points

- `scope="session"` — DB created once per `pytest` run, not per test
- Each individual test gets its own session with rollback — full isolation
- Uses `AUTOCOMMIT` isolation to execute `CREATE/DROP DATABASE` outside transaction
- `pg_terminate_backend` prevents "database in use" errors

---

## 9. File Structure Summary

```
backend/
  app/
    core/
      config/
        database.py          # DatabaseConfig (Pydantic Settings)
      db/
        engine.py            # create_async_engine, async_session_factory
        dependencies.py      # get_db() FastAPI dependency
    models/
      __init__.py            # Barrel import of ALL models
      base.py                # Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
      user.py                # User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin)
    crud/
      crud_users.py          # FastCRUD[User, ...]
    schemas/
      user.py                # UserRead, UserCreate, UserCreateInternal, UserUpdate
  migrations/
    alembic.ini
    env.py                   # Async env.py
    versions/                # Auto-generated, committed to git
  tests/
    conftest.py              # Ephemeral test DB setup
```

---

## 10. Gotchas & Pitfalls

| Pitfall | Mitigation |
|---------|------------|
| `MissingGreenlet` on attribute access after commit | Set `expire_on_commit=False` on session factory |
| Alembic autogenerate misses models | Barrel-import ALL models in `models/__init__.py` before metadata |
| `CREATE DATABASE` inside transaction | Use `isolation_level="AUTOCOMMIT"` for admin connection |
| UUID performance on large tables | UUID column is indexed but FKs use int `id` — no UUID joins |
| `pool_pre_ping` overhead | ~1ms per checkout; negligible vs stale connection errors |
| `server_default=func.now()` vs `default=func.now()` | Use `server_default` for DB-level defaults (works with raw SQL, migrations) |
| Soft delete + unique constraints | Add partial unique index: `WHERE deleted_at IS NULL` |
| fastcrud `is_deleted_column` confusion | We pass `"deleted_at"` not `"is_deleted"` since we use timestamp, not boolean |

---

*Research complete. Ready for implementation planning.*
