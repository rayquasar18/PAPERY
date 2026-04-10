---
phase: 04-authentication-advanced-password-management
plan: "04-01"
subsystem: auth
tags: [jwt, password-reset, jinja2, email-templates, rate-limiting, redis, anti-enumeration]

# Dependency graph
requires:
  - phase: 03-authentication-core-flows
    provides: JWT infrastructure (security.py), auth_service.py, auth routes, UserRepository, Redis blacklist

provides:
  - POST /auth/forgot-password — rate-limited, anti-enumeration, fire-and-forget email
  - POST /auth/reset-password — single-use JWT token validation, password update
  - create_password_reset_token() with token override (blacklists previous JTI on re-request)
  - Jinja2 email template infrastructure (EN + VI) with render_email_template()
  - ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest, SetPasswordRequest schemas
  - 11 tests covering all AUTH-06 flows

affects:
  - 04-02 (email verification may reuse template infrastructure)
  - 04-04 (ChangePasswordRequest + SetPasswordRequest schemas already added)
  - 05 (user profile — change password endpoint)

# Tech tracking
tech-stack:
  added:
    - jinja2>=3.1.0 (HTML email template rendering)
  patterns:
    - Anti-enumeration: always return same message regardless of email existence
    - Token override: blacklist previous reset JTI when new reset is requested (D-06)
    - Single-use JTI enforcement via Redis blacklist after successful reset
    - Fire-and-forget email: route catches all exceptions, never exposes internal errors
    - Locale-aware templates with EN fallback in render_email_template()

key-files:
  created:
    - backend/app/templates/__init__.py
    - backend/app/templates/email/password_reset_en.html
    - backend/app/templates/email/password_reset_vi.html
    - backend/tests/test_password_reset.py
  modified:
    - backend/pyproject.toml (added jinja2 dependency)
    - backend/app/utils/email.py (added render_email_template())
    - backend/app/core/security.py (added RESET_JTI_PREFIX, create_password_reset_token())
    - backend/app/schemas/auth.py (added 4 new schemas)
    - backend/app/services/auth_service.py (added request_password_reset, reset_password)
    - backend/app/api/v1/auth.py (added routes 8 and 9)

key-decisions:
  - "create_password_reset_token() is async (unlike email verification token) because it needs Redis for token override"
  - "Token override: blacklisting old JTI before creating new one ensures only one active reset link per user"
  - "ChangePasswordRequest and SetPasswordRequest schemas added proactively to avoid future file conflicts with plans 04-04"
  - "Response key is 'message' (not 'detail') — consistent with ErrorResponse format from handlers.py"
  - "forgot-password rate limit uses email+IP combination; reset-password uses IP-only (token already bound to user)"

patterns-established:
  - "Fire-and-forget service calls: wrap in try/except in route handler, log warning, never surface errors"
  - "render_email_template(name, locale, context) — locale-aware Jinja2 rendering with EN fallback"
  - "Anti-enumeration: service returns None silently; route always returns same success message"
  - "Single-use tokens: blacklist JTI in Redis immediately after successful use"

requirements-completed:
  - AUTH-06

# Metrics
duration: ~25min
completed: 2026-04-10
---

# Plan 04-01: Password Reset Flow Summary

**Complete AUTH-06 password reset via single-use JWT links with Jinja2 HTML email templates, anti-enumeration, token override, and rate limiting**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-10
- **Completed:** 2026-04-10
- **Tasks:** 6
- **Files modified:** 10 (6 modified, 4 created)

## Accomplishments
- Full password reset flow: forgot-password → email with JWT link → reset-password endpoint
- Security-hardened: anti-enumeration, single-use JTI blacklist, token override on re-request, rate limiting per threat model
- Jinja2 template infrastructure supporting EN/VI locales with automatic fallback
- 11 tests passing (146 total, zero regressions)

## Task Commits

1. **T1: Jinja2 email template infrastructure** — `afb3dc3` (feat)
2. **T2: create_password_reset_token with JTI override** — `c3a571b` (feat)
3. **T3: Password reset schemas (Forgot/Reset/Change/Set)** — `b6adce8` (feat)
4. **T4: request_password_reset + reset_password service functions** — `3f361db` (feat)
5. **T5: POST /auth/forgot-password and /auth/reset-password routes** — `646351c` (feat)
6. **T6: Password reset flow tests** — `f2ea65a` (test)

## Files Created/Modified
- `backend/pyproject.toml` — Added `jinja2>=3.1.0` dependency
- `backend/app/utils/email.py` — Added `render_email_template()` with Jinja2 lazy-init env
- `backend/app/templates/__init__.py` — Package marker (empty)
- `backend/app/templates/email/password_reset_en.html` — English reset email template
- `backend/app/templates/email/password_reset_vi.html` — Vietnamese reset email template
- `backend/app/core/security.py` — Added `RESET_JTI_PREFIX`, `create_password_reset_token()`
- `backend/app/schemas/auth.py` — Added `ForgotPasswordRequest`, `ResetPasswordRequest`, `ChangePasswordRequest`, `SetPasswordRequest`
- `backend/app/services/auth_service.py` — Added `request_password_reset()`, `reset_password()`
- `backend/app/api/v1/auth.py` — Added routes 8 (`/forgot-password`) and 9 (`/reset-password`)
- `backend/tests/test_password_reset.py` — 11 tests for the complete flow

## Decisions Made
- `create_password_reset_token()` is `async` (unlike `create_email_verification_token`) because token override requires Redis access to blacklist the old JTI
- `ChangePasswordRequest` and `SetPasswordRequest` added proactively to avoid a later plan touching `auth.py` for the same purpose
- Error response key is `"message"` (not `"detail"`) — the `http_exception_handler` maps `exc.detail` → `message` field in `ErrorResponse`; tests adjusted accordingly

## Deviations from Plan

### Auto-fixed Issues

**1. RateLimitError → RateLimitedError (naming mismatch)**
- **Found during:** Task 6 (tests)
- **Issue:** Plan test template used `RateLimitError` but actual exception class is `RateLimitedError`
- **Fix:** Updated test imports to use `RateLimitedError` from `app.core.exceptions`
- **Files modified:** `backend/tests/test_password_reset.py`
- **Verification:** `pytest tests/test_password_reset.py` — 11/11 passed
- **Committed in:** `f2ea65a` (Task 6 commit)

**2. response["detail"] → response["message"] (error response format)**
- **Found during:** Task 6 (tests)
- **Issue:** Plan template asserted `response.json()["detail"]` but `http_exception_handler` puts the error message in `"message"` key (`detail=None` in `ErrorResponse`)
- **Fix:** Changed assertion to `response.json()["message"]`
- **Files modified:** `backend/tests/test_password_reset.py`
- **Verification:** Test `test_reset_with_used_token_fails` now passes
- **Committed in:** `f2ea65a` (Task 6 commit)

---

**Total deviations:** 2 auto-fixed (naming mismatch, response format)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
None beyond the two auto-fixed test deviations above.

## User Setup Required
None — no external service configuration required. SMTP is optional and degrades gracefully.

## Next Phase Readiness
- AUTH-06 complete — password reset flow fully implemented and tested
- Template infrastructure (`render_email_template`) ready for reuse by email verification (04-02) if needed
- `ChangePasswordRequest` and `SetPasswordRequest` schemas pre-added, ready for plans 04-04 and 05
- Ready to proceed to plan 04-02 (OAuth flows)

---
*Phase: 04-authentication-advanced-password-management*
*Completed: 2026-04-10*
