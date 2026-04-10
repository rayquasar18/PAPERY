---
phase: 04-authentication-advanced-password-management
plan: "04"
subsystem: auth
tags: [jwt, password, bcrypt, fastapi, pydantic, rate-limit, session-invalidation]

# Dependency graph
requires:
  - phase: 04-01
    provides: ChangePasswordRequest and SetPasswordRequest Pydantic schemas
  - phase: 04-03
    provides: invalidate_all_user_sessions in security.py, AuthService class-based pattern, get_current_active_user dependency

provides:
  - POST /auth/change-password endpoint (authenticated, rate-limited 5/min per user)
  - POST /auth/set-password endpoint (authenticated, rate-limited 5/min per user)
  - change_password module-level service function with session invalidation (D-17)
  - set_password module-level service function for OAuth-only users
  - Tests for both endpoints covering all threat model scenarios

affects:
  - 05-documents
  - any phase implementing user account management UI

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-level service functions alongside class-based AuthService (for shared use by routes)
    - get_current_active_user dependency for password mutation endpoints (active account required)
    - Per-user UUID rate limiting keys (not IP-based) for authenticated endpoints
    - D-17 session invalidation: all token families revoked after password change

key-files:
  created:
    - backend/tests/test_change_password.py
  modified:
    - backend/app/services/auth_service.py
    - backend/app/api/v1/auth.py

key-decisions:
  - "change_password and set_password implemented as module-level functions (not class methods) to match existing oauth_login_or_register pattern and allow direct calls from routes"
  - "change-password invalidates ALL sessions via invalidate_all_user_sessions (D-17) — forces re-login on all devices after password change"
  - "set-password does NOT invalidate sessions — OAuth users have no password-based sessions to protect"
  - "Rate limiting keyed on user.uuid (not IP) since endpoints require authentication"
  - "Tests use mock-based approach consistent with conftest.py pattern (no real DB/Redis needed)"

patterns-established:
  - "Per-user UUID rate limit key: f'auth:<action>:{user.uuid}' for authenticated endpoints"
  - "BadRequestError for wrong endpoint (OAuth tries change-password; local user tries set-password)"
  - "UnauthorizedError for wrong credentials (bad current password)"

requirements-completed:
  - USER-03
  - AUTH-06
  - AUTH-07
  - AUTH-08

# Metrics
duration: 15min
completed: 2026-04-10
---

# Plan 04-04: Change Password & Set Password Summary

**POST /auth/change-password and /auth/set-password endpoints with D-17 session invalidation, per-user rate limiting, and full threat model coverage**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-10T00:00:00Z
- **Completed:** 2026-04-10T00:15:00Z
- **Tasks:** 3
- **Files modified:** 3 (2 modified, 1 created)

## Accomplishments
- `change_password` service function: verifies current password via bcrypt, updates hash, calls `invalidate_all_user_sessions` to revoke all token families (D-17 security requirement)
- `set_password` service function: allows OAuth-only users (hashed_password IS NULL) to add a password; raises BadRequestError if password already exists
- Two authenticated API routes with `get_current_active_user` dependency and 5 req/min per-user rate limiting
- Tests covering: auth required, same-password 422, valid change 200, wrong password 401, session invalidation, OAuth user rejection, route-level success

## Task Commits

Each task was committed atomically:

1. **Task T1: Add change_password and set_password service functions** - `81106ab` (feat)
2. **Task T2: Add change-password and set-password API routes** - `7c64338` (feat)
3. **Task T3: Write tests for change-password and set-password** - `8977ed3` (test)

## Files Created/Modified
- `backend/app/services/auth_service.py` - Added `invalidate_all_user_sessions` import + `change_password` and `set_password` module-level functions
- `backend/app/api/v1/auth.py` - Added `ChangePasswordRequest`, `SetPasswordRequest` imports; `get_current_active_user` dependency; routes 14 and 15
- `backend/tests/test_change_password.py` - 11 test cases across TestChangePassword and TestSetPassword classes

## Decisions Made
- `change_password` and `set_password` as module-level functions (matching `oauth_login_or_register` pattern) so routes can call `await auth_service.change_password(db, user, ...)` directly
- Rate limit key uses `user.uuid` (not IP) since these are authenticated endpoints — prevents per-user brute force
- Mock-based tests consistent with existing conftest.py approach (no real DB/Redis overhead)

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None — implementation was straightforward following established patterns from 04-01 and 04-03.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Auth system now complete: register, login, logout, refresh, email verify, password reset, OAuth (Google/GitHub), change-password, set-password
- Ready for Phase 05 (document management) or any feature phase requiring authenticated users
- No blockers

---
*Phase: 04-authentication-advanced-password-management*
*Completed: 2026-04-10*
