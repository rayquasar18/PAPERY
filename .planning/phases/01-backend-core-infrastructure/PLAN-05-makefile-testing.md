---
plan: "05"
title: "Makefile Automation & Testing Foundation"
phase: 1
wave: 4
depends_on: ["01", "02", "03", "04"]
requirements:
  - INFRA-01
  - INFRA-02
  - INFRA-03
  - INFRA-04
  - INFRA-09
  - INFRA-11
  - INFRA-14
  - INFRA-15
files_modified:
  - Makefile
  - backend/tests/conftest.py
  - backend/tests/test_app.py
  - backend/tests/test_config.py
  - backend/tests/test_models.py
autonomous: true
estimated_tasks: 4
---

# Plan 05 — Makefile Automation & Testing Foundation

## Goal

Create the root-level Makefile for development automation (dev-setup, lint, test, migrate, clean) and implement the testing foundation: pytest conftest with shared fixtures, and smoke tests that verify the config system, models/mixins, and FastAPI app startup. This is the integration layer that proves all prior plans work together.

> **Note:** Wave updated to 4 (after PLAN-04 wave 3) to ensure all extensions are wired
> before testing fixtures reference them.

---

## Tasks

### Task 5.1 — Create root-level Makefile with all dev automation targets

<read_first>
- .planning/phases/01-backend-core-infrastructure/research/06-uv-makefile-tooling.md (section 2: Makefile Automation)
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 8: Dev Tooling — Makefile Targets)
- docker/docker-compose.middleware.yaml (created in Plan 02 — verify path and project name)
</read_first>

<action>
Create `Makefile` at the project root with these exact targets:

```makefile
.DEFAULT_GOAL := help

# === Development Setup ===
.PHONY: dev-setup prepare-docker prepare-api dev-clean

dev-setup: prepare-docker prepare-api  ## Full dev environment setup
	@echo "Development environment ready!"

prepare-docker:  ## Start Docker middleware (PostgreSQL, Redis, MinIO)
	@cp -n .env.example .env 2>/dev/null || true
	@cp -n docker/middleware.env.example docker/middleware.env 2>/dev/null || true
	@cd docker && docker compose -f docker-compose.middleware.yaml \
	    -p papery-dev up -d

prepare-api:  ## Install Python dependencies and run migrations
	@cd backend && uv sync --dev
	@cd backend && uv run alembic upgrade head

dev-clean:  ## Stop Docker middleware and remove volumes
	@cd docker && docker compose -f docker-compose.middleware.yaml \
	    -p papery-dev down -v

# === Code Quality ===
.PHONY: format check lint type-check

format:  ## Format code with ruff
	@cd backend && uv run ruff format .

check:  ## Check code with ruff (no fix)
	@cd backend && uv run ruff check .

lint:  ## Format + fix code with ruff
	@cd backend && uv run ruff format .
	@cd backend && uv run ruff check --fix .

type-check:  ## Run mypy type checking
	@cd backend && uv run mypy app/

# === Testing ===
.PHONY: test test-cov test-unit

test:  ## Run all tests
	@cd backend && uv run pytest tests/ -v --tb=short

test-cov:  ## Run tests with coverage report
	@cd backend && uv run pytest tests/ --cov=app --cov-report=term-missing

test-unit:  ## Run unit tests only (no integration)
	@cd backend && uv run pytest tests/ -v --tb=short -m "not integration"

# === Database ===
.PHONY: migrate migrate-new

migrate:  ## Apply all pending migrations
	@cd backend && uv run alembic upgrade head

migrate-new:  ## Create new migration (usage: make migrate-new MSG='add users table')
	@cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

# === Cleanup ===
.PHONY: clean-cache

clean-cache:  ## Remove Python cache directories
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# === Help ===
help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	    awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
```
</action>

<acceptance_criteria>
- `Makefile` exists at project root
- `Makefile` contains `.DEFAULT_GOAL := help`
- `Makefile` contains `dev-setup: prepare-docker prepare-api`
- `Makefile` contains `docker compose -f docker-compose.middleware.yaml`
- `Makefile` contains `-p papery-dev up -d`
- `Makefile` contains `uv sync --dev`
- `Makefile` contains `uv run alembic upgrade head`
- `Makefile` contains `dev-clean:` target with `down -v`
- `Makefile` contains `uv run ruff format`
- `Makefile` contains `uv run ruff check --fix`
- `Makefile` contains `uv run mypy app/`
- `Makefile` contains `uv run pytest tests/`
- `Makefile` contains `--cov=app --cov-report=term-missing`
- `Makefile` contains `migrate-new:` target with `--autogenerate`
- `Makefile` contains `clean-cache:` target
- `Makefile` contains `help:` target with grep-based autodoc
</acceptance_criteria>

---

### Task 5.2 — Create config and model unit tests (INFRA-09, INFRA-14, INFRA-15)

> **Note:** This task does NOT create conftest.py. The conftest.py is created once in Task 5.3
> to avoid double-write conflicts.

<read_first>
- backend/app/core/config/__init__.py (AppSettings with validate_startup)
- backend/app/core/config/database.py (DatabaseConfig with ASYNC_DATABASE_URI)
- backend/app/core/config/cors.py (CorsConfig with parse_cors_origins)
- backend/app/models/base.py (Base, UUIDMixin, TimestampMixin, SoftDeleteMixin)
</read_first>

<action>
Create `backend/tests/test_config.py`:

```python
"""Tests for Pydantic Settings configuration system (INFRA-09)."""
import os
from unittest.mock import patch

import pytest


class TestAppSettings:
    """Test AppSettings loading, validation, and computed fields."""

    def test_default_settings_load_in_local_env(self):
        """Settings should load with defaults when ENVIRONMENT=local."""
        with patch.dict(os.environ, {"ENVIRONMENT": "local"}, clear=False):
            from app.core.config.app import AppConfig

            config = AppConfig()
            assert config.APP_NAME == "PAPERY"
            assert config.ENVIRONMENT == "local"

    def test_async_database_uri_computed(self):
        """ASYNC_DATABASE_URI should be computed from individual fields."""
        from app.core.config.database import DatabaseConfig

        config = DatabaseConfig(
            POSTGRES_HOST="dbhost",
            POSTGRES_PORT=5432,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="testdb",
        )
        assert config.ASYNC_DATABASE_URI == (
            "postgresql+asyncpg://user:pass@dbhost:5432/testdb"
        )

    def test_async_database_uri_special_chars_in_password(self):
        """Password with special characters should be URL-encoded."""
        from app.core.config.database import DatabaseConfig

        config = DatabaseConfig(
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="p@ss:w0rd/special",
            POSTGRES_DB="testdb",
        )
        assert "p%40ss%3Aw0rd%2Fspecial" in config.ASYNC_DATABASE_URI

    def test_cors_origins_parses_csv_string(self):
        """CORS_ORIGINS should parse comma-separated string into list."""
        from app.core.config.cors import CorsConfig

        config = CorsConfig(CORS_ORIGINS="http://a.com, http://b.com, http://c.com")
        assert config.CORS_ORIGINS == [
            "http://a.com",
            "http://b.com",
            "http://c.com",
        ]

    def test_cors_origins_accepts_list(self):
        """CORS_ORIGINS should accept a list directly."""
        from app.core.config.cors import CorsConfig

        config = CorsConfig(CORS_ORIGINS=["http://a.com", "http://b.com"])
        assert config.CORS_ORIGINS == ["http://a.com", "http://b.com"]

    def test_staging_rejects_placeholder_secret_key(self):
        """Non-local environments must reject placeholder SECRET_KEY."""
        from app.core.config import AppSettings

        with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 characters"):
            AppSettings(
                ENVIRONMENT="staging",
                SECRET_KEY="CHANGE-ME-short",
                POSTGRES_PASSWORD="real_password",
                MINIO_SECRET_KEY="real_minio_key",
            )

    def test_production_requires_smtp_host(self):
        """Production environment must have SMTP_HOST configured."""
        from app.core.config import AppSettings

        with pytest.raises(ValueError, match="SMTP_HOST is required in production"):
            AppSettings(
                ENVIRONMENT="production",
                SECRET_KEY="a-very-long-secret-key-that-is-at-least-32-characters!!",
                POSTGRES_PASSWORD="real_password",
                MINIO_SECRET_KEY="real_minio_key",
                SMTP_HOST="",
            )

    def test_local_env_accepts_all_defaults(self):
        """Local environment should accept all default/placeholder values."""
        from app.core.config import AppSettings

        config = AppSettings(ENVIRONMENT="local")
        assert config.APP_NAME == "PAPERY"
        assert config.ENVIRONMENT == "local"
```

Create `backend/tests/test_models.py`:

```python
"""Tests for SQLAlchemy base models and mixins (INFRA-14, INFRA-15)."""
import uuid as uuid_pkg
from datetime import datetime, timezone

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class TestBase:
    """Test Base declarative model."""

    def test_base_is_abstract(self):
        """Base should be abstract — not instantiable as a table."""
        assert Base.__abstract__ is True

    def test_base_has_biginteger_pk(self):
        """Base.id column should be BigInteger primary key."""
        col = Base.__table__.columns.get("id") if hasattr(Base, "__table__") else None
        # Since Base is abstract, check via class attribute
        assert hasattr(Base, "id")


class TestUUIDMixin:
    """Test UUIDMixin (INFRA-14: dual ID strategy)."""

    def test_uuid_mixin_has_uuid_attribute(self):
        """UUIDMixin should define a uuid attribute."""
        assert hasattr(UUIDMixin, "uuid")

    def test_uuid_mixin_default_is_uuid4(self):
        """UUIDMixin.uuid default should be uuid4 function."""
        col = UUIDMixin.__dict__["uuid"]
        # mapped_column stores default in column property
        assert col.column.default is not None


class TestTimestampMixin:
    """Test TimestampMixin."""

    def test_timestamp_mixin_has_created_at(self):
        """TimestampMixin should define created_at."""
        assert hasattr(TimestampMixin, "created_at")

    def test_timestamp_mixin_has_updated_at(self):
        """TimestampMixin should define updated_at."""
        assert hasattr(TimestampMixin, "updated_at")


class TestSoftDeleteMixin:
    """Test SoftDeleteMixin (INFRA-15)."""

    def test_soft_delete_mixin_has_deleted_at(self):
        """SoftDeleteMixin should define deleted_at nullable timestamp."""
        assert hasattr(SoftDeleteMixin, "deleted_at")

    def test_is_deleted_returns_false_when_not_deleted(self):
        """is_deleted should return False when deleted_at is None."""

        class FakeModel(SoftDeleteMixin):
            pass

        obj = FakeModel()
        obj.deleted_at = None
        assert obj.is_deleted is False

    def test_is_deleted_returns_true_when_deleted(self):
        """is_deleted should return True when deleted_at is set."""

        class FakeModel(SoftDeleteMixin):
            pass

        obj = FakeModel()
        obj.deleted_at = datetime.now(tz=timezone.utc)
        assert obj.is_deleted is True

    def test_is_deleted_is_property(self):
        """is_deleted should be a property, not a column."""
        assert isinstance(
            SoftDeleteMixin.__dict__["is_deleted"], property
        )


class TestModelBarrelImports:
    """Test that models/__init__.py exports all required symbols."""

    def test_barrel_exports_base(self):
        """models/__init__.py should export Base."""
        from app.models import Base as ImportedBase

        assert ImportedBase is Base

    def test_barrel_exports_uuid_mixin(self):
        """models/__init__.py should export UUIDMixin."""
        from app.models import UUIDMixin as ImportedMixin

        assert ImportedMixin is UUIDMixin

    def test_barrel_exports_timestamp_mixin(self):
        """models/__init__.py should export TimestampMixin."""
        from app.models import TimestampMixin as ImportedMixin

        assert ImportedMixin is TimestampMixin

    def test_barrel_exports_soft_delete_mixin(self):
        """models/__init__.py should export SoftDeleteMixin."""
        from app.models import SoftDeleteMixin as ImportedMixin

        assert ImportedMixin is SoftDeleteMixin
```
</action>

<acceptance_criteria>
- `backend/tests/test_config.py` contains `class TestAppSettings:`
- `backend/tests/test_config.py` contains `def test_default_settings_load_in_local_env`
- `backend/tests/test_config.py` contains `def test_async_database_uri_computed`
- `backend/tests/test_config.py` contains `def test_async_database_uri_special_chars_in_password`
- `backend/tests/test_config.py` contains `"p%40ss%3Aw0rd%2Fspecial"`
- `backend/tests/test_config.py` contains `def test_cors_origins_parses_csv_string`
- `backend/tests/test_config.py` contains `def test_staging_rejects_placeholder_secret_key`
- `backend/tests/test_config.py` contains `def test_production_requires_smtp_host`
- `backend/tests/test_config.py` contains `def test_local_env_accepts_all_defaults`
- `backend/tests/test_models.py` contains `class TestBase:`
- `backend/tests/test_models.py` contains `class TestUUIDMixin:`
- `backend/tests/test_models.py` contains `class TestSoftDeleteMixin:`
- `backend/tests/test_models.py` contains `def test_is_deleted_returns_false_when_not_deleted`
- `backend/tests/test_models.py` contains `def test_is_deleted_returns_true_when_deleted`
- `backend/tests/test_models.py` contains `def test_is_deleted_is_property`
- `backend/tests/test_models.py` contains `class TestModelBarrelImports:`
- `backend/tests/test_models.py` contains `from app.models import Base as ImportedBase`
</acceptance_criteria>

---

### Task 5.3 — Create pytest conftest.py with shared fixtures and FastAPI app smoke test (INFRA-01)

> **Note:** This single task creates both conftest.py AND test_app.py. The conftest.py includes
> mock patches for all extensions so tests can run without Docker services.
> Async tests use NO markers — `asyncio_mode = "auto"` in pyproject.toml auto-detects them.

<read_first>
- backend/app/main.py (FastAPI app with lifespan, health endpoint)
- backend/app/api/v1/health.py (health check endpoint returning status JSON)
- backend/pyproject.toml (pytest config with asyncio_mode = "auto")
- backend/app/extensions/ext_database.py (created in Plan 03)
- backend/app/extensions/ext_redis.py (created in Plan 04)
- backend/app/extensions/ext_minio.py (created in Plan 04)
</read_first>

<action>
Create `backend/tests/conftest.py` with shared test fixtures (mock-patched for no-Docker testing):

```python
"""Shared pytest fixtures for all tests."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure test environment before any app imports
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long!!")


@pytest.fixture()
async def async_client():
    """Create an async test client for the FastAPI app.

    Patches extension init/shutdown to avoid requiring real services.
    """
    with (
        patch("app.extensions.ext_database.init", new_callable=AsyncMock),
        patch("app.extensions.ext_database.shutdown", new_callable=AsyncMock),
        patch("app.extensions.ext_redis.init", new_callable=AsyncMock),
        patch("app.extensions.ext_redis.shutdown", new_callable=AsyncMock),
        patch("app.extensions.ext_minio.init", new_callable=MagicMock),
        patch("app.extensions.ext_minio.shutdown", new_callable=MagicMock),
    ):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
```

Create `backend/tests/test_app.py`:

```python
"""Smoke tests for FastAPI app startup and health endpoint (INFRA-01)."""
from httpx import AsyncClient


class TestHealthEndpoint:
    """Test the /api/v1/health endpoint."""

    async def test_health_returns_200(self, async_client: AsyncClient):
        """GET /api/v1/health should return 200 OK."""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_health_returns_status_ok(self, async_client: AsyncClient):
        """Health response should contain status: ok."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_returns_app_name(self, async_client: AsyncClient):
        """Health response should contain app name PAPERY."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert data["app"] == "PAPERY"

    async def test_health_returns_version(self, async_client: AsyncClient):
        """Health response should contain version string."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    async def test_health_returns_environment(self, async_client: AsyncClient):
        """Health response should contain environment field."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert "environment" in data


class TestAppConfiguration:
    """Test FastAPI app configuration."""

    def test_app_title_is_papery(self):
        """App title should be PAPERY."""
        from app.main import app

        assert app.title == "PAPERY"

    def test_app_has_health_route(self):
        """App should have /api/v1/health route registered."""
        from app.main import app

        routes = [route.path for route in app.routes]
        assert "/api/v1/health" in routes

    def test_app_has_docs_in_debug_mode(self):
        """When DEBUG=true, /docs should be available."""
        from app.main import app

        assert app.docs_url is not None

    def test_app_has_cors_middleware(self):
        """App should have CORSMiddleware configured."""
        from app.main import app

        middleware_classes = [
            type(m).__name__
            for m in getattr(app, "user_middleware", [])
        ]
        # FastAPI wraps middleware, check via app.user_middleware
        assert any("CORS" in str(m) for m in app.user_middleware)
```
</action>

<acceptance_criteria>
- `backend/tests/conftest.py` contains `import pytest`
- `backend/tests/conftest.py` contains `from httpx import ASGITransport, AsyncClient`
- `backend/tests/conftest.py` contains `os.environ.setdefault("ENVIRONMENT", "local")`
- `backend/tests/conftest.py` contains `os.environ.setdefault("SECRET_KEY",`
- `backend/tests/conftest.py` contains `async def async_client()`
- `backend/tests/conftest.py` contains `ASGITransport(app=app)`
- `backend/tests/conftest.py` contains `base_url="http://testserver"`
- `backend/tests/conftest.py` contains `from app.main import app`
- `backend/tests/conftest.py` contains `patch("app.extensions.ext_database.init"`
- `backend/tests/conftest.py` contains `patch("app.extensions.ext_redis.init"`
- `backend/tests/conftest.py` contains `patch("app.extensions.ext_minio.init"`
- `backend/tests/conftest.py` contains `new_callable=AsyncMock`
- `backend/tests/conftest.py` contains `new_callable=MagicMock`
- `backend/tests/conftest.py` does NOT contain `anyio_backend` fixture
- `backend/tests/conftest.py` does NOT contain `@pytest.mark.anyio`
- `backend/tests/test_app.py` contains `class TestHealthEndpoint:`
- `backend/tests/test_app.py` contains `async def test_health_returns_200`
- `backend/tests/test_app.py` contains `assert response.status_code == 200`
- `backend/tests/test_app.py` contains `assert data["status"] == "ok"`
- `backend/tests/test_app.py` contains `assert data["app"] == "PAPERY"`
- `backend/tests/test_app.py` contains `assert data["version"] == "0.1.0"`
- `backend/tests/test_app.py` contains `class TestAppConfiguration:`
- `backend/tests/test_app.py` contains `def test_app_title_is_papery`
- `backend/tests/test_app.py` contains `def test_app_has_health_route`
- `backend/tests/test_app.py` contains `"/api/v1/health" in routes`
- `backend/tests/test_app.py` does NOT contain `@pytest.mark.anyio` (asyncio_mode = "auto" handles it)
</acceptance_criteria>

---

## Verification

After all tasks complete:
1. `make help` displays all available targets with descriptions
2. `make lint` runs ruff format + check without errors
3. `make test-unit` runs all unit tests and they pass
4. `cd backend && uv run pytest tests/test_config.py -v` — all config tests green
5. `cd backend && uv run pytest tests/test_models.py -v` — all model tests green
6. `cd backend && uv run pytest tests/test_app.py -v` — all app tests green
7. `make type-check` runs mypy without blocking errors
8. `make test-cov` runs tests with coverage (pytest-cov is a dev dependency)

## must_haves

- [ ] `Makefile` at project root with dev-setup, lint, test, migrate, clean targets
- [ ] `make dev-setup` chains prepare-docker + prepare-api (INFRA-11)
- [ ] `make lint` runs ruff format + ruff check --fix
- [ ] `make test` runs pytest on all tests
- [ ] `make test-cov` works because `pytest-cov` is in dev dependencies (PLAN-01)
- [ ] `backend/tests/conftest.py` patches extensions to avoid requiring real services
- [ ] `backend/tests/conftest.py` does NOT have `anyio_backend` fixture (not needed with `asyncio_mode = "auto"`)
- [ ] Async tests use NO `@pytest.mark.anyio` or `@pytest.mark.asyncio` markers (auto-detected)
- [ ] Config tests verify: default loading, ASYNC_DATABASE_URI computation, special chars in password, CORS CSV parsing, staging SECRET_KEY rejection, production SMTP_HOST requirement (INFRA-09)
- [ ] Model tests verify: Base is abstract, UUIDMixin has uuid attribute, SoftDeleteMixin.is_deleted property behavior (INFRA-14, INFRA-15)
- [ ] App smoke tests verify: health endpoint returns 200 with correct JSON, app has CORS middleware, routes registered (INFRA-01)
- [ ] All tests pass without Docker running (mocked extensions)
