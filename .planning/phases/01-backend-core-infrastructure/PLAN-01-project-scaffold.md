---
plan: "01"
title: "Project Scaffold & Python Tooling"
phase: 1
wave: 1
depends_on: []
requirements:
  - INFRA-01
  - INFRA-09
files_modified:
  - backend/pyproject.toml
  - backend/.python-version
  - backend/app/__init__.py
  - backend/app/main.py
  - backend/app/api/__init__.py
  - backend/app/api/v1/__init__.py
  - backend/app/api/v1/health.py
  - backend/app/api/dependencies.py
  - backend/app/core/__init__.py
  - backend/app/core/config/__init__.py
  - backend/app/core/config/app.py
  - backend/app/core/config/database.py
  - backend/app/core/config/redis.py
  - backend/app/core/config/minio.py
  - backend/app/core/config/security.py
  - backend/app/core/config/email.py
  - backend/app/core/config/cors.py
  - backend/app/core/config/admin.py
  - backend/app/extensions/__init__.py
  - backend/app/models/__init__.py
  - backend/app/schemas/__init__.py
  - backend/app/crud/__init__.py
  - backend/app/services/__init__.py
  - backend/app/middleware/__init__.py
  - backend/tests/__init__.py
  - backend/tests/conftest.py
  - backend/scripts/.gitkeep
  - .env.example
  - .pre-commit-config.yaml
autonomous: true
estimated_tasks: 6
---

# Plan 01 — Project Scaffold & Python Tooling

## Goal

Create the complete backend directory structure, pyproject.toml with all dependencies and tool configs, Pydantic Settings configuration system, and a minimal FastAPI app that starts successfully. This is the foundation everything else builds on.

---

## Tasks

### Task 1.1 — Create pyproject.toml with all dependencies and tool configs

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (sections 8: Dev Tooling)
</read_first>

<action>
Create `backend/pyproject.toml` with the following exact content:

```toml
[project]
name = "papery-backend"
version = "0.1.0"
description = "PAPERY — AI-powered document intelligence platform (backend)"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.35",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "redis[hiredis]>=5.2.0",
    "minio>=7.2",
    "fastcrud>=0.16.0",
    "python-multipart>=0.0.18",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "httpx>=0.28.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.0",
    "fakeredis[aioredis]>=2.25.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "pre-commit>=4.0.0",
]

[tool.uv]
package = false
default-groups = ["dev"]

[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "S", "T20", "PT", "ASYNC", "RUF"]
ignore = [
    "B008",
    "RUF012",
    "S105",
]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.mypy]
python_version = "3.12"
strict = false
warn_return_any = true
warn_unused_configs = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = "fastcrud.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "minio.*"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests requiring external services",
]
```

Also create `backend/.python-version` with content: `3.12`
</action>

<acceptance_criteria>
- `backend/pyproject.toml` exists and contains `name = "papery-backend"`
- `backend/pyproject.toml` contains `"fastapi>=0.115.0"` in dependencies
- `backend/pyproject.toml` contains `"sqlalchemy[asyncio]>=2.0.35"` in dependencies
- `backend/pyproject.toml` contains `"redis[hiredis]>=5.2.0"` in dependencies
- `backend/pyproject.toml` contains `"minio>=7.2"` in dependencies
- `backend/pyproject.toml` contains `"fastcrud>=0.16.0"` in dependencies
- `backend/pyproject.toml` contains `package = false` under `[tool.uv]`
- `backend/pyproject.toml` contains `[dependency-groups]` section with `dev` group
- `backend/pyproject.toml` contains `"B008"` in ruff ignore list
- `backend/pyproject.toml` contains `plugins = ["pydantic.mypy"]` under `[tool.mypy]`
- `backend/pyproject.toml` contains `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`
- `backend/.python-version` contains `3.12`
</acceptance_criteria>

---

### Task 1.2 — Create backend directory structure with all __init__.py files

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 1: Monorepo Structure)
</read_first>

<action>
Create the following directory structure with empty `__init__.py` files (or `.gitkeep` for non-Python dirs):

```
backend/
├── app/
│   ├── __init__.py            # empty
│   ├── api/
│   │   ├── __init__.py        # empty
│   │   └── v1/
│   │       └── __init__.py    # empty
│   ├── core/
│   │   ├── __init__.py        # empty
│   │   └── config/
│   │       └── __init__.py    # (will be populated in Task 1.3)
│   ├── extensions/
│   │   └── __init__.py        # empty
│   ├── models/
│   │   └── __init__.py        # empty (will be barrel-import in Plan 03)
│   ├── schemas/
│   │   └── __init__.py        # empty
│   ├── crud/
│   │   └── __init__.py        # empty
│   ├── services/
│   │   └── __init__.py        # empty
│   └── middleware/
│       └── __init__.py        # empty
├── migrations/                 # (Alembic, created in Plan 03)
├── tests/
│   └── __init__.py            # empty
├── scripts/
│   └── .gitkeep               # empty placeholder
```

Every `__init__.py` file should be empty (zero bytes or just a newline).
</action>

<acceptance_criteria>
- `backend/app/__init__.py` exists
- `backend/app/api/__init__.py` exists
- `backend/app/api/v1/__init__.py` exists
- `backend/app/core/__init__.py` exists
- `backend/app/core/config/__init__.py` exists
- `backend/app/extensions/__init__.py` exists
- `backend/app/models/__init__.py` exists
- `backend/app/schemas/__init__.py` exists
- `backend/app/crud/__init__.py` exists
- `backend/app/services/__init__.py` exists
- `backend/app/middleware/__init__.py` exists
- `backend/tests/__init__.py` exists
- `backend/scripts/.gitkeep` exists
</acceptance_criteria>

---

### Task 1.3 — Create Pydantic Settings configuration system (INFRA-09)

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 6: Pydantic Settings Config)
- .planning/phases/01-backend-core-infrastructure/research/04-config-settings.md
</read_first>

<action>
Create modular config files under `backend/app/core/config/`:

**`backend/app/core/config/app.py`:**
```python
from pydantic import Field
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    APP_NAME: str = Field(default="PAPERY")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="local")  # local | staging | production
```

**`backend/app/core/config/database.py`:**
```python
from functools import cached_property
from urllib.parse import quote_plus

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_USER: str = Field(default="papery")
    POSTGRES_PASSWORD: str = Field(default="papery_dev_password")
    POSTGRES_DB: str = Field(default="papery")
    POSTGRES_POOL_SIZE: int = Field(default=20)
    POSTGRES_MAX_OVERFLOW: int = Field(default=10)
    POSTGRES_POOL_RECYCLE: int = Field(default=3600)

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def ASYNC_DATABASE_URI(self) -> str:
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
```

**`backend/app/core/config/redis.py`:**
```python
from pydantic import Field
from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    REDIS_CACHE_HOST: str = Field(default="localhost")
    REDIS_CACHE_PORT: int = Field(default=6379)
    REDIS_CACHE_DB: int = Field(default=0)
    REDIS_CACHE_PASSWORD: str = Field(default="")

    REDIS_QUEUE_HOST: str = Field(default="localhost")
    REDIS_QUEUE_PORT: int = Field(default=6379)
    REDIS_QUEUE_DB: int = Field(default=1)
    REDIS_QUEUE_PASSWORD: str = Field(default="")

    REDIS_RATE_LIMIT_HOST: str = Field(default="localhost")
    REDIS_RATE_LIMIT_PORT: int = Field(default=6379)
    REDIS_RATE_LIMIT_DB: int = Field(default=2)
    REDIS_RATE_LIMIT_PASSWORD: str = Field(default="")
```

**`backend/app/core/config/minio.py`:**
```python
from pydantic import Field
from pydantic_settings import BaseSettings


class MinioConfig(BaseSettings):
    MINIO_ENDPOINT: str = Field(default="localhost:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")
    MINIO_BUCKET_NAME: str = Field(default="papery")
    MINIO_SECURE: bool = Field(default=False)
    MINIO_PRESIGNED_GET_EXPIRY: int = Field(default=3600)  # 1 hour in seconds
    MINIO_PRESIGNED_PUT_EXPIRY: int = Field(default=1800)  # 30 minutes in seconds
```

**`backend/app/core/config/security.py`:**
```python
from pydantic import Field
from pydantic_settings import BaseSettings


class SecurityConfig(BaseSettings):
    SECRET_KEY: str = Field(default="CHANGE-ME-IN-PRODUCTION-minimum-32-chars!!")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
```

**`backend/app/core/config/email.py`:**
```python
from pydantic import Field
from pydantic_settings import BaseSettings


class EmailConfig(BaseSettings):
    SMTP_HOST: str = Field(default="")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_FROM_EMAIL: str = Field(default="noreply@papery.local")
```

**`backend/app/core/config/cors.py`:**
```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class CorsConfig(BaseSettings):
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
```

**`backend/app/core/config/admin.py`:**
```python
from pydantic import Field
from pydantic_settings import BaseSettings


class AdminConfig(BaseSettings):
    ADMIN_EMAIL: str = Field(default="admin@papery.local")
    ADMIN_PASSWORD: str = Field(default="admin_dev_password")
```

**`backend/app/core/config/__init__.py`:**
```python
from typing import Self

from pydantic import model_validator
from pydantic_settings import SettingsConfigDict

from app.core.config.admin import AdminConfig
from app.core.config.app import AppConfig
from app.core.config.cors import CorsConfig
from app.core.config.database import DatabaseConfig
from app.core.config.email import EmailConfig
from app.core.config.minio import MinioConfig
from app.core.config.redis import RedisConfig
from app.core.config.security import SecurityConfig


class AppSettings(
    AppConfig,
    DatabaseConfig,
    RedisConfig,
    MinioConfig,
    SecurityConfig,
    EmailConfig,
    CorsConfig,
    AdminConfig,
):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @model_validator(mode="after")
    def validate_startup(self) -> Self:
        # Reject placeholder SECRET_KEY in non-local environments
        if self.ENVIRONMENT != "local":
            if "CHANGE-ME" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters and not a placeholder "
                    f"in {self.ENVIRONMENT} environment"
                )
            if self.POSTGRES_PASSWORD in ("papery_dev_password", ""):
                raise ValueError(
                    f"POSTGRES_PASSWORD must be set in {self.ENVIRONMENT} environment"
                )
            if self.MINIO_SECRET_KEY in ("minioadmin", ""):
                raise ValueError(
                    f"MINIO_SECRET_KEY must be set in {self.ENVIRONMENT} environment"
                )
        if self.ENVIRONMENT == "production" and not self.SMTP_HOST:
            raise ValueError("SMTP_HOST is required in production environment")
        return self


settings = AppSettings()
```

</action>

<acceptance_criteria>
- `backend/app/core/config/__init__.py` contains `class AppSettings(`
- `backend/app/core/config/__init__.py` contains `settings = AppSettings()`
- `backend/app/core/config/__init__.py` contains `model_config = SettingsConfigDict(`
- `backend/app/core/config/__init__.py` contains `extra="ignore"`
- `backend/app/core/config/__init__.py` contains `case_sensitive=True`
- `backend/app/core/config/__init__.py` contains `def validate_startup`
- `backend/app/core/config/__init__.py` contains `"CHANGE-ME" in self.SECRET_KEY`
- `backend/app/core/config/database.py` contains `def ASYNC_DATABASE_URI`
- `backend/app/core/config/database.py` contains `quote_plus(self.POSTGRES_PASSWORD)`
- `backend/app/core/config/redis.py` contains `REDIS_CACHE_DB: int = Field(default=0)`
- `backend/app/core/config/redis.py` contains `REDIS_QUEUE_DB: int = Field(default=1)`
- `backend/app/core/config/redis.py` contains `REDIS_RATE_LIMIT_DB: int = Field(default=2)`
- `backend/app/core/config/cors.py` contains `def parse_cors_origins`
- `backend/app/core/config/cors.py` contains `v.split(",")`
- `backend/app/core/config/minio.py` contains `MINIO_PRESIGNED_GET_EXPIRY: int = Field(default=3600)`
- `backend/app/core/config/minio.py` contains `MINIO_PRESIGNED_PUT_EXPIRY: int = Field(default=1800)`
</acceptance_criteria>

---

### Task 1.4 — Create .env.example with all environment variables

<read_first>
- backend/app/core/config/__init__.py (the file created in Task 1.3)
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 6: Pydantic Settings Config)
</read_first>

<action>
Create `.env.example` at the project root with every config variable documented:

```env
# =============================================================================
# PAPERY — Environment Variables
# Copy this file to .env and update values for your environment.
# =============================================================================

# --- Application ---
APP_NAME=PAPERY
APP_VERSION=0.1.0
DEBUG=true
ENVIRONMENT=local  # local | staging | production

# --- PostgreSQL ---
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=papery
POSTGRES_PASSWORD=papery_dev_password
POSTGRES_DB=papery
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=10
POSTGRES_POOL_RECYCLE=3600

# --- Redis Cache (db=0) ---
REDIS_CACHE_HOST=localhost
REDIS_CACHE_PORT=6379
REDIS_CACHE_DB=0
REDIS_CACHE_PASSWORD=

# --- Redis Queue (db=1) ---
REDIS_QUEUE_HOST=localhost
REDIS_QUEUE_PORT=6379
REDIS_QUEUE_DB=1
REDIS_QUEUE_PASSWORD=

# --- Redis Rate Limit (db=2) ---
REDIS_RATE_LIMIT_HOST=localhost
REDIS_RATE_LIMIT_PORT=6379
REDIS_RATE_LIMIT_DB=2
REDIS_RATE_LIMIT_PASSWORD=

# --- MinIO (S3-compatible storage) ---
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=papery
MINIO_SECURE=false
MINIO_PRESIGNED_GET_EXPIRY=3600
MINIO_PRESIGNED_PUT_EXPIRY=1800

# --- Security / JWT ---
SECRET_KEY=CHANGE-ME-IN-PRODUCTION-minimum-32-chars!!
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# --- Email (SMTP) ---
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@papery.local

# --- CORS ---
CORS_ORIGINS=http://localhost:3000

# --- Admin Bootstrap ---
ADMIN_EMAIL=admin@papery.local
ADMIN_PASSWORD=admin_dev_password
```
</action>

<acceptance_criteria>
- `.env.example` exists at project root
- `.env.example` contains `POSTGRES_HOST=localhost`
- `.env.example` contains `REDIS_CACHE_DB=0`
- `.env.example` contains `REDIS_QUEUE_DB=1`
- `.env.example` contains `REDIS_RATE_LIMIT_DB=2`
- `.env.example` contains `MINIO_ENDPOINT=localhost:9000`
- `.env.example` contains `SECRET_KEY=CHANGE-ME-IN-PRODUCTION-minimum-32-chars!!`
- `.env.example` contains `ENVIRONMENT=local`
- `.env.example` contains `CORS_ORIGINS=http://localhost:3000`
</acceptance_criteria>

---

### Task 1.5 — Create FastAPI app entry point with lifespan stub and health endpoint

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 2: FastAPI Layered Architecture)
- backend/app/core/config/__init__.py (the config created in Task 1.3)
</read_first>

<action>
Create `backend/app/main.py`:

```python
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
```

Create `backend/app/api/v1/health.py`:

```python
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
```

Create `backend/app/api/dependencies.py`:

```python
"""Shared FastAPI dependencies (auth, db session, etc.)."""
# Dependencies will be added as features are implemented.
```
</action>

<acceptance_criteria>
- `backend/app/main.py` contains `async def lifespan(`
- `backend/app/main.py` contains `app = FastAPI(`
- `backend/app/main.py` contains `title=settings.APP_NAME`
- `backend/app/main.py` contains `CORSMiddleware`
- `backend/app/main.py` contains `app.include_router(health_router`
- `backend/app/main.py` contains `prefix="/api/v1"`
- `backend/app/api/v1/health.py` contains `@router.get("/health")`
- `backend/app/api/v1/health.py` contains `async def health_check(`
- `backend/app/api/v1/health.py` contains `"status": "ok"`
- `backend/app/api/dependencies.py` exists
</acceptance_criteria>

---

### Task 1.6 — Create .pre-commit-config.yaml and install dependencies with uv

<read_first>
- backend/pyproject.toml (created in Task 1.1)
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 8: Dev Tooling)
</read_first>

<action>
Create `.pre-commit-config.yaml` at project root:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
        types_or: [python, pyi]
      - id: ruff-format
        types_or: [python, pyi]
```

Then run:
```bash
cd backend && uv sync --dev
```

This installs all dependencies and creates `uv.lock`.
</action>

<acceptance_criteria>
- `.pre-commit-config.yaml` exists at project root
- `.pre-commit-config.yaml` contains `ruff-pre-commit`
- `.pre-commit-config.yaml` contains `id: ruff`
- `.pre-commit-config.yaml` contains `id: ruff-format`
- `backend/uv.lock` exists (generated by `uv sync`)
- Running `cd backend && uv run python -c "import fastapi; print(fastapi.__version__)"` outputs a version string
- Running `cd backend && uv run python -c "import sqlalchemy; print(sqlalchemy.__version__)"` outputs a version string
</acceptance_criteria>

---

## Verification

After all tasks complete:
1. `cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` starts without errors
2. `curl http://localhost:8000/api/v1/health` returns `{"status":"ok","app":"PAPERY","version":"0.1.0","environment":"local"}`
3. `curl http://localhost:8000/docs` returns Swagger UI HTML (when DEBUG=true)
4. `cd backend && uv run ruff check app/` passes with no errors
5. `cd backend && uv run mypy app/` passes (or only expected warnings)

## must_haves

- [ ] `backend/pyproject.toml` exists with all production and dev dependencies
- [ ] `backend/app/core/config/__init__.py` defines `AppSettings` class composing all config modules
- [ ] `settings = AppSettings()` singleton instantiated at module level
- [ ] Startup validation rejects placeholder `SECRET_KEY` in non-local environments
- [ ] `CORS_ORIGINS` field_validator parses comma-separated strings
- [ ] `ASYNC_DATABASE_URI` computed_field uses `quote_plus()` for password
- [ ] FastAPI app with lifespan context manager is in `backend/app/main.py`
- [ ] Health endpoint at `GET /api/v1/health` returns status JSON
- [ ] All `__init__.py` files exist for proper Python package structure
- [ ] `.env.example` documents every environment variable
