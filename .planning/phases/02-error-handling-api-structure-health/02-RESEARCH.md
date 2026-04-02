# Phase 2: Error Handling, API Structure & Health — Research

**Researched:** 2026-04-02
**Phase:** 02-error-handling-api-structure-health
**Requirements covered:** INFRA-06, INFRA-07, INFRA-08, INFRA-10, INFRA-12

---

## 1. What Exists (Phase 1 Output)

### 1.1 Current `main.py` State

```python
app = FastAPI(
    docs_url="/docs" if settings.DEBUG else None,   # NOT at /api/v1/docs yet
    redoc_url="/redoc" if settings.DEBUG else None,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, ...)
app.include_router(health_router, prefix="/api/v1", tags=["health"])
```

**Gaps to fix:**
- `docs_url` is `/docs`, must move to `/api/v1/docs`
- No `root_path` or `openapi_url` customization — OpenAPI JSON will be at `/openapi.json` not `/api/v1/openapi.json`
- No exception handlers registered
- No request ID middleware
- No CORS production validation (wildcard guard)

### 1.2 Current `health.py` State

Only `/health` (liveness). No `/ready` (deep readiness check).

```python
@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": ..., "version": ..., "environment": ...}
```

**Gap:** `/ready` with PostgreSQL, Redis, MinIO connectivity checks is missing.

### 1.3 Extensions Available for Health Checks

| Extension | Check method | Sync/Async | Complexity |
|-----------|-------------|-----------|-----------|
| `ext_database` | `engine.connect()` + `SELECT 1` | Async | Straightforward |
| `ext_redis` | `cache_client.ping()` | Async | Straightforward |
| `ext_minio` | `client.list_buckets()` | **Sync** | Must use `run_in_executor()` |

MinIO's SDK is urllib3-based (synchronous). The `upload_file()` function in Phase 1 already demonstrates the `run_in_executor` pattern — the same applies to health checks.

### 1.4 CORS Config State

`CorsConfig` in `core/config/cors.py` already parses `CORS_ORIGINS` from env. The `AppSettings.validate_startup()` model_validator checks placeholder secrets but does **not yet** guard against CORS wildcard in production.

### 1.5 Docker State

`docker/Dockerfile.dev` exists for development (hot-reload). No production Dockerfile exists.

---

## 2. Key Technical Findings

### 2.1 FastAPI OpenAPI URL Customization

FastAPI's constructor accepts `openapi_url` and `docs_url` separately. To host OpenAPI JSON and Swagger UI under `/api/v1/`:

```python
app = FastAPI(
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs" if settings.DEBUG else None,
    redoc_url="/api/v1/redoc" if settings.DEBUG else None,
)
```

This is the cleanest solution — no proxy, no prefix trickery. All routers still use their own paths, but the schema discovery endpoint is versioned.

### 2.2 FastAPI Exception Handler Registration

FastAPI uses `@app.exception_handler(ExceptionType)` or `app.add_exception_handler(ExceptionType, handler_fn)`. The handler receives `(request: Request, exc: ExceptionType) -> Response`.

**Pattern for a single catch-all handler:**

```python
@app.exception_handler(PaperyError)
async def papery_error_handler(request: Request, exc: PaperyError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error_code=exc.error_code,
            message=exc.message,
            detail=exc.detail,
            request_id=request.state.request_id,
        ).model_dump(),
    )
```

**Important:** FastAPI's built-in `RequestValidationError` (Pydantic validation failures on request body/params) is a **separate exception type** from custom domain errors. It must also be handled to return the consistent `ErrorResponse` format:

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Normalize Pydantic validation errors → ErrorResponse format
```

**Also:** Unhandled `Exception` (unexpected errors) should be caught with a fallback handler returning 500 — never expose Python stack traces in production.

### 2.3 Request ID Strategy

`request.state.request_id` must be set before any handler runs. Two approaches:

**Approach A — Middleware (recommended):**
```python
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response
```

**Approach B — Dependency injection:**
Add `request_id: str = Header(None, alias="X-Request-ID")` and generate if missing.

**Decision (from CONTEXT D-04):** Include `request_id` in error responses for observability. Middleware is the cleaner approach — it guarantees presence for *all* requests including ones that fail at routing.

**Caution with `BaseHTTPMiddleware`:** In FastAPI, `BaseHTTPMiddleware` has a known issue with streaming responses — it buffers the entire response body. For non-streaming endpoints this is fine. Since Phase 2 has no streaming (that's auth/chat phase), this is safe to use now.

### 2.4 Exception Hierarchy Design (INFRA-06)

**Base class pattern:**

```python
class PaperyError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        detail: Any | None = None,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
    ):
        self.message = message
        self.detail = detail
        if error_code:
            self.error_code = error_code
        if status_code:
            self.status_code = status_code
        super().__init__(message)
```

**Subclass pattern (class-level defaults, constructor overrides):**

```python
class ResourceNotFoundError(PaperyError):
    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"

class AuthError(PaperyError):
    status_code = 401
    error_code = "AUTH_ERROR"

class AccessDeniedError(PaperyError):
    status_code = 403
    error_code = "ACCESS_DENIED"

class ConflictError(PaperyError):
    status_code = 409
    error_code = "CONFLICT"

class ValidationError(PaperyError):
    status_code = 422
    error_code = "VALIDATION_ERROR"

class StorageError(PaperyError):
    status_code = 502
    error_code = "STORAGE_ERROR"

class RateLimitError(PaperyError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"

class ExternalServiceError(PaperyError):
    status_code = 503
    error_code = "EXTERNAL_SERVICE_ERROR"
```

**Usage in CRUD/services (D-09 — no HTTPException at inner layers):**
```python
# In crud layer:
user = await crud_users.get(db=db, uuid=user_uuid)
if not user:
    raise ResourceNotFoundError(f"User {user_uuid} not found", detail={"uuid": str(user_uuid)})
```

**Error code naming convention:** `UPPER_SNAKE_CASE` (D-02). Allows frontend to use as i18n lookup key. More readable than `dot.separated` for Python constants.

### 2.5 ErrorResponse Schema (INFRA-06, D-01 to D-05)

```python
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str
    detail: Any | None = None
    request_id: str
```

This schema enforces shape consistency. The exception handler serializes with `.model_dump()` — no manual dict construction.

**Successful responses:** Phase 2 does NOT define a universal success wrapper (that would be a breaking constraint on all future endpoints). Success response shape is endpoint-specific (per FastAPI/REST best practices). This is intentional.

### 2.6 `/ready` Deep Health Check (INFRA-08)

**Pattern:**

```python
@router.get("/ready")
async def readiness_check() -> JSONResponse:
    checks = {}
    healthy = True
    
    # PostgreSQL check (async)
    try:
        async with asyncio.timeout(2.5):
            async with ext_database.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"
        healthy = False
    
    # Redis check (async)
    try:
        async with asyncio.timeout(2.5):
            await ext_redis.cache_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        healthy = False
    
    # MinIO check (sync → executor)
    try:
        loop = asyncio.get_running_loop()
        async with asyncio.timeout(2.5):
            await loop.run_in_executor(None, ext_minio.client.list_buckets)
        checks["minio"] = "ok"
    except Exception as e:
        checks["minio"] = f"error: {e}"
        healthy = False
    
    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if healthy else "unhealthy", "checks": checks}
    )
```

**Key decisions (from CONTEXT D-11, D-12, D-13):**
- Binary: 200 healthy / 503 unhealthy — no partial "degraded" state
- Per-service timeout: 2-3s — fail fast, don't block Docker Compose probe cycles
- MinIO wrapped in `run_in_executor` (SDK is synchronous)
- No caching of health results (Docker Compose probes at 10-30s interval — caching overhead not worth it)
- **Do not use the full `ext_database.get_session()` generator** for health check — use raw `engine.connect()` to avoid session factory dependency

**`asyncio.timeout()` vs `asyncio.wait_for()`:** Python 3.11+ added `asyncio.timeout()` context manager. Since project uses Python 3.12+, this is preferred over `wait_for()`.

### 2.7 CORS Production Validation (INFRA-10)

Add CORS wildcard guard to `AppSettings.validate_startup()`:

```python
if self.ENVIRONMENT != "local":
    if "*" in self.CORS_ORIGINS:
        raise ValueError("CORS wildcard '*' is not allowed in non-local environments")
```

This is a startup-time validation — the app will refuse to start if misconfigured. Correct approach for a security constraint.

### 2.8 Router Aggregation Pattern (INFRA-07)

**Target structure:**

```
app/api/
├── __init__.py          ← top-level /api router (optional, can skip)
└── v1/
    ├── __init__.py      ← aggregates all v1 routers → single api_v1_router
    └── health.py        ← /health + /ready
```

**`app/api/v1/__init__.py` pattern:**
```python
from fastapi import APIRouter
from app.api.v1.health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router, tags=["health"])
```

**`main.py` registration:**
```python
from app.api.v1 import api_v1_router
app.include_router(api_v1_router)
```

This eliminates the `prefix="/api/v1"` scatter across multiple `include_router()` calls in `main.py`. The router aggregator owns the prefix.

### 2.9 Production Docker — `uvicorn-worker` Package (INFRA-12)

**Critical decision (D-18):** Use `uvicorn-worker` package (by Kludex), NOT the deprecated `uvicorn.workers.UvicornWorker`:

```
# WRONG (deprecated, will be removed from uvicorn in future):
gunicorn app.main:app -k uvicorn.workers.UvicornWorker

# CORRECT (maintained, current package):
pip install uvicorn-worker
gunicorn app.main:app -k uvicorn_worker.UvicornWorker
```

The `uvicorn-worker` package is the maintained successor of `uvicorn.workers` — Kludex (maintainer of uvicorn) moved it to a standalone package.

**Worker count (D-19):** `WEB_CONCURRENCY` env var, default 2. FastAPI is async I/O bound — 2 workers handle high concurrency without excessive memory.

**Multi-stage build pattern (D-20, D-21):**

```dockerfile
# Stage 1: builder — install deps with uv
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# Stage 2: runtime — copy only .venv
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY . .
CMD ["gunicorn", "app.main:app", ...]
```

**pyproject.toml dependency:** `uvicorn-worker` must be added to project dependencies (not dev-only):
```toml
dependencies = [
    ...
    "gunicorn>=23.0.0",
    "uvicorn-worker>=0.3.0",
]
```

**Entrypoint command (production):**
```
gunicorn app.main:app \
  --bind 0.0.0.0:8000 \
  --workers ${WEB_CONCURRENCY:-2} \
  --worker-class uvicorn_worker.UvicornWorker \
  --timeout 120 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --log-level info
```

**vs Dify approach:** Dify uses `gevent` workers (Flask is sync). FastAPI is native async — uvicorn workers are required, not gevent. Dify's Dockerfile structure (2-stage: packages → production) is the pattern to follow, not its worker class.

---

## 3. What Dify's Reference Teaches Us

### Useful patterns
- **`/health` liveness endpoint** — simple `{"status": "ok", "pid": ..., "version": ...}` (Dify's `ext_app_metrics.py`)
- **Exception class design** — `BaseHTTPException` with class-level `error_code`, `description`, `code` attributes (Dify's `libs/exception.py`)
- **2-stage Docker build** — `packages` stage installs deps, `production` stage copies only `.venv` (Dify's `Dockerfile`)
- **entrypoint.sh for runtime mode switching** — `MODE=worker` vs `MODE=web`, `DEBUG=true` vs production gunicorn

### Differences from PAPERY
- Dify is Flask (sync); PAPERY is FastAPI (async) — **worker class is different** (gevent vs uvicorn_worker)
- Dify's error format: `{"code": ..., "message": ..., "status": ...}` — PAPERY's is richer: adds `success`, `detail`, `request_id`
- Dify has no `/ready` deep check — PAPERY needs it for Docker Compose health probes

---

## 4. File Impact Map

### Files to CREATE in Phase 2

| File | Purpose | Requirement |
|------|---------|------------|
| `backend/app/core/exceptions/__init__.py` | Re-exports PaperyError + subclasses | INFRA-06 |
| `backend/app/core/exceptions/base.py` | `PaperyError` base class | INFRA-06 |
| `backend/app/core/exceptions/domain.py` | All domain exception subclasses | INFRA-06 |
| `backend/app/schemas/error.py` | `ErrorResponse` Pydantic schema | INFRA-06 |
| `backend/app/middleware/request_id.py` | `RequestIDMiddleware` | INFRA-06 (request_id) |
| `backend/app/api/v1/__init__.py` | `api_v1_router` aggregator | INFRA-07 |
| `docker/Dockerfile` | Production multi-stage Dockerfile | INFRA-12 |

### Files to MODIFY in Phase 2

| File | Change | Requirement |
|------|--------|------------|
| `backend/app/main.py` | Move docs_url, register exception handlers, add RequestID middleware, import api_v1_router | INFRA-06, INFRA-07 |
| `backend/app/api/v1/health.py` | Add `/ready` endpoint | INFRA-08 |
| `backend/app/core/config/__init__.py` | Add CORS wildcard guard to `validate_startup()` | INFRA-10 |
| `backend/pyproject.toml` | Add `gunicorn` + `uvicorn-worker` dependencies | INFRA-12 |
| `docker/docker-compose.yaml` | Reference new `Dockerfile` for production service | INFRA-12 |

---

## 5. Dependency and Import Considerations

### Import order problem in `main.py`

Current `main.py` has an anti-pattern:
```python
# ...app is created above...
from app.api.v1.health import router as health_router  # noqa: E402  ← late import
app.include_router(...)
```

Phase 2 should fix this by:
1. Creating `api_v1_router` in `app/api/v1/__init__.py`
2. Importing it at the top of `main.py` (no late import needed because lifespan is defined first, avoiding circular init)

### Exception handler import order

Exception handlers must be registered **after** `app = FastAPI(...)` but **before** any request arrives. They can be registered in `main.py` directly or extracted to a setup function. Given the small count (3 handlers: PaperyError, RequestValidationError, Exception), inline registration in `main.py` is sufficient.

### `asyncio.timeout` in Python 3.12

`asyncio.timeout()` is available since Python 3.11. The project requires `>=3.12` — no backport needed, use directly.

---

## 6. Testing Considerations

### Unit tests for exception hierarchy
- Each exception class should instantiate correctly with default and custom args
- `status_code`, `error_code`, `message` attributes must be set correctly

### Integration tests for exception handlers
- `TestClient` from `httpx` (already in `pyproject.toml`) can test that:
  - Raising `ResourceNotFoundError` in a route returns `{"success": false, "error_code": "RESOURCE_NOT_FOUND", ...}` with 404
  - Raising `PaperyError` with custom status_code/error_code works
  - Invalid request body returns 422 in `ErrorResponse` format

### Integration test for `/ready`
- Use `pytest` marks: `@pytest.mark.integration` — requires running services
- Unit test: mock extensions and verify 200/503 based on mock return values

### `fakeredis` pattern (already in dev deps)
The `fakeredis` package is already in `dev` dependencies — health check tests can mock Redis ping.

---

## 7. Edge Cases and Pitfalls

### 7.1 `RequestValidationError` vs `PaperyError`
FastAPI raises `RequestValidationError` before the route handler runs (during request parsing). This is **not** a subclass of `PaperyError`. A separate handler is required. The handler should map Pydantic's verbose error format to `ErrorResponse`.

### 7.2 `HTTPException` from FastAPI internals
FastAPI itself raises `HTTPException` for 404 (route not found), 405 (method not allowed). These should also be caught and converted to `ErrorResponse` format — otherwise clients get FastAPI's default `{"detail": "Not Found"}` shape.

Register a handler for `starlette.exceptions.HTTPException` (FastAPI's `HTTPException` inherits from it).

### 7.3 MinIO health check timeout
MinIO's `list_buckets()` is synchronous — when wrapped with `run_in_executor`, `asyncio.timeout()` wraps the awaitable but the underlying thread continues. If MinIO is slow, the timeout will cancel the async wait but the thread keeps running. This is acceptable — the health check returns unhealthy, and the thread eventually completes or times out at the socket level.

### 7.4 Engine availability in `/ready`
`ext_database.engine` is set during `lifespan` startup. If `/ready` is called before startup completes, `engine` is `None`. The health check should guard against this:
```python
if ext_database.engine is None:
    checks["postgres"] = "error: not initialized"
    healthy = False
```

### 7.5 `BaseHTTPMiddleware` streaming limitation
`BaseHTTPMiddleware` buffers response body — not an issue for Phase 2 (no streaming endpoints). When chat streaming is added in later phases, this middleware must be reviewed. The `RequestIDMiddleware` should be positioned early in the middleware stack.

### 7.6 CORS middleware must remain after all exception handlers
CORSMiddleware runs before exception handlers in Starlette's stack. If an exception handler generates a response without CORS headers, CORS-aware clients may fail. FastAPI's `CORSMiddleware` wraps the entire app including error responses — this is correct as long as `app.add_middleware(CORSMiddleware, ...)` is called once.

---

## 8. Open Questions (Claude's Discretion)

The following were explicitly left to Claude's discretion in CONTEXT.md:

| Question | Recommended Approach |
|---------|---------------------|
| Request ID generation | UUID4 in middleware (simpler than header propagation for v1) |
| Error code naming convention | `UPPER_SNAKE_CASE` (confirmed — readable, matches Python constants) |
| Exception constructor factory methods | Add `@classmethod` factories like `ResourceNotFoundError.for_uuid(uuid)` if repetitive patterns emerge — not needed for Phase 2 |
| Logging integration | Log all `PaperyError` instances at WARNING level, all unhandled `Exception` at ERROR level with traceback, inside exception handlers |
| OpenAPI response schema annotations | Add `responses={404: {"model": ErrorResponse}}` to routes that raise `ResourceNotFoundError` — optional for Phase 2, can be added as endpoints are built |

---

## 9. Phase Boundary (What NOT to Build)

Phase 2 is infrastructure-only:
- **No auth** — `dependencies.py` will stay minimal (expanded in Phase 3)
- **No rate limiting** — Redis rate limit client exists but logic is Phase 6
- **No API endpoints beyond health** — `/api/v1/auth/`, `/api/v1/users/` are Phase 3+
- **No frontend** — Phase 9
- **No worker** — Phase 10

---

## 10. Summary: Key Facts for Planning

| Topic | Key Fact |
|-------|---------|
| OpenAPI URL | Set `openapi_url="/api/v1/openapi.json"` in FastAPI constructor |
| Exception catch order | Register handlers: `PaperyError` → `RequestValidationError` → `HTTPException` → `Exception` |
| Request ID | Middleware sets `request.state.request_id = uuid4()`, included in all error responses |
| `/ready` timeout | `asyncio.timeout(2.5)` per service (Python 3.12, no backport needed) |
| MinIO in health | `run_in_executor(None, client.list_buckets)` — same pattern as Phase 1 `upload_file` |
| CORS guard | `if "*" in self.CORS_ORIGINS and self.ENVIRONMENT != "local": raise ValueError(...)` |
| Production worker | `uvicorn_worker.UvicornWorker` from `uvicorn-worker` package (not deprecated `uvicorn.workers`) |
| Docker stages | Stage 1 (builder): `uv sync --locked --no-dev` → Stage 2 (runtime): copy `.venv` only |
| New deps needed | `gunicorn>=23.0.0`, `uvicorn-worker>=0.3.0` to `pyproject.toml` |
| Late import fix | Move health router import to top-level via `api_v1_router` aggregator in `api/v1/__init__.py` |

---

*Research completed: 2026-04-02*
*Phase: 02-error-handling-api-structure-health*
