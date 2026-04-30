---
phase: 10-dashboard-admin-ui-quasarflow-stubs
plan: 01
subsystem: api
tags: [quasarflow, stub, pydantic, contracts, pytest]
requires:
  - phase: 10-dashboard-admin-ui-quasarflow-stubs
    provides: Phase context and locked polling-first integration decisions
provides:
  - Typed QuasarFlow provider interface with submit/process/status contracts
  - Canonical AI job request/response DTO boundary with strict validation
  - Deterministic realistic stub provider for development-time AI flows
affects: [QFLOW-01, QFLOW-02, backend-service-boundary, ai-job-orchestration]
tech-stack:
  added: []
  patterns:
    - Contract-first provider abstraction in service layer
    - Canonical DTO validation at provider boundary
    - Deterministic seeded stub realism for repeatable tests
key-files:
  created:
    - backend/app/services/quasarflow/contracts.py
    - backend/app/services/quasarflow/stub_client.py
    - backend/app/services/quasarflow/__init__.py
    - backend/app/schemas/ai_job.py
    - backend/tests/test_quasarflow_stub.py
  modified:
    - backend/pyproject.toml
key-decisions:
  - "Kept QuasarFlow contract transport-agnostic with submit/process/status typed methods to preserve future SSE migration path."
  - "Validated all stub outputs through canonical AIJobProviderResponse schema before returning from the provider boundary."
patterns-established:
  - "Provider boundary pattern: service code consumes contracts + schema only, never concrete provider module imports"
  - "Stub realism pattern: deterministic payloads seeded by job_id with summary, citations, and status metadata"
requirements-completed: [QFLOW-01, QFLOW-02]
duration: 31 min
completed: 2026-04-28
---

# Phase 10 Plan 01: QuasarFlow Contract Boundary Summary

**Transport-agnostic QuasarFlow contract + deterministic realistic stub provider validated by canonical AI job DTOs and focused tests.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-04-28T09:35:00Z
- **Completed:** 2026-04-28T10:06:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Established typed QuasarFlow abstraction with explicit submit/process/status operations (`QuasarFlowClient`).
- Added canonical `ai_job` schema boundary with strict Pydantic validation for request, status, output, and structured error payloads.
- Implemented deterministic development stub returning realistic summaries, citations, token/latency metadata, and canonical failure mode for simulation.
- Added test coverage that verifies contract shape, schema acceptance/rejection behavior, provider decoupling at import level, deterministic output, and failure payload compliance.

## Task Commits

1. **Task 1 (TDD RED): Define QuasarFlow contracts/schema expectations** - `7838ca3` (test)
2. **Task 1 (TDD GREEN): Implement contracts and canonical schema boundary** - `3126632` (feat)
3. **Task 2 (TDD GREEN): Implement deterministic realistic stub provider** - `71b05e1` (feat)

## Files Created/Modified

- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/services/quasarflow/contracts.py` - Abstract typed provider boundary and result contracts.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/services/quasarflow/stub_client.py` - Deterministic realistic stub implementation with canonical success/failure outputs.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/services/quasarflow/__init__.py` - QuasarFlow service package marker.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/schemas/ai_job.py` - Canonical request/response DTOs and status/error definitions.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/tests/test_quasarflow_stub.py` - Contract, schema, determinism, and realism test coverage.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml` - Registered custom pytest markers used by new test suite.

## Decisions Made

- Used explicit `AIJobStatus` enum with terminal and non-terminal states (`pending`, `running`, `succeeded`, `failed`, `timed_out`) to keep polling-first compatibility and future SSE extensibility.
- Required structured `AIJobErrorDetail` for failed/timed_out payloads to prevent malformed error propagation across trust boundary.
- Deterministic stub realism is based on `job_id` seed and includes citation-like objects expected by downstream dashboard/admin surfaces.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Registered pytest markers used by new contract/schema/stub tests**
- **Found during:** Task 2 verification
- **Issue:** New tests introduced custom markers (`contract`, `schema`, `stub`) that were not registered in pytest config, causing warning noise and unstable strict-marker setups.
- **Fix:** Added marker registrations under `[tool.pytest.ini_options].markers` in `backend/pyproject.toml`.
- **Files modified:** `backend/pyproject.toml`
- **Verification:** `uv run pytest tests/test_quasarflow_stub.py -q` passes cleanly with no unknown-marker warnings.
- **Committed in:** `71b05e1`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Improves reliability of automated verification without scope creep; all planned deliverables remain intact.

## Issues Encountered

- None.

## Authentication Gates

- None.

## Known Stubs

- None that block this plan objective. The implemented stub provider is intentional and required by plan scope.

## Next Phase Readiness

- QuasarFlow provider boundary is now stable for wiring async submit/status orchestration in follow-up plans.
- Deterministic stub behavior enables reproducible dashboard/admin integration tests before real QuasarFlow connectivity.

## Self-Check: PASSED

- Verified created files exist on disk.
- Verified all task commit hashes are present in git history (`7838ca3`, `3126632`, `71b05e1`).
