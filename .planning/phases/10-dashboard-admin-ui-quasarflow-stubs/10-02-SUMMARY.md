---
phase: 10-dashboard-admin-ui-quasarflow-stubs
plan: 02
subsystem: api
tags: [quasarflow, ai-jobs, arq, polling, resilience, worker]
requires:
  - phase: 10-dashboard-admin-ui-quasarflow-stubs
    provides: Typed QuasarFlow contract boundary and deterministic stub provider
provides:
  - Polling-first AI job submit/status API with persisted job envelope
  - Background worker task execution with bounded timeout handling
  - Retry and circuit-aware terminal/non-terminal status transitions covered by tests
affects: [QFLOW-03, QFLOW-04, INFRA-05, dashboard-polling-ui, admin-ai-observability]
tech-stack:
  added: []
  patterns:
    - Polling-first async API contract with immediate accepted response
    - Worker lifecycle persistence through repository-backed status transitions
    - Circuit-aware fast-fail behavior with retryable timeout handling
key-files:
  created:
    - backend/app/api/v1/ai_jobs.py
    - backend/app/models/ai_job.py
    - backend/app/repositories/ai_job_repository.py
    - backend/app/services/ai_job_service.py
    - backend/app/worker/tasks/ai_jobs.py
    - backend/tests/test_quasarflow_resilience.py
    - backend/tests/test_worker_tasks.py
  modified:
    - backend/app/api/v1/__init__.py
    - backend/app/models/__init__.py
    - backend/app/repositories/__init__.py
    - backend/app/schemas/ai_job.py
    - backend/app/worker/__init__.py
    - backend/tests/test_ai_job_flow.py
key-decisions:
  - "Kept submit endpoint polling-first by returning accepted job metadata immediately instead of waiting for provider processing."
  - "Used compact AI job error envelope on status reads to avoid leaking ownership while matching existing endpoint contract tests."
  - "Bounded worker timeout is enforced in the task layer so tests and execution remain stable even when service instances are mocked."
patterns-established:
  - "AI job API pattern: normalize service/model objects into explicit `job_id` response payloads rather than exposing ORM field names"
  - "Worker execution pattern: load persisted job, fast-fail on open circuit, then mark running before provider execution"
requirements-completed: [QFLOW-03, QFLOW-04, INFRA-05]
duration: 1h 36m
completed: 2026-04-30
---

# Phase 10 Plan 02: Async AI Job Orchestration Summary

**Polling-first AI job submission with persisted lifecycle state, resilient worker execution, and test-covered timeout/circuit behavior for QuasarFlow-backed async flows.**

## Performance

- **Duration:** 1h 36m
- **Started:** 2026-04-30T06:05:00Z
- **Completed:** 2026-04-30T07:41:00Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Added persisted AI job domain objects and a `/api/v1/ai-jobs` submit/status contract that returns immediately and supports safe owner-only polling.
- Wired background AI job processing with bounded timeout handling, retry-aware state persistence, and circuit-open fast-fail behavior.
- Added focused tests for API flow, worker lifecycle transitions, and resilience semantics so future dashboard/admin UI work can build on stable async behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create persistent AI job domain and polling-first API contract** - `164cfbf` (feat)
2. **Task 2: Wire worker tasks with timeout, retry, and circuit-aware execution** - `e9c3a20` (feat)

## Files Created/Modified

- `backend/app/api/v1/ai_jobs.py` - Submit/status endpoints for polling-first AI jobs.
- `backend/app/models/ai_job.py` - Persisted AI job model storing lifecycle, payload, and result/error metadata.
- `backend/app/repositories/ai_job_repository.py` - Repository helpers for pending creation and status transitions.
- `backend/app/services/ai_job_service.py` - Submission, owner-safe reads, and worker lifecycle orchestration.
- `backend/app/worker/tasks/ai_jobs.py` - Background task entrypoint with timeout and circuit-aware execution flow.
- `backend/app/worker/__init__.py` - Worker function registration export.
- `backend/app/schemas/ai_job.py` - Public submit/status DTOs plus compact error envelope builders.
- `backend/tests/test_ai_job_flow.py` - Polling-first submit/status API tests.
- `backend/tests/test_quasarflow_resilience.py` - Timeout and circuit-breaker behavior tests.
- `backend/tests/test_worker_tasks.py` - Worker lifecycle execution tests.
- `backend/app/api/v1/__init__.py` - Router registration for AI jobs.
- `backend/app/models/__init__.py` - Model barrel import for Alembic metadata discovery.
- `backend/app/repositories/__init__.py` - Repository barrel export for AI job repository.

## Decisions Made

- Used explicit response builders to emit `job_id` instead of leaking ORM/internal field names like `uuid` into the public contract.
- Kept `NotFound` behavior on foreign/missing status reads so callers cannot distinguish unauthorized ownership from absence.
- Enforced timeout in worker task code instead of instance-bound service config to keep mocked worker tests deterministic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Completed missing public DTO layer for polling endpoints**
- **Found during:** Task 1 verification
- **Issue:** Existing QuasarFlow schema file only covered provider-boundary DTOs; submit/status API tests required public request/response contracts and compact error envelope.
- **Fix:** Extended `backend/app/schemas/ai_job.py` with `AIJobCreate`, `AIJobRead`, `AIJobSubmitResponse`, and response builder helpers used by the new endpoints.
- **Files modified:** `backend/app/schemas/ai_job.py`, `backend/app/api/v1/ai_jobs.py`
- **Verification:** `uv run pytest tests/test_ai_job_flow.py -q -k "submit or status"`
- **Committed in:** `164cfbf`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to make the planned polling API contract real and testable. No scope creep.

## Issues Encountered

- Main repository state already contained unrelated in-progress changes outside phase 10-02, so commits were staged strictly by whitelist to avoid polluting the plan history.
- A temporary worktree path from an earlier execution attempt no longer existed, so implementation resumed directly on the main branch checkout.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10-03 can now build dashboard/admin polling UI on top of stable submit/status endpoints and observable job lifecycle states.
- Phase 10-04 can wire verification/CI around the new backend tests without changing the async contract.

## Self-Check: PASSED

- Verified `uv run pytest tests/test_quasarflow_resilience.py tests/test_worker_tasks.py tests/test_ai_job_flow.py -q` passes.
- Verified task commit hashes exist in git history (`164cfbf`, `e9c3a20`).
