# Pitfalls Research — PAPERY

> AI-Powered Document Intelligence SaaS Platform
> Research date: 2026-04-01

---

## 1. Authentication & Security Pitfalls

### PIT-01: Default Passwords in Config (Critical)

**What goes wrong:** Shipping `.env.example` with real-looking passwords (`123456`, `admin123`). Developers copy without changing. Production gets compromised.

**Warning signs:** Any hardcoded credential in version control. Any `.env.example` with non-placeholder values.

**Prevention:**
- `.env.example` uses `CHANGE_ME_xxx` placeholders, never real-looking values
- Startup validation: fail fast if any `CHANGE_ME` values detected
- CI check: grep for common weak passwords in config files

**Phase:** Phase 1 (Backend Foundation) — establish from day one.

**Source:** v0 had `123456` as default admin password in `.env.example`.

---

### PIT-02: JWT Token in Response Body Instead of HttpOnly Cookie (Critical)

**What goes wrong:** Returning tokens in JSON response body. Frontend stores in localStorage. XSS attack steals all tokens.

**Warning signs:** `return {"access_token": token}` in login endpoint. `localStorage.setItem("token")` in frontend.

**Prevention:**
- Tokens ONLY in HttpOnly, Secure, SameSite=Lax cookies
- Never expose tokens to JavaScript
- Refresh token rotation on each use
- Token blacklist in Redis for logout

**Phase:** Phase 1 (Auth System) — non-negotiable security requirement.

**Source:** v0 sent refresh tokens via response body.

---

### PIT-03: Missing Email Verification Enforcement (High)

**What goes wrong:** Users can use full app without verifying email. Fake accounts, spam, no password recovery path.

**Warning signs:** `is_verified` field exists but isn't checked in middleware.

**Prevention:**
- Middleware checks `is_verified` on all protected routes
- Grace period: 24h to verify, then account suspended
- Resend verification endpoint with rate limiting

**Phase:** Phase 1 (Auth System).

---

### PIT-04: Overly Permissive CORS (High)

**What goes wrong:** `CORS_ORIGINS=*` in production. Any website can make authenticated requests.

**Warning signs:** Wildcard CORS, no environment-specific configuration.

**Prevention:**
- Explicit origin allowlist from environment variable
- Different CORS config per environment
- Never allow `*` in staging or production

**Phase:** Phase 1 (Backend Setup).

---

## 2. Architecture Pitfalls

### PIT-05: Skipping Service Layer (High)

**What goes wrong:** Business logic in routers (FastAPI endpoints). Logic becomes untestable, duplicated, tangled with HTTP concerns.

**Warning signs:** Router functions >30 lines. Multiple routers doing similar logic. Hard to write unit tests.

**Prevention:**
- Strict layering: Router → Service → CRUD → Model
- Routers only: parse request, call service, return response
- Services contain ALL business logic
- Unit tests target service layer, not routers

**Phase:** Phase 1 (Backend Foundation) — establish pattern early.

**Source:** v0 had business logic in routers (no service layer).

---

### PIT-06: Synchronous AI Service Calls (High)

**What goes wrong:** `await quasarflow_client.process(doc)` blocks the request for 30+ seconds. Server threads exhausted. Users see timeouts.

**Warning signs:** Long-running API calls in request handlers. No timeout configuration.

**Prevention:**
- All AI calls go through background task queue (ARQ)
- Frontend polls for results or uses WebSocket/SSE for streaming
- Timeout + retry logic on QuasarFlow client
- Circuit breaker pattern: if QuasarFlow is down, gracefully degrade

**Phase:** Phase with AI integration (v2). But design the pattern in v1.

---

### PIT-07: Migrations in .gitignore (Critical)

**What goes wrong:** `migrations/versions/` gitignored. Each developer generates different migrations. Production schema drifts. Data loss.

**Warning signs:** Migration files not in git. `alembic upgrade head` gives different results per machine.

**Prevention:**
- NEVER gitignore migration files
- Migration files are committed and reviewed like code
- CI runs `alembic check` to detect pending migrations

**Phase:** Phase 1 (Database Setup) — must fix from v0's mistake.

**Source:** v0 had `migrations/versions/` in `.gitignore`.

---

### PIT-08: Single Redis for Everything Without Namespace Isolation (Medium)

**What goes wrong:** Cache keys collide with rate limit keys. `FLUSHDB` for cache wipes rate limits and task queue.

**Warning signs:** All Redis operations on same database number. No key prefix convention.

**Prevention:**
- Use separate Redis databases (db=0 cache, db=1 queue, db=2 rate_limit)
- OR strict key prefix convention: `cache:`, `queue:`, `rl:`
- Never `FLUSHDB` — use targeted key deletion with prefix scan

**Phase:** Phase 1 (Infrastructure Setup).

**Source:** v0 used single Redis for cache, queue, and rate limiting.

---

## 3. Frontend Pitfalls

### PIT-09: No Server State Management (High)

**What goes wrong:** Manual `fetch` + `useState` for API data. No caching, no background refetching, no optimistic updates. Stale data everywhere. User sees loading spinners constantly.

**Warning signs:** `useEffect(() => fetch(...))` patterns. No data caching library.

**Prevention:**
- Use TanStack Query from day one
- Define query keys consistently
- Configure stale times per resource type
- Implement optimistic updates for mutations

**Phase:** Phase 2 (Frontend Foundation).

**Source:** v0 had no React Query — manual fetch in components.

---

### PIT-10: Zustand Store Sprawl (Medium)

**What goes wrong:** Creating a Zustand store for every piece of state. Stores become mini-databases. State sync issues between stores.

**Warning signs:** >10 Zustand stores. Stores referencing each other. Duplicate data across stores.

**Prevention:**
- Zustand for TRUE client state only (UI preferences, sidebar state, draft content)
- Server state belongs in TanStack Query
- Limit to 3-5 stores maximum
- Never put API response data in Zustand

**Phase:** Phase 2 (Frontend Foundation).

---

### PIT-11: i18n Afterthought (Medium)

**What goes wrong:** Building UI with hardcoded English strings, then trying to add i18n later. Hundreds of strings to extract. Layout breaks with longer translations.

**Warning signs:** Hardcoded strings in components. No locale files. `"Submit"` instead of `t('common.submit')`.

**Prevention:**
- Set up next-intl from first component
- Every user-visible string goes through `t()` from day one
- Locale parity tests: ensure all languages have all keys
- Design UI with flexible widths (Vietnamese text is often longer than English)

**Phase:** Phase 2 (Frontend Foundation) — must be from the start.

---

## 4. SaaS-Specific Pitfalls

### PIT-12: Tier System Without Feature Flags (Medium)

**What goes wrong:** Checking tier permissions with scattered `if user.tier == 'pro'` throughout code. Adding a new tier requires touching dozens of files.

**Warning signs:** Tier checks hardcoded in business logic. No centralized feature gate.

**Prevention:**
- Centralized feature flag system tied to tiers
- `has_feature(user, 'advanced_search')` instead of `user.tier == 'pro'`
- Tier → feature mapping in database, not code
- Admin can modify tier features without deployment

**Phase:** Phase 1 (Tier System Design).

---

### PIT-13: No Soft Delete Consistency (Medium)

**What goes wrong:** Some models have soft delete, some don't. Queries sometimes filter `is_deleted`, sometimes don't. Deleted data leaks into responses.

**Warning signs:** Inconsistent `is_deleted` filtering. Hard deletes on some tables.

**Prevention:**
- ALL core entities use SoftDeleteMixin (established in v0)
- Base query methods ALWAYS filter `is_deleted=False`
- Hard delete only for truly transient data (sessions, temporary tokens)
- Periodic cleanup job for old soft-deleted records

**Phase:** Phase 1 (Database Models).

**Source:** v0 established this pattern — maintain it.

---

### PIT-14: Monolithic Admin Panel (Medium)

**What goes wrong:** Building admin features into main user-facing routes. Admin and user UX compromises each other. Security boundary blurred.

**Warning signs:** `/dashboard` has admin sections visible to regular users. Same components serve admin and user views.

**Prevention:**
- Separate `/admin` route group with superuser middleware
- Admin components don't share state with user components
- Admin API endpoints have dedicated router with superuser dependency
- Consider: admin panel as separate Next.js route group, not separate app

**Phase:** Phase 1 (Admin Panel).

---

## 5. Deployment Pitfalls

### PIT-15: Development Config in Production (High)

**What goes wrong:** `--reload` flag, debug mode, verbose logging in production Docker image. Performance tanks, secrets leak in logs.

**Warning signs:** Single Dockerfile for dev and prod. No environment-specific startup commands.

**Prevention:**
- Separate Docker Compose files: `docker-compose.yml` (base) + `docker-compose.dev.yml` (overrides)
- Production: `uvicorn --workers 4` (no `--reload`)
- Environment variable: `ENVIRONMENT=production` controls behavior
- No `DEBUG=True` ever reaching production

**Phase:** Phase 1 (Docker Setup).

**Source:** v0 had `--reload` in Docker Compose.

---

### PIT-16: No Health Checks or Readiness Probes (Medium)

**What goes wrong:** Container reports "running" but database connection is dead. Load balancer routes traffic to broken instance. Users see 500 errors.

**Warning signs:** No `/health` endpoint. Docker `HEALTHCHECK` not configured.

**Prevention:**
- `/health` endpoint checks: DB connection, Redis ping, MinIO reachable
- Docker HEALTHCHECK instruction in Dockerfile
- Separate `/ready` for deep checks vs `/alive` for basic liveness

**Phase:** Phase 1 (Backend Foundation).

---

## 6. Summary Table

| ID | Pitfall | Severity | Phase | Source |
|----|---------|----------|-------|--------|
| PIT-01 | Default passwords in config | Critical | 1 | v0 |
| PIT-02 | JWT in response body | Critical | 1 | v0 |
| PIT-03 | Missing email verification | High | 1 | — |
| PIT-04 | Overly permissive CORS | High | 1 | — |
| PIT-05 | Skipping service layer | High | 1 | v0 |
| PIT-06 | Synchronous AI calls | High | v2 | — |
| PIT-07 | Migrations gitignored | Critical | 1 | v0 |
| PIT-08 | Redis without namespaces | Medium | 1 | v0 |
| PIT-09 | No server state management | High | 2 | v0 |
| PIT-10 | Zustand store sprawl | Medium | 2 | — |
| PIT-11 | i18n afterthought | Medium | 2 | — |
| PIT-12 | Tier without feature flags | Medium | 1 | — |
| PIT-13 | No soft delete consistency | Medium | 1 | v0 |
| PIT-14 | Monolithic admin panel | Medium | 1 | — |
| PIT-15 | Dev config in production | High | 1 | v0 |
| PIT-16 | No health checks | Medium | 1 | — |

---

*Research based on v0 post-mortem (CONCERNS.md), SaaS security best practices, and FastAPI + Next.js community patterns.*
