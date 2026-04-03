# Quick Task Plan: Refactor Backend Structure

**ID:** 260403-kva
**Created:** 2026-04-03
**Status:** planned
**Estimated effort:** ~25 min (3 tasks)

---

## Context

User wants 4 structural improvements to the backend before Phase 3 (Auth) begins:
1. Remove `libs/` → rename to `utils/` (libs/ is empty, just a scaffold)
2. Replace custom `PaperyError` hierarchy with FastAPI's `HTTPException` + `request_id`
3. Move database from `extensions/ext_database.py` → `core/db/session.py`
4. Add `Makefile` with development automation commands

---

## Task 1: Remove libs/, create utils/, move DB to core/db/session.py

### Actions

**1a. Delete `app/libs/` → Create `app/utils/__init__.py`**
- Delete `app/libs/__init__.py` and `app/libs/` directory
- Create `app/utils/__init__.py` with placeholder docstring
- libs/ is empty (just docstring), no imports to update anywhere

**1b. Move database to `core/db/session.py`**
- Create `app/core/db/__init__.py`
- Create `app/core/db/session.py` — move ALL content from `extensions/ext_database.py` here
- Keep the same API: `engine`, `async_session_factory`, `init()`, `shutdown()`, `get_session()`
- Delete `extensions/ext_database.py`

**1c. Update all imports**

Files that import `ext_database`:
| File | Current import | New import |
|------|---------------|------------|
| `app/main.py` | `from app.extensions import ext_database` | `from app.core.db import session as db_session` |
| `app/api/v1/health.py` | `from app.extensions import ext_database` | `from app.core.db import session as db_session` |

In `main.py` lifespan:
- `ext_database.init()` → `db_session.init()`
- `ext_database.shutdown()` → `db_session.shutdown()`

In `health.py`:
- `ext_database.engine` → `db_session.engine`

Update `extensions/__init__.py` — remove ext_database re-export (if any; currently empty file).

**1d. Update test mocks**

| Test file | Current mock path | New mock path |
|-----------|------------------|---------------|
| `tests/conftest.py` | `app.extensions.ext_database.init` | `app.core.db.session.init` |
| `tests/conftest.py` | `app.extensions.ext_database.shutdown` | `app.core.db.session.shutdown` |
| `tests/test_health.py` | `app.api.v1.health.ext_database` | `app.api.v1.health.db_session` |

### Verification
- `uv run pytest` — all tests pass
- No remaining imports of `app.extensions.ext_database` or `app.libs`

---

## Task 2: Replace PaperyError with FastAPI HTTPException + request_id

### Design

The user wants to use FastAPI's built-in `HTTPException` as the base, not a separate hierarchy. Custom exceptions should **inherit from FastAPI's HTTPException** and only add `request_id` + `error_code`.

**New `app/core/exceptions/base.py`:**
```python
from fastapi import HTTPException


class PaperyHTTPException(HTTPException):
    """Base PAPERY HTTP exception — extends FastAPI's HTTPException with request_id and error_code.
    
    All domain exceptions inherit from this. The exception handler reads
    error_code and request_id to build consistent ErrorResponse JSON.
    """
    error_code: str = "INTERNAL_ERROR"
    
    def __init__(
        self,
        status_code: int = 500,
        detail: str = "An unexpected error occurred",
        *,
        error_code: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        if error_code is not None:
            self.error_code = error_code
```

**New `app/core/exceptions/http.py`** (replaces `domain.py`):
```python
from app.core.exceptions.base import PaperyHTTPException


class NotFoundError(PaperyHTTPException):
    def __init__(self, detail: str = "Resource not found", **kwargs):
        super().__init__(status_code=404, detail=detail, error_code="RESOURCE_NOT_FOUND", **kwargs)

class AuthenticationError(PaperyHTTPException):
    def __init__(self, detail: str = "Authentication failed", **kwargs):
        super().__init__(status_code=401, detail=detail, error_code="AUTH_ERROR", **kwargs)

class ForbiddenError(PaperyHTTPException):
    def __init__(self, detail: str = "Access denied", **kwargs):
        super().__init__(status_code=403, detail=detail, error_code="ACCESS_DENIED", **kwargs)

class ConflictError(PaperyHTTPException):
    def __init__(self, detail: str = "Resource conflict", **kwargs):
        super().__init__(status_code=409, detail=detail, error_code="CONFLICT", **kwargs)

class ValidationError(PaperyHTTPException):
    def __init__(self, detail: str = "Validation failed", **kwargs):
        super().__init__(status_code=422, detail=detail, error_code="VALIDATION_ERROR", **kwargs)

class RateLimitError(PaperyHTTPException):
    def __init__(self, detail: str = "Too many requests", **kwargs):
        super().__init__(status_code=429, detail=detail, error_code="RATE_LIMIT_EXCEEDED", **kwargs)

class StorageError(PaperyHTTPException):
    def __init__(self, detail: str = "Storage operation failed", **kwargs):
        super().__init__(status_code=502, detail=detail, error_code="STORAGE_ERROR", **kwargs)

class ExternalServiceError(PaperyHTTPException):
    def __init__(self, detail: str = "External service unavailable", **kwargs):
        super().__init__(status_code=503, detail=detail, error_code="EXTERNAL_SERVICE_ERROR", **kwargs)
```

**Update `app/core/exceptions/__init__.py`** — barrel exports of new classes.

**Update `app/main.py` exception handlers:**
- Remove the `papery_error_handler` for old `PaperyError`
- Modify `http_exception_handler` for `StarletteHTTPException` to:
  - Check if exc is `PaperyHTTPException` → use `exc.error_code`
  - Otherwise use the status-code mapping dict (existing logic)
  - Always include `request_id` from `_get_request_id(request)`
- Keep `validation_error_handler` and `unhandled_exception_handler` as-is

Delete `app/core/exceptions/domain.py` (replaced by `http.py`).

**Update `app/schemas/error.py`** — no changes needed (ErrorResponse still works).

**Update tests:**
- `tests/test_exceptions.py` — rewrite to test new `PaperyHTTPException` hierarchy:
  - Verify each subclass inherits from `fastapi.HTTPException`
  - Verify `error_code`, `status_code`, `detail` attributes
  - Verify `ErrorResponse` schema still works

### Verification
- `uv run pytest` — all tests pass
- Raising `NotFoundError("User not found")` in a route returns `{"success": false, "error_code": "RESOURCE_NOT_FOUND", "message": "User not found", "request_id": "..."}`

---

## Task 3: Add Makefile

Create `backend/Makefile` with practical development targets.

### Targets

```makefile
.PHONY: help install dev test lint format typecheck clean migrate docker-up docker-down

help              # Show available targets
install           # uv sync (install dependencies)
dev               # Run FastAPI dev server (uvicorn --reload)
test              # uv run pytest
test-cov          # uv run pytest --cov=app
lint              # uv run ruff check .
format            # uv run ruff format .
typecheck         # uv run mypy app/
clean             # Remove __pycache__, .mypy_cache, .pytest_cache, .ruff_cache
migrate           # uv run alembic upgrade head
migrate-new       # uv run alembic revision --autogenerate -m "$(msg)"
docker-up         # docker compose up -d
docker-down       # docker compose down
docker-build      # docker build -t papery-backend .
```

### Verification
- `cd backend && make help` works
- `make test` runs pytest successfully

---

## Files Changed Summary

### Created (new)
- `app/utils/__init__.py`
- `app/core/db/__init__.py`
- `app/core/db/session.py`
- `app/core/exceptions/http.py`
- `backend/Makefile`

### Modified
- `app/main.py` — import paths + exception handler logic
- `app/api/v1/health.py` — import path for db session
- `app/core/exceptions/__init__.py` — barrel exports updated
- `app/core/exceptions/base.py` — PaperyHTTPException (replaces PaperyError)
- `tests/conftest.py` — mock paths updated
- `tests/test_exceptions.py` — rewritten for new hierarchy
- `tests/test_health.py` — mock paths updated

### Deleted
- `app/libs/__init__.py` + `app/libs/` directory
- `app/extensions/ext_database.py`
- `app/core/exceptions/domain.py`

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| `utils/` over `libs/` | Convention: utils/ is universally understood; libs/ is non-standard |
| DB in `core/db/session.py` not `extensions/` | Database is core infrastructure, not an optional extension |
| Keep Redis/MinIO in `extensions/` | They ARE optional extensions; DB is mandatory core |
| `PaperyHTTPException(HTTPException)` base | User requirement: use FastAPI defaults, inherit only to add error_code |
| `http.py` replaces `domain.py` | Clearer name: these ARE HTTP exceptions now, not abstract domain errors |
| Import alias `db_session` | Reads naturally: `db_session.init()`, `db_session.engine`, `db_session.get_session()` |
| Makefile at `backend/` level | Backend is the primary development target; future root Makefile can delegate |
