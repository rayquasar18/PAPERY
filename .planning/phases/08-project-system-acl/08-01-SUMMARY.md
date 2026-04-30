---
phase: 08-project-system-acl
plan: 01
subsystem: api
tags: [projects, acl, soft-delete, fastapi, sqlalchemy, pytest]
requires:
  - phase: 06-tier-system-permissions
    provides: usage-limit enforcement dependency and usage tracking service
  - phase: 03-authentication-core-flows
    provides: authenticated user dependency and JWT-backed route protection
provides:
  - project ORM contracts with owner/editor/viewer roles
  - repository-backed project create/detail/update/soft-delete behavior
  - authenticated project CRUD routes with create quota guard
  - regression coverage for owner seeding and soft-delete exclusion
affects: [08-02, 08-03, 08-04, project-acl, invites, project-listing]
tech-stack:
  added: []
  patterns:
    - repository-first project access via ProjectService(db)
    - not-found masking for inaccessible project UUIDs
    - soft-delete-only deletion path for projects
key-files:
  created:
    - backend/app/models/project.py
    - backend/app/repositories/project_repository.py
    - backend/app/schemas/project.py
    - backend/app/services/project_service.py
    - backend/app/api/v1/projects.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/repositories/__init__.py
    - backend/app/api/v1/__init__.py
    - backend/tests/test_projects.py
key-decisions:
  - "Create endpoint keeps CheckUsageLimit('projects') as dependency guard while resolving user identity via get_current_active_user."
  - "Project detail/update/delete access resolves through owner/member scoped repository lookup and raises NotFoundError when inaccessible."
patterns-established:
  - "Project model uses UUIDMixin + TimestampMixin + SoftDeleteMixin and avoids hard-delete helpers."
  - "Owner membership is seeded at project creation through repository transaction flow."
requirements-completed: [PROJ-01, PROJ-02]
duration: 14 min
completed: 2026-04-27
---

# Phase 08 Plan 01: Project Core CRUD Summary

**Project CRUD foundation shipped with owner membership seeding, authenticated service/routing, and immediate soft-delete exclusion from normal reads.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-27T08:11:08Z
- **Completed:** 2026-04-27T08:25:30Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Added core project contracts: `Project`, `ProjectMember`, and `ProjectMemberRole` (`owner`, `editor`, `viewer`) with soft-delete support.
- Implemented `ProjectRepository` and `ProjectService(db)` for create/read/update/soft-delete flows using repository-first data access only.
- Added authenticated `/api/v1/projects` POST/GET/PATCH/DELETE routes with create quota enforcement and not-found masking semantics.
- Added `backend/tests/test_projects.py` coverage for owner seeding, schema validation bounds, authenticated CRUD, and soft-delete exclusion.

## Task Commits

Each task was committed atomically:

1. **Task 1 (TDD RED): Add project CRUD/contract failing tests** - `d747a67` (test)
2. **Task 1 (TDD GREEN): Add project models/repository/schemas and satisfy contract tests** - `b29f2a2` (feat)
3. **Task 2 (TDD GREEN): Implement project service/routes and complete CRUD behavior tests** - `da4c9d3` (feat)

## Files Created/Modified
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/models/project.py` - Project and membership ORM contracts.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/repositories/project_repository.py` - ACL-scoped project repository helpers and owner-seed persistence.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/schemas/project.py` - Project create/update/read contracts with trimmed name validation bounds.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/services/project_service.py` - CRUD business logic + usage increment after successful create.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/v1/projects.py` - Authenticated project CRUD endpoints.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/v1/__init__.py` - Router registration for projects API.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/models/__init__.py` - Barrel export registration for new project models.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/repositories/__init__.py` - Repository barrel export for `ProjectRepository`.
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/tests/test_projects.py` - Integration/regression coverage for this plan scope.

## Decisions Made
- Kept project create quota guard at route dependency level and incremented usage only after successful persistence in service.
- Enforced inaccessible UUID handling via `NotFoundError` to reduce IDOR disclosure.
- Restricted deletion to soft-delete path only; no restore or hard-delete behavior introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed create-route validation failure caused by dependency patching approach in tests**
- **Found during:** Task 2 verification
- **Issue:** Patching `CheckUsageLimit.__call__` directly introduced FastAPI dependency signature mismatch and 422 errors in test execution.
- **Fix:** Introduced module-level `create_project_usage_guard` dependency instance in routes and overrode it through `app.dependency_overrides` in tests.
- **Files modified:** `backend/app/api/v1/projects.py`, `backend/tests/test_projects.py`
- **Verification:** `cd backend && uv run pytest tests/test_projects.py -q`
- **Committed in:** `da4c9d3`

**2. [Rule 1 - Bug] Fixed mocked service return shape causing Pydantic model validation error**
- **Found during:** Task 2 verification
- **Issue:** `MagicMock` objects used as model returns produced invalid attribute types (e.g., `name` resolving to MagicMock).
- **Fix:** Switched to `SimpleNamespace` payload objects with concrete scalar values and explicit `NotFoundError` side effects.
- **Files modified:** `backend/tests/test_projects.py`
- **Verification:** `cd backend && uv run pytest tests/test_projects.py -q`
- **Committed in:** `da4c9d3`

---

**Total deviations:** 2 auto-fixed (2 rule-1 bug fixes)
**Impact on plan:** Deviations were test/runtime correctness fixes required to satisfy acceptance criteria without scope creep.

## Authentication Gates
None.

## Issues Encountered
- Initial RED test run failed as expected before project modules existed.
- One dependency-override mismatch and one mock shape mismatch were resolved inline during Task 2.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for 08-02 ACL matrix implementation on top of seeded owner membership.
- Project CRUD base and soft-delete behavior are stable with regression coverage.

## Self-Check: PASSED
- FOUND: /Users/mqcbook/Documents/github/my-source/PAPERY/.planning/phases/08-project-system-acl/08-01-SUMMARY.md
- FOUND: d747a67
- FOUND: b29f2a2
- FOUND: da4c9d3
