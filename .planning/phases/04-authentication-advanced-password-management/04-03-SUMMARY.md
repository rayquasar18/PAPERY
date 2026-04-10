---
phase: 04-authentication-advanced-password-management
plan: "03"
subsystem: auth
tags: [oauth, google, github, jwt, redis, csrf, security]

# Dependency graph
requires:
  - phase: 04-02
    provides: OAuthProvider base class, GoogleOAuthProvider, GitHubOAuthProvider, OAuthAccountRepository, OAuthUserInfo schema, OAuthConfig settings
  - phase: 04-01
    provides: create_password_reset_token, RESET_JTI_PREFIX in security.py; auth_service.reset_password; auth.py reset routes
  - phase: 03-04
    provides: AuthService class, register/login/logout/refresh routes, JWT cookie helpers, token family tracking infrastructure

provides:
  - OAUTH_STATE_PREFIX + create_oauth_state() + validate_oauth_state() — Redis CSRF state for OAuth (10-min TTL, single-use)
  - USER_FAMILIES_PREFIX + track_user_family() + invalidate_all_user_sessions() — per-user session index in Redis
  - oauth_login_or_register() service function — 3-case OAuth user lookup/creation with D-14 auto-link and D-15 single-provider enforcement
  - GET /auth/google + GET /auth/google/callback — Google OAuth initiate + callback routes
  - GET /auth/github + GET /auth/github/callback — GitHub OAuth initiate + callback routes
  - Retroactive track_user_family() calls in register + login routes
  - test_oauth.py — full OAuth test suite (route + service level)

affects:
  - 04-04 (change-password uses invalidate_all_user_sessions from security.py)
  - 05 (user profile — OAuth accounts visible, no password for OAuth users)
  - 09 (frontend — OAuth login buttons, /dashboard redirect after OAuth)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Redis single-use state pattern for OAuth CSRF (setex + delete)
    - Redis set for per-user token family index (sadd + smembers + delete)
    - Module-level service function (oauth_login_or_register) alongside class-based AuthService
    - OAuth callback as redirect-only route (no JSON response, sets cookies on RedirectResponse)

key-files:
  created:
    - backend/tests/test_oauth.py
  modified:
    - backend/app/core/security.py
    - backend/app/services/auth_service.py
    - backend/app/api/v1/auth.py

key-decisions:
  - "oauth_login_or_register implemented as module-level function (not AuthService method) — OAuth doesn't use class-bound UserRepository; cleaner to accept db directly like create_first_superuser"
  - "OAuth callbacks use RedirectResponse — no JSON body; cookies set on the redirect object itself (not on response parameter)"
  - "track_user_family() added retroactively to register and login routes to build per-user session index from the start"
  - "invalidate_all_user_sessions() built in T2 (not T4) to avoid modifying security.py a third time — pre-built for plan 04-04"
  - "D-15 enforced at service layer: single OAuth provider per user; second link raises ConflictError"

patterns-established:
  - "OAuth CSRF pattern: create_oauth_state() on initiate, validate_oauth_state() (delete + check) on callback — single-use via Redis delete"
  - "User session index pattern: track_user_family(user_uuid, family_id) called on every login/register/OAuth — enables bulk invalidation"
  - "OAuth callback error pattern: all failures redirect to frontend /login?error=<code> — no error detail in URL"
  - "Unconfigured OAuth 404 pattern: _get_*_provider() helper raises NotFoundError when client credentials are empty (D-12)"

requirements-completed:
  - AUTH-07
  - AUTH-08

# Metrics
duration: 25min
completed: 2026-04-10
---

# Plan 04-03: OAuth Routes — Google & GitHub Login/Register Summary

**Redis CSRF state + per-user session index + oauth_login_or_register service + 4 OAuth routes (Google/GitHub initiate+callback) with auto-link (D-14), single-provider enforcement (D-15), and full test coverage**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-10T15:30:00Z
- **Completed:** 2026-04-10T15:55:00Z
- **Tasks:** 5
- **Files modified:** 3 modified, 1 created

## Accomplishments
- Added `create_oauth_state()` / `validate_oauth_state()` to security.py for Redis-backed single-use CSRF protection
- Added `track_user_family()` / `invalidate_all_user_sessions()` to security.py for per-user session index (enables all-device logout on password change in plan 04-04)
- Implemented `oauth_login_or_register()` module-level service function with 3-case logic: existing OAuth → login, email match → auto-link (D-14) with single-provider check (D-15), new → register
- Wired 4 OAuth routes: `GET /auth/google`, `GET /auth/google/callback`, `GET /auth/github`, `GET /auth/github/callback`
- Retroactively added `track_user_family()` calls to existing register + login routes

## Task Commits

Each task was committed atomically:

1. **Task T1: OAuth CSRF state helpers** - `819e55e` (feat)
2. **Task T2: User family tracking helpers** - `54820a1` (feat)
3. **Task T3: oauth_login_or_register service function** - `4fc2556` (feat)
4. **Task T4: OAuth routes for Google and GitHub** - `6f35771` (feat)
5. **Task T5: OAuth flow tests** - `eb26c3c` (test)

## Files Created/Modified
- `backend/app/core/security.py` — Added `OAUTH_STATE_PREFIX`, `USER_FAMILIES_PREFIX`, `create_oauth_state()`, `validate_oauth_state()`, `track_user_family()`, `invalidate_all_user_sessions()`
- `backend/app/services/auth_service.py` — Added `OAuthAccountRepository` + `OAuthUserInfo` imports, `oauth_login_or_register()` module-level function
- `backend/app/api/v1/auth.py` — Added `RedirectResponse`, security + provider imports, `_get_google_provider()`, `_get_github_provider()`, 4 OAuth routes, retroactive `track_user_family()` in register + login
- `backend/tests/test_oauth.py` — Created: `TestOAuthDisabled`, `TestOAuthStateValidation`, `TestOAuthCallbackSuccess`, `TestOAuthLoginOrRegister` (13 test functions)

## Decisions Made
- `oauth_login_or_register` is a module-level function (not an `AuthService` method) — mirrors the `create_first_superuser` pattern; OAuth flow doesn't benefit from class-level `_user_repo` binding since it needs `OAuthAccountRepository` too
- `invalidate_all_user_sessions()` built in T2 (alongside `track_user_family`) to avoid a 4th modification to security.py — it's needed by plan 04-04 anyway
- OAuth callbacks are redirect-only routes — no JSON response body; auth cookies are set directly on the `RedirectResponse` object

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all imports and patterns aligned with existing codebase conventions.

## User Setup Required

To use Google OAuth, set in `.env`:
```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

To use GitHub OAuth, set:
```
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

Also configure `OAUTH_REDIRECT_BASE_URL` (defaults to `http://localhost:8000`).

When not configured, endpoints return `404` — no error detail leakage.

## Next Phase Readiness
- `invalidate_all_user_sessions()` in security.py is ready for plan 04-04 (change-password)
- All OAuth infrastructure is complete; plan 04-04 can use `track_user_family` + `invalidate_all_user_sessions` without any further security.py modifications
- Frontend (plan 09) can wire OAuth login buttons to `GET /api/v1/auth/google` and `GET /api/v1/auth/github`

---
*Phase: 04-authentication-advanced-password-management*
*Completed: 2026-04-10*
