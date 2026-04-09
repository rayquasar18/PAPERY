# Quick Plan: Refactor Backend — core/ as Foundation, extensions/ → infra/, tasks/ → worker/

**ID:** 260409-sml
**Type:** refactor
**Created:** 2026-04-09
**Estimated:** ~20 min

---

## Goal

Restructure backend architecture so `core/` stays a lean Foundation layer (DB + exceptions only), move external service integrations from `extensions/` to `infra/`, and rename `tasks/` to `worker/` for background task definitions.

## Rationale

`core/` should never grow when new external services are added — it's the domain foundation. Redis, MinIO, email, broker are infrastructure concerns that can be swapped/disabled. The `extensions/` naming is Dify-inspired but doesn't communicate intent; `infra/` is clearer and standard. `worker/` is more descriptive than `tasks/` for background job definitions.

---

## Current State

### Files to Move/Rename

| Current Path | Target Path | Action |
|---|---|---|
| `app/extensions/ext_redis.py` | `app/infra/redis/client.py` | Move + rename |
| `app/extensions/ext_minio.py` | `app/infra/minio/client.py` | Move + rename |
| `app/extensions/__init__.py` | DELETE | Remove directory |
| `app/tasks/__init__.py` | `app/worker/__init__.py` | Rename directory |

### Files That Import from `extensions`

| File | Current Import | Target Import |
|---|---|---|
| `app/main.py` | `from app.extensions import ext_minio, ext_redis` | `from app.infra.redis import client as redis_client` + `from app.infra.minio import client as minio_client` |
| `app/api/v1/health.py` | `from app.extensions import ext_minio, ext_redis` | `from app.infra.redis import client as redis_client` + `from app.infra.minio import client as minio_client` |
| `tests/conftest.py` | `patch("app.extensions.ext_redis.*")` + `patch("app.extensions.ext_minio.*")` | `patch("app.infra.redis.client.*")` + `patch("app.infra.minio.client.*")` |
| `tests/test_health.py` | `patch("app.api.v1.health.ext_redis")` + `patch("app.api.v1.health.ext_minio")` | `patch("app.api.v1.health.redis_client")` + `patch("app.api.v1.health.minio_client")` |

### Files That Stay Unchanged

- `app/core/db/session.py` — already in correct place
- `app/core/exceptions/` — already in correct place
- `app/core/__init__.py` — already correct docstring

---

## Tasks

### Task 1: Create `infra/` package structure and move Redis + MinIO

**Files to create:**
- `app/infra/__init__.py` — docstring: "Infrastructure services — external integrations (Redis, MinIO, email, broker)."
- `app/infra/redis/__init__.py` — barrel exports from `client.py`
- `app/infra/redis/client.py` — content from `ext_redis.py` (update module docstring)
- `app/infra/minio/__init__.py` — barrel exports from `client.py`
- `app/infra/minio/client.py` — content from `ext_minio.py` (update module docstring)

**Files to delete:**
- `app/extensions/ext_redis.py`
- `app/extensions/ext_minio.py`
- `app/extensions/__init__.py`

**Verification:**
1. `cd backend && uv run python -c "from app.infra.redis.client import init, shutdown, cache_client; print('Redis infra OK')"` → outputs "Redis infra OK"
2. `cd backend && uv run python -c "from app.infra.minio.client import init, shutdown, presigned_get_url; print('MinIO infra OK')"` → outputs "MinIO infra OK"
3. `ls backend/app/extensions/` → directory does not exist

### Task 2: Rename `tasks/` → `worker/` and update all imports

**Files to create:**
- `app/worker/__init__.py` — docstring: "Background worker — task definitions and worker settings."

**Files to delete:**
- `app/tasks/__init__.py`

**Files to update (imports):**

1. **`app/main.py`** — Update imports and lifespan references:
   ```python
   # OLD:
   from app.extensions import ext_minio, ext_redis
   # NEW:
   from app.infra.minio import client as minio_client
   from app.infra.redis import client as redis_client
   ```
   Update lifespan body:
   ```python
   # OLD: await ext_redis.init() / ext_minio.init() / ext_minio.shutdown() / await ext_redis.shutdown()
   # NEW: await redis_client.init() / minio_client.init() / minio_client.shutdown() / await redis_client.shutdown()
   ```

2. **`app/api/v1/health.py`** — Update imports and all references:
   ```python
   # OLD:
   from app.extensions import ext_minio, ext_redis
   # NEW:
   from app.infra.minio import client as minio_client
   from app.infra.redis import client as redis_client
   ```
   Update body: `ext_redis.cache_client` → `redis_client.cache_client`, `ext_minio.client` → `minio_client.client`

3. **`tests/conftest.py`** — Update patch paths:
   ```python
   # OLD:
   patch("app.extensions.ext_redis.init", ...)
   patch("app.extensions.ext_redis.shutdown", ...)
   patch("app.extensions.ext_minio.init", ...)
   patch("app.extensions.ext_minio.shutdown", ...)
   # NEW:
   patch("app.infra.redis.client.init", ...)
   patch("app.infra.redis.client.shutdown", ...)
   patch("app.infra.minio.client.init", ...)
   patch("app.infra.minio.client.shutdown", ...)
   ```

4. **`tests/test_health.py`** — Update patch paths:
   ```python
   # OLD:
   patch("app.api.v1.health.ext_redis")
   patch("app.api.v1.health.ext_minio")
   # NEW:
   patch("app.api.v1.health.redis_client")
   patch("app.api.v1.health.minio_client")
   ```

**Verification:**
1. `cd backend && uv run python -c "from app.worker import __doc__; print('Worker OK')"` → outputs docstring
2. `ls backend/app/tasks/` → directory does not exist
3. `cd backend && uv run pytest -x -q` → all tests pass

### Task 3: Run linter, verify final structure, commit

**Actions:**
1. `cd backend && uv run ruff check --fix .` — auto-fix lint issues
2. `cd backend && uv run ruff format .` — format all changed files
3. `cd backend && uv run pytest -x -q` — all tests pass

**Final structure verification:**
```
backend/app/
├── core/              # Foundation: DB + exceptions (LEAN — never grows for new services)
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── session.py
│   └── exceptions/
│       ├── __init__.py
│       └── handlers.py
├── infra/             # Infrastructure: swappable external services
│   ├── __init__.py
│   ├── redis/
│   │   ├── __init__.py
│   │   └── client.py
│   └── minio/
│       ├── __init__.py
│       └── client.py
├── worker/            # Background task definitions
│   └── __init__.py
├── services/          # Business logic (placeholder)
│   └── __init__.py
├── utils/             # Shared utilities (placeholder)
│   └── __init__.py
├── configs/           # Settings modules
├── api/               # v1 routes
├── middleware/         # Request middleware
├── models/            # SQLAlchemy models
├── schemas/           # Pydantic schemas
└── main.py
```

**Must-haves (GATE):**
- [ ] `app/infra/redis/client.py` exists with same functionality as old `ext_redis.py`
- [ ] `app/infra/minio/client.py` exists with same functionality as old `ext_minio.py`
- [ ] `app/worker/__init__.py` exists
- [ ] `app/extensions/` directory does NOT exist
- [ ] `app/tasks/` directory does NOT exist
- [ ] `app/main.py` imports from `app.infra.*` (not `app.extensions`)
- [ ] `app/api/v1/health.py` imports from `app.infra.*` (not `app.extensions`)
- [ ] All tests pass: `uv run pytest -x -q`
- [ ] Ruff clean: `uv run ruff check .` returns 0

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `infra/redis/client.py` not `infra/redis.py` | Subdirectory | Future-proof: room for `infra/redis/cache.py`, `infra/redis/pubsub.py` etc. |
| `client` alias in imports | `import client as redis_client` | Readable, distinguishes redis vs minio at call sites |
| Barrel `__init__.py` in each infra subpackage | Yes | Clean public API: `from app.infra.redis import client` |
| `worker/` not `jobs/` or `tasks/` | `worker/` | Matches ARQ convention; clearer than generic "tasks" |

## Commit

```
refactor: move extensions/ to infra/, rename tasks/ to worker/

Restructure backend architecture for clearer separation of concerns:
- core/ stays lean (DB + exceptions only) — foundation layer
- infra/ houses swappable external services (Redis, MinIO)
- worker/ replaces tasks/ for background job definitions
- extensions/ directory removed entirely

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
