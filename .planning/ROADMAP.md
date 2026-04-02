# Roadmap: PAPERY v1

**Created:** 2026-04-01
**Granularity:** Fine (8-12 phases, 5-10 plans each)
**Total v1 Requirements:** 61
**Phases:** 10

---

## Phase 1: Backend Core Infrastructure

**Goal:** Establish the foundational backend skeleton — project structure, database, Redis, MinIO connections, configuration system, Docker Compose dev environment, and core patterns (dual-ID, soft delete, layered architecture).

**Status:** ✅ Complete — 5/5 plans complete (2026-04-02)
**Plans progress:** 01-01 ✅ Project Scaffold & Python Tooling | 01-02 ✅ Docker Compose Dev Environment | 01-03 ✅ Database Layer, Models & Alembic | 01-04 ✅ Redis & MinIO Extensions | 01-05 ✅ Makefile Automation & Testing Foundation

**Why first:** Every backend feature depends on these primitives. Database models, configuration, Docker stack, and architectural patterns must be correct before any business logic is built. Getting these wrong means rebuilding from the foundation.

### Requirements

| ID | Requirement |
|----|-------------|
| INFRA-01 | FastAPI backend with layered architecture (Router -> Service -> CRUD -> Schema -> Model) |
| INFRA-02 | PostgreSQL 16+ with SQLAlchemy 2.0 async ORM and Alembic migrations |
| INFRA-03 | Redis 7+ with namespace isolation (cache db=0, queue db=1, rate_limit db=2) |
| INFRA-04 | MinIO file storage with presigned URL support |
| INFRA-09 | Environment-based configuration (Pydantic Settings) with startup validation |
| INFRA-11 | Docker Compose development environment (backend, worker, PostgreSQL, Redis, MinIO) |
| INFRA-14 | Dual ID strategy — int id (internal) + UUID (public API) |
| INFRA-15 | Soft delete mixin on all core entities |

### Success Criteria

1. `docker compose up` starts all services (backend, PostgreSQL, Redis, MinIO) and backend responds to requests
2. A sample model with dual-ID + soft delete can be created, queried by UUID, soft-deleted, and excluded from default queries
3. Alembic migration generates and applies successfully; `alembic check` passes in CI
4. Redis connections work with three separate DB namespaces (verified by writing/reading to each)
5. MinIO presigned upload URL can be generated and used to upload a test file

---

## Phase 2: Error Handling, API Structure & Health

**Goal:** Establish API versioning, structured error handling, health checks, CORS, and production Docker images — the API contract and operational observability layer.

**Why here:** Before building any business endpoints (auth, projects), the API structure, error format, and operational endpoints must be defined. All subsequent endpoints will use these patterns.

**Status:** 🔄 In Progress — Plan 02-01 ✅ (Exception Hierarchy & ErrorResponse) | Plan 02-02 ✅ (RequestIDMiddleware) | Plan 02-03 ✅ (Router Aggregator, Exception Handlers, /ready, CORS Guard)

### Requirements

| ID | Requirement |
|----|-------------|
| INFRA-06 | Structured error handling with custom exception hierarchy and consistent API error format |
| INFRA-07 | API versioning at /api/v1/ with OpenAPI auto-documentation |
| INFRA-08 | Health check endpoints (/health for liveness, /ready for deep checks) |
| INFRA-10 | CORS configuration — explicit origin allowlist from environment, never wildcard in production |
| INFRA-12 | Production-optimized Docker images (multi-stage build, no --reload, proper workers) |

### Success Criteria

1. All API endpoints are mounted under `/api/v1/` and OpenAPI docs are accessible at `/api/v1/docs`
2. Any raised application exception returns a consistent JSON error response with error code, message, and details
3. `/health` returns 200 immediately; `/ready` checks PostgreSQL, Redis, and MinIO connectivity and returns 503 if any fail
4. CORS rejects requests from unlisted origins; production config validates that wildcard `*` is not in the allowlist
5. Production Docker image builds successfully with multi-stage build and runs without `--reload`

---

## Phase 3: Authentication — Core Flows

**Goal:** Implement the core authentication system — registration, login, logout, JWT token management via HttpOnly cookies, and token refresh/rotation.

**Why here:** Authentication is the prerequisite for every protected endpoint. The JWT + cookie pattern must be established before any user-facing features.

### Requirements

| ID | Requirement |
|----|-------------|
| AUTH-01 | User can sign up with email and password |
| AUTH-02 | User receives email verification after signup; account is restricted until verified |
| AUTH-03 | User can log in with email and password; receives JWT access + refresh tokens via HttpOnly cookies |
| AUTH-04 | User session persists across browser refresh via automatic token refresh |
| AUTH-05 | User can log out; tokens are blacklisted in Redis |
| AUTH-09 | Refresh token rotation — each refresh issues new token pair and invalidates old |

### Success Criteria

1. A new user can register with email/password, receives a verification email, and cannot access protected endpoints until verified
2. After login, JWT access + refresh tokens are set as HttpOnly cookies (not visible to JavaScript, not in response body)
3. When access token expires, the client can hit the refresh endpoint; old refresh token is invalidated and a new pair is issued
4. After logout, both tokens are blacklisted in Redis; subsequent requests with those tokens return 401
5. Token refresh persists user session across browser refresh without re-login

---

## Phase 4: Authentication — Advanced & Password Management

**Goal:** Complete the authentication system with OAuth providers (Google, GitHub) and password management (reset, change).

**Why here:** OAuth and password management are secondary auth flows that build on the core JWT infrastructure from Phase 3. Separating them allows Phase 3 to be tested and validated before adding complexity.

### Requirements

| ID | Requirement |
|----|-------------|
| AUTH-06 | User can reset password via secure time-limited email link |
| AUTH-07 | User can sign up / log in via Google OAuth |
| AUTH-08 | User can sign up / log in via GitHub OAuth |
| USER-03 | User can change password (requires current password) |

### Success Criteria

1. User can request a password reset; receives an email with a time-limited link that expires after use or timeout
2. Google OAuth flow completes end-to-end: redirect -> Google consent -> callback -> JWT cookies set -> user created or linked
3. GitHub OAuth flow completes end-to-end with same pattern as Google OAuth
4. User can change password by providing current password; the change invalidates all existing sessions (Redis token blacklist)
5. OAuth user who has no password set cannot use password-change; is directed to set initial password first

---

## Phase 5: User Profile & Account Management

**Goal:** Complete user self-service — view/edit profile, avatar upload, and account deletion with soft delete grace period.

**Why here:** Profile and account management depend on auth (Phases 3-4) and file storage (Phase 1 MinIO). They are standalone features that complete the user identity system before building tier/permissions on top.

### Requirements

| ID | Requirement |
|----|-------------|
| USER-01 | User can view own profile (name, email, avatar, tier, created date) |
| USER-02 | User can edit own profile (display name, avatar) |
| USER-04 | User can delete own account (soft delete with grace period) |

### Success Criteria

1. Authenticated user can fetch their profile and see name, email, avatar URL, current tier, and account creation date
2. User can update display name and upload avatar (stored in MinIO, URL returned in profile)
3. Account deletion marks the user as soft-deleted with a grace period; user cannot log in during grace period
4. After grace period, scheduled task permanently anonymizes user data (GDPR compliance pattern)
5. During grace period, user can reactivate account by contacting support (account still exists in DB)

---

## Phase 6: Tier System & Permissions

**Goal:** Build the tier/subscription system with feature flags, tier-aware rate limiting, and Stripe billing integration.

**Why here:** Tiers and permissions are the authorization layer that gates all subsequent features (admin, projects). Must be built after auth (user exists) and before any feature that checks permissions.

### Requirements

| ID | Requirement |
|----|-------------|
| TIER-01 | System supports multiple tiers (free, pro, enterprise) with configurable feature limits |
| TIER-02 | Each tier maps to feature flags (centralized, not hardcoded in business logic) |
| TIER-03 | Rate limiting is tier-aware — different limits per endpoint per tier |
| TIER-04 | Tier upgrades/downgrades update user permissions immediately |
| TIER-05 | Billing integration (Stripe) — user can subscribe, upgrade, downgrade, cancel |
| TIER-06 | Webhook handling for Stripe events (payment success, failure, cancellation) |

### Success Criteria

1. Three tiers (free, pro, enterprise) exist with distinct feature limits (e.g., max projects, max documents, API rate limits)
2. Feature access checks use centralized feature flag lookup by tier — no hardcoded tier names in business logic
3. Rate limiting middleware applies different limits per endpoint based on user's tier; exceeding limit returns 429 with retry-after header
4. When a user's tier changes (upgrade/downgrade), their permissions and rate limits update immediately without re-login
5. Stripe checkout flow works: user subscribes -> webhook confirms payment -> tier upgrades; cancellation -> tier downgrades at period end

---

## Phase 7: Admin Panel (Backend)

**Goal:** Build admin-only backend endpoints for user management, tier configuration, rate limit management, and system settings.

**Why here:** Admin features depend on auth (Phase 3-4), user system (Phase 5), and tier system (Phase 6). Admin is a separate privilege layer that manages these existing systems.

### Requirements

| ID | Requirement |
|----|-------------|
| ADMIN-01 | Superuser can view and search all users |
| ADMIN-02 | Superuser can activate/deactivate/ban user accounts |
| ADMIN-03 | Superuser can create/edit/delete tiers and their feature flags |
| ADMIN-04 | Superuser can create/edit/delete rate limit rules per tier per endpoint |
| ADMIN-05 | Superuser can view system configuration and modify runtime settings |
| ADMIN-06 | Admin panel is a separate route group with superuser-only middleware |

### Success Criteria

1. Admin endpoints are mounted under `/api/v1/admin/` with superuser-only middleware; non-superuser gets 403
2. Superuser can list users with pagination, search by email/name, and filter by tier/status
3. Superuser can activate, deactivate, or ban a user; banned users cannot log in and active sessions are invalidated
4. Superuser can CRUD tiers and their associated feature flags; changes propagate immediately to affected users
5. Superuser can CRUD rate limit rules and view/modify runtime system settings

---

## Phase 8: Project System & ACL

**Goal:** Implement the project system with CRUD, access control lists (ACL), member management, and invite flows.

**Why here:** Projects are the top-level container for all user content (documents, chats, AI results). They depend on auth + tiers (permission checks) and are required before document/AI features in v2. ACL is the reusable permission model for all future resources.

### Requirements

| ID | Requirement |
|----|-------------|
| PROJ-01 | User can create a project (name, description) |
| PROJ-02 | User can view, edit, and soft-delete own projects |
| PROJ-03 | Project has ACL — owner, editor, viewer roles |
| PROJ-04 | Owner can invite users to project via invite link or email |
| PROJ-05 | Owner can change member roles or remove members |
| PROJ-06 | User can list and search own projects (owned + shared with) |

### Success Criteria

1. Authenticated user can create a project with name/description; project count is limited by tier
2. Project owner can view, edit name/description, and soft-delete the project; soft-deleted projects are excluded from listings
3. ACL system supports owner/editor/viewer roles; editor can modify project content but not manage members; viewer is read-only
4. Owner can generate an invite link (expiring) or send email invite; invited user gets correct role on acceptance
5. User's project list includes both owned projects and projects shared with them, with search by name

---

## Phase 9: Frontend Foundation & Auth UI

**Goal:** Set up the complete frontend infrastructure — Next.js App Router, i18n, theming, state management, HTTP client, component library, and authentication UI (login, register, password flows).

**Why here:** Frontend depends on backend API being stable (Phases 1-8 complete the full backend). However, frontend foundation and auth UI can be built once Phases 1-4 backend endpoints exist. Grouped here as a single phase because the frontend setup and auth UI are deeply intertwined (middleware, route protection, cookie handling).

### Requirements

| ID | Requirement |
|----|-------------|
| FRONT-01 | Next.js 16 + React 19 App Router setup with TypeScript strict mode |
| FRONT-02 | Internationalization from day one via next-intl (EN + VI minimum) |
| FRONT-03 | Dark/light/system theme with user preference persistence |
| FRONT-04 | Responsive layout (mobile + tablet + desktop) via Tailwind CSS |
| FRONT-05 | TanStack Query v5 for server state management |
| FRONT-06 | Zustand v5 for client-only state (UI preferences, sidebar state) — max 3-5 stores |
| FRONT-07 | Zod v4 for runtime validation of API responses and form inputs |
| FRONT-08 | Auth middleware — cookie-based JWT, auto-refresh on 401, route protection |
| FRONT-09 | shadcn/ui component library setup (Radix UI primitives, accessible) |
| FRONT-10 | HTTP client with typed API calls, Bearer token injection, error normalization |
| FRONT-11 | React Hook Form + Zod resolver for all form handling |

### Success Criteria

1. Next.js app boots with App Router, TypeScript strict mode, and locale-based routing (`/en/...`, `/vi/...`) working end-to-end
2. All UI text uses `t()` function from next-intl; switching locale changes all visible text without page reload
3. Dark/light/system theme toggle works and persists user preference across sessions (localStorage + cookie for SSR)
4. Auth flow works end-to-end: register form -> API call -> email verification notice -> login form -> JWT cookies set -> redirect to dashboard
5. Protected routes redirect unauthenticated users to login; 401 responses trigger automatic token refresh before retry

---

## Phase 10: Dashboard, Admin UI & QuasarFlow Stubs

**Goal:** Build the user dashboard (project management UI), admin panel UI, and QuasarFlow integration stubs — completing the v1 deliverable.

**Why here:** This is the final phase that brings everything together. Dashboard and admin UI consume all backend APIs built in Phases 1-8. QuasarFlow stubs are placed here because they are the last piece — the integration point that v2 will swap with real AI implementation.

### Requirements

| ID | Requirement |
|----|-------------|
| QFLOW-01 | Abstract QuasarFlow client interface (base class with typed methods) |
| QFLOW-02 | Mock/stub implementation for development (returns realistic fake data) |
| QFLOW-03 | Error handling patterns — timeout, retry, circuit breaker |
| QFLOW-04 | Async pattern — AI calls go through ARQ task queue, frontend polls or SSE for results |
| INFRA-05 | ARQ background task worker for async processing |
| INFRA-13 | CI/CD pipeline via GitHub Actions (lint, type check, test, build, deploy) |

### Success Criteria

1. User dashboard shows project list with create/edit/delete actions, member management, and search — all consuming backend APIs
2. Admin panel UI shows user management, tier configuration, rate limit management, and system settings — all behind superuser-only route guard
3. QuasarFlow client has a typed abstract interface and a mock implementation that returns realistic fake data for all expected AI operations
4. AI call simulation works end-to-end: frontend triggers action -> backend enqueues ARQ task -> mock QuasarFlow processes -> frontend polls/SSE for result
5. CI/CD pipeline runs lint, type check, tests, builds Docker images, and deploys on push to main/develop

---

## Phase Dependency Graph

```
Phase 1 (Backend Core)
  └── Phase 2 (API Structure & Health)
        └── Phase 3 (Auth Core)
              ├── Phase 4 (Auth Advanced)
              │     └── Phase 5 (User Profile)
              │           └── Phase 6 (Tier & Permissions)
              │                 ├── Phase 7 (Admin Backend)
              │                 └── Phase 8 (Project & ACL)
              └── Phase 9 (Frontend Foundation) [can start after Phase 3]
                    └── Phase 10 (Dashboard, Admin UI & QFlow Stubs)
                          [depends on Phases 7, 8, 9]
```

**Parallelization opportunities:**
- Phase 9 (Frontend) can start after Phase 3 is complete (auth API exists)
- Phase 7 (Admin Backend) and Phase 8 (Projects) can run in parallel after Phase 6
- Phase 10 requires Phases 7, 8, and 9 to all be complete

---

## Coverage Summary

| Category | Requirements | Phase(s) |
|----------|-------------|----------|
| Authentication (9) | AUTH-01..09 | Phase 3 (6), Phase 4 (3) |
| User & Profile (4) | USER-01..04 | Phase 4 (1), Phase 5 (3) |
| Tier & Permissions (6) | TIER-01..06 | Phase 6 (6) |
| Admin Panel (6) | ADMIN-01..06 | Phase 7 (6) |
| Project System (6) | PROJ-01..06 | Phase 8 (6) |
| Backend Infrastructure (15) | INFRA-01..15 | Phase 1 (8), Phase 2 (5), Phase 10 (2) |
| Frontend Foundation (11) | FRONT-01..11 | Phase 9 (11) |
| QuasarFlow Integration (4) | QFLOW-01..04 | Phase 10 (4) |
| **Total** | **61** | **61 mapped (100%)** |

**Unmapped requirements: 0**

---

*Roadmap created: 2026-04-01*
*Last updated: 2026-04-03 — Plan 02-01 complete (Exception Hierarchy & ErrorResponse), Plan 02-02 complete (RequestIDMiddleware), Plan 02-03 complete (Router Aggregator, Exception Handlers, /ready, CORS Guard)*
