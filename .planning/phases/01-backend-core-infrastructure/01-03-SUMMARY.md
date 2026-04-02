---
phase: 01-backend-core-infrastructure
plan: "03"
subsystem: database
tags: [sqlalchemy, alembic, postgresql, asyncpg, async-orm]

# Dependency graph
requires:
  - phase: 01-backend-core-infrastructure
    provides: Plan 01 — FastAPI app scaffold, modular Pydantic Settings with ASYNC_DATABASE_URI, extensions/ and models/ stubs
provides:
  - SQLAlchemy async engine and session factory (ext_database.py)
  - Base model with BigInteger PK (dual-ID strategy, INFRA-14)
  - UUIDMixin for public-facing API identifiers
  - TimestampMixin with server-side created_at/updated_at
  - SoftDeleteMixin with deleted_at + is_deleted property (INFRA-15)
  - Alembic async migration setup with autogenerate support
  - FastAPI lifespan wired to init/shutdown database extension
affects:
  - 01-backend-core-infrastructure (plans 04, 05)
  - All subsequent phases using SQLAlchemy models

# Tech tracking
tech-stack:
  added: [sqlalchemy-async, alembic, asyncpg]
  patterns:
    - Dual-ID model pattern (BigInteger PK + UUID public identifier)
    - Extension singleton pattern (module-level engine + init/shutdown)
    - Alembic async migration with NullPool
    - Barrel import in models/__init__.py for Alembic autogenerate discovery

key-files:
  created:
    - backend/app/models/base.py
    - backend/app/models/__init__.py
    - backend/app/extensions/ext_database.py
    - backend/alembic.ini
    - backend/migrations/env.py
    - backend/migrations/script.py.mako
    - backend/migrations/versions/.gitkeep
  modified:
    - backend/app/main.py

key-decisions:
  - "BigInteger PK (not UUID PK) — internal auto-increment for join performance; UUID is secondary public identifier"
  - "server_default=func.now() for timestamps — database-side defaults are more reliable than Python-side"
  - "NullPool for Alembic migrations — avoids connection leaks during migration runs"
  - "Barrel import in models/__init__.py — Alembic autogenerate only discovers models imported into Base.metadata"

patterns-established:
  - "Dual-ID pattern: all core models use Base (int PK) + UUIDMixin (uuid public API) — never expose int ID in API responses"
  - "Soft delete pattern: SoftDeleteMixin.deleted_at IS NULL = active; deleted_at IS NOT NULL = soft deleted"
  - "Extension singleton: module-level engine/session_factory, init() on startup, shutdown() on lifespan exit"
  - "All models must be imported in models/__init__.py for Alembic autogenerate to detect them"

requirements-completed:
  - INFRA-02
  - INFRA-14
  - INFRA-15

# Metrics
duration: 4min
completed: 2026-04-02
---

# Phase 01 Plan 03: Database Layer, Models & Alembic Summary

**Async SQLAlchemy engine with dual-ID Base model (BigInteger PK + UUIDMixin), TimestampMixin, SoftDeleteMixin, and Alembic async migration setup wired into FastAPI lifespan**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-02T05:10:29Z
- **Completed:** 2026-04-02T05:15:03Z
- **Tasks:** 4
- **Files modified:** 8

## Accomplishments

- `Base(DeclarativeBase)` with BigInteger PK + `UUIDMixin` for dual-ID strategy (INFRA-14)
- `TimestampMixin` with server-side `func.now()` and `SoftDeleteMixin` with `is_deleted` property (INFRA-15)
- `ext_database.py` async engine singleton with full pool config, connection verification, and `get_session()` FastAPI dependency
- Alembic async migration environment with `NullPool`, `compare_type=True`, autogenerate via barrel import
- FastAPI lifespan fully wired: `ext_database.init()` on startup, `ext_database.shutdown()` on exit

## Task Commits

Each task was committed atomically:

1. **Task 3.1: SQLAlchemy Base model with mixins** — `71d0547` (feat)
2. **Task 3.2: Database extension ext_database.py** — `671e6fd` (feat)
3. **Task 3.3: Alembic async migrations setup** — `2da9225` (feat)
4. **Task 3.4: Wire lifespan hooks in main.py** — `d04866e` (feat)

**Plan metadata:** `9942445` (docs: complete plan)

## Files Created/Modified

- `backend/app/models/base.py` — Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
- `backend/app/models/__init__.py` — barrel imports for Alembic autogenerate discovery
- `backend/app/extensions/ext_database.py` — async engine singleton + session factory + get_session()
- `backend/alembic.ini` — Alembic config with date-prefixed migration file template
- `backend/migrations/env.py` — async migration runner (NullPool, offline + online modes)
- `backend/migrations/script.py.mako` — migration file template
- `backend/migrations/versions/.gitkeep` — empty versions directory tracked in git
- `backend/app/main.py` — lifespan wired with ext_database.init/shutdown

## Decisions Made

- **BigInteger PK (not UUID PK):** Internal int IDs for join performance; UUIDMixin adds the public-facing UUID column. API consumers only ever see UUIDs.
- **server_default=func.now():** Server-side timestamp defaults are more reliable than Python-side defaults, especially for bulk inserts and migrations.
- **NullPool for Alembic:** Migration runs use NullPool to avoid connection pool leaks; the persistent engine in ext_database.py uses a proper pool.
- **Barrel import in models/__init__.py:** Alembic's autogenerate only discovers models registered in `Base.metadata`. The barrel import ensures every model file triggers the SQLAlchemy mapper registration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RUF022 __all__ sort order in models/__init__.py**
- **Found during:** Post-task ruff verification
- **Issue:** Ruff RUF022 requires isort-style alphabetical sorting of `__all__` exports; `["Base", "UUIDMixin", "TimestampMixin", "SoftDeleteMixin"]` was not sorted
- **Fix:** Sorted to `["Base", "SoftDeleteMixin", "TimestampMixin", "UUIDMixin"]`
- **Files modified:** backend/app/models/__init__.py
- **Verification:** `uv run ruff check app/models/ app/extensions/` — All checks passed
- **Committed in:** `9942445`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial sort fix. No scope creep.

## Issues Encountered

None — all tasks completed as planned.

## User Setup Required

None — no external service configuration required. PostgreSQL connection is needed for `alembic heads` verification (Verification 5), which requires Docker middleware running. This is expected and covered by Plan 02 (Docker Compose dev environment, already complete).

## Next Phase Readiness

- Database layer is complete and ready for Plan 04 (Redis + MinIO extensions)
- All models created in subsequent plans must be added to `models/__init__.py` barrel for Alembic to detect them
- `alembic revision --autogenerate` is ready to generate migrations once concrete models are added
- `ext_database.get_session()` is available as FastAPI `Depends()` for route handlers in Plans 04+

---

*Phase: 01-backend-core-infrastructure*
*Completed: 2026-04-02*
