---
phase: 01-backend-core-infrastructure
plan: "04"
subsystem: infra
tags: [redis, minio, async, connection-pool, presigned-urls, fastapi-lifespan]

# Dependency graph
requires:
  - phase: 01-backend-core-infrastructure plan 01
    provides: FastAPI scaffold, extension pattern (ext_database.py)
  - phase: 01-backend-core-infrastructure plan 03
    provides: ext_database.py pattern, main.py lifespan hook established

provides:
  - ext_redis.py — three isolated async Redis clients (cache db=0, queue db=1, rate_limit db=2)
  - ext_minio.py — MinIO client with bucket auto-create, presigned GET/PUT URLs, async upload
  - main.py updated — both extensions wired into FastAPI lifespan with correct startup/shutdown order

affects:
  - Phase 3 (Auth Core) — Redis cache_client for token blacklist, rate_limit_client for auth rate limiting
  - Phase 5 (User Profile) — MinIO ext for avatar upload via presigned PUT URLs
  - Phase 6 (Tier & Permissions) — rate_limit_client for tier-aware rate limiting
  - Phase 2 (Error Handling & Health) — /ready endpoint will check Redis + MinIO connectivity

# Tech tracking
tech-stack:
  added:
    - redis[asyncio] 5.x (already in pyproject.toml via Plan 01)
    - minio 7.x (already in pyproject.toml via Plan 01)
  patterns:
    - Module-level singleton with init()/shutdown() — same pattern as ext_database.py
    - Three separate Redis DB numbers (0/1/2) instead of SELECT command (connection-pool safe)
    - MinIO sync init() called without await in async lifespan (SDK is urllib3-based)
    - run_in_executor for blocking MinIO put_object in async context

key-files:
  created:
    - backend/app/extensions/ext_redis.py
    - backend/app/extensions/ext_minio.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Three separate ConnectionPool instances (one per Redis DB) prevents namespace starvation under load"
  - "aclose() not close() for Redis async cleanup — redis.asyncio API requirement"
  - "MinIO init()/shutdown() are sync (no await) — SDK uses urllib3, not asyncio"
  - "upload_file() uses asyncio.get_running_loop().run_in_executor() — not deprecated get_event_loop()"
  - "Import order in main.py is alphabetical (ruff-enforced): ext_database, ext_minio, ext_redis"

patterns-established:
  - "Extension singleton pattern: module-level globals + init()/shutdown() async functions"
  - "Fail-fast ping() verification during Redis init() — startup fails immediately if Redis unreachable"
  - "Bucket auto-create on MinIO init() — idempotent, eliminates manual setup"

requirements-completed:
  - INFRA-03
  - INFRA-04

# Metrics
duration: 14min
completed: 2026-04-02
---

# Phase 1 Plan 04: Redis & MinIO Extensions Summary

**Redis 3-namespace isolation (cache/queue/rate_limit) and MinIO file storage with presigned URL generation wired into FastAPI lifespan using the established ext_database singleton pattern.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-02T05:20:54Z
- **Completed:** 2026-04-02T05:35:29Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `ext_redis.py` with 3 isolated async clients (cache db=0, queue db=1, rate_limit db=2), each with independent ConnectionPool and fail-fast ping() on startup
- Created `ext_minio.py` with sync init/shutdown, bucket auto-create, presigned GET/PUT URL generation, and async-safe upload via run_in_executor
- Updated `main.py` lifespan: startup order database→redis→minio, shutdown order minio→redis→database (reverse)

## Task Commits

Each task was committed atomically:

1. **Task 4.1: Redis extension with 3-namespace isolation** - `f706bd2` (feat)
2. **Task 4.2: MinIO extension with presigned URL support** - `e8308d1` (feat)
3. **Task 4.3: Wire Redis and MinIO into FastAPI lifespan** - `fe36a1e` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `backend/app/extensions/ext_redis.py` — Three isolated async Redis clients with ConnectionPool, health checks, fail-fast ping, aclose() shutdown
- `backend/app/extensions/ext_minio.py` — MinIO client singleton, bucket auto-create, presigned_get_url(), presigned_put_url(), async upload_file() via run_in_executor
- `backend/app/main.py` — Added ext_redis and ext_minio imports, wired into lifespan startup/shutdown with correct ordering

## Decisions Made

- **Three separate ConnectionPools** instead of one shared pool with SELECT: each namespace gets independent pool sizing, preventing cache traffic from starving rate_limit connections
- **`aclose()` not `close()`**: redis.asyncio.Redis requires `aclose()` for proper coroutine cleanup; `close()` exists but is not awaitable
- **MinIO sync pattern**: MinIO SDK is urllib3-based, not asyncio. `init()` runs once at startup (no blocking concern), presigned URL generation is local crypto (no network). Only `upload_file()` wraps in `run_in_executor`
- **`asyncio.get_running_loop()`** not `asyncio.get_event_loop()`: the latter is deprecated in Python 3.10+ and raises deprecation warnings in 3.12
- **Import alphabetical order**: ruff isort enforces alphabetical import order — `ext_minio` sorts before `ext_redis`, but functional startup/shutdown order in lifespan body is correct (database→redis→minio)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Import statement alphabetical ordering**
- **Found during:** Task 4.3 (wire extensions into lifespan)
- **Issue:** Plan spec `from app.extensions import ext_database, ext_redis, ext_minio` has ext_redis before ext_minio, but ruff isort enforces alphabetical ordering
- **Fix:** Used `from app.extensions import ext_database, ext_minio, ext_redis` (ruff-compliant). Functional startup/shutdown ORDER in lifespan body is unchanged and correct
- **Files modified:** backend/app/main.py
- **Verification:** `ruff check app/extensions/` passes; startup order in lifespan is still database→redis→minio
- **Committed in:** fe36a1e (Task 4.3 commit)

---

**Total deviations:** 1 auto-fixed (1 style/convention)
**Impact on plan:** Zero functional impact — only import line ordering differs, not execution order.

## Issues Encountered

None — all three verification checks passed:
- `uv run python -c "from app.extensions.ext_redis import ..."` → "Redis ext OK"
- `uv run python -c "from app.extensions.ext_minio import ..."` → "MinIO ext OK"
- `uv run ruff check app/extensions/` → "All checks passed!"

## User Setup Required

None — no external service configuration required for extension code itself. Redis and MinIO connectivity is verified when `docker compose up` starts middleware services (covered in Plan 02 Docker Compose setup).

## Next Phase Readiness

- **ext_redis** provides `cache_client`, `queue_client`, `rate_limit_client` ready for import anywhere in the app
- **ext_minio** provides `presigned_get_url()`, `presigned_put_url()`, `upload_file()` ready for document/avatar features
- **Plan 05** (the final plan of Phase 1) can proceed — all infrastructure extensions are now complete
- All Phase 1 success criteria for INFRA-03 and INFRA-04 satisfied

---
*Phase: 01-backend-core-infrastructure*
*Completed: 2026-04-02*
