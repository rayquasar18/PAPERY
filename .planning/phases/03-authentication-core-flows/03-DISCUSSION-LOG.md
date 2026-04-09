# Phase 3: Authentication — Core Flows - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 03-authentication-core-flows
**Areas discussed:** Token Strategy, User Model, Email Verification, Auth API Design

---

## Token Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| HS256 symmetric | Simple, single secret key. Good for single-server. | ✓ |
| RS256 asymmetric | RSA keypair. External verification without signing key. | |

**User's choice:** HS256 symmetric
**Notes:** Already scaffolded in SecurityConfig

| Option | Description | Selected |
|--------|-------------|----------|
| Dual cookies | Access + refresh in separate HttpOnly cookies. SameSite=Lax, Secure in prod. | ✓ |
| Hybrid (cookie + body) | Refresh in cookie, access in response body. More flexible for mobile. | |

**User's choice:** Dual cookies
**Notes:** Clean separation, consistent XSS protection

| Option | Description | Selected |
|--------|-------------|----------|
| Redis JTI blacklist | Store invalidated JTI in Redis with TTL. Auto-cleanup. | ✓ |
| Redis token family tracking | Track valid families per user. More complex, enables logout all devices. | |

**User's choice:** Redis JTI blacklist
**Notes:** Simple, self-cleaning via Redis TTL

| Option | Description | Selected |
|--------|-------------|----------|
| Strict rotation + replay detection | New pair on refresh, old blacklisted, family invalidated on replay. | ✓ |
| Simple rotation | New pair, old blacklisted. No family tracking. | |

**User's choice:** Strict rotation with replay detection
**Notes:** Security-first approach, detects token theft

---

## User Model

| Option | Description | Selected |
|--------|-------------|----------|
| Standard SaaS fields | email, hashed_password, display_name, avatar_url, is_active, is_verified, is_superuser | ✓ |
| Extended fields | Standard + phone, locale, timezone, last_login_at | |

**User's choice:** Standard SaaS fields
**Notes:** Keep lean, extend later if needed

| Option | Description | Selected |
|--------|-------------|----------|
| bcrypt via passlib | Proven, adaptive hashing, configurable work factor | ✓ |
| Argon2 via argon2-cffi | Memory-hard, newer, better GPU resistance | |

**User's choice:** bcrypt via passlib
**Notes:** Industry standard, wide ecosystem support

| Option | Description | Selected |
|--------|-------------|----------|
| Boolean flags | is_active, is_verified, is_superuser. Simple, queryable. | ✓ |
| Status enum + flags | Single status enum + is_superuser flag. More explicit state machine. | |

**User's choice:** Boolean flags
**Notes:** No enum overhead, straightforward querying

| Option | Description | Selected |
|--------|-------------|----------|
| Separate OAuth table | OAuthAccount (user_id FK, provider, provider_user_id, email) | ✓ |
| Provider columns on User | google_id, github_id directly on User table | |

**User's choice:** Separate OAuthAccount table
**Notes:** Extensible, clean separation, supports multiple providers

---

## Email Verification

| Option | Description | Selected |
|--------|-------------|----------|
| Signed JWT token | JWT with user ID + purpose claim. No DB lookup. Self-expiring. | ✓ |
| Random token in Redis | UUID stored with user_id and expiry. Requires lookup. | |

**User's choice:** Signed JWT token
**Notes:** Stateless verification, consistent with auth token approach

| Option | Description | Selected |
|--------|-------------|----------|
| 24 hours | Generous window for delayed email delivery | ✓ |
| 1 hour | Tighter security, may cause issues with slow delivery | |

**User's choice:** 24 hours
**Notes:** User-friendly, accommodates email delays

| Option | Description | Selected |
|--------|-------------|----------|
| Allow login, restrict later | Login immediately, banner/warning, restrictions via tier system (Phase 6) | ✓ |
| Block login until verified | Cannot log in until email confirmed | |

**User's choice:** Allow login, restrict later
**Notes:** Lower friction, Phase 6 handles feature restrictions

| Option | Description | Selected |
|--------|-------------|----------|
| Rate-limited resend | /auth/resend-verification, 1/60s per email, old token stays valid | ✓ |
| Resend + invalidate previous | New token invalidates old one | |

**User's choice:** Rate-limited resend endpoint
**Notes:** Prevents abuse, old links still work

---

## Auth API Design

| Option | Description | Selected |
|--------|-------------|----------|
| RESTful /auth/* namespace | All endpoints under /api/v1/auth/* | ✓ |
| Split /auth + /users | Identity separate from user resource | |

**User's choice:** RESTful /auth/* namespace
**Notes:** Clean, single namespace for all auth operations

| Option | Description | Selected |
|--------|-------------|----------|
| User data in body, tokens in cookies only | {user, message} in body, tokens exclusively in HttpOnly cookies | ✓ |
| User data + tokens in body | Tokens also in response body for non-browser clients | |

**User's choice:** User data in body, tokens in cookies only
**Notes:** Consistent with dual-cookie decision (D-02)

| Option | Description | Selected |
|--------|-------------|----------|
| 8+ chars, basic rules | Min 8 chars, cannot match email, no special char requirement. NIST-aligned. | ✓ |
| Length-only 12+ | Minimum 12 chars, no complexity rules | |

**User's choice:** 8+ characters with basic rules
**Notes:** User specified: 8+ chars, basic rules (no email match), no special character requirement

| Option | Description | Selected |
|--------|-------------|----------|
| Per-endpoint limits | Login 5/min, Register 3/min, Resend 1/60s. Redis DB 2. | ✓ |
| Global auth rate limit | 20 req/min on all /auth/* per IP | |

**User's choice:** Per-endpoint limits
**Notes:** Granular protection on sensitive endpoints

---

## Claude's Discretion

- JWT claims structure beyond required fields
- Exact cookie path/domain configuration
- OAuth state parameter implementation
- SMTP email template structure
- Rate limiter implementation (sliding vs fixed window)
- Google OAuth library choice

## Deferred Ideas

None — discussion stayed within phase scope
