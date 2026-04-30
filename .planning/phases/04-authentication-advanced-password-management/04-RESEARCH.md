# Phase 4 Research: Authentication — Advanced & Password Management

**Researched:** 2026-04-10
**Phase requirements:** AUTH-06, AUTH-07, AUTH-08, USER-03
**Research scope:** What do I need to know to PLAN this phase well?

---

## 1. What We Are Building

Four interconnected features on top of Phase 3's JWT+cookie auth foundation:

| Feature | Requirement | Core Mechanism |
|---------|-------------|----------------|
| Password reset via email | AUTH-06 | One-time JWT → email → form → update |
| Google OAuth | AUTH-07 | httpx → Google → callback → JWT cookies |
| GitHub OAuth | AUTH-08 | httpx → GitHub → callback → JWT cookies |
| Change password (authenticated) | USER-03 | Verify current → hash new → invalidate all sessions |

---

## 2. Existing Assets We Reuse (Do Not Rewrite)

### 2.1 `core/security.py` — JWT & Redis primitives
- `create_email_verification_token()` → template for `create_password_reset_token()`
- `decode_token()` → reuse for reset token validation
- `blacklist_token(jti, expire_seconds)` → single-use enforcement for reset JTI
- `is_token_blacklisted(jti)` → verify token not already used
- `invalidate_token_family(family_id)` → for change-password session invalidation
- `hash_password()` / `verify_password()` → for change-password current password check

**Gap:** No function to invalidate ALL token families for a user. Need to implement `invalidate_all_user_sessions(user_uuid)`. This requires a Redis key pattern for user→family mapping (e.g., `user_families:{user_uuid}` as a Redis Set), OR scanning `token_family:*` keys by user — the latter is unsafe at scale. **Must add user→families index in Redis on login/registration.**

### 2.2 `api/v1/auth.py` — Cookie helpers
- `_set_auth_cookies(response, access_token, refresh_token)` → reuse in OAuth callback
- `_clear_auth_cookies(response)` → not needed here
- Router prefix `/auth` already set — add new routes directly

### 2.3 `services/auth_service.py` — Business logic patterns
- Anti-enumeration response pattern (resend-verification → forgot-password)
- Fire-and-forget email pattern (try/except + logger.warning)
- `UserRepository` usage pattern: `user_repo.get(email=email.lower())`

### 2.4 `models/user.py` — Ready for OAuth
- `hashed_password: Mapped[str | None]` — nullable → OAuth-only users already supported
- `OAuthAccount` model already migrated with `provider`, `provider_user_id`, `provider_email`
- Unique constraint on `(provider, provider_user_id)` already in place

### 2.5 `utils/email.py` — SMTP delivery
- `send_email(to, subject, html_body)` — already works
- Currently takes raw `html_body` string → needs to be extended with Jinja2 template rendering
- Multi-language support needed (user locale → template selection)

### 2.6 `utils/rate_limit.py` — Redis sliding window
- `check_rate_limit(key, max_requests, window_seconds)` → identical pattern for all new endpoints

### 2.7 `configs/__init__.py` — Multiple-inheritance settings
- New `OAuthConfig(BaseSettings)` follows exact pattern of `SecurityConfig`, `EmailConfig`
- Add `OAuthConfig` to `AppSettings(... OAuthConfig, ...)`
- Must add FRONTEND_URL field if not present (needed for reset link)

---

## 3. New Files to Create

| File | Purpose |
|------|---------|
| `backend/app/configs/oauth.py` | `OAuthConfig(BaseSettings)` with Google/GitHub credentials + OAUTH_REDIRECT_BASE_URL |
| `backend/app/infra/oauth/` | OAuth provider clients (base + Google + GitHub subclasses) |
| `backend/app/infra/oauth/__init__.py` | Module init |
| `backend/app/infra/oauth/base.py` | Abstract `OAuthProvider` base class with `httpx.AsyncClient` |
| `backend/app/infra/oauth/google.py` | `GoogleOAuthProvider(OAuthProvider)` |
| `backend/app/infra/oauth/github.py` | `GitHubOAuthProvider(OAuthProvider)` |
| `backend/app/repositories/oauth_account_repository.py` | `OAuthAccountRepository(BaseRepository[OAuthAccount])` |
| `backend/app/schemas/oauth.py` | Request/response schemas for OAuth flows |

**Modified files:**
- `backend/app/core/security.py` — add `create_password_reset_token()`, `invalidate_all_user_sessions()`
- `backend/app/services/auth_service.py` — add 4 new service functions
- `backend/app/api/v1/auth.py` — add 8 new routes
- `backend/app/configs/__init__.py` — add `OAuthConfig` to `AppSettings`
- `backend/app/utils/email.py` — add Jinja2 template support
- `backend/app/schemas/auth.py` — add new request schemas

---

## 4. Critical Design Decisions (from CONTEXT.md)

### 4.1 Password Reset Token Design (D-01 to D-06)

```python
# Token payload mirrors email_verification_token:
{
    "sub": str(user_uuid),
    "jti": str(uuid4()),          # For single-use enforcement
    "type": "password_reset",     # Or reuse "verification" type?
    "purpose": "password_reset",  # D-01: purpose claim
    "iat": int(now.timestamp()),
    "exp": int((now + timedelta(hours=1)).timestamp())  # D-02: 1-hour TTL
}
```

**Single-use (D-03):** On successful reset → `blacklist_token(jti, remaining_seconds)`. Before reset → `is_token_blacklisted(jti)`.

**Token override on new request (D-06):** When user requests a new reset email while a valid token exists, the old JTI must be blacklisted. Two approaches:
- Option A: Store current reset JTI in Redis keyed by user UUID (`reset_token:{user_uuid}` → `jti`). On new request: retrieve old JTI, blacklist it, store new JTI.
- Option B: Just issue new token — old token expires naturally after 1 hour. But D-06 says explicitly blacklist previous.

**Recommended: Option A** — Redis key `reset_jti:{user_uuid}` with 1-hour TTL stores the current valid JTI. On new request: read old JTI → blacklist → store new JTI.

### 4.2 OAuth Flow Architecture (D-07 to D-10)

**Dify reference pattern** (`oauth.py`) adapted to async FastAPI:
- Dify uses sync `httpx.Client` → we use `httpx.AsyncClient`
- Dify uses `get_pooled_http_client` → we use a simple module-level `AsyncClient` or per-request (simpler for v1)
- Dify uses `TypedDict` + `TypeAdapter` for response validation → same pattern

**Complete OAuth flow:**
```
1. GET /auth/google
   → generate state UUID
   → store state in Redis: "oauth_state:{state}" = "1" with 10min TTL (D-10)
   → return RedirectResponse to Google auth URL with state param

2. GET /auth/google/callback?code=xxx&state=yyy
   → validate state param against Redis (CSRF protection)
   → delete state from Redis (single-use)
   → exchange code for access_token (httpx POST to Google token endpoint)
   → fetch user info (httpx GET to Google userinfo endpoint)
   → find or create User + OAuthAccount (service layer)
   → issue JWT token pair (reuse create_token_pair)
   → set HttpOnly cookies (reuse _set_auth_cookies)
   → return RedirectResponse to frontend dashboard
```

**State Redis key pattern:** `oauth_state:{provider}:{state_value}` → value "1" or provider name.

### 4.3 Account Linking Logic (D-14 to D-16)

```python
async def oauth_login_or_register(db, provider, provider_user_id, email, name):
    oauth_repo = OAuthAccountRepository(db)
    user_repo = UserRepository(db)

    # 1. Look for existing OAuthAccount
    oauth_account = await oauth_repo.get(provider=provider, provider_user_id=provider_user_id)
    if oauth_account:
        return oauth_account.user  # Existing OAuth login

    # 2. Look for existing User by email (D-14: auto-link)
    user = await user_repo.get(email=email.lower())
    if user:
        # D-15: Single provider limit check
        if user.oauth_accounts:  # Already has an OAuth account
            raise ConflictError("Account already linked to another OAuth provider")
        # Link OAuth to existing user
        await oauth_repo.create_oauth_account(user.id, provider, provider_user_id, email)
        return user

    # 3. Create new user + OAuth account
    user = await user_repo.create_user(
        email=email.lower(),
        hashed_password=None,  # OAuth-only
        is_active=True,
        is_verified=True,  # OAuth email is pre-verified
        is_superuser=False,
    )
    await oauth_repo.create_oauth_account(user.id, provider, provider_user_id, email)
    return user
```

**Key insight:** OAuth users are auto-verified (`is_verified=True`) because the OAuth provider guarantees email ownership.

### 4.4 Change Password & Session Invalidation (D-17 to D-18)

**Problem:** `invalidate_token_family()` takes a single `family_id`. To invalidate ALL sessions for a user, we need to know all active family IDs.

**Solution:** Add user→families mapping in Redis:
- On every login/registration/OAuth: `SADD user_families:{user_uuid} {family_id}` with TTL = REFRESH_TOKEN_EXPIRE_DAYS
- On change-password: `SMEMBERS user_families:{user_uuid}` → iterate → `invalidate_token_family(family_id)` for each → `DEL user_families:{user_uuid}`

**This requires a retroactive change to Phase 3 code** (register/login routes must populate the family index). This is a **cross-cutting concern** that must be done carefully:
1. Add `track_user_family(user_uuid, family_id)` to `security.py`
2. Call it in `auth.py` at every `register_token_in_family()` call site

**Alternative (simpler, less precise):** Store families in Redis per user, but accept that sessions from before Phase 4 won't be invalidated. Since Phase 3 is complete but no users exist yet (test environment), this is acceptable.

### 4.5 Set Password for OAuth-only Users (D-18)

```python
async def set_password(db, user, new_password):
    if user.hashed_password is not None:
        raise BadRequestError("Account already has a password. Use change-password instead.")
    user.hashed_password = hash_password(new_password)
    user_repo = UserRepository(db)
    await user_repo.update(user)
```

No current-password verification needed. No session invalidation needed (user has no existing password-based sessions).

---

## 5. GitHub Private Email Fallback (Critical Pattern)

From Dify's `oauth.py` (studied reference):

```python
# When user has "Keep email addresses private" enabled:
# 1. GET /user → email field is None
# 2. GET /user/emails → find primary+verified email
# 3. If none: use {github_id}@users.noreply.github.com
```

This is a real-world requirement — ~30% of GitHub users have private emails. Without this, sign-in silently fails or creates accounts with no email.

Our async implementation needs `httpx.AsyncClient` instead of Dify's sync `httpx.Client`.

---

## 6. Redis Keys Reference (New in Phase 4)

| Key Pattern | Value | TTL | Purpose |
|-------------|-------|-----|---------|
| `oauth_state:{provider}:{state}` | `"1"` | 10 min | CSRF protection for OAuth flow |
| `reset_jti:{user_uuid}` | `{jti}` | 1 hour | Track current valid reset token |
| `user_families:{user_uuid}` | Set of family_ids | 7 days | All-sessions invalidation |

**Redis DB:** All use `cache_client` (DB 0) for auth state. Rate limit keys use `rate_limit_client` (DB 2) as per established pattern.

---

## 7. New API Routes (8 routes)

| Method | Path | Auth | Rate Limit | Notes |
|--------|------|------|------------|-------|
| POST | `/auth/forgot-password` | None | 3/min per email+IP | Anti-enumeration response |
| POST | `/auth/reset-password` | None | 5/min per IP | Token in body, not header |
| POST | `/auth/change-password` | JWT cookie | 5/min per user | Requires current password |
| POST | `/auth/set-password` | JWT cookie | 5/min per user | OAuth-only users only |
| GET | `/auth/google` | None | 10/min per IP | Redirect to Google |
| GET | `/auth/google/callback` | None | 10/min per IP | Callback, sets cookies |
| GET | `/auth/github` | None | 10/min per IP | Redirect to GitHub |
| GET | `/auth/github/callback` | None | 10/min per IP | Callback, sets cookies |

**Note:** Callback routes return `RedirectResponse` (HTTP 302), not JSON. This is the one place where we don't follow the JSON response pattern.

---

## 8. New Schemas Required

```python
# schemas/auth.py additions:
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
    # model_validator: password must not match email (but we don't have email here)
    # → validate password != token (edge case, probably skip)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    # model_validator: current != new

class SetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)

# schemas/oauth.py (new file):
class OAuthUserInfo(BaseModel):
    """Normalized user info returned by OAuth providers."""
    provider_id: str
    email: str
    name: str
```

---

## 9. OAuthConfig Pattern

Following `SecurityConfig` exactly:

```python
# configs/oauth.py
from pydantic import Field
from pydantic_settings import BaseSettings

class OAuthConfig(BaseSettings):
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_SECRET: str = Field(default="")
    GITHUB_CLIENT_ID: str = Field(default="")
    GITHUB_CLIENT_SECRET: str = Field(default="")
    OAUTH_REDIRECT_BASE_URL: str = Field(default="http://localhost:8000")
    FRONTEND_URL: str = Field(default="http://localhost:3000")
```

**Graceful disable (D-12):** In route handlers, check if credentials are configured:
```python
if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
    raise HTTPException(status_code=404, detail="Google OAuth not configured")
```

---

## 10. OAuth Provider Implementation (Async Dify Pattern)

```python
# infra/oauth/base.py
from dataclasses import dataclass
import httpx

@dataclass
class OAuthUserInfo:
    provider_id: str
    email: str
    name: str

class OAuthProvider:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        ...

    def get_authorization_url(self, state: str) -> str: ...
    async def get_access_token(self, code: str) -> str: ...
    async def get_user_info(self, access_token: str) -> OAuthUserInfo: ...
```

Key difference from Dify: `async` methods, `httpx.AsyncClient` instead of `httpx.Client`.

**Connection handling:** Create `httpx.AsyncClient` per-request or module-level. Per-request is simpler and safer for v1. Module-level requires careful lifecycle management with FastAPI lifespan.

**Recommended: per-request `async with httpx.AsyncClient() as client:`** — no lifecycle complexity, sufficient for v1 traffic.

---

## 11. Email Template Refactor

Current `auth_service.py` builds HTML inline (f-strings). For password reset and multi-language:

**Minimal approach (no Jinja2 dependency added):**
- Keep inline HTML templates as Python functions/constants
- Add locale parameter to email functions
- Two template dicts: `{"en": html_en, "vi": html_vi}`

**Full Jinja2 approach (D-23):**
- Create `backend/app/templates/email/` directory
- Files: `password_reset_en.html`, `password_reset_vi.html`, `verify_email_en.html`, etc.
- `utils/email.py` gains `render_template(name, locale, context)` function
- Requires `jinja2` added to dependencies

**Decision for planning:** Jinja2 is already likely available (FastAPI depends on Starlette which optionally uses Jinja2). Check `pyproject.toml` for existing dependency. If not present, the inline approach avoids a new dependency.

**Recommended:** Add `jinja2` as explicit dependency (it's very likely already transitive), use template files. This is cleaner and future-proof for multi-language.

---

## 12. Session Family Tracking — Retroactive Phase 3 Fix

The `invalidate_all_user_sessions()` function requires knowing all family IDs for a user. This data isn't tracked today.

**Minimal fix to Phase 3 code (additive, non-breaking):**

In `core/security.py`, add:
```python
USER_FAMILIES_PREFIX = "user_families:"

async def track_user_family(user_uuid: uuid_pkg.UUID, family_id: str) -> None:
    """Record that a token family belongs to this user."""
    client = _redis()
    key = f"{USER_FAMILIES_PREFIX}{user_uuid}"
    await client.sadd(key, family_id)
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400 + 3600
    await client.expire(key, ttl)

async def invalidate_all_user_sessions(user_uuid: uuid_pkg.UUID) -> None:
    """Revoke all active token families for a user (used on password change)."""
    client = _redis()
    key = f"{USER_FAMILIES_PREFIX}{user_uuid}"
    family_ids = await client.smembers(key)
    for family_id in family_ids:
        await invalidate_token_family(family_id)
    await client.delete(key)
```

In `api/v1/auth.py`, at all `register_token_in_family()` call sites (register, login, OAuth callback), add:
```python
await track_user_family(user.uuid, refresh_payload.family)
```

This is a small, additive, safe change to Phase 3 output.

---

## 13. Dependency Additions

| Package | Reason | Already present? |
|---------|--------|-----------------|
| `httpx` | OAuth HTTP calls | Likely yes (FastAPI recommends it) |
| `jinja2` | Email templates | Likely yes (Starlette dependency) |

Check `pyproject.toml` before adding. If not present, add them.

---

## 14. Testing Considerations

New test scenarios for Phase 4:

**Password Reset:**
- Request for non-existent email → same success response (anti-enumeration)
- Request for existing email → email sent (mock SMTP), token created
- Reset with valid token → password updated, token blacklisted
- Reset with already-used token → 400 error
- Reset with expired token → 400 error
- Second reset request → first token blacklisted, new token valid

**OAuth:**
- Valid Google callback → user created, cookies set, redirect to frontend
- Valid GitHub callback (with private email) → /user/emails called, user created
- Invalid OAuth state → 400 error (CSRF protection)
- OAuth email matches existing local account → accounts linked (D-14)
- OAuth callback with existing OAuth account → login (not create)

**Change Password:**
- Valid current password → updated, all sessions invalidated
- Wrong current password → 401
- OAuth-only user → 400 (use set-password endpoint instead)
- After change → old tokens rejected

**Set Password:**
- User with no password → success
- User with existing password → 400 (use change-password instead)

---

## 15. Plan Structure Recommendation

Given the complexity, split into 4 focused plans:

| Plan | Scope | Files |
|------|-------|-------|
| 04-01 | Password Reset (AUTH-06) | `security.py`, `auth_service.py`, `auth.py`, `schemas/auth.py`, `configs/oauth.py` (FRONTEND_URL only) |
| 04-02 | OAuth Infrastructure (providers + config) | `configs/oauth.py`, `infra/oauth/`, `repositories/oauth_account_repository.py` |
| 04-03 | OAuth Routes — Google + GitHub (AUTH-07, AUTH-08) | `auth_service.py` (oauth_login_or_register), `api/v1/auth.py` (4 OAuth routes) |
| 04-04 | Change/Set Password + Session Invalidation (USER-03) | `security.py` (track_user_family, invalidate_all), `auth_service.py`, `auth.py` + Phase 3 retroactive fix |

---

## 16. Open Questions for Planner

1. **FRONTEND_URL config:** Does it already exist in `AppConfig` / `configs/app.py`? Check before adding to `OAuthConfig`.
2. **httpx in pyproject.toml:** Is it already an explicit dependency? If not, add it.
3. **jinja2 in pyproject.toml:** Same question. Confirm before creating template infrastructure.
4. **OAuth state Redis DB:** Use `cache_client` (DB 0) or `rate_limit_client` (DB 2)? Cache makes more sense semantically; keep consistent with token blacklist.
5. **Token family tracking retroactive fix:** Plan 04-04 adds `track_user_family()` calls to Phase 3 code. This must be done carefully to not break existing tests.
6. **OAuthAccount `display_name`:** Store `name` from OAuth provider? Current `User` model has `display_name: Mapped[str | None]`. Should OAuth registration populate it? — Yes, populate from provider name.

---

## Summary: Key Insights for Planning

1. **Reuse is the theme** — 80% of Phase 4 is calling existing primitives (`decode_token`, `blacklist_token`, `check_rate_limit`, `_set_auth_cookies`, `send_email`) in new combinations.

2. **The async gap in Dify reference** — Dify uses sync `httpx.Client`. We need async. The pattern is identical, just `async def` + `httpx.AsyncClient`. No architectural difference.

3. **Family tracking is the hardest part** — `invalidate_all_user_sessions()` requires tracking user→families in Redis. This requires a small, safe retrofit to Phase 3 login/register routes.

4. **OAuth state = CSRF protection** — The Redis state parameter (D-10) is mandatory for security. Pattern: generate UUID → store in Redis → include in auth URL → verify on callback.

5. **GitHub private email is a real edge case** — Must implement the `/user/emails` fallback. ~30% of GitHub users will hit this. Skip it and the OAuth flow silently creates accounts with broken email addresses.

6. **OAuth users are auto-verified** — `is_verified=True` on OAuth registration because the provider guarantees email ownership. This is intentional and correct.

7. **Graceful disable** — If Google/GitHub credentials are not in `.env`, those endpoints return 404. This allows deploying without OAuth configured.

---

*Research completed: 2026-04-10*
*Phase: 04-authentication-advanced-password-management*
