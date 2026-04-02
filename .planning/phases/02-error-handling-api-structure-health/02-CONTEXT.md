# Phase 2: Error Handling, API Structure & Health - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish API versioning, structured error handling, health checks, CORS hardening, and production Docker images — the API contract and operational observability layer. All subsequent endpoints (auth, projects, admin) will use the error format, exception hierarchy, and API structure defined here.

</domain>

<decisions>
## Implementation Decisions

### Error Response Format
- **D-01:** Custom flat JSON format for all API error responses: `{ success: bool, error_code: str, message: str, detail: Any | null, request_id: str }`
- **D-02:** `error_code` is a machine-readable catalog key (e.g., `"AUTH_TOKEN_EXPIRED"`, `"RESOURCE_NOT_FOUND"`) — frontend uses this for i18n lookup
- **D-03:** `message` is human-readable English default — frontend may override via i18n using `error_code` as key
- **D-04:** `request_id` included in every error response for observability and debugging correlation
- **D-05:** Enforce consistency via Pydantic BaseModel `ErrorResponse` schema — all error handlers must return this shape

### Exception Hierarchy
- **D-06:** Domain-grouped exception hierarchy with base class `PaperyError` carrying `status_code: int`, `error_code: str`, `detail: Any | None`
- **D-07:** Subclasses: `ResourceNotFoundError`, `AuthError`, `AccessDeniedError`, `ConflictError`, `ValidationError`, `StorageError`, `RateLimitError`, `ExternalServiceError`
- **D-08:** Single catch-all exception handler in `main.py` that reads `.status_code` from `PaperyError` — no need to add handlers per phase
- **D-09:** Inner layers (CRUD, services) raise domain exceptions, not HTTP exceptions — keeps business logic decoupled from transport

### Health Check Endpoints
- **D-10:** Follow Dify's health check pattern — `/health` for liveness (immediate 200), `/ready` for deep readiness checks
- **D-11:** Binary healthy/unhealthy for `/ready` — returns 200 if all services pass, 503 if any fail. No degraded state (no external LB reading response body in current VPS+Docker setup)
- **D-12:** Per-service timeout: 2-3s each for PostgreSQL, Redis, MinIO checks. No caching of health results (Docker Compose probes at 10-30s intervals — caching unnecessary)
- **D-13:** MinIO health check wrapped in `run_in_executor()` (SDK is synchronous) with 2s timeout

### CORS Configuration
- **D-14:** Explicit origin allowlist from `CORS_ORIGINS` environment variable — already partially implemented in `main.py`
- **D-15:** Production validation: reject wildcard `*` in allowlist; startup validator must enforce this in non-local environments

### API Versioning
- **D-16:** All endpoints under `/api/v1/` prefix — router aggregation in `app/api/v1/__init__.py`
- **D-17:** OpenAPI docs accessible at `/api/v1/docs` (Swagger UI) — only in DEBUG mode (already configured)

### Production Docker
- **D-18:** ASGI server: `gunicorn` with `uvicorn-worker` package (not deprecated `uvicorn.workers`)
- **D-19:** Worker count: `WEB_CONCURRENCY=2` default, configurable via environment variable. Async FastAPI is I/O-bound — 2 workers handle high concurrency
- **D-20:** Base image: `python:3.12-slim` (uv docs standard, avoids musl issues with psycopg/cryptography on Alpine)
- **D-21:** 2-stage multi-stage build: builder stage installs deps with `uv sync --locked`, runtime stage copies only `.venv` to fresh slim image
- **D-22:** No `--reload` in production, proper signal handling for graceful shutdown

### Directory Structure (DDD-style)
- **D-23:** Flat DDD-style directory structure — `models/`, `api/`, `schemas/`, `repository/`, `services/`, `core/`, `extensions/`, `config/` as separate top-level directories under `app/`. Not domain-module grouped (not `modules/auth/`, `modules/project/` etc.)
- **D-24:** This carries forward from Phase 1 structure (`app/api/`, `app/models/`, `app/schemas/`, `app/crud/`, `app/services/`, `app/core/`, `app/extensions/`) — rename `crud/` to `repository/` for DDD clarity if appropriate, or keep as-is for consistency with fastcrud

### Claude's Discretion
- Exact exception class constructors and convenience factory methods
- Request ID generation strategy (UUID4 middleware vs header propagation)
- Specific error_code naming convention (UPPER_SNAKE vs dot.separated)
- Logging integration with error responses
- OpenAPI response schema annotations for error types

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Enterprise Architecture Reference
- `.reference/dify/` — Dify enterprise patterns for health checks, error handling, Docker production images
- `.reference/dify/api/controllers/` — Dify's API error handling patterns
- `.reference/dify/docker/` — Production Docker configuration, multi-stage builds

### Project Documentation
- `.planning/ROADMAP.md` — Phase 2 requirements (INFRA-06, 07, 08, 10, 12) and success criteria
- `.planning/REQUIREMENTS.md` — Full requirement details for INFRA-06 through INFRA-12
- `.planning/codebase/ARCHITECTURE.md` — v0 architectural patterns, exception patterns from v0
- `.planning/codebase/CONVENTIONS.md` — Code style, naming conventions
- `.planning/codebase/STRUCTURE.md` — Target directory layout

### Existing Code (Phase 1 output)
- `backend/app/main.py` — FastAPI app entry point, CORSMiddleware already configured, health router mounted
- `backend/app/api/v1/health.py` — Basic `/health` endpoint (liveness only, needs `/ready` deep check)
- `backend/app/extensions/` — `ext_database.py`, `ext_redis.py`, `ext_minio.py` — extensions that `/ready` must check
- `backend/app/core/config/` — Modular Pydantic Settings (CORS_ORIGINS already defined)
- `docker/docker-compose.yaml` — Full stack Docker Compose with service healthchecks
- `docker/Dockerfile.dev` — Development Dockerfile (production Dockerfile to be created)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/main.py` — FastAPI app with lifespan, CORSMiddleware already added
- `backend/app/api/v1/health.py` — Basic health endpoint to extend with `/ready`
- `backend/app/extensions/` — Database, Redis, MinIO extension singletons for health checks
- `backend/app/core/config/` — Modular Pydantic Settings with CORS_ORIGINS
- `docker/Dockerfile.dev` — Development Dockerfile as base reference for production Dockerfile

### Established Patterns
- FastAPI lifespan pattern for startup/shutdown
- Extension init/shutdown pattern (ext_database, ext_redis, ext_minio)
- Docker Compose split (middleware vs full stack)
- uv as package manager with `pyproject.toml`
- Pydantic Settings modular composition via multiple inheritance

### Integration Points
- Exception handler registration in `main.py` (single catch-all for PaperyError)
- Router mounting under `/api/v1/` prefix (health router already mounted)
- CORS middleware configuration (already in `main.py`, needs production validation)
- Docker Compose `web` service needs production Dockerfile reference
- Phase 3 (Auth) will be the first consumer of the error format and exception hierarchy

</code_context>

<specifics>
## Specific Ideas

- **Follow Dify patterns** for health check implementation — study how Dify does readiness checks
- **DDD-style flat directories** — user explicitly wants models, api, schemas, repository, services, core, extensions, config as separate clear directories, NOT domain-module grouped
- **uvicorn-worker package** (by Kludex) for production — `uvicorn.workers` is deprecated upstream
- **Error format must support frontend i18n** — `error_code` as machine-readable key for Vietnamese/English error messages on frontend

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-error-handling-api-structure-health*
*Context gathered: 2026-04-02*
