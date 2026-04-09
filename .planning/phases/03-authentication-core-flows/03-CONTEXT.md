# Phase 3: Authentication — Core Flows - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Registration, login, logout, JWT management via HttpOnly cookies, token refresh/rotation with replay detection, email verification, and Google OAuth integration. This phase delivers the backend auth system — frontend auth UI is Phase 9.

</domain>

<decisions>
## Implementation Decisions

### Token Strategy
- **D-01:** HS256 symmetric signing — single SECRET_KEY (already in SecurityConfig). All tokens invalidated if secret rotates.
- **D-02:** Dual HttpOnly cookies — access token in short-lived cookie (30min), refresh token in separate long-lived cookie (7 days). Both SameSite=Lax, Secure=true in production. Tokens never returned in response body.
- **D-03:** Redis JTI blacklist for logout — store invalidated JWT ID in Redis with TTL matching token expiry. Auto-cleanup via Redis TTL. Uses Redis cache DB (DB 0).
- **D-04:** Strict refresh rotation with replay detection — each refresh issues new access + refresh token pair, old refresh JTI is immediately blacklisted. If a blacklisted refresh token is reused, the entire token family for that user is invalidated (logout all sessions).

### User Model
- **D-05:** Standard SaaS fields — email (unique, indexed), hashed_password (nullable for OAuth-only users), display_name, avatar_url, is_active, is_verified, is_superuser. Extends Base with UUIDMixin + TimestampMixin + SoftDeleteMixin.
- **D-06:** bcrypt via passlib for password hashing — proven, adaptive hashing with configurable work factor.
- **D-07:** Boolean flags for account status — is_active (can login), is_verified (email confirmed), is_superuser (admin). Simple and queryable, no enum overhead.
- **D-08:** Separate OAuthAccount table for provider links — (user_id FK, provider, provider_user_id, provider_email). One user can link multiple OAuth providers. Clean separation from User model.

### Email Verification
- **D-09:** Signed JWT token for email verification — short-lived JWT with user ID and purpose="email_verification" claim. Verify by decoding, no database lookup needed. Self-expiring.
- **D-10:** 24-hour expiry for verification links — generous window for delayed email delivery.
- **D-11:** Allow login before verification — user can log in immediately after registration. Unverified status shown as banner/warning. Feature restrictions enforced later by tier system (Phase 6).
- **D-12:** Rate-limited resend endpoint — POST /auth/resend-verification, 1 request per 60 seconds per email to prevent abuse. Previous token stays valid until its own expiry.

### Auth API Design
- **D-13:** RESTful /auth/* namespace — all auth endpoints under /api/v1/auth/*:
  - POST /auth/register
  - POST /auth/login
  - POST /auth/logout
  - POST /auth/refresh
  - GET /auth/me
  - POST /auth/verify-email
  - POST /auth/resend-verification
  - GET /auth/google (OAuth redirect)
  - GET /auth/google/callback
- **D-14:** User data in body, tokens in cookies only — login/register return {user: {...}, message: "..."} in response body. Access and refresh tokens set exclusively as HttpOnly cookies (never in response body). Consistent with D-02.
- **D-15:** Password validation: 8+ characters, cannot match user's email. No special character requirement (NIST-aligned). Validated server-side via Pydantic field_validator.
- **D-16:** Per-endpoint rate limits using Redis DB 2:
  - Login: 5 attempts per minute per IP
  - Register: 3 per minute per IP
  - Resend verification: 1 per 60s per email
  - Returns 429 with Retry-After header

### Claude's Discretion
- JWT claims structure beyond required fields (sub, jti, exp, iat, type, purpose)
- Exact cookie path and domain configuration
- OAuth state parameter implementation details
- SMTP email template structure for verification emails
- Exact rate limiter middleware implementation (sliding window vs fixed window)
- Google OAuth library choice (httpx direct vs authlib)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Enterprise Architecture Reference
- `.reference/dify/` — Dify enterprise patterns for auth, user management, security

### Project Documentation
- `.planning/ROADMAP.md` — Phase 3 requirements (AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-09) and success criteria
- `.planning/REQUIREMENTS.md` — Full requirement details for AUTH-01 through AUTH-09
- `.planning/codebase/ARCHITECTURE.md` — Layered architecture patterns, extension points
- `.planning/codebase/CONVENTIONS.md` — Code style, naming conventions
- `.planning/codebase/STRUCTURE.md` — Target directory layout (auth.py router, User model, security.py)

### Existing Code (Phase 1 & 2 output)
- `backend/app/configs/security.py` — SecurityConfig with SECRET_KEY, ALGORITHM, ACCESS/REFRESH token expiry
- `backend/app/configs/email.py` — EmailConfig with SMTP settings
- `backend/app/configs/admin.py` — AdminConfig with default admin email/password
- `backend/app/models/base.py` — Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
- `backend/app/api/dependencies.py` — Stub file, auth dependencies to be added here
- `backend/app/extensions/ext_redis.py` — Redis client (DB 0 for cache/blacklist, DB 2 for rate limiting)
- `backend/app/core/exceptions/` — PaperyHTTPException hierarchy for error responses

### Prior Phase Context
- `.planning/phases/01-backend-core-infrastructure/01-CONTEXT.md` — Dual-ID strategy, Redis 3-DB setup, modular settings
- `.planning/phases/02-error-handling-api-structure-health/02-CONTEXT.md` — Error format, API versioning, CORS

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SecurityConfig` (configs/security.py): SECRET_KEY, HS256, 30min/7d expiry already configured
- `EmailConfig` (configs/email.py): SMTP host/port/user/password/from ready for verification emails
- `Base` model with UUIDMixin, TimestampMixin, SoftDeleteMixin (models/base.py): User model extends these
- `PaperyHTTPException` hierarchy: 401 Unauthorized, 403 Forbidden, 409 Conflict, 422 Validation errors
- Redis extension (`ext_redis.py`): Connection pool for token blacklist (DB 0) and rate limiting (DB 2)

### Established Patterns
- Flat directory structure: models/user.py, schemas/auth.py, services/auth_service.py, api/v1/auth.py
- Pydantic v2 schemas with ConfigDict (Read/Create/Update schema separation from Phase 1 CONTEXT)
- async SQLAlchemy 2.0 with declarative mapping
- Extension init/shutdown via lifespan
- Router mounting under /api/v1/ prefix

### Integration Points
- `dependencies.py`: Auth dependency (get_current_user) to be used by all subsequent protected endpoints
- `models/__init__.py`: User and OAuthAccount models must be registered for Alembic autogenerate
- `main.py`: Auth router mounted alongside health router
- Phase 4 (Auth Advanced) will add: password reset, 2FA, session management — building on this auth foundation
- Phase 5 (User Profile) will add: profile endpoints, avatar upload — extending the User model
- Phase 9 (Frontend Auth UI) will consume these auth endpoints

</code_context>

<specifics>
## Specific Ideas

- **Dify-style patterns** for auth implementation — study how Dify handles user registration, token management, and OAuth
- **NIST SP 800-63B aligned** password policy — length-based (8+), no special character requirement, password cannot match email
- **Token family concept** for replay detection — track which refresh tokens belong to the same login session, invalidate entire family on replay attack
- **Email as primary identifier** — no username, email is the login credential

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-authentication-core-flows*
*Context gathered: 2026-04-07*
