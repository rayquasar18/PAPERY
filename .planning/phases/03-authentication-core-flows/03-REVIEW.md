---
status: issues_found
phase: "03"
phase_name: "authentication-core-flows"
depth: standard
files_reviewed: 15
findings:
  critical: 3
  warning: 7
  info: 4
  total: 14
reviewed_at: "2026-04-10"
---

# Code Review: Phase 03 — Authentication Core Flows

## Summary

The authentication core is architecturally sound. The design choices — HttpOnly cookies, refresh-token family replay detection, bcrypt via passlib, anti-enumeration on resend, and the soft-delete pattern — are all correct and deliberate. The JWT blacklist TTL accounting is well thought out. No secrets are leaked in API responses, and the test suite covers the happy path and most error branches with clean mock isolation.

Three critical issues require fixing before this phase can be considered complete: a race condition in the rate limiter that can be exploited under load, an unverified-account login gap (users can log in without verifying their email), and a token-type confusion vulnerability in the `/refresh` endpoint. Seven warnings address real but lower-severity gaps. Four informational items note missing coverage and minor hardening opportunities.

---

## Findings

### CR-01: Rate Limiter Race Condition — INCR/EXPIRE Not Atomic
**Severity:** critical
**File:** `backend/app/utils/rate_limit.py`
**Line:** 42–44
**Issue:** The rate limiter performs two separate Redis commands — `INCR` then `EXPIRE` — with no atomicity guarantee. Between those two calls a process crash, a Redis failover, or a concurrent request can leave the key without a TTL, making it **immortal**. Affected users would be permanently rate-limited until someone manually deletes the Redis key. This is a classic INCR+EXPIRE split-brain bug.

```python
count = await redis_client.rate_limit_client.incr(key)
if count == 1:
    await redis_client.rate_limit_client.expire(key, window_seconds)  # not atomic
```

**Fix:** Use a Lua script or a Redis pipeline with `SET key 0 NX EX window_seconds` followed by `INCR`, or use `SET … EX … KEEPTTL` via a pipeline. The simplest production-safe pattern:

```python
pipe = redis_client.rate_limit_client.pipeline()
pipe.incr(key)
pipe.expire(key, window_seconds)   # always set — idempotent if already set
count, _ = await pipe.execute()
```

This does not give a perfect sliding window but eliminates the immortal-key failure mode. True sliding windows require a sorted-set approach.

---

### CR-02: Unverified Users Can Log In and Receive Tokens
**Severity:** critical
**File:** `backend/app/services/auth_service.py`
**Line:** 204–225
**Issue:** `authenticate_user` does not check `user.is_verified` before returning the user. A user who registered but never clicked the verification link receives full access tokens on login. This contradicts the stated requirement ("Please check your email to verify your account") and allows unverified identities to access protected resources indefinitely.

```python
async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    ...
    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError(detail="Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError(detail="Account is deactivated")
    return user   # <-- is_verified is NEVER checked
```

**Fix:** Add an `is_verified` guard after the password check. Return a distinct error code so the frontend can prompt the user to verify:

```python
if not user.is_verified:
    raise UnauthorizedError(
        detail="Email address not verified. Please check your inbox.",
        error_code="EMAIL_NOT_VERIFIED",
    )
```

If unverified login is intentionally allowed for MVP, this decision should be documented explicitly in the service code and in the CONTEXT file.

---

### CR-03: Token-Type Not Validated Before `rotate_refresh_token` Is Called
**Severity:** critical
**File:** `backend/app/api/v1/auth.py`
**Line:** 217–219
**Issue:** The `/refresh` endpoint calls `decode_token(token)` — which succeeds for *any* valid JWT — and passes the result directly to `rotate_refresh_token`. Although `rotate_refresh_token` does check `old_payload.type != "refresh"`, the problem is the type check happens *after* the decode. An attacker who presents a valid **access** token (which is also signed with the same `SECRET_KEY`) to the refresh endpoint gets a proper `UnauthorizedError`, but the error path goes through the service rather than the route, and the token is not blacklisted. More importantly, there is a subtler issue: the route decodes the cookie token (`old_payload`) but then independently loads the user again from `old_payload.sub` *after* `rotate_refresh_token` has already validated and queried the user — the user is fetched twice, with no guarantee the state is consistent between the two DB hits.

```python
old_payload = auth_service.decode_token(token)                          # (1) decodes any token type
access_token, refresh_token = await auth_service.rotate_refresh_token(db, old_payload)  # (2) checks type
...
user = await auth_service.get_user_by_uuid(db, uuid_pkg.UUID(old_payload.sub))  # (3) second DB hit
```

**Fix:** Validate token type at the route level before calling the service, and eliminate the redundant second user query by returning the user from `rotate_refresh_token` or caching it from the service call:

```python
if old_payload.type != "refresh":
    raise UnauthorizedError(detail="Refresh token missing or wrong type")
```

Also consider returning `(access_token, refresh_token, user)` from `rotate_refresh_token` so the route doesn't need a second independent user fetch.

---

### WR-01: `authenticate_user` Checks `is_active` After Password Verification — Timing Leak
**Severity:** warning
**File:** `backend/app/services/auth_service.py`
**Line:** 219–223
**Issue:** The order is: verify password → check `is_active`. This means a deactivated user receives a *different* error message than an invalid-credential user. An attacker can enumerate valid email addresses by observing whether they get "Invalid email or password" vs "Account is deactivated". The `dummy_verify()` path only covers user-not-found, not deactivated users.

**Fix:** Return the same generic "Invalid email or password" error for both wrong password and deactivated accounts, or check `is_active` before running `verify_password` and treat inactive accounts the same as non-existent ones (i.e. run `dummy_verify` and then raise the generic error).

---

### WR-02: `logout_user` Double-Blacklists Family Members Without Expiry Accuracy
**Severity:** warning
**File:** `backend/app/services/auth_service.py`
**Line:** 246–254
**Issue:** `logout_user` blacklists the `refresh_jti` with a fixed TTL of `REFRESH_TOKEN_EXPIRE_DAYS * 86400` — regardless of how much lifetime the token actually has remaining. Shortly afterward, `invalidate_token_family` also blacklists the same jti (via the family members set) with `REFRESH_TOKEN_EXPIRE_DAYS * 86400 + 3600`. The first `blacklist_token(refresh_jti, ...)` call is therefore redundant when a `family` is present, and the TTL it sets is less than the one subsequently set by `invalidate_token_family`, meaning Redis will overwrite it anyway. This is harmless but shows unclear logic ownership.

**Fix:** Remove the `refresh_jti` explicit blacklisting inside `logout_user` when `access_payload.family` is set, since `invalidate_token_family` covers it. Or document the redundancy explicitly with a comment explaining why both paths exist.

---

### WR-03: `_SECURE_COOKIE` Computed at Module Import Time
**Severity:** warning
**File:** `backend/app/api/v1/auth.py`
**Line:** 40
**Issue:** `_SECURE_COOKIE = settings.ENVIRONMENT != "local"` is evaluated once when the module is imported. If `ENVIRONMENT` is mutated after import (e.g., in tests or via a live config reload), the cookie secure flag won't update. More concretely, in the test suite `os.environ.setdefault("ENVIRONMENT", "local")` is set in `conftest.py` *before* app import — this works only if the import happens strictly after the env var is set. If test ordering or lazy imports change this, cookies in tests could incorrectly get `secure=True`.

**Fix:** Either compute the value lazily inside `_set_auth_cookies` (`secure=settings.ENVIRONMENT != "local"`), or explicitly document the import-time evaluation and ensure the conftest ordering is locked.

---

### WR-04: `refresh` Route Doesn't Validate Token Type Before Calling Service
**Severity:** warning  
**File:** `backend/app/api/v1/auth.py`  
**Line:** 217  
**Issue:** (Companion to CR-03 — distinct aspect.) If `decode_token` succeeds on an access token presented to `/refresh`, the route happily calls `rotate_refresh_token`, which then raises `UnauthorizedError("Token is not a refresh token")`. The error message leaks information about which token types are expected at which endpoints, aiding an attacker mapping the API. Additionally, presenting an access token to `/refresh` does **not** blacklist the access token — so after this failed attempt the access token is still usable for its remaining lifetime.

**Fix:** Add explicit type guard at route level (see CR-03 fix). This reduces information leakage and prevents the wasted DB roundtrip.

---

### WR-05: HTML Email Body Uses f-string Without Escaping
**Severity:** warning
**File:** `backend/app/services/auth_service.py`
**Line:** 361–382
**Issue:** The verification email HTML is built via an f-string that interpolates `verification_url` directly into an `href`. If `settings.FRONTEND_URL` were misconfigured to contain a single-quote or script-inject sequence (e.g., an attacker-controlled config value in a multi-tenant future scenario), the resulting email would contain unescaped HTML. Currently the `verification_url` is constructed from `settings.FRONTEND_URL` + a JWT, so the risk is low — but it is not zero (environment misconfiguration can happen).

**Fix:** Use `html.escape(verification_url)` when inserting into the `href` attribute and visible link text. This is a one-liner with no functional cost.

---

### WR-06: `request.client` Can Be `None` — Default Falls Back to `"unknown"` as Shared Rate Limit Key
**Severity:** warning
**File:** `backend/app/api/v1/auth.py`
**Line:** 105, 147, 273
**Issue:** When `request.client` is `None` (e.g., behind some proxy configurations or in ASGI test scenarios), all such requests share the single rate limit key `"auth:register:unknown"`. This means all clients without a resolved IP share one bucket, allowing them to collectively consume the rate limit very quickly, or alternatively a single client that can trigger `client=None` bypass individual limiting entirely by rotating through None-state.

**Fix:** Use a more defensive fallback: extract IP from `X-Forwarded-For` or `X-Real-IP` headers before falling back to `"unknown"`. Reject requests with no resolvable IP if strict rate limiting is required.

---

### WR-07: `invalidate_token_family` Uses Non-Atomic `SMEMBERS` + Pipeline
**Severity:** warning
**File:** `backend/app/services/auth_service.py`
**Line:** 154–166
**Issue:** `invalidate_token_family` reads all family members with `smembers` and then blacklists them in a pipeline. Between the `smembers` call and `pipeline.execute()`, a concurrent token rotation could add a new jti to the family set. That newly-added jti would not be in `members` and would not be blacklisted — creating a window where a "revoked family" still has one live token.

**Fix:** Use a Lua script that atomically reads members and deletes the key in one round-trip, or move family invalidation to a Lua `EVAL`. For most practical threat models the window is very small, but the correct fix is Lua atomicity if the concern is stolen refresh tokens (the exact scenario this code defends against).

---

### IR-01: `conftest.py` Fixture `async_client` Leaks `app.dependency_overrides` on Exception
**Severity:** info
**File:** `backend/tests/conftest.py`
**Line:** 44–50
**Issue:** `app.dependency_overrides[get_session] = _mock_get_session` is set before `async with AsyncClient(...)`. If the `AsyncClient` context manager raises before yielding (e.g., startup failure), the `pop` on line 50 is still executed — but only because `pop` is outside the `async with`. However, if the `with` patch block itself raises, the `pop` is skipped entirely because it's inside the `with`. This can leave `dependency_overrides` dirty between test runs when patching fails.

**Fix:** Use `try/finally` to unconditionally clean up `dependency_overrides`:
```python
app.dependency_overrides[get_session] = _mock_get_session
try:
    async with AsyncClient(...) as client:
        yield client
finally:
    app.dependency_overrides.pop(get_session, None)
```

---

### IR-02: `TokenPayload.type` and `TokenPayload.purpose` Have No Enum Constraints
**Severity:** info
**File:** `backend/app/schemas/auth.py`
**Line:** 85–89
**Issue:** `type: str` and `purpose: str | None` are free-form strings with no `Literal` or `Enum` constraint. A JWT with `type: "admin"` or a crafted `purpose: "password_reset"` (if a password reset flow is added later) would parse correctly and pass the `TokenPayload(**raw)` construction step. The token type check relies entirely on downstream caller discipline.

**Fix:** Use `Literal`:
```python
type: Literal["access", "refresh", "verification"]
purpose: Literal["email_verify"] | None = None
```

This makes invalid token types a Pydantic validation error at parse time rather than a silent field value that callers must remember to check.

---

### IR-03: Email Verification Token Is Never Blacklisted After Use
**Severity:** info
**File:** `backend/app/services/auth_service.py`
**Line:** 329–353
**Issue:** After a successful email verification, the `token` (a JWT) is not blacklisted. The token remains valid until its 24-hour expiry. An attacker who intercepts the verification link can replay it multiple times. The only natural protection is `user.is_verified = True` check — but this raises `BadRequestError("Email is already verified")` which leaks that the token was already used, rather than gracefully ignoring the replay.

**Fix:** Blacklist the verification token's `jti` after first successful use:
```python
await blacklist_token(payload.jti, remaining_seconds)
```
And on `is_verified` being True, consider returning a neutral success message rather than an error — since the end state (verified) is already achieved.

---

### IR-04: Test Suite Has No Coverage for Replay Attack Path in `rotate_refresh_token`
**Severity:** info
**File:** `backend/tests/test_auth_service.py`
**Issue:** `rotate_refresh_token` contains replay detection logic (blacklisted jti → invalidate family → raise `TOKEN_REPLAY`). This is a critical security path but has no test in `test_auth_service.py`. The route-level test only checks the happy path and missing-cookie case.

**Fix:** Add tests:
- `test_rotate_refresh_token_replay_triggers_family_invalidation` — blacklisted old jti should call `invalidate_token_family` and raise `UnauthorizedError` with `error_code="TOKEN_REPLAY"`.
- `test_rotate_refresh_token_missing_family_claim` — payload without `family` should raise.
- `test_rotate_refresh_token_inactive_user` — user with `is_active=False` should invalidate family and raise.

---

## Summary Table

| ID | Severity | File | Title |
|----|----------|------|-------|
| CR-01 | critical | `utils/rate_limit.py` | INCR/EXPIRE race — immortal rate limit keys |
| CR-02 | critical | `services/auth_service.py` | Unverified users can log in and receive tokens |
| CR-03 | critical | `api/v1/auth.py` | Token-type not validated at route level before rotation |
| WR-01 | warning | `services/auth_service.py` | `is_active` check leaks account existence via distinct error |
| WR-02 | warning | `services/auth_service.py` | Redundant / inconsistent TTLs in `logout_user` |
| WR-03 | warning | `api/v1/auth.py` | `_SECURE_COOKIE` evaluated at import — fragile in tests |
| WR-04 | warning | `api/v1/auth.py` | Access token presented to `/refresh` not blacklisted |
| WR-05 | warning | `services/auth_service.py` | HTML email builds href with unescaped `verification_url` |
| WR-06 | warning | `api/v1/auth.py` | `request.client=None` collapses all anonymous clients into one rate limit key |
| WR-07 | warning | `services/auth_service.py` | `invalidate_token_family` non-atomic SMEMBERS + pipeline |
| IR-01 | info | `tests/conftest.py` | `dependency_overrides` can leak on patch-block exception |
| IR-02 | info | `schemas/auth.py` | `TokenPayload.type` / `purpose` have no `Literal` constraints |
| IR-03 | info | `services/auth_service.py` | Email verification token not blacklisted after first use |
| IR-04 | info | `tests/test_auth_service.py` | No test coverage for token replay detection path |
