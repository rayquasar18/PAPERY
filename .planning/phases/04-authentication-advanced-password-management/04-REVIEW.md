---
phase: "04"
phase_name: authentication-advanced-password-management
status: issues_found
depth: standard
files_reviewed: 32
findings:
  critical: 2
  warning: 5
  info: 4
  total: 11
---

# Code Review — Phase 04: Authentication & Advanced Password Management

**Reviewer:** Claude Opus 4.6  
**Date:** 2026-04-10  
**Scope:** All source files in phase 04 (auth routes, service layer, security primitives, OAuth providers, repositories, schemas, utils, tests)

---

## Summary

The overall architecture is solid and well-structured. Security fundamentals are correct: bcrypt password hashing, JWT with blacklisting, HttpOnly cookies, CSRF-protected OAuth state, replay-detection via token families, and rate limiting on all sensitive endpoints. Two **critical** bugs were found that would cause runtime crashes in production.

---

## Critical Findings

### CR-1: GitHub Callback Handler — NameError Crash on Success Path
- **Severity**: critical
- **File**: `backend/app/api/v1/auth.py`
- **Line**: 526–527
- **Issue**: The `github_callback` handler at line 527 references `access_jwt` and `refresh_jwt` before they are ever assigned. The entire code block that exchanges the authorization code for tokens (equivalent to lines 455–472 in `google_callback`) is **completely missing** from the GitHub handler. After CSRF validation passes, the function jumps directly to building the redirect and calling `_set_auth_cookies(redirect, access_jwt, refresh_jwt)` — but those variables do not exist. Any successful GitHub OAuth attempt will raise `UnboundLocalError: cannot access local variable 'access_jwt' before assignment`, crashing with a 500 error.
- **Fix**: Add the missing code block between the CSRF check and the redirect:
  ```python
  try:
      provider = _get_github_provider()
      access_token = await provider.get_access_token(code)
      user_info = await provider.get_user_info(access_token)
      user = await auth_service.oauth_login_or_register(db, user_info)
  except Exception:
      logger.exception("GitHub OAuth callback failed")
      return RedirectResponse(url=f"{frontend_url}/login?error=oauth_failed", status_code=302)

  access_jwt, refresh_jwt = create_token_pair(user.uuid)
  refresh_payload = decode_token(refresh_jwt)
  await register_token_in_family(refresh_payload.family, refresh_payload.jti)
  await track_user_family(user.uuid, refresh_payload.family)
  ```

### CR-2: Rate Limit Race Condition — INCR/EXPIRE Not Atomic
- **Severity**: critical
- **File**: `backend/app/utils/rate_limit.py`
- **Line**: 42–44
- **Issue**: The INCR and EXPIRE calls are two separate, non-atomic Redis operations. If the process crashes or the connection drops between `incr(key)` and `expire(key, window_seconds)`, the key persists without a TTL and will **never expire**, permanently blocking the caller at that key. Under high concurrency, multiple processes can also each see `count == 1` and each try to set the TTL, leading to subtle window drift.
- **Fix**: Use a Lua script or Redis pipeline to make the operation atomic:
  ```python
  pipe = redis_client.rate_limit_client.pipeline()
  pipe.incr(key)
  pipe.expire(key, window_seconds)
  count, _ = await pipe.execute()
  # Then check count > max_requests
  ```
  This guarantees TTL is always set when the key is first created.

---

## Warning Findings

### WR-1: `access_token` Family Claim is Never Set — Logout Leaves Refresh Tokens Alive
- **Severity**: warning
- **File**: `backend/app/core/security.py`
- **Line**: 39–50 (`create_access_token`)
- **Issue**: `create_access_token` never embeds a `family` claim in the access token payload. In `logout_user` (auth_service.py, line 163), `if access_payload.family:` will always be `False`, so `invalidate_token_family` is **never called** during logout. The logout only blacklists the single access token JTI and (optionally) the explicit refresh JTI. Any other refresh tokens in the same family (e.g., on other devices) remain valid and usable after logout.
- **Fix**: Either pass `family_id` into `create_access_token` and embed it in the payload, or change `logout_user` to accept the `family_id` parameter directly and call `invalidate_token_family` unconditionally.

### WR-2: Verification Email Uses Inline HTML — Inconsistent With Password Reset Template
- **Severity**: warning
- **File**: `backend/app/services/auth_service.py`
- **Line**: 257–284 (`send_verification_email`)
- **Issue**: The verification email is built as a raw inline f-string with unsanitized user input (`settings.APP_NAME`, `verification_url`). While these values come from config (not user input), it is inconsistent with the approach used for password reset emails which correctly uses the Jinja2 template engine (`render_email_template`). Inline f-string HTML also bypasses Jinja2's autoescape, which means any future refactoring that includes user-supplied content could silently introduce HTML injection.
- **Fix**: Create a `templates/email/verify_email_en.html` (and `_vi.html`) template and call `render_email_template("verify_email", locale="en", context={...})` the same way `request_password_reset` does.

### WR-3: `OAuthUserInfo.name` is Required — Breaks If Provider Returns No Name
- **Severity**: warning
- **File**: `backend/app/schemas/oauth.py`
- **Line**: 18 (`OAuthUserInfo`)
- **Issue**: `name: str` is a required field with no default. In `google.py` line 81, `name=data.get("name", "")` passes an empty string defensively, but in `github.py` line 84, `name = user_data.get("name") or user_data.get("login", "")` — if both `name` and `login` are absent (unlikely but possible with a malformed response), the value will be an empty string. More critically, if any future OAuth provider fails to provide a name and the caller passes `None`, Pydantic will raise a `ValidationError` causing a 500 error in the callback handler where exceptions are only caught generically.
- **Fix**: Change `name: str` to `name: str = ""` in `OAuthUserInfo` to make it optional with a safe default. This also documents the intent that name is best-effort.

### WR-4: `decode_token` Error Message Leaks JWT Exception Details to Client
- **Severity**: warning
- **File**: `backend/app/core/security.py`
- **Line**: 92
- **Issue**: `raise UnauthorizedError(detail=f"Invalid token: {exc}")` embeds the raw `JWTError` exception message in the HTTP 401 response sent to the client. Jose's error messages can be informative (e.g., "Signature has expired", "Not enough segments") which leaks implementation details. Worse, in `verify_email` (auth_service.py line 237) and `reset_password` (line 332), the same pattern is repeated: `detail=f"Invalid or expired ... token: {exc}"`. These details are returned to the caller in the 400/401 response body.
- **Fix**: Use a fixed, opaque error message: `raise UnauthorizedError(detail="Invalid or expired token")` and log the exception detail server-side at debug level.

### WR-5: Missing `is_active` Check on `get_current_user` — Deactivated Users Can Call Unprotected Endpoints
- **Severity**: warning
- **File**: `backend/app/api/dependencies.py`
- **Line**: 25–58 (`get_current_user`)
- **Issue**: `get_current_user` does not check `user.is_active`. Only `get_current_active_user` (which wraps it) performs that check. Any endpoint using the bare `get_current_user` dependency (e.g., `/auth/logout` at line 192) will allow a deactivated user to proceed. For logout this is arguably intentional (let them log out), but it's an implicit assumption that can cause surprises if future endpoints use `get_current_user` without realizing the active-check is omitted.
- **Fix**: Document the intentional distinction clearly in both dependency docstrings. Add a note to the pattern guide that `get_current_user` is **deliberately** active-check-free (for logout), and that all resource endpoints must use `get_current_active_user`.

---

## Info Findings

### IR-1: `import uuid as uuid_pkg` Inside Route Handler Body
- **Severity**: info
- **File**: `backend/app/api/v1/auth.py`
- **Line**: 246
- **Issue**: `import uuid as uuid_pkg` is placed inside the `refresh` route handler body rather than at the top of the module. This is functional but unconventional; the module already imports uuid at the top level indirectly through other modules.
- **Fix**: Move `import uuid as uuid_pkg` to the top of the file with the other standard library imports.

### IR-2: `jose` Imported Twice in Service Layer
- **Severity**: info
- **File**: `backend/app/services/auth_service.py`
- **Line**: 230–231 (`verify_email`) and 325–326 (`reset_password`)
- **Issue**: `from jose import JWTError` and `from jose import jwt as jose_jwt` are imported inside two separate method bodies (`verify_email` and `reset_password`) rather than at the module level. The `decode_token` function in `security.py` already provides a unified decode interface that raises `UnauthorizedError`. These two methods bypass `decode_token` and re-implement decoding inline, which duplicates logic and contradicts the module boundary design.
- **Fix**: Use the existing `decode_token` utility from `app.core.security` and catch `UnauthorizedError` (re-raising as `BadRequestError`) instead of importing jose directly in the service layer.

### IR-3: Rate Limit on `reset-password` Keyed Only on IP — Not on Token
- **Severity**: info
- **File**: `backend/app/api/v1/auth.py`
- **Line**: 369–372
- **Issue**: The `/reset-password` rate limit key is `auth:reset-password:{client_ip}` (IP only). An attacker who knows a valid (not-yet-used) reset token can try up to 5 new passwords per minute from any IP before the window resets. Since tokens are single-use and blacklisted on success, the practical risk is low, but keying on the token hash as well would add defense-in-depth.
- **Fix**: Consider adding the token's JTI as part of the rate limit key or adding per-token attempt tracking in Redis (e.g., max 3 attempts per JTI).

### IR-4: No Test Coverage for `github_callback` Success Path (Which Is Also Broken — See CR-1)
- **Severity**: info
- **File**: `backend/tests/test_oauth.py`
- **Line**: 239–293 (`test_github_callback_success_redirects_to_dashboard`)
- **Issue**: The test for the GitHub success callback (line 239) mocks `auth_service.oauth_login_or_register`, `create_token_pair`, and `decode_token` — the same variables that are missing in the production code. Because the test patches out all the relevant functions, the `UnboundLocalError` from CR-1 is never triggered. The test passes green even though the production code path is completely broken. This is a case where mocking too aggressively masked a real bug.
- **Fix**: After fixing CR-1, verify the test actually exercises the real code path by checking that `_get_github_provider` is called and the code/token exchange occurs. Consider adding an integration-level smoke test that does not mock the provider factory.

---

## Notes

- **Token family design**: The `token_family` set in Redis stores all JTIs ever issued for a family but never prunes individual entries after a JTI is blacklisted. This is harmless (the set TTL matches the refresh lifetime) but the set could grow large in long-lived sessions with many rotations. Consider storing only the *current* valid JTI instead of a set.
- **`_SECURE_COOKIE` at module load time**: `_SECURE_COOKIE = settings.ENVIRONMENT != "local"` is evaluated once at import time. This is correct for production use but can cause test confusion when `ENVIRONMENT` is not set before the module is imported.
- **`passlib` + `bcrypt` compatibility**: `pyproject.toml` pins `passlib[bcrypt]>=1.7.4`. The `test_auth_service.py` file explicitly notes a bcrypt 5.x/passlib version incompatibility and mocks `pwd_context` to work around it. This should be resolved by pinning `bcrypt<4.0` or migrating to `bcrypt` directly, as passlib is no longer maintained.
