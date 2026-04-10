# Phase 4: Authentication — Advanced & Password Management - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete the authentication system with OAuth provider integration (Google, GitHub), password management (reset via email, change, set for OAuth-only users), and account linking. This phase builds on Phase 3's core auth foundation (JWT cookies, token rotation, email verification) to deliver AUTH-06, AUTH-07, AUTH-08, and USER-03.

</domain>

<decisions>
## Implementation Decisions

### Password Reset Flow
- **D-01:** JWT token with `purpose='password_reset'` — reuses existing JWT infrastructure from Phase 3, consistent with email verification token (D-09). Contains user UUID, purpose claim, and JTI for single-use enforcement.
- **D-02:** 1-hour expiry for reset tokens — balances security and usability.
- **D-03:** Single-use enforcement — JTI blacklisted in Redis immediately after successful password reset. Prevents token reuse.
- **D-04:** Anti-enumeration response — POST /auth/forgot-password always returns "If an account with that email exists, a reset email has been sent" regardless of whether the email exists. Consistent with resend-verification pattern (Phase 3).
- **D-05:** Two-step reset flow — email link → intermediate verify page (confirms token is valid) → reset form (enter new password) → submit. Provides better UX than direct form.
- **D-06:** Token override on new request — when user requests a new reset, the previous reset token is blacklisted. Only the most recent token is valid.

### OAuth Integration
- **D-07:** httpx.AsyncClient direct — Dify-style pattern with base OAuth class and provider subclasses (GoogleOAuth, GitHubOAuth). No Authlib/fastapi-users dependency. Full control, async-native, minimal dependencies.
- **D-08:** Server-side OAuth flow — backend generates auth URL → redirect user to provider → provider consent → callback to backend → exchange code → set HttpOnly cookies → redirect to frontend. Secrets never exposed to client.
- **D-09:** Backend callback with frontend redirect — after successful OAuth callback, backend sets auth cookies and redirects to frontend dashboard URL. Frontend doesn't need to handle OAuth tokens.
- **D-10:** Redis state parameter for CSRF protection — random state string stored in Redis with 10-minute TTL. Verified on callback. Prevents CSRF attacks on OAuth flow.

### OAuth Configuration
- **D-11:** Separate OAuthConfig(BaseSettings) — new `configs/oauth.py` with GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, OAUTH_REDIRECT_BASE_URL. Follows existing config pattern (SecurityConfig, EmailConfig, etc.).
- **D-12:** Graceful disable when credentials missing — if Google/GitHub OAuth credentials are not configured (empty/absent), the OAuth endpoints return 404 or are not registered. No startup errors. OAuth is an optional feature.
- **D-13:** Backend callback URLs — `/api/v1/auth/google/callback` and `/api/v1/auth/github/callback`. Registered with OAuth providers.

### Account Linking Policy
- **D-14:** Auto-link by email — when OAuth provider email matches an existing local account's email, automatically link the OAuth account to the existing user. No new account created. Seamless experience.
- **D-15:** Single OAuth provider per user — only one OAuth provider can be linked at a time. If user already has Google linked, cannot add GitHub. Business logic enforces this even though OAuthAccount table supports multiple.
- **D-16:** Unlink with safety check (Claude's Discretion) — allow unlink only if user has a password set (hashed_password is not NULL). Prevents user from locking themselves out of their account.

### Password Change & Sessions
- **D-17:** Change password invalidates ALL sessions — all token families for the user are invalidated in Redis. Forces re-login on all devices. Maximum security on password change.
- **D-18:** Separate set-password endpoint for OAuth-only users — POST /auth/set-password, only allowed when hashed_password is NULL. Does not require "current password" verification. Enables OAuth-only users to add password-based login.
- **D-19:** Rate limit: 5 req/min per user for change/set password endpoints.

### Rate Limiting & Abuse Prevention
- **D-20:** Forgot password: 3 req/min per email+IP combination. Prevents spam reset emails.
- **D-21:** OAuth endpoints: 10 req/min per IP. Generous for normal OAuth redirects, prevents abuse.
- **D-22:** Token override on re-request — previous reset token blacklisted when new one is generated (see D-06).

### Email Templates
- **D-23:** HTML + Jinja2 templates — responsive email design with logo, title, content, CTA button, footer. Professional look.
- **D-24:** Multi-language email support — email template rendered in user's locale preference. EN + VI minimum, extensible.
- **D-25:** Reset link points to frontend URL — format: `{FRONTEND_URL}/reset-password?token=xxx`. Frontend renders the form, calls backend API to verify and reset.

### API Route Design
- **D-26:** All routes under /auth/* namespace — consistent with Phase 3 (D-13):
  - POST /auth/forgot-password (request reset email)
  - POST /auth/reset-password (submit new password with token)
  - POST /auth/change-password (authenticated, requires current password)
  - POST /auth/set-password (OAuth-only users, no current password)
  - GET /auth/google (initiate Google OAuth)
  - GET /auth/google/callback (Google OAuth callback)
  - GET /auth/github (initiate GitHub OAuth)
  - GET /auth/github/callback (GitHub OAuth callback)

### Claude's Discretion
- Exact Jinja2 template HTML structure and styling
- OAuth scope selection beyond minimum (email, profile)
- Password validation rules for reset (reuse Phase 3 D-15: 8+ chars, cannot match email)
- Exact Redis key patterns for OAuth state storage
- Error response messages for OAuth failures
- Whether to store user locale preference in User model or derive from request

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Enterprise Architecture Reference
- `.reference/dify/api/libs/oauth.py` — Dify's OAuth implementation: base OAuth class with httpx.Client, GitHubOAuth and GoogleOAuth subclasses, user info extraction patterns, GitHub private email fallback
- `.reference/dify/` — Dify enterprise patterns for auth, user management, security

### Project Documentation
- `.planning/ROADMAP.md` — Phase 4 requirements (AUTH-06, AUTH-07, AUTH-08, USER-03) and success criteria
- `.planning/REQUIREMENTS.md` — Full requirement details
- `.planning/codebase/STRUCTURE.md` — Target directory layout and module boundaries

### Existing Code (Phase 1-3 output)
- `backend/app/core/security.py` — JWT create/decode, bcrypt hash/verify, blacklist, family invalidation — reuse for reset tokens
- `backend/app/services/auth_service.py` — Registration, login, logout, token rotation — extend with OAuth and password flows
- `backend/app/api/v1/auth.py` — Existing auth routes with cookie helpers (_set_auth_cookies, _clear_auth_cookies) — add new routes here
- `backend/app/models/user.py` — User model (hashed_password nullable for OAuth) + OAuthAccount model (already migrated)
- `backend/app/repositories/user_repository.py` — UserRepository with generic get(**filters) — extend for OAuth lookups
- `backend/app/configs/security.py` — SecurityConfig — reference for new OAuthConfig pattern
- `backend/app/utils/email.py` — send_email utility — extend for password reset emails
- `backend/app/utils/rate_limit.py` — check_rate_limit utility — reuse for new endpoints
- `backend/app/schemas/auth.py` — Auth schemas (RegisterRequest, LoginRequest, etc.) — add new schemas

### Prior Phase Context
- `.planning/phases/01-backend-core-infrastructure/01-CONTEXT.md` — Redis 3-DB setup, modular settings, dual-ID
- `.planning/phases/02-error-handling-api-structure-health/02-CONTEXT.md` — Error format, API versioning, CORS
- `.planning/phases/03-authentication-core-flows/03-CONTEXT.md` — JWT strategy, token rotation, email verification, auth API design, rate limits

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `security.py`: JWT create/decode, bcrypt, blacklist, family tracking — extend with `create_password_reset_token()`, `invalidate_all_user_sessions()`
- `auth_service.py`: Registration/login/logout/rotation — extend with `request_password_reset()`, `reset_password()`, `change_password()`, `set_password()`, `oauth_login_or_register()`
- `auth.py` router: Cookie helpers `_set_auth_cookies()`, `_clear_auth_cookies()` — reuse for OAuth callback
- `User` model: `hashed_password` nullable (D-05/Phase 3) — ready for OAuth-only users
- `OAuthAccount` model: Already migrated with `provider`, `provider_user_id`, `provider_email`, unique constraint on (provider, provider_user_id)
- `check_rate_limit()` utility: Redis-based, per-key sliding window — reuse for all new endpoints
- `send_email()` utility: SMTP delivery — extend with Jinja2 template rendering

### Established Patterns
- All auth routes under `/api/v1/auth/*` prefix
- HttpOnly cookie transport (never tokens in response body)
- Anti-enumeration responses (consistent success messages)
- Rate limiting per endpoint with Redis DB 2
- Pydantic v2 schemas with ConfigDict (Read/Create/Update separation)
- Repository pattern: `UserRepository(BaseRepository[User])` with `get(**filters)`

### Integration Points
- `configs/__init__.py`: Add OAuthConfig to composed settings singleton
- `auth.py` router: Add 8 new routes (forgot, reset, change, set, google, google/callback, github, github/callback)
- `models/__init__.py`: OAuthAccount already registered
- `utils/email.py`: Add Jinja2 template loading and multi-language support
- Phase 5 (User Profile) will use change-password and set-password from this phase
- Phase 9 (Frontend Auth UI) will consume all these backend endpoints

</code_context>

<specifics>
## Specific Ideas

- **Dify-style OAuth pattern** — base OAuth class with provider subclasses, httpx.AsyncClient for API calls, TypedDict + Pydantic TypeAdapter for response validation. Study `.reference/dify/api/libs/oauth.py` for implementation reference.
- **GitHub private email fallback** — when user has "Keep my email addresses private" enabled, call /user/emails endpoint for primary/verified email. Fall back to noreply address if needed. Dify implements this pattern.
- **Token family invalidation on password change** — reuse `invalidate_token_family()` for ALL families of a user, not just current session. Need to track user→family mapping or iterate.
- **Consistent pattern** — every new endpoint follows the same structure: rate limit check → business logic (service) → response. No shortcuts.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-authentication-advanced-password-management*
*Context gathered: 2026-04-10*
