# Summary: Plan 03-03 — Auth Routes, Dependencies & Rate Limiting

```yaml
plan: 03-03
wave: 3
status: complete
executed_at: "2026-04-10"
commits:
  - 5127c0e  # feat(auth): wire HTTP layer — dependencies, rate limiting, auth routes
  - 7a0d54e  # fix(auth): add explicit error_code to ForbiddenError in dependencies
```

## What Was Done

All 4 tasks were executed. The HTTP layer connecting the auth service to FastAPI is
now fully wired. Code for tasks T1–T4 was already present from a prior execution
(commit `5127c0e`); this run added the final acceptance-criteria fix (explicit
`error_code` on `ForbiddenError` in dependencies).

---

## Tasks

### T1 — Rate Limiting Utility ✅

**File:** `backend/app/utils/rate_limit.py`

Created `check_rate_limit(key, max_requests, window_seconds)` using Redis INCR +
EXPIRE sliding window pattern:

- Uses `rate_limit_client` (Redis DB 2), not `cache_client`
- Returns 429 with `Retry-After` header on limit exceeded
- Guards against uninitialised Redis client with `RuntimeError`

### T2 — Auth Dependencies ✅

**File:** `backend/app/api/dependencies.py`

Implemented the three-level dependency chain:

```
get_current_superuser → get_current_active_user → get_current_user → get_session
```

- `get_current_user`: reads `access_token` cookie → decodes JWT → checks blacklist → loads User from DB
- `get_current_active_user`: checks `is_active`, raises `ForbiddenError(error_code="ACCOUNT_INACTIVE")`
- `get_current_superuser`: checks `is_superuser`, raises `ForbiddenError(error_code="SUPERUSER_REQUIRED")`

**Fix applied in this run:** added explicit `error_code` kwargs to both
`ForbiddenError` raises to satisfy acceptance criteria.

### T3 — Auth Route Handlers ✅

**File:** `backend/app/api/v1/auth.py`

Created all 7 auth endpoints under `/auth`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Register new user (201), rate: 3/min/IP |
| POST | `/login` | Email+password login, rate: 5/min/IP |
| POST | `/logout` | Blacklist tokens + clear cookies |
| POST | `/refresh` | Rotate refresh token (replay detection) |
| GET  | `/me` | Current user profile |
| POST | `/verify-email` | Verify email with JWT token |
| POST | `/resend-verification` | Resend verification (anti-enum, rate: 1/60s/email) |

Security properties implemented:
- `HttpOnly=True` on both cookies
- `Secure=True` in non-local environments
- `SameSite=lax`
- Refresh cookie scoped to `path="/api/v1/auth/refresh"` only
- Tokens never in response body
- Anti-enumeration on resend-verification (always returns success)

### T4 — Register Auth Router ✅

**File:** `backend/app/api/v1/__init__.py`

Added `auth_router` to the v1 aggregator. All 7 endpoints now appear under
`/api/v1/auth/*` and are visible in OpenAPI docs at `/api/v1/docs`.

---

## Verification

```
ruff check backend/app/api/dependencies.py backend/app/api/v1/auth.py backend/app/utils/rate_limit.py
# → All checks passed!
```

Auth endpoints registered:
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `GET  /api/v1/auth/me`
- `POST /api/v1/auth/verify-email`
- `POST /api/v1/auth/resend-verification`

---

## Acceptance Criteria Checklist

### T1
- [x] `backend/app/utils/rate_limit.py` exists
- [x] `async def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> None:`
- [x] Uses `redis_client.rate_limit_client.incr(key)`
- [x] Uses `redis_client.rate_limit_client.expire(key, window_seconds)`
- [x] Raises `RateLimitedError` with `headers={"Retry-After": str(ttl)}`
- [x] Guards with `if redis_client.rate_limit_client is None:`

### T2
- [x] `async def get_current_user(request: Request, db: AsyncSession = Depends(get_session)) -> User:`
- [x] `token = request.cookies.get("access_token")`
- [x] `payload = auth_service.decode_token(token)`
- [x] `if payload.type != "access":` check
- [x] `if await auth_service.is_token_blacklisted(payload.jti):` check
- [x] `user = await auth_service.get_user_by_uuid(db, ...)`
- [x] `async def get_current_active_user(user: User = Depends(get_current_user)) -> User:`
- [x] `if not user.is_active:` with `raise ForbiddenError(` and `error_code="ACCOUNT_INACTIVE"`
- [x] `async def get_current_superuser(user: User = Depends(get_current_active_user)) -> User:`
- [x] `if not user.is_superuser:` with `raise ForbiddenError(` and `error_code="SUPERUSER_REQUIRED"`

### T3
- [x] `router = APIRouter(prefix="/auth", tags=["auth"])`
- [x] `def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:`
- [x] `httponly=True` in set_cookie calls
- [x] `samesite="lax"` in set_cookie calls
- [x] `path="/api/v1/auth/refresh"` for refresh token cookie
- [x] 7 route handlers: register, login, logout, refresh, me, verify_email, resend_verification
- [x] `@router.post("/register"` with `status_code=201`
- [x] Register: `check_rate_limit(... max_requests=3, window_seconds=60)`
- [x] Login: `check_rate_limit(... max_requests=5, window_seconds=60)`
- [x] Logout: `Depends(get_current_user)` + `_clear_auth_cookies(response)`
- [x] Refresh: `request.cookies.get("refresh_token")`
- [x] Me: `@router.get("/me"` with `Depends(get_current_user)`
- [x] Verify-email: `auth_service.verify_email(db, body.token)`
- [x] Resend-verification: `check_rate_limit(... max_requests=1, window_seconds=60)`
- [x] Resend-verification returns generic message (anti-enumeration)

### T4
- [x] `from app.api.v1.auth import router as auth_router`
- [x] `api_v1_router.include_router(auth_router)`
- [x] `api_v1_router.include_router(health_router, tags=["health"])` still present

---

## Threat Model Coverage

| Threat | Mitigation | Status |
|--------|------------|--------|
| XSS token theft | HttpOnly=True on both cookies | ✅ |
| CSRF | SameSite=lax | ✅ |
| Session fixation | New token pair on every login | ✅ |
| Token replay | Family tracking in rotate_refresh_token | ✅ |
| Credential stuffing | Rate limit: login 5/min/IP | ✅ |
| Registration spam | Rate limit: register 3/min/IP | ✅ |
| Email enumeration (resend) | Always returns same success message | ✅ |
| Refresh cookie scope leakage | path="/api/v1/auth/refresh" | ✅ |
| Cookie downgrade | Secure=True in non-local environments | ✅ |
