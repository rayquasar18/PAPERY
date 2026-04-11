---
phase: 05-user-profile-account-management
plan: 01
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, minio, jwt, user-profile]

# Dependency graph
requires:
  - phase: 03-authentication-core-flows
    provides: UserRepository, User model, get_current_active_user dependency, JWT auth
  - phase: 04-authentication-advanced-password
    provides: AuthService class-based DI pattern, OAuthAccount model with oauth_accounts relationship

provides:
  - UserProfileRead schema with computed fields (tier_name, has_password, oauth_providers, presigned avatar_url)
  - UserProfileUpdate schema with display_name validation (2-50 chars, unicode pattern)
  - DeleteAccountRequest and AvatarUploadResponse schemas
  - UserRepository.get_with_oauth_accounts() with selectinload eager loading
  - UserService class with get_profile() and update_profile() methods
  - GET /api/v1/users/me endpoint (full profile with computed fields)
  - PATCH /api/v1/users/me endpoint (display_name edit with rate limiting)
  - users_router registered in api_v1_router aggregator

affects: [phase-05-02-avatar-account-deletion, phase-06-tier-system, phase-07-admin-panel]

# Tech tracking
tech-stack:
  added: [pillow>=10.0.0]
  patterns:
    - importlib.import_module to avoid minio singleton name collision
    - _get_presigned_url wrapper function for patchable minio calls in tests
    - UserService follows AuthService constructor DI pattern

key-files:
  created:
    - backend/app/schemas/user.py
    - backend/app/services/user_service.py
    - backend/app/api/v1/users.py
    - backend/tests/test_users.py
  modified:
    - backend/pyproject.toml (pillow dependency)
    - backend/app/repositories/user_repository.py (get_with_oauth_accounts)
    - backend/app/services/__init__.py (UserService docstring)
    - backend/app/api/v1/__init__.py (users_router registration)

key-decisions:
  - "importlib.import_module('app.infra.minio.client') used in UserService to resolve the actual module, avoiding collision with 'client' singleton (None) exported via app.infra.minio.__init__"
  - "_get_presigned_url wrapper function introduced for clean test patching — avoids patching internal MinIO singleton state"
  - "tier_name hardcoded as 'free' — placeholder until Phase 6 tier system is built"
  - "check_rate_limit patched at app.api.v1.users.check_rate_limit (import location) not app.utils.rate_limit.check_rate_limit (definition location)"

patterns-established:
  - "UserService(db) constructor DI pattern — matches AuthService(db), sets template for all future services"
  - "selectinload(User.oauth_accounts) in get_with_oauth_accounts() — async-safe eager loading avoiding MissingGreenlet"
  - "Patch rate_limit at the router module import site (app.api.v1.users.check_rate_limit) in tests"

requirements-completed:
  - USER-01
  - USER-02

# Metrics
duration: 35min
completed: 2026-04-11
---

# Plan 05-01: User Profile Schemas, Service & GET/PATCH Endpoints Summary

**UserProfileRead with presigned avatar URL, computed has_password/oauth_providers fields, UserService DI class, and GET/PATCH /api/v1/users/me endpoints with rate limiting**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-04-11T07:30:00Z
- **Completed:** 2026-04-11T08:05:00Z
- **Tasks:** 5
- **Files modified:** 8

## Accomplishments
- Created `UserProfileRead` schema with computed fields: `tier_name="free"`, `has_password` (from `hashed_password is not None`), `oauth_providers` (from eager-loaded `oauth_accounts`)
- Built `UserService` class following `AuthService(db)` DI pattern with `get_profile()` (presigned avatar URL) and `update_profile()` (whitespace-stripped display_name)
- Added `UserRepository.get_with_oauth_accounts()` using `selectinload` for async-safe eager loading
- Registered `GET /api/v1/users/me` (60 req/min) and `PATCH /api/v1/users/me` (10 req/min) endpoints with JWT auth
- 9/9 tests pass including unauthenticated, OAuth user, avatar presigned URL, and display_name validation cases

## Task Commits

Each task was committed atomically:

1. **Task 05-01-01: Add Pillow dependency and create user profile schemas** - `c91a477` (feat)
2. **Task 05-01-02: Add get_with_oauth_accounts to UserRepository** - `a110e7b` (feat)
3. **Task 05-01-03: Create UserService with get_profile and update_profile** - `9304b52` (feat)
4. **Task 05-01-04: Create users router with GET and PATCH /users/me** - `3e25cba` (feat)
5. **Task 05-01-05: Create tests + minio wrapper fix** - `f0be6fc` (feat)

## Files Created/Modified
- `backend/app/schemas/user.py` — UserProfileRead, UserProfileUpdate, DeleteAccountRequest, AvatarUploadResponse
- `backend/app/services/user_service.py` — UserService class with get_profile(), update_profile(), _get_presigned_url wrapper
- `backend/app/api/v1/users.py` — GET/PATCH /users/me endpoints with rate limiting
- `backend/tests/test_users.py` — 9 tests covering all endpoint scenarios
- `backend/app/repositories/user_repository.py` — added get_with_oauth_accounts() with selectinload
- `backend/app/api/v1/__init__.py` — registered users_router
- `backend/app/services/__init__.py` — added UserService to docstring
- `backend/pyproject.toml` — added pillow>=10.0.0

## Decisions Made

1. **importlib workaround for minio singleton collision**: `app.infra.minio.__init__.py` exports `client` (the `Minio | None` singleton) which shadows the `client.py` submodule. Used `importlib.import_module("app.infra.minio.client")` to resolve the actual module object.

2. **`_get_presigned_url` wrapper**: A module-level thin wrapper around `_minio_client_module.presigned_get_url()` makes the call patchable in tests via `patch("app.services.user_service._get_presigned_url")`.

3. **Rate limit patch target**: `check_rate_limit` must be patched at `app.api.v1.users.check_rate_limit` (where it was imported into) not `app.utils.rate_limit.check_rate_limit` (its definition site).

## Deviations from Plan

### Auto-fixed Issues

**1. [Test Fix] Corrected patch target for check_rate_limit**
- **Found during:** Task 5 (tests)
- **Issue:** Plan used `patch("app.utils.rate_limit.check_rate_limit")` but the function is imported with `from app.utils.rate_limit import check_rate_limit` in `users.py`, so the patch must target `app.api.v1.users.check_rate_limit`
- **Fix:** Changed all test patches to `app.api.v1.users.check_rate_limit`
- **Files modified:** backend/tests/test_users.py
- **Verification:** All 9 tests pass
- **Committed in:** f0be6fc

**2. [Service Fix] importlib import to avoid minio singleton collision**
- **Found during:** Task 5 (tests — avatar presigned URL test failure)
- **Issue:** `from app.infra.minio import client as minio_client` imports the `None` singleton (not the module), causing `AttributeError: 'NoneType' object has no attribute 'presigned_get_url'`
- **Fix:** Used `importlib.import_module("app.infra.minio.client")` + `_get_presigned_url` wrapper
- **Files modified:** backend/app/services/user_service.py, backend/tests/test_users.py
- **Verification:** Avatar presigned URL test passes
- **Committed in:** f0be6fc

---

**Total deviations:** 2 auto-fixed (1 test patch target, 1 minio import collision)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- MinIO `__init__.py` exports `client` variable (singleton `None`) shadowing the `client` submodule name — required importlib workaround in `user_service.py`. Future plans using MinIO in services should use the same `importlib.import_module("app.infra.minio.client")` pattern.
- Pre-existing test failure in `test_auth_routes.py::TestChangePassword::test_change_password_same_as_current_returns_422` — unrelated to this plan (JSON serialization issue with `ValueError`).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `GET /api/v1/users/me` and `PATCH /api/v1/users/me` fully operational
- `UserService` class ready to be extended in Plan 05-02 (avatar upload, account deletion)
- `_get_presigned_url` pattern established for future MinIO calls in services
- Pre-existing `test_change_password` failure should be investigated separately (not a blocker)

---
*Phase: 05-user-profile-account-management*
*Completed: 2026-04-11*
