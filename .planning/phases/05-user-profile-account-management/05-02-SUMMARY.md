---
phase: 05-user-profile-account-management
plan: 05-02
subsystem: api
tags: [minio, pillow, avatar, account-deletion, jwt, redis, fastapi, cookies]

# Dependency graph
requires:
  - phase: 05-01
    provides: UserService skeleton, UserRepository, GET/PATCH /users/me endpoints, AvatarUploadResponse schema, DeleteAccountRequest schema

provides:
  - delete_file() async wrapper on MinIO client (run_in_executor + partial pattern)
  - Shared clear_auth_cookies() utility in app/utils/cookies.py
  - UserService.upload_avatar(): MIME/size validation, Pillow resize 200x200+50x50 WebP, MinIO upload
  - UserService.remove_avatar(): MinIO deletion of both sizes, clears avatar_url
  - UserService.delete_account(): password/email verification, soft-delete, Redis session invalidation, cookie clear
  - POST /api/v1/users/me/avatar endpoint (rate limit: 5/min)
  - DELETE /api/v1/users/me/avatar endpoint (rate limit: 5/min)
  - DELETE /api/v1/users/me endpoint (rate limit: 3/min)
  - 11 new tests covering all happy paths and error cases

affects: [06-tier-system-permissions, 09-frontend-foundation-auth-ui]

# Tech tracking
tech-stack:
  added: [Pillow (PIL) — image resizing and WebP conversion]
  patterns:
    - importlib pattern for MinIO module access (avoids __init__.py singleton collision)
    - Shared cookie utility extracted to utils/cookies.py to avoid cross-router imports
    - run_in_executor + partial for all sync MinIO SDK calls

key-files:
  created:
    - backend/app/utils/cookies.py
  modified:
    - backend/app/infra/minio/client.py
    - backend/app/infra/minio/__init__.py
    - backend/app/services/user_service.py
    - backend/app/api/v1/auth.py
    - backend/app/api/v1/users.py
    - backend/tests/test_users.py

key-decisions:
  - "All MinIO calls in user_service.py use _minio_client_module (importlib) — not from app.infra.minio import client — because __init__.py exports client=None which is stale at import time"
  - "clear_auth_cookies extracted to utils/cookies.py to be shared between auth.py (logout) and users.py (account deletion) without cross-router imports"
  - "Pillow processing is synchronous but acceptable for ≤2MB avatars; noted in comment that run_in_executor should be added for high-volume production"
  - "remove_avatar swallows MinIO deletion exceptions (logs warning) but always clears avatar_url — ensures DB consistency even if MinIO is temporarily unavailable"

patterns-established:
  - "Shared utilities that cross router boundaries live in app/utils/, not in routers"
  - "importlib.import_module pattern for MinIO module to avoid frozen None reference"
  - "Patch target for rate_limit in endpoint tests: app.api.v1.<router>.check_rate_limit (not app.utils.rate_limit.check_rate_limit)"

requirements-completed: [USER-02, USER-04]

# Metrics
duration: 35min
completed: 2026-04-11
---

# Plan 05-02: Avatar Upload/Delete & Account Deletion Summary

**Avatar upload (JPEG/PNG/WebP → 200x200+50x50 WebP via Pillow), avatar removal, and soft-delete account deletion with password/email verification, Redis session invalidation, and HttpOnly cookie clearing**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-04-11T~08:30Z
- **Completed:** 2026-04-11T~09:05Z
- **Tasks:** 5
- **Files modified:** 6 (+ 1 created)

## Accomplishments
- MinIO `delete_file()` async wrapper added using identical `run_in_executor + partial` pattern as `upload_file()`
- `clear_auth_cookies()` extracted from `auth.py` into `app/utils/cookies.py` for shared use between logout and account deletion
- `UserService` expanded with `upload_avatar`, `remove_avatar`, `delete_account` — full USER-02 and USER-04 coverage
- Three new endpoints: `POST /me/avatar`, `DELETE /me/avatar`, `DELETE /me` with per-endpoint rate limits
- 11 new tests (20 total in `test_users.py`) — all pass

## Task Commits

Each task was committed atomically:

1. **Task 05-02-01: Add delete_file() to MinIO client** - `287e426` (feat)
2. **Task 05-02-02: Extract shared cookie utility** - `826fc5b` (refactor)
3. **Task 05-02-03: Add upload_avatar/remove_avatar/delete_account to UserService** - `84aec52` (feat)
4. **Task 05-02-04: Add avatar & account deletion endpoints to users router** - `f94c4fe` (feat)
5. **Task 05-02-05: Tests for avatar upload/remove and account deletion** - `2ba7387` (test)

## Files Created/Modified
- `backend/app/infra/minio/client.py` — Added `delete_file()` async wrapper
- `backend/app/infra/minio/__init__.py` — Exported `delete_file`
- `backend/app/utils/cookies.py` — Created: shared `clear_auth_cookies()` utility
- `backend/app/api/v1/auth.py` — Replaced local `_clear_auth_cookies` with imported `clear_auth_cookies`
- `backend/app/services/user_service.py` — Added `upload_avatar`, `remove_avatar`, `delete_account` methods + Pillow imports
- `backend/app/api/v1/users.py` — Added `POST /me/avatar`, `DELETE /me/avatar`, `DELETE /me` endpoints
- `backend/tests/test_users.py` — Added `TestAvatarUpload`, `TestAvatarRemove`, `TestDeleteAccount` + `valid_jpeg_bytes` fixture

## Decisions Made

- **importlib pattern for MinIO**: `from app.infra.minio import client as minio_client` would capture the `None` singleton at import time (before `init()` is called). Using `_minio_client_module = importlib.import_module("app.infra.minio.client")` and accessing attributes dynamically avoids this. All new methods use `_minio_client_module.*` consistently.
- **Swallow MinIO delete errors in `remove_avatar`**: MinIO unavailability shouldn't prevent DB cleanup. Avatar URL is always cleared; errors are logged as warnings.
- **Patch target in tests**: New tests patch `app.api.v1.users.check_rate_limit` (the imported reference in the router module), not `app.utils.rate_limit.check_rate_limit` (source module). This matches the existing test pattern in `TestGetProfile`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Correctness] Fixed MinIO import to use _minio_client_module consistently**
- **Found during:** Task 05-02-03 (UserService methods)
- **Issue:** Plan used `from app.infra.minio import client as minio_client` which captures `None` at import time due to the `__init__.py` singleton collision noted in the important_context
- **Fix:** Removed the direct import; all new methods use `_minio_client_module.*` (the existing importlib workaround already in the file from 05-01)
- **Files modified:** `backend/app/services/user_service.py`
- **Verification:** Tests mock `app.services.user_service._minio_client_module` successfully
- **Committed in:** `84aec52` (Task 03 commit)

**2. [Correctness] Fixed rate_limit patch path in tests**
- **Found during:** Task 05-02-05 (test run)
- **Issue:** Tests initially patched `app.utils.rate_limit.check_rate_limit` — but endpoint uses the imported reference in `app.api.v1.users`, so patch had no effect; Redis client not initialized error
- **Fix:** Changed all new test patches to `app.api.v1.users.check_rate_limit`
- **Files modified:** `backend/tests/test_users.py`
- **Verification:** All 20 tests pass
- **Committed in:** `2ba7387` (Task 05 commit)

---

**Total deviations:** 2 auto-fixed (both correctness issues, no scope creep)
**Impact on plan:** Both fixes necessary for correct behavior and test isolation. No unplanned features added.

## Issues Encountered

- Pre-existing failing test `test_change_password_same_as_current_returns_422` in `test_change_password.py` — confirmed it was already failing before plan 05-02 started (git stash verified). Not caused by our changes.

## User Setup Required

None — no external service configuration required beyond existing MinIO/Redis setup. Pillow (`Pillow`) must be present in `pyproject.toml` dependencies.

## Next Phase Readiness

- Phase 5 (User Profile & Account Management) is now functionally complete — USER-02 (avatar) and USER-04 (account deletion) implemented and tested
- Phase 6 (Tier System & Permissions) can proceed: `tier_name` placeholder (`"free"`) is in place in `UserProfileRead`, ready to be replaced with real tier logic
- `clear_auth_cookies` shared utility is now available for any future flow that needs to invalidate sessions (e.g., password reset)

---
*Phase: 05-user-profile-account-management*
*Completed: 2026-04-11*
