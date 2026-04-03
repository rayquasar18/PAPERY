# Research: Dify Backend Architecture → PAPERY Restructuring

**Date:** 2026-04-03
**Task:** Analyze Dify backend patterns, map to PAPERY restructuring plan

---

## 1. Dify Backend Architecture Summary

Dify is a Flask-based LLM platform. Its `api/` directory is the backend root with the following top-level structure:

```
api/
├── app.py                    # Entry point (factory call)
├── app_factory.py            # Flask app factory + extension registration
├── configs/                  # Pydantic-settings config (modular, composed via MI)
│   ├── app_config.py         # DifyConfig = MI of all config modules
│   ├── deploy/
│   ├── feature/
│   ├── middleware/            # DB, Redis, Celery, Storage, VectorDB configs
│   ├── observability/
│   └── packaging/
├── controllers/              # API endpoint handlers (≈ FastAPI routers)
│   ├── console/              # Admin/console endpoints
│   │   ├── auth/             # Auth controllers
│   │   ├── app/
│   │   ├── datasets/
│   │   └── wraps.py          # Auth decorators
│   ├── service_api/          # External API endpoints
│   └── web/                  # Web interface endpoints
├── core/                     # Core business logic (AI/RAG/workflow)
│   ├── app/
│   ├── rag/
│   ├── workflow/
│   └── repositories/         # Some repos live here (core-domain-specific)
├── extensions/               # Infrastructure init (ext_database, ext_redis, etc.)
│   ├── ext_database.py
│   ├── ext_redis.py
│   ├── ext_celery.py
│   ├── ext_storage.py
│   └── ... (25+ extensions)
├── libs/                     # Shared utilities (encryption, email, validators)
├── models/                   # SQLAlchemy models (flat, one file per domain)
│   ├── base.py
│   ├── account.py
│   ├── dataset.py
│   └── workflow.py
├── repositories/             # Data access layer (abstract + SQLAlchemy impl)
├── services/                 # Business logic (static-method classes)
│   ├── account_service.py
│   ├── auth/
│   ├── workflow/
│   └── ... (55+ service files)
├── tasks/                    # Celery/async background tasks
├── fields/                   # Marshmallow field definitions (Flask-specific)
└── migrations/               # Alembic migrations
```

### Key Dify Patterns

| Pattern | Dify's Approach |
|---------|----------------|
| **Data access** | `services/` are the primary data access + business logic layer. `repositories/` exist but are minimal (only workflow-related). Most CRUD is done directly in services via SQLAlchemy queries. |
| **Config** | `configs/` directory (not `core/config/`). Modular Pydantic classes composed via MI into `DifyConfig`. |
| **Extensions** | `extensions/` holds all infrastructure init (`ext_*.py` pattern). Each has `init_app()` and optional `is_enabled()`. |
| **Controllers** | `controllers/` ≈ routers. Organized by interface type (console, web, service_api). |
| **Models** | Flat `models/` directory. One file per domain. UUIDv7 for IDs. |
| **Middleware** | No dedicated `middleware/` dir. Auth/permissions via decorators in `controllers/console/wraps.py`. CORS/proxy-fix in extensions. |
| **Libs** | `libs/` for shared utilities (password, encryption, email, pagination). |
| **Services** | Static-method classes. No instance state. Services call SQLAlchemy directly. |

---

## 2. Current PAPERY Backend Structure

```
backend/app/
├── main.py                   # FastAPI entry point + exception handlers
├── api/                      # API routers
│   ├── dependencies.py       # Shared FastAPI deps (empty)
│   └── v1/
│       ├── __init__.py       # Router aggregator
│       └── health.py         # Health endpoints
├── core/                     # Config + exceptions
│   ├── config/               # Pydantic-settings (modular MI, same as Dify)
│   │   ├── __init__.py       # AppSettings = MI composition
│   │   ├── app.py, database.py, redis.py, minio.py, ...
│   └── exceptions/           # PaperyError hierarchy
│       ├── base.py
│       └── domain.py
├── extensions/               # Infrastructure init (already Dify-aligned!)
│   ├── ext_database.py
│   ├── ext_redis.py
│   └── ext_minio.py
├── middleware/                # ASGI middleware
│   ├── __init__.py
│   └── request_id.py
├── models/                   # SQLAlchemy models
│   ├── base.py               # Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
│   └── __init__.py
├── schemas/                  # Pydantic response schemas
│   └── error.py
├── crud/                     # (empty — placeholder)
└── services/                 # (empty — placeholder)
```

---

## 3. Analysis: What's Already Aligned vs What Needs Change

### ✅ Already Aligned with Dify

| Aspect | Status |
|--------|--------|
| `extensions/ext_*.py` pattern | ✅ Identical — Dify uses exact same naming |
| Config via Pydantic MI composition | ✅ Identical pattern (`AppSettings` = `DifyConfig`) |
| Models in `models/` with `base.py` | ✅ Same approach |
| `schemas/` for API schemas | ✅ Similar (Dify uses `fields/` for Marshmallow, but we use Pydantic) |
| Exception hierarchy in `core/exceptions/` | ✅ Good pattern, Dify has `services/errors/` but our approach is cleaner |

### ⚠️ Needs Restructuring

| Current PAPERY | Dify Pattern | Recommendation |
|---------------|-------------|----------------|
| `app/crud/` (empty) | No `crud/` dir. Business logic + data access in `services/` | **Delete `crud/`**. Use `services/` for all business logic + data access. |
| `app/core/config/` | `configs/` (top-level, not inside `core/`) | **Move** `core/config/` → `configs/` at app level. `core/` should be for core business logic, not config. |
| `app/middleware/` | No `middleware/` dir. Auth via decorators, CORS/proxy via extensions | **Keep `middleware/`** — valid for FastAPI (ASGI middleware is framework-native). Dify doesn't have it because Flask handles this differently. |
| `app/api/v1/` (single router file) | `controllers/` with subdirs per interface | **Keep `api/`** naming — FastAPI convention. But adopt Dify's subdirectory organization as routes grow. |
| No `libs/` directory | `libs/` for shared utils | **Add `libs/`** when utility code grows (password, encryption, email helpers). |
| `app/api/dependencies.py` | `controllers/console/wraps.py` | **Keep `dependencies.py`** — FastAPI-native DI pattern. Add auth deps here. |

---

## 4. Proposed Restructuring Plan

### 4.1 Directory Changes

```
backend/app/
├── main.py                          # No change
├── api/                             # KEEP (FastAPI convention)
│   ├── dependencies.py              # KEEP (auth deps go here)
│   └── v1/
│       ├── __init__.py
│       ├── health.py
│       ├── auth.py                  # (future)
│       └── users.py                 # (future)
├── configs/                         # MOVE from core/config/ → configs/
│   ├── __init__.py                  # AppSettings composition
│   ├── app.py
│   ├── database.py
│   ├── redis.py
│   ├── minio.py
│   ├── security.py
│   ├── email.py
│   ├── cors.py
│   └── admin.py
├── core/                            # REPURPOSE: core business logic only
│   ├── exceptions/                  # KEEP here
│   │   ├── base.py
│   │   └── domain.py
│   └── (future: AI/doc processing core logic)
├── extensions/                      # NO CHANGE (already Dify-aligned)
│   ├── ext_database.py
│   ├── ext_redis.py
│   └── ext_minio.py
├── middleware/                       # KEEP (FastAPI-specific, valid)
│   └── request_id.py
├── models/                          # NO CHANGE
│   ├── base.py
│   └── __init__.py
├── schemas/                         # NO CHANGE
│   └── error.py
├── services/                        # PRIMARY business logic layer
│   ├── __init__.py
│   ├── account_service.py           # (future: auth/user logic)
│   └── errors/                      # (future: service-specific errors)
├── libs/                            # NEW: shared utilities
│   ├── __init__.py
│   ├── password.py                  # (future)
│   └── pagination.py               # (future)
└── tasks/                           # NEW: background task definitions
    └── __init__.py
```

### 4.2 Specific Changes Required

| # | Change | Impact | Risk |
|---|--------|--------|------|
| 1 | **Move** `core/config/` → `configs/` | All `from app.core.config import settings` → `from app.configs import settings`. ~15 import updates. | Low — search-and-replace |
| 2 | **Delete** `crud/` | Directory is empty — no code impact | None |
| 3 | **Create** `libs/` | No existing code to move | None |
| 4 | **Create** `tasks/` | No existing code to move | None |
| 5 | **Update** `core/` purpose | Remove config, keep only exceptions and future core logic | Low |
| 6 | **Update** all imports | `app.core.config` → `app.configs` in: main.py, extensions/*, tests/*, migrations/env.py | Medium — many files but mechanical |

### 4.3 What NOT to Change (Keep PAPERY-Specific)

| Keep | Reason |
|------|--------|
| `api/` not `controllers/` | FastAPI uses "routers" not "controllers". `api/` is the standard convention. |
| `api/dependencies.py` | FastAPI's `Depends()` DI is superior to Dify's decorator-based auth. Keep it. |
| `middleware/` directory | ASGI middleware is a first-class FastAPI concept. Dify doesn't have it because Flask handles this via extensions. |
| `schemas/` directory | Pydantic schemas > Marshmallow fields. Our schema approach is better. |
| Async everywhere | Dify uses sync Flask + gevent. PAPERY uses native async. Keep async. |
| `services/` as static-method classes | Adopt Dify's pattern of stateless service classes with static methods. No repository layer needed. |

---

## 5. Service Layer Pattern (from Dify)

Dify's service pattern worth adopting:

```python
# services/account_service.py
class AccountService:
    """All methods are static — stateless business logic."""

    @staticmethod
    async def create_account(*, email: str, name: str, password: str) -> Account:
        """Create a new user account."""
        # Validation
        # Hash password
        # Create model
        # Save to DB
        # Return account

    @staticmethod
    async def authenticate(*, email: str, password: str) -> Account:
        """Authenticate user credentials."""
        # ...

    @staticmethod
    async def get_account_by_uuid(*, uuid: UUID) -> Account:
        """Fetch account by public UUID."""
        # ...
```

**Key principles from Dify:**
- Services contain ALL business logic (no separate "crud" layer)
- Static methods — no instance state
- Services call SQLAlchemy directly (via session)
- One service class per domain (AccountService, ProjectService, etc.)
- Service errors raised as domain exceptions, caught by controller/router layer

---

## 6. Migration Order (Recommended)

1. **Move `core/config/` → `configs/`** — biggest change, touch many files
2. **Delete `crud/`** — trivial
3. **Create `libs/` and `tasks/`** — empty scaffolds
4. **Update all imports** — mechanical refactor
5. **Update tests** — fix import paths
6. **Verify** — run test suite

**Total estimated effort:** ~30 minutes for a focused refactor session.

---

## Summary

PAPERY is already well-aligned with Dify's patterns in several areas (extensions, config composition, models). The main changes are:

1. **`configs/` extraction** — Move config out of `core/` to match Dify's separation
2. **Kill `crud/` layer** — Adopt Dify's single `services/` layer pattern
3. **Add `libs/` and `tasks/`** — Scaffolding for future utility code and background tasks
4. **Keep PAPERY-specific patterns** — `api/` routers, `middleware/`, `schemas/`, async-first, FastAPI DI

The restructuring is low-risk since Phase 1-2 have minimal code. Best done before Phase 3 (Auth) starts.
