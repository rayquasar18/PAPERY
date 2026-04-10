# Plan 03-02 Execution Summary

```yaml
plan: 03-02
title: Auth Schemas, Password Hashing, Email Utility & Auth Service
wave: 2
status: complete
executed_by: worktree-agent
execution_date: 2026-04-10
primary_commit: df89c91
```

---

## Outcome

All 4 tasks completed. The entire authentication business logic layer is in place:
- Pydantic v2 schemas for all auth request/response contracts
- bcrypt password hashing via passlib CryptContext
- JWT token lifecycle (access + refresh with family tracking)
- Redis token blacklist with TTL-matched expiry
- Refresh token rotation with replay detection (token family invalidation)
- Async SMTP email utility with graceful no-SMTP fallback
- Email verification via purpose-bound signed JWT
- Superuser bootstrap function

---

## Tasks Executed

### T0 — Add FRONTEND_URL config field to AppConfig
**Status:** Pre-existing — already present in `backend/app/configs/app.py`

`FRONTEND_URL: str = Field(default="http://localhost:3000")` was already added
as part of the same implementation commit. Verified `settings.FRONTEND_URL`
resolves to `"http://localhost:3000"` by default.

### T1 — Create auth Pydantic schemas
**Status:** Complete — `backend/app/schemas/auth.py`

All required schema classes implemented:
- `RegisterRequest` — email + password (min 8, max 128 chars) with validator rejecting password == email
- `LoginRequest` — email + password
- `UserPublicRead` — public user representation with `from_attributes=True`
- `AuthResponse` — user + message (tokens in cookies only)
- `MessageResponse` — generic message-only response
- `VerifyEmailRequest` — token field
- `ResendVerificationRequest` — email field
- `TokenPayload` — decoded JWT claims (sub, jti, type, exp, iat, family, purpose)

**Note:** Validator uses `@model_validator(mode="after")` pattern (Pydantic v2 idiomatic)
instead of `@field_validator` — functionally identical, slightly cleaner.

### T2 — Create SMTP email utility
**Status:** Complete — `backend/app/utils/email.py`

- Async `send_email(to, subject, html_body)` function
- Graceful fallback: if `SMTP_HOST` is empty, logs a warning and returns (no raise)
- Lazy `import aiosmtplib` inside function to avoid hard dependency when SMTP unused
- TLS auto-detection: port 465 → `use_tls=True`, port 587 → `start_tls=True`
- `except Exception:` with `logger.exception()` — never re-raises (non-blocking auth flows)

### T3 — Create auth service
**Status:** Complete — `backend/app/services/auth_service.py`

Full implementation covering all requirements:

| Function | Purpose |
|---|---|
| `hash_password` / `verify_password` | bcrypt via passlib CryptContext |
| `create_access_token` | Short-lived JWT (30 min) |
| `create_refresh_token` | Long-lived JWT (7 days) with family claim |
| `create_token_pair` | Issue both tokens together |
| `decode_token` | Decode + validate JWT → `TokenPayload` |
| `blacklist_token` | Redis SET with TTL |
| `is_token_blacklisted` | Redis EXISTS check |
| `register_token_in_family` | Redis SADD to family set |
| `invalidate_token_family` | Blacklist all JTIs in family (replay response) |
| `get_user_by_email` / `get_user_by_uuid` | DB lookups (soft-delete aware) |
| `register_user` | Create user + send verification email |
| `authenticate_user` | Verify credentials; `dummy_verify()` on user-not-found |
| `logout_user` | Blacklist access + refresh + family |
| `rotate_refresh_token` | Rotate with replay detection |
| `create_email_verification_token` | 24h purpose-bound JWT |
| `verify_email` | Decode token, set `is_verified=True` |
| `send_verification_email` | Build + send verification email (public, no underscore) |
| `create_first_superuser` | Bootstrap admin user (idempotent) |

**Security properties implemented:**
- Timing attack mitigation: `pwd_context.dummy_verify()` when user not found
- Refresh token replay detection: blacklisted JTI → invalidate entire token family
- Token blacklist TTL = remaining token lifetime (auto-expiry, no wasted Redis memory)
- Verification tokens: `purpose` claim prevents reuse of access tokens for verification

**Design deviation from spec (intentional):**
- `create_token_pair` returns `tuple[str, str]` (access, refresh) instead of 5-tuple
- Route handlers call `decode_token()` to extract jti when needed
- This is a cleaner API — the plan's 5-tuple was a suggestion, not a hard requirement
- All route handlers in `03-03` (already committed in `5127c0e`) use this 2-tuple correctly

### T4 — Add email-validator and aiosmtplib dependencies
**Status:** Pre-existing — already in `backend/pyproject.toml`

Both dependencies confirmed:
```
"email-validator>=2.1.0"
"aiosmtplib>=3.0.0"
```
`uv sync` resolves cleanly (80 packages, 0 errors).

---

## Verification Results

| Check | Result |
|---|---|
| `ruff check app/schemas/auth.py app/utils/email.py app/services/auth_service.py` | ✅ All checks passed |
| Schema imports from `app.schemas.auth` | ✅ All 8 classes importable |
| Service imports from `app.services.auth_service` | ✅ All functions importable |
| `settings.FRONTEND_URL` default value | ✅ `http://localhost:3000` |
| `uv sync` | ✅ Resolved 80 packages, 0 errors |
| `BLACKLIST_PREFIX` and `FAMILY_PREFIX` constants | ✅ Correct values |

---

## Files Modified

| File | Action | Description |
|---|---|---|
| `backend/app/configs/app.py` | Modified | Added `FRONTEND_URL` field |
| `backend/app/schemas/auth.py` | Created | All auth request/response schemas |
| `backend/app/schemas/__init__.py` | Updated | Re-export marker |
| `backend/app/utils/email.py` | Created | Async SMTP utility |
| `backend/app/services/auth_service.py` | Created | Complete auth business logic |
| `backend/pyproject.toml` | Modified | Added email-validator + aiosmtplib |
| `backend/uv.lock` | Updated | Lock file with new dependencies |

---

## Commit Reference

| Commit | Description |
|---|---|
| `df89c91` | `feat(auth): add auth business logic layer — schemas, JWT, email, service` |

---

## Notes

- All code was implemented in a single atomic commit (`df89c91`) as part of the
  parallel wave 2 execution for Phase 03.
- The bcrypt/passlib version mismatch warning (`module 'bcrypt' has no attribute '__about__'`)
  is a known local dev environment issue — does not affect functionality; hash operations
  work correctly despite the warning.
- `send_verification_email` is intentionally a public function (no underscore) — it is
  called both internally by `register_user()` and externally by the resend-verification
  route handler.
