---
phase: 04-authentication-advanced-password-management
plan: "02"
subsystem: auth
tags: [oauth, google, github, httpx, pydantic, repository]

# Dependency graph
requires:
  - phase: 03-authentication-core-flows
    provides: User model with OAuthAccount relationship, BaseRepository pattern, UserRepository pattern

provides:
  - OAuthConfig with Google + GitHub credentials (graceful empty-string disable)
  - OAuthConfig integrated into AppSettings singleton
  - OAuthUserInfo schema (provider, provider_user_id, email, name)
  - OAuthProvider abstract base class (three-step flow contract)
  - GoogleOAuthProvider with consent URL, token exchange, user info fetch
  - GitHubOAuthProvider with private email fallback via /user/emails
  - OAuthAccountRepository with create_oauth_account factory method

affects:
  - 04-03 (OAuth auth routes wire these providers into FastAPI endpoints)
  - 05-user-profile (OAuthAccount lookup for linked provider display)

# Tech tracking
tech-stack:
  added: [httpx (async HTTP for OAuth API calls)]
  patterns: [provider abstraction via ABC, graceful disable via empty credentials, private email fallback]

key-files:
  created:
    - backend/app/configs/oauth.py
    - backend/app/schemas/oauth.py
    - backend/app/infra/oauth/__init__.py
    - backend/app/infra/oauth/base.py
    - backend/app/infra/oauth/google.py
    - backend/app/infra/oauth/github.py
    - backend/app/repositories/oauth_account_repository.py
  modified:
    - backend/app/configs/__init__.py

key-decisions:
  - "OAuthConfig defaults to empty strings — OAuth endpoints return 404 when not configured (D-12)"
  - "All OAuth HTTP calls use httpx.AsyncClient per-request (no shared client lifecycle)"
  - "GitHub private email fallback: /user/emails → first verified → noreply address"
  - "OAuthProvider as ABC enforces the three-step flow contract on all providers"

patterns-established:
  - "Provider abstraction: OAuthProvider ABC → concrete GoogleOAuthProvider / GitHubOAuthProvider"
  - "Graceful disable: empty client_id/secret → 404 (wired in plan 04-03)"
  - "Repository factory method: create_oauth_account mirrors create_user pattern"

requirements-completed:
  - AUTH-07
  - AUTH-08

# Metrics
duration: 15min
completed: 2026-04-10
---

# Plan 04-02: OAuth Infrastructure Summary

**Google + GitHub OAuth provider clients with abstract base, OAuthUserInfo schema, and OAuthAccountRepository — the complete infrastructure layer for Plan 04-03 route wiring**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-10T14:30:00Z
- **Completed:** 2026-04-10T14:45:00Z
- **Tasks:** 5
- **Files modified:** 8

## Accomplishments
- OAuthConfig integrated into AppSettings — Google + GitHub credentials with empty-string graceful disable
- OAuthProvider ABC defines the three-step OAuth flow contract (authorization URL → token exchange → user info)
- GoogleOAuthProvider: full consent URL with `openid email profile` scopes, server-side token exchange via httpx
- GitHubOAuthProvider: private email fallback chain (`/user/emails` → first verified → noreply address) handles ~30% of GitHub users with hidden emails
- OAuthAccountRepository follows existing repository pattern — `create_oauth_account` factory mirrors `create_user`

## Task Commits

Each task was committed atomically:

1. **T1: OAuthConfig + AppSettings integration** - `a3d2077` (feat)
2. **T2: OAuthUserInfo schema + OAuthProvider ABC** - `359288c` (feat)
3. **T3: GoogleOAuthProvider** - `6571356` (feat)
4. **T4: GitHubOAuthProvider with private email fallback** - `b5f46c9` (feat)
5. **T5: OAuthAccountRepository** - `39eb866` (feat)

## Files Created/Modified
- `backend/app/configs/oauth.py` — OAuthConfig with Google + GitHub credential fields
- `backend/app/configs/__init__.py` — OAuthConfig added to AppSettings inheritance chain
- `backend/app/schemas/oauth.py` — OAuthUserInfo normalized schema
- `backend/app/infra/oauth/__init__.py` — Package init
- `backend/app/infra/oauth/base.py` — OAuthProvider abstract base class
- `backend/app/infra/oauth/google.py` — Google OAuth 2.0 provider implementation
- `backend/app/infra/oauth/github.py` — GitHub OAuth provider with private email fallback
- `backend/app/repositories/oauth_account_repository.py` — OAuthAccount data access layer

## Decisions Made
- `OAUTH_REDIRECT_BASE_URL` lives in OAuthConfig (not AppConfig) — OAuth-specific concern; `FRONTEND_URL` already in AppConfig
- All OAuth HTTP calls use `httpx.AsyncClient()` as context manager per-request — no shared client lifecycle management needed at infra layer
- GitHub noreply fallback format: `{github_id}+noreply@users.noreply.github.com` — matches GitHub's own format

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None — all imports and verifications passed on first attempt.

## User Setup Required
**OAuth credentials require manual configuration.** Add to `backend/.env`:
```
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GITHUB_CLIENT_ID=<from GitHub OAuth App>
GITHUB_CLIENT_SECRET=<from GitHub OAuth App>
OAUTH_REDIRECT_BASE_URL=http://localhost:8000
```
Leave empty to disable OAuth endpoints (they will return 404).

## Next Phase Readiness
- All OAuth infrastructure ready for Plan 04-03 route wiring
- `GoogleOAuthProvider` and `GitHubOAuthProvider` instantiated with settings values in route handlers
- `OAuthAccountRepository` ready for use in auth service OAuth flow
- Redis state parameter storage (CSRF protection) to be implemented in Plan 04-03

---
*Phase: 04-authentication-advanced-password-management*
*Completed: 2026-04-10*
