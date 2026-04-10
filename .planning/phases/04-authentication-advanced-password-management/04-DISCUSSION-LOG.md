# Phase 4: Authentication — Advanced & Password Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 04-authentication-advanced-password-management
**Areas discussed:** Password Reset Flow, OAuth Integration, Account Linking Policy, Password Change & Sessions, Rate Limit & Abuse Prevention, OAuth Config & Env Vars, Email Templates, API Route Design

---

## Password Reset Flow

### Reset Token Format

| Option | Description | Selected |
|--------|-------------|----------|
| JWT token (Recommended) | Reuse JWT system with purpose='password_reset', 1h expiry, single-use via Redis blacklist. Consistent with email verification flow. | ✓ |
| DB-stored random token | Random string saved in DB, cleaned up by background job. Easy revocation. | |
| Redis-stored token | Random token in Redis with TTL, no DB table needed. Fast, auto-expiring. | |

**User's choice:** JWT token
**Notes:** Consistent with existing email verification pattern from Phase 3.

### Reset Link Expiry

| Option | Description | Selected |
|--------|-------------|----------|
| 1 hour (Recommended) | Balance between security and user experience | ✓ |
| 15 minutes | Only for high-security requirements | |
| 24 hours | Generous for delayed email delivery | |

**User's choice:** 1 hour

### Single-Use Enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Single-use (Recommended) | Token blacklisted after use, cannot be reused | ✓ |
| Multi-use | Token can be reused within validity period | |

**User's choice:** Single-use

### Anti-Enumeration

| Option | Description | Selected |
|--------|-------------|----------|
| Anti-enumeration (Recommended) | Always return generic success message regardless of email existence | ✓ |
| Transparent errors | Return error if email doesn't exist | |

**User's choice:** Anti-enumeration

### Reset Flow Steps

| Option | Description | Selected |
|--------|-------------|----------|
| Direct to reset form | Simple, one-step: click link → reset form | |
| Intermediate confirm step | Email → verify page → reset form. Better UX. | ✓ |

**User's choice:** Intermediate confirm step

---

## OAuth Integration

### OAuth Library

| Option | Description | Selected |
|--------|-------------|----------|
| httpx direct (Recommended) | Dify-style: base OAuth class + provider subclasses, httpx.AsyncClient. Full control, async-native. | ✓ |
| Authlib | Full-featured OAuth2/OIDC library. OIDC auto-discovery. Large dependency. | |
| fastapi-users | FastAPI-specific. Opinionated, may conflict with custom JWT system. | |

**User's choice:** httpx direct
**Notes:** User asked about Dify's approach first. After research showing Dify uses httpx directly (not Authlib despite having it in dependencies), user confirmed httpx direct approach.

### OAuth Flow Type

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side (Recommended) | Backend handles entire flow. Secrets never exposed to client. | ✓ |
| Client-side | Frontend redirect directly. Insecure (client_secret exposed). | |

**User's choice:** Server-side

### Callback Response

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect to frontend (Recommended) | Backend sets cookies, redirects to frontend dashboard. Simple. | ✓ |
| JSON response | Backend returns JSON, frontend navigates. More frontend work. | |

**User's choice:** Redirect to frontend

### State Parameter Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Redis state (Recommended) | Random state in Redis with 10min TTL. Standard CSRF protection. | ✓ |
| Signed JWT state | State as signed JWT with redirect info. No Redis lookup needed. | |

**User's choice:** Redis state

---

## Account Linking Policy

### Auto-Link by Email

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-link by email (Recommended) | OAuth email matches existing account → auto-link. Seamless. | ✓ |
| No auto-link | Always create new account. User links manually later. | |
| Ask user first | Prompt user before linking. Safer but more complex. | |

**User's choice:** Auto-link by email

### Multi-Provider Support

| Option | Description | Selected |
|--------|-------------|----------|
| Multiple providers (Recommended) | One user can link Google + GitHub. DB supports this. | |
| 1 provider total | Only one OAuth provider per user. Cannot add second. | ✓ |
| 1 per provider type | One Google + one GitHub ok, but not two Google accounts. | |

**User's choice:** 1 provider total
**Notes:** User confirmed this means only one OAuth provider total — if Google is linked, cannot add GitHub. Clarification question was asked because this conflicts with OAuthAccount table design from Phase 3.

### Unlink Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Conditional unlink (Recommended) | Allow unlink only if user has password or another auth method. | |
| No unlink | Once linked, cannot remove. | |
| You decide | Claude's discretion | ✓ |

**User's choice:** Claude's discretion
**Notes:** Will implement conditional unlink (only if user has password set) to prevent account lockout.

---

## Password Change & Sessions

### Session Invalidation on Password Change

| Option | Description | Selected |
|--------|-------------|----------|
| Invalidate all sessions (Recommended) | Kill all token families. Force re-login everywhere. Most secure. | ✓ |
| Keep current, kill others | Current session stays, others invalidated. | |
| No change | No sessions affected. Least secure. | |

**User's choice:** Invalidate all sessions

### OAuth-Only User Set Password

| Option | Description | Selected |
|--------|-------------|----------|
| Separate endpoint (Recommended) | POST /auth/set-password, only when hashed_password is NULL. No current password required. | ✓ |
| Shared endpoint, skip verify | Same change-password endpoint, skip current password check if NULL. | |
| Not allowed | OAuth-only users cannot set password. | |

**User's choice:** Separate endpoint

### Rate Limit for Password Endpoints

| Option | Description | Selected |
|--------|-------------|----------|
| 5 req/min per user (Recommended) | Prevents brute-force, allows retries. | ✓ |
| 3 req/min per user | Stricter. | |
| You decide | Claude's discretion. | |

**User's choice:** 5 req/min per user

---

## Rate Limit & Abuse Prevention

### Forgot Password Rate Limit

| Option | Description | Selected |
|--------|-------------|----------|
| 3 req/min per email+IP (Recommended) | Prevents spam reset emails. Matches register pattern. | ✓ |
| 1 req/min per email | Stricter, like resend-verification. | |
| You decide | Claude's discretion. | |

**User's choice:** 3 req/min per email+IP

### OAuth Endpoints Rate Limit

| Option | Description | Selected |
|--------|-------------|----------|
| 10 req/min per IP (Recommended) | Generous for OAuth redirects, prevents abuse. | ✓ |
| 5 req/min per IP | Stricter. | |
| No rate limit | No rate limiting on OAuth. | |
| You decide | Claude's discretion. | |

**User's choice:** 10 req/min per IP

### Token Override on Re-Request

| Option | Description | Selected |
|--------|-------------|----------|
| Override token (Recommended) | New request blacklists old token. Only newest is valid. | ✓ |
| Coexist | Multiple tokens valid simultaneously. | |
| You decide | Claude's discretion. | |

**User's choice:** Override token

---

## OAuth Config & Env Vars

### Config Location

| Option | Description | Selected |
|--------|-------------|----------|
| Separate OAuthConfig (Recommended) | New configs/oauth.py with all OAuth env vars. Clean separation. | ✓ |
| In SecurityConfig | Add to existing security config. | |

**User's choice:** Separate OAuthConfig

### Missing Credentials Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful disable (Recommended) | OAuth endpoints return 404 or aren't registered. No startup errors. | ✓ |
| Fail on start | Raise error on startup if credentials missing. | |
| You decide | Claude's discretion. | |

**User's choice:** Graceful disable

### Callback URL Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Backend callbacks (Recommended) | /api/v1/auth/{provider}/callback. Backend handles, redirects to frontend. | ✓ |
| Frontend callbacks | Frontend URL, forwards to backend. | |

**User's choice:** Backend callbacks

---

## Email Templates

### Template Format

| Option | Description | Selected |
|--------|-------------|----------|
| HTML + Jinja2 (Recommended) | Responsive HTML with logo, CTA button, footer. Professional. | ✓ |
| Plain text only | Simple but not professional. | |
| You decide | Claude's discretion. | |

**User's choice:** HTML + Jinja2

### Email Language

| Option | Description | Selected |
|--------|-------------|----------|
| English only (Recommended) | Simple, focus on v1. | |
| Multi-language | Template in user's locale. EN + VI minimum. Extensible. | ✓ |
| You decide | Claude's discretion. | |

**User's choice:** Multi-language

### Reset Link Target

| Option | Description | Selected |
|--------|-------------|----------|
| Frontend URL (Recommended) | Link to frontend: {FRONTEND_URL}/reset-password?token=xxx. Frontend renders form. | ✓ |
| Backend URL + redirect | Link to backend API, redirects to frontend after verify. | |

**User's choice:** Frontend URL

---

## API Route Design

### Route Namespace

| Option | Description | Selected |
|--------|-------------|----------|
| All under /auth/* (Recommended) | Consistent with Phase 3. All 8 new routes under /api/v1/auth/*. | ✓ |
| Separate sub-groups | /password/* and /oauth/* sub-namespaces. | |

**User's choice:** All under /auth/*

---

## Claude's Discretion

- Jinja2 template HTML structure and styling
- OAuth scope selection beyond minimum
- Password validation rules for reset (reuse Phase 3 D-15)
- Redis key patterns for OAuth state storage
- Error response messages for OAuth failures
- User locale preference storage strategy
- Unlink safety check implementation

## Deferred Ideas

None — discussion stayed within phase scope
