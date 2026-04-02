# Summary: Plan 02-04 — Production Dockerfile, Dependencies & Tests

```yaml
plan: 02-04
wave: 3
phase: 02
status: complete
completed_at: "2026-04-03"
duration_estimate: ~15min
tasks_completed: 5
tasks_total: 5
tests_added: 42
tests_total: 61
```

## What Was Done

### T1 — Production dependencies in pyproject.toml
- Added `gunicorn>=23.0.0` and `uvicorn-worker>=0.3.0` to main `dependencies` list
- Ran `uv lock` — resolved to gunicorn v25.3.0 and uvicorn-worker v0.4.0
- These are production deps (not dev-only) since the production Dockerfile needs them

### T2 — Production Dockerfile (multi-stage build)
- Created `docker/Dockerfile` with two stages:
  - **Stage 1 (builder):** `python:3.12-slim`, installs uv from ghcr, runs `uv sync --locked --no-dev --no-install-project`
  - **Stage 2 (runtime):** fresh `python:3.12-slim`, copies only `.venv` from builder — minimal image
- Non-root `papery` user (uid/gid 1000) for security
- `WEB_CONCURRENCY=2` default, overridable via env var
- Shell-form CMD so `${WEB_CONCURRENCY:-2}` expands properly at runtime
- HEALTHCHECK uses stdlib `urllib.request` (no curl needed in minimal image)
- `gunicorn` with `uvicorn_worker.UvicornWorker` (not deprecated `uvicorn.workers`)
- No `--reload` in production

### T3 — Production service in docker-compose.yaml
- Added `web-prod` service with `profiles: [production]`
- Build context is `..` (repo root) since Dockerfile COPYs from `backend/`
- No source volume mount — production uses baked-in code
- `WEB_CONCURRENCY` env var passed through
- Healthcheck mirrors Dockerfile HEALTHCHECK
- `depends_on` all three services with `service_healthy` conditions
- Existing `web` (dev) service unchanged

### T4 — Exception hierarchy unit tests (`test_exceptions.py`)
- 19 tests covering `PaperyError` base class (6 tests), all 8 domain exceptions (9 tests), `ErrorResponse` schema (4 tests)
- Verifies `status_code`, `error_code`, `message`, `detail`, `isinstance` hierarchy
- Verifies `model_dump()` output shape

### T5 — Integration tests (`test_health.py`) + updated `test_app.py`
- `test_health.py` — 11 tests across 4 classes:
  - `TestReadyEndpoint` (3 tests): 200 healthy, 503 on DB down, 503 on Redis down
  - `TestExceptionHandlerIntegration` (2 tests): 404 and 405 return `ErrorResponse` format
  - `TestRequestIDMiddleware` (3 tests): X-Request-ID header, client propagation, error body
  - `TestOpenAPIVersionedDocs` (3 tests): openapi_url and docs_url versioned at `/api/v1/`
- `test_app.py` — updated `test_app_has_docs_in_debug_mode` to assert `docs_url == "/api/v1/docs"`

## Files Created/Modified

| File | Action | Notes |
|------|--------|-------|
| `backend/pyproject.toml` | Modified | Added gunicorn + uvicorn-worker |
| `backend/uv.lock` | Modified | Updated after uv lock |
| `docker/Dockerfile` | Created | Production multi-stage build |
| `docker/docker-compose.yaml` | Modified | Added web-prod service |
| `backend/tests/test_exceptions.py` | Created | 19 exception unit tests |
| `backend/tests/test_health.py` | Created | 11 integration tests |
| `backend/tests/test_app.py` | Modified | Updated docs_url assertion |

## Test Results

```
61 passed in 0.35s
- test_app.py:       9 tests ✅
- test_config.py:    7 tests ✅  
- test_exceptions.py: 19 tests ✅
- test_health.py:    11 tests ✅
- test_models.py:    15 tests ✅
```

## Requirements Satisfied

| Requirement | Status |
|------------|--------|
| INFRA-06 | ✅ Exception hierarchy + ErrorResponse + handlers tested |
| INFRA-07 | ✅ OpenAPI at /api/v1/docs and /api/v1/openapi.json |
| INFRA-08 | ✅ /ready endpoint with 200/503 tested |
| INFRA-10 | ✅ Covered by earlier plans (request ID middleware) |
| INFRA-12 | ✅ Production Dockerfile with gunicorn + uvicorn-worker |

## Decisions Made

None new — all implementation followed plan specifications exactly.

## Phase 2 Completion

All 4 plans in Phase 2 are now complete:
- 02-01 ✅ PaperyError base + domain exceptions + ErrorResponse schema
- 02-02 ✅ RequestIDMiddleware
- 02-03 ✅ api_v1_router aggregator + exception handlers in main.py + /ready endpoint + CORS guard
- 02-04 ✅ Production Dockerfile + dependencies + comprehensive tests
