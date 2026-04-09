# Phase 3: Authentication — Core Flows — Research

**Researched:** 2026-04-09
**Status:** Complete — ready for planning

---

## 1. What This Phase Delivers

Phase 3 delivers the **entire backend authentication foundation** that every subsequent phase depends on:

- User registration (email + password)
- Email verification via signed JWT token
- Login → JWT tokens issued as HttpOnly cookies
- Logout → tokens blacklisted in Redis
- Token refresh with rotation and replay detection
- `get_current_user` dependency (the gating function for all protected endpoints)

This phase is **backend-only**. The frontend auth UI is Phase 9.

---

## 2. Available Building Blocks (Phase 1 & 2 Output)

### What already exists — use these directly:

| Asset | Location | How it's used in Phase 3 |
|---|---|---|
| `SecurityConfig` | `configs/security.py` | `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` |
| `EmailConfig` | `configs/email.py` | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` |
| `AdminConfig` | `configs/admin.py` | `ADMIN_EMAIL`, `ADMIN_PASSWORD` — bootstrap first superuser |
| `Base`, `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin` | `models/base.py` | User model extends these 4 |
| `ext_redis.cache_client` | `extensions/ext_redis.py` | Token blacklist (DB 0) |
| `ext_redis.rate_limit_client` | `extensions/ext_redis.py` | Rate limiting (DB 2) |
| `db_session.get_session` | `core/db/session.py` | DB dependency in auth routes |
| `UnauthorizedError`, `ConflictError`, `NotFoundError`, `RateLimitedError` | `core/exceptions/__init__.py` | Auth error responses |
| `dependencies.py` | `api/dependencies.py` | Stub file — auth deps go here |

### Installed packages (no new deps needed for core auth):

| Package | Use |
|---|---|
| `python-jose[cryptography]` | JWT encode/decode (HS256) |
| `passlib[bcrypt]` | Password hashing |
| `fastapi` | Route handlers, `Depends()`, `Response`, cookies |
| `sqlalchemy[asyncio]` + `asyncpg` | Async DB access |
| `redis[hiredis]` | Token blacklist + rate limiting |
| `fastcrud` | CRUD layer for User model |
| `httpx` | Google OAuth token exchange (Phase 4, but available) |

**No new packages are required for Phase 3 core flows.**

---

## 3. New Files to Create

### 3.1 Models

**`models/user.py`** — User ORM model:
```
User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
  - email: str (unique, indexed, not null)
  - hashed_password: str | None (nullable — OAuth-only users have no password)
  - display_name: str | None
  - avatar_url: str | None
  - is_active: bool (default True)
  - is_verified: bool (default False)
  - is_superuser: bool (default False)
  - __tablename__ = "user"
```

Register in `models/__init__.py` so Alembic autogenerates the migration.

### 3.2 Schemas

**`schemas/auth.py`** — All auth-related Pydantic schemas:

| Schema | Fields | Purpose |
|---|---|---|
| `RegisterRequest` | `email`, `password` | POST /auth/register input |
| `LoginRequest` | `email`, `password` | POST /auth/login input |
| `UserPublicRead` | `uuid`, `email`, `display_name`, `avatar_url`, `is_verified`, `created_at` | Response body after login/register/me |
| `AuthResponse` | `user: UserPublicRead`, `message: str` | Standard auth response (tokens in cookies, NOT here) |
| `VerifyEmailRequest` | `token: str` | POST /auth/verify-email input |
| `ResendVerificationRequest` | `email: str` | POST /auth/resend-verification input |
| `TokenPayload` | `sub`, `jti`, `exp`, `iat`, `type`, `purpose?` | JWT claims — internal only (not in API responses) |

### 3.3 Services

**`services/auth_service.py`** — Business logic layer:

| Function | Responsibility |
|---|---|
| `register_user(db, email, password)` | Hash password, create User, send verification email, return UserPublicRead |
| `authenticate_user(db, email, password)` | Look up user by email, verify bcrypt hash, check is_active, return User |
| `create_access_token(user_id, user_uuid)` | Build JWT payload (sub=uuid, jti=new UUID, type="access"), sign HS256 |
| `create_refresh_token(user_id, user_uuid, family_id)` | Build JWT payload (sub=uuid, jti=new UUID, type="refresh", family=family_id), sign HS256 |
| `create_token_pair(user)` | Calls both above, returns (access_token, refresh_token) |
| `blacklist_token(jti, expire_seconds)` | Redis SET jti "" EX expire_seconds using cache_client |
| `is_token_blacklisted(jti)` | Redis EXISTS jti using cache_client |
| `rotate_refresh_token(db, old_payload)` | Check blacklist → detect replay → blacklist old JTI → issue new pair |
| `logout_user(access_jti, refresh_jti, ...)` | Blacklist both tokens |
| `send_verification_email(email, user_uuid)` | Create signed JWT (purpose="email_verification"), send via SMTP |
| `verify_email(db, token)` | Decode JWT, check purpose, set user.is_verified=True |
| `create_first_superuser(db)` | Used in scripts/create_first_superuser.py |

### 3.4 Utilities

**`utils/email.py`** — Low-level SMTP sender:
```python
async def send_email(to: str, subject: str, html_body: str) -> None
```

### 3.5 API Router

**`api/v1/auth.py`** — Route handlers:

| Endpoint | Method | Auth | Rate Limit |
|---|---|---|---|
| `/auth/register` | POST | Public | 3/min per IP |
| `/auth/login` | POST | Public | 5/min per IP |
| `/auth/logout` | POST | Cookie (access token) | Standard |
| `/auth/refresh` | POST | Cookie (refresh token) | Standard |
| `/auth/me` | GET | Cookie (access token) | Standard |
| `/auth/verify-email` | POST | Public | Standard |
| `/auth/resend-verification` | POST | Public | 1/60s per email |

### 3.6 Dependencies

**`api/dependencies.py`** — Add auth dependencies:

| Function | Behavior |
|---|---|
| `get_current_user(request, db)` | Extract `access_token` cookie → decode JWT → check blacklist → load User → return UserPublicRead |
| `get_current_active_user(user)` | Wraps `get_current_user`, raises 403 if `not user.is_active` |
| `get_current_superuser(user)` | Wraps `get_current_active_user`, raises 403 if `not user.is_superuser` |

---

## 4. Key Implementation Patterns

### 4.1 JWT Token Structure

```python
# Access token payload
{
    "sub": str(user.uuid),          # Subject — public UUID (never int id)
    "jti": str(uuid4()),            # JWT ID — unique per token (for blacklisting)
    "type": "access",               # "access" | "refresh"
    "iat": datetime.utcnow(),
    "exp": datetime.utcnow() + timedelta(minutes=30),
}

# Refresh token payload — adds family_id for replay detection
{
    "sub": str(user.uuid),
    "jti": str(uuid4()),
    "type": "refresh",
    "family": str(uuid4()),         # Family ID — shared across rotation chain
    "iat": datetime.utcnow(),
    "exp": datetime.utcnow() + timedelta(days=7),
}
```

### 4.2 Cookie Strategy

```python
# Set access token cookie
response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,
    secure=settings.ENVIRONMENT != "local",  # Secure=True in staging/prod
    samesite="lax",
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    path="/",
)

# Set refresh token cookie
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=settings.ENVIRONMENT != "local",
    samesite="lax",
    max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    path="/api/v1/auth/refresh",   # Scope refresh cookie to refresh endpoint only
)
```

**Critical:** Tokens are NEVER returned in the response body. Response body = `{user: {...}, message: "..."}`.

### 4.3 Token Blacklist (Redis)

```python
# Blacklist key pattern
BLACKLIST_KEY_PREFIX = "blacklist:jti:"

# On logout / token rotation
await cache_client.set(
    f"{BLACKLIST_KEY_PREFIX}{jti}",
    "1",
    ex=remaining_ttl_seconds,  # Auto-expires with the token
)

# On each authenticated request
if await cache_client.exists(f"{BLACKLIST_KEY_PREFIX}{jti}"):
    raise UnauthorizedError("Token has been revoked", error_code="TOKEN_REVOKED")
```

### 4.4 Refresh Token Rotation with Replay Detection

The "token family" concept (D-04 from CONTEXT.md):

```
Login → issue (access_1, refresh_1) with family_id="F1"
Client uses access_1 normally.
access_1 expires → client hits POST /auth/refresh with refresh_1
  → check: is refresh_1.jti blacklisted? No → proceed
  → blacklist refresh_1.jti (old token)
  → issue (access_2, refresh_2) — same family_id="F1"

REPLAY ATTACK:
Attacker reuses old refresh_1 → POST /auth/refresh with refresh_1
  → check: is refresh_1.jti blacklisted? YES
  → ENTIRE FAMILY F1 is compromised
  → blacklist ALL tokens in family F1
  → return 401 "Token has been revoked — all sessions terminated"
```

**Family tracking in Redis:**
```python
# When issuing a new token pair, register JTI in family set
FAMILY_KEY = f"token_family:{family_id}"
await cache_client.sadd(FAMILY_KEY, new_jti)
await cache_client.expire(FAMILY_KEY, REFRESH_TOKEN_EXPIRE_DAYS * 86400)

# On replay detection, invalidate entire family
family_jtis = await cache_client.smembers(FAMILY_KEY)
for jti in family_jtis:
    await cache_client.set(f"{BLACKLIST_KEY_PREFIX}{jti}", "1", ex=REFRESH_EXPIRE)
await cache_client.delete(FAMILY_KEY)
```

### 4.5 Rate Limiting

Simple Redis sliding window per endpoint:

```python
async def check_rate_limit(
    client: Redis,
    key: str,          # e.g., "rate_limit:login:127.0.0.1"
    max_requests: int, # e.g., 5
    window_seconds: int # e.g., 60
) -> None:
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, window_seconds)
    if count > max_requests:
        ttl = await client.ttl(key)
        raise RateLimitedError(
            detail=f"Too many requests. Retry after {ttl} seconds.",
            headers={"Retry-After": str(ttl)},
        )
```

Use `rate_limit_client` (DB 2), NOT `cache_client` (DB 0).

### 4.6 Password Validation (Pydantic)

```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str, info: FieldValidationInfo) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        email = info.data.get("email", "")
        if email and v.lower() == email.lower():
            raise ValueError("Password cannot match email address")
        return v
```

### 4.7 Email Verification Token

```python
def create_email_verification_token(user_uuid: str) -> str:
    payload = {
        "sub": user_uuid,
        "purpose": "email_verification",
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_email_verification_token(token: str) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("purpose") != "email_verification":
        raise UnauthorizedError("Invalid verification token")
    return payload["sub"]  # user_uuid
```

---

## 5. File-by-File Creation Plan

### New files (in dependency order):

1. `models/user.py` — User + OAuthAccount models
2. `models/__init__.py` — register User for Alembic
3. `schemas/auth.py` — all auth schemas
4. `utils/email.py` — SMTP email sender
5. `services/auth_service.py` — business logic
6. `api/dependencies.py` — auth dependency functions
7. `api/v1/auth.py` — route handlers
8. `api/v1/__init__.py` — mount auth_router
9. `migrations/versions/<timestamp>_add_user_table.py` — Alembic migration

### Bootstrap script:
10. `scripts/create_first_superuser.py` — creates ADMIN_EMAIL/ADMIN_PASSWORD superuser

---

## 6. Alembic Migration Strategy

Phase 3 creates the **first real migration** with database tables.

**Approach:** Use `alembic revision --autogenerate` after registering User model in `models/__init__.py`. Commit the generated migration file to git (unlike `versions/` which is gitignored for auto-generated files — check if gitignore applies here).

**Migration checklist:**
- `user` table with all columns
- Unique index on `user.email`
- Index on `user.uuid`
- Index on `user.deleted_at` (from SoftDeleteMixin)

---

## 7. Testing Strategy

### Unit tests (`tests/unit/`):
- `test_auth_service.py` — token creation, blacklisting, rotation, password hashing
- `test_password_validation.py` — Pydantic validator edge cases

### Integration tests (`tests/integration/`):
- `test_auth_register.py` — register → email sent, user in DB, 409 on duplicate
- `test_auth_login.py` — login success (cookies set), wrong password (401), unverified warning
- `test_auth_logout.py` — logout → tokens blacklisted → subsequent request 401
- `test_auth_refresh.py` — rotation: old token blacklisted, new cookies issued
- `test_auth_refresh_replay.py` — replay attack → family invalidated, 401
- `test_auth_verify_email.py` — verify → is_verified=True, expired token 401
- `test_auth_rate_limit.py` — login 6th request → 429 with Retry-After

### Fixtures needed:
- `test_user` — registered but unverified user
- `verified_user` — registered + verified user
- `superuser` — is_superuser=True
- `auth_headers` — returns response with auth cookies set

---

## 8. Critical Design Decisions (Already Made — Do Not Re-open)

| Decision | Choice | Source |
|---|---|---|
| Token algorithm | HS256 | D-01: SecurityConfig.ALGORITHM already set |
| Token transport | HttpOnly cookies only, never response body | D-02 |
| Token blacklist storage | Redis DB 0 (cache_client) | D-03 |
| Replay detection | Token family concept — full family invalidation | D-04 |
| User model fields | email, hashed_password(nullable), display_name, avatar_url, is_active, is_verified, is_superuser | D-05 |
| Password hashing | bcrypt via passlib | D-06 |
| Account status | Boolean flags (is_active, is_verified, is_superuser) | D-07 |
| OAuth account separation | Separate `OAuthAccount` table | D-08 (scaffold only in Phase 3, full impl in Phase 4) |
| Verification token | Signed JWT (purpose=email_verification), 24h expiry | D-09, D-10 |
| Pre-verification login | Allowed — unverified users can log in | D-11 |
| Verification resend rate | 1/60s per email | D-12 |
| API endpoints | /api/v1/auth/* namespace | D-13 |
| Password rules | 8+ chars, cannot match email, no special char requirement | D-15 |
| Rate limits | Login: 5/min/IP, Register: 3/min/IP | D-16 |

---

## 9. Integration Points for Future Phases

| Future Phase | What It Needs from Phase 3 |
|---|---|
| Phase 4 (Auth Advanced) | `OAuthAccount` model stub, `get_current_user` dep, password reset token pattern |
| Phase 5 (User Profile) | `User` model, `UserPublicRead` schema, `get_current_user` dep |
| Phase 6 (Tier System) | `User` model (will add `tier_id` FK in Phase 6) |
| Phase 7 (Admin Panel) | `get_current_superuser` dep, `User` CRUD |
| Phase 8 (Projects) | `get_current_user` dep, `User.uuid` for ACL entries |
| Phase 9 (Frontend Auth UI) | All /auth/* endpoints + cookie behavior |

---

## 10. Scope Guard — What is NOT in Phase 3

| Feature | Why Deferred |
|---|---|
| Google OAuth (AUTH-07) | Phase 4 — depends on this Phase 3 foundation |
| GitHub OAuth (AUTH-08) | Phase 4 |
| Password reset (AUTH-06) | Phase 4 |
| Change password (USER-03) | Phase 4 |
| 2FA | Out of scope for v1 entirely |
| Frontend login/register UI | Phase 9 |
| Tier-aware rate limiting | Phase 6 — Phase 3 uses simple IP-based rate limits |

---

## 11. Plan Decomposition (Recommended Split)

| Plan # | Scope | Deliverable |
|---|---|---|
| 03-01 | User model + migration | `models/user.py`, Alembic migration, `models/__init__.py` |
| 03-02 | Auth schemas + service layer | `schemas/auth.py`, `utils/email.py`, `services/auth_service.py` |
| 03-03 | Auth routes + dependencies | `api/v1/auth.py`, `api/dependencies.py`, router registration |
| 03-04 | Tests + bootstrap script | Full test suite, `scripts/create_first_superuser.py` |

This 4-plan split mirrors the Phase 2 pattern (4 plans, ~5-15 min each).

---

*Research completed: 2026-04-09*
*Phase: 03-authentication-core-flows*
