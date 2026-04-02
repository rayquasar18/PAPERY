---
plan: "03"
title: "Database Layer, Models & Alembic"
phase: 1
wave: 2
depends_on: ["01"]
requirements:
  - INFRA-02
  - INFRA-14
  - INFRA-15
files_modified:
  - backend/app/extensions/ext_database.py
  - backend/app/models/base.py
  - backend/app/models/__init__.py
  - backend/app/main.py
  - backend/migrations/env.py
  - backend/migrations/script.py.mako
  - backend/alembic.ini
autonomous: true
estimated_tasks: 4
---

# Plan 03 — Database Layer, Models & Alembic

## Goal

Implement the complete database layer: async SQLAlchemy engine/session factory as an extension, Base model with dual-ID strategy (INFRA-14), UUIDMixin, TimestampMixin, SoftDeleteMixin (INFRA-15), and Alembic async migration setup. The FastAPI lifespan must initialize the database extension on startup.

---

## Tasks

### Task 3.1 — Create SQLAlchemy Base model with mixins (INFRA-14, INFRA-15)

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 3: Database Layer — Base Model + Mixins)
- .planning/phases/01-backend-core-infrastructure/research/02-database-models.md
</read_first>

<action>
Create `backend/app/models/base.py`:

```python
"""SQLAlchemy base model and mixins for all PAPERY models."""
import uuid as uuid_pkg
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Abstract base for all models. Provides auto-increment BigInteger PK."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )


class UUIDMixin:
    """Adds a public-facing UUID column. Used as API identifier instead of id."""

    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid_pkg.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )


class TimestampMixin:
    """Adds created_at and updated_at columns with server-side defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """Soft delete via deleted_at timestamp. Records are never physically deleted."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Return True if this record has been soft-deleted."""
        return self.deleted_at is not None
```

Update `backend/app/models/__init__.py` to barrel-import (critical for Alembic autogenerate):

```python
"""
Model barrel imports — ALL models must be imported here.

Alembic autogenerate relies on this file to discover all models via
Base.metadata. If a model is not imported here, it will NOT be detected
by `alembic revision --autogenerate`.
"""
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
]
```
</action>

<acceptance_criteria>
- `backend/app/models/base.py` contains `class Base(DeclarativeBase):`
- `backend/app/models/base.py` contains `__abstract__ = True`
- `backend/app/models/base.py` contains `id: Mapped[int] = mapped_column(` with `BigInteger`
- `backend/app/models/base.py` contains `class UUIDMixin:`
- `backend/app/models/base.py` contains `UUID(as_uuid=True)`
- `backend/app/models/base.py` contains `default=uuid_pkg.uuid4`
- `backend/app/models/base.py` contains `class TimestampMixin:`
- `backend/app/models/base.py` contains `server_default=func.now()`
- `backend/app/models/base.py` contains `onupdate=func.now()`
- `backend/app/models/base.py` contains `class SoftDeleteMixin:`
- `backend/app/models/base.py` contains `deleted_at: Mapped[datetime | None]`
- `backend/app/models/base.py` contains `def is_deleted(self) -> bool:`
- `backend/app/models/__init__.py` contains `from app.models.base import Base`
- `backend/app/models/__init__.py` contains `from app.models.base import` with all 4 exports
</acceptance_criteria>

---

### Task 3.2 — Create database extension (ext_database.py) with async engine and session factory

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 3: Engine & Session)
- backend/app/core/config/database.py (DatabaseConfig with ASYNC_DATABASE_URI)
- backend/app/models/base.py (created in Task 3.1)
</read_first>

<action>
Create `backend/app/extensions/ext_database.py`:

```python
"""Database extension — async SQLAlchemy engine + session factory."""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level singletons (initialized in init())
engine = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init() -> None:
    """Initialize the async database engine and session factory."""
    global engine, async_session_factory

    engine = create_async_engine(
        settings.ASYNC_DATABASE_URI,
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        pool_recycle=settings.POSTGRES_POOL_RECYCLE,
        pool_pre_ping=True,
        pool_timeout=30,
        echo=settings.DEBUG,
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Verify connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database engine initialized: %s", settings.POSTGRES_HOST)


async def shutdown() -> None:
    """Dispose the engine and release all connections."""
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        logger.info("Database engine disposed")
    engine = None
    async_session_factory = None


async def get_session() -> AsyncSession:
    """Get an async session. Use as FastAPI dependency.

    Usage in routes:
        session: AsyncSession = Depends(get_session)
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call ext_database.init() first.")
    async with async_session_factory() as session:
        yield session  # type: ignore[misc]
```
</action>

<acceptance_criteria>
- `backend/app/extensions/ext_database.py` contains `from sqlalchemy import text`
- `backend/app/extensions/ext_database.py` contains `create_async_engine(`
- `backend/app/extensions/ext_database.py` contains `pool_size=settings.POSTGRES_POOL_SIZE`
- `backend/app/extensions/ext_database.py` contains `pool_pre_ping=True`
- `backend/app/extensions/ext_database.py` contains `expire_on_commit=False`
- `backend/app/extensions/ext_database.py` contains `async def init()`
- `backend/app/extensions/ext_database.py` contains `async def shutdown()`
- `backend/app/extensions/ext_database.py` contains `async def get_session()`
- `backend/app/extensions/ext_database.py` contains `await engine.dispose()`
- `backend/app/extensions/ext_database.py` contains `echo=settings.DEBUG`
- `backend/app/extensions/ext_database.py` contains `settings.ASYNC_DATABASE_URI`
- `backend/app/extensions/ext_database.py` contains `await conn.execute(text("SELECT 1"))`
- `backend/app/extensions/ext_database.py` does NOT contain `__import__("sqlalchemy")`
</acceptance_criteria>

---

### Task 3.3 — Set up Alembic async migrations

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 3: Alembic Async Migrations)
- .planning/phases/01-backend-core-infrastructure/research/02-database-models.md
- backend/app/models/__init__.py (barrel imports, created in Task 3.1)
- backend/app/core/config/__init__.py (settings with ASYNC_DATABASE_URI)
</read_first>

<action>
Create `backend/alembic.ini`:

```ini
[alembic]
script_location = migrations
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(rev)s_%%(slug)s
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[handler_file]
class = FileHandler
args = ('alembic.log',)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Create `backend/migrations/` directory structure:
- `backend/migrations/env.py`
- `backend/migrations/script.py.mako`
- `backend/migrations/versions/` (empty directory with .gitkeep)

Create `backend/migrations/env.py`:

```python
"""Alembic async migration environment."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings

# CRITICAL: Import all models so Base.metadata knows about them
from app.models import Base  # noqa: F401

# Alembic Config object
config = context.config

# Set sqlalchemy.url from app settings
config.set_main_option("sqlalchemy.url", settings.ASYNC_DATABASE_URI)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Configure and run migrations with a given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Create `backend/migrations/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

Create `backend/migrations/versions/.gitkeep` (empty file).
</action>

<acceptance_criteria>
- `backend/alembic.ini` exists and contains `script_location = migrations`
- `backend/alembic.ini` contains `file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(rev)s_%%(slug)s`
- `backend/migrations/env.py` exists and contains `from app.models import Base`
- `backend/migrations/env.py` contains `async_engine_from_config`
- `backend/migrations/env.py` contains `poolclass=pool.NullPool`
- `backend/migrations/env.py` contains `compare_type=True`
- `backend/migrations/env.py` contains `compare_server_default=True`
- `backend/migrations/env.py` contains `config.set_main_option("sqlalchemy.url", settings.ASYNC_DATABASE_URI)`
- `backend/migrations/env.py` contains `target_metadata = Base.metadata`
- `backend/migrations/script.py.mako` exists
- `backend/migrations/versions/.gitkeep` exists
</acceptance_criteria>

---

### Task 3.4 — Wire database extension into FastAPI lifespan

<read_first>
- backend/app/main.py (current state from Plan 01)
- backend/app/extensions/ext_database.py (created in Task 3.2)
</read_first>

<action>
Update `backend/app/main.py` lifespan function to import and call `ext_database.init()` and `ext_database.shutdown()`:

Replace the commented-out placeholder lines in the lifespan with actual calls:

```python
# In the lifespan function, change:
# # await ext_database.init()
# to:
from app.extensions import ext_database

# In the startup section:
await ext_database.init()

# In the shutdown section:
await ext_database.shutdown()
```

The complete updated lifespan should be:

```python
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
```

Add the import at the top of main.py:
```python
from app.extensions import ext_database
```
</action>

<acceptance_criteria>
- `backend/app/main.py` contains `from app.extensions import ext_database`
- `backend/app/main.py` contains `await ext_database.init()`
- `backend/app/main.py` contains `await ext_database.shutdown()`
- `backend/app/main.py` does NOT contain the old comment `# await ext_database.init()` as an active line (the database init is now real, not commented)
</acceptance_criteria>

---

## Verification

After all tasks complete:
1. `cd backend && uv run python -c "from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin; print('Models OK')"` outputs "Models OK"
2. `cd backend && uv run python -c "from app.extensions.ext_database import init, shutdown, get_session; print('DB ext OK')"` outputs "DB ext OK"
3. `cd backend && uv run python -c "from app.models import Base; print(Base.metadata); print('Barrel OK')"` outputs metadata info
4. `cd backend && uv run ruff check app/models/ app/extensions/` passes with no errors
5. With Docker middleware running: `cd backend && uv run alembic heads` succeeds

## must_haves

- [ ] `Base` class uses `BigInteger` primary key with `autoincrement=True` (INFRA-14)
- [ ] `UUIDMixin` provides `uuid` column with `UUID(as_uuid=True)`, `unique=True`, `index=True` (INFRA-14)
- [ ] `TimestampMixin` uses `server_default=func.now()` (not Python-side `default`)
- [ ] `SoftDeleteMixin` uses `deleted_at` timestamp with `is_deleted` property (INFRA-15)
- [ ] `ext_database.py` uses `from sqlalchemy import text` (proper import, no `__import__` anti-pattern)
- [ ] `ext_database.py` creates engine with `expire_on_commit=False` and `pool_pre_ping=True`
- [ ] `get_session()` is an async generator suitable for FastAPI `Depends()`
- [ ] Alembic `env.py` imports `Base` from barrel (`app.models`) to discover all models
- [ ] Alembic uses `NullPool` and async engine for migrations
- [ ] FastAPI lifespan calls `ext_database.init()` on startup and `ext_database.shutdown()` on shutdown
