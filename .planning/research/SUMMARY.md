# Project Research Summary

**Project:** PAPERY — AI-Powered Document Intelligence SaaS Platform
**Domain:** AI SaaS / Document Intelligence Platform
**Researched:** 2026-04-01
**Confidence:** HIGH

---

## Executive Summary

PAPERY is an AI-powered document intelligence platform built around a clear architectural principle: the core application handles all user management, document storage, permissions, and UI rendering, while AI/LLM processing is fully delegated to an external service (QuasarFlow) via API. This "AI-Delegated Layered Monolith" pattern means PAPERY v1 can ship as a complete, production-grade SaaS foundation without requiring any AI features to be ready. The QuasarFlow client starts as a stub — the platform works end-to-end, and AI features are layered in later.

The recommended stack is Python/FastAPI (async backend) + Next.js 15 (frontend) + PostgreSQL + Redis + MinIO — a proven combination for async document processing SaaS. The critical architectural decision is the introduction of a proper **Service Layer** between API routers and CRUD, which was absent in v0. This layer is where business logic lives, QuasarFlow calls are made, and cross-resource operations are coordinated. Skipping this layer (as happened in v0) causes cascading complexity as features scale.

The primary risk is feature scope creep: there is a strong temptation to build document AI features before the SaaS foundation is solid. Research strongly supports the opposite approach — ship a rock-solid auth, tier, ACL, and project system first. Every document and AI feature depends on these foundations. Building them wrong means rebuilding everything.

---

## Key Findings

### Recommended Stack

The stack is a refined evolution of PAPERY v0, addressing v0's known weaknesses while preserving its proven strengths. The backend adds `fastcrud` (eliminating CRUD boilerplate), `ARQ` over Celery (simpler async task queue), and a Service Layer pattern. The frontend upgrades to TanStack Query v5 (replacing manual `fetch`/`useState`), `next-intl` v4 for App Router-native i18n, and Zustand v5 for client state.

See full details: [`STACK.md`](./STACK.md)

**Core technologies:**
- **FastAPI 0.115+** (Python 3.12): Web framework — async-native, Pydantic v2 integrated, OpenAPI auto-docs
- **SQLAlchemy 2.0+ + Alembic**: ORM/migrations — best async ORM for Python, type-safe mapped columns
- **fastcrud 0.15+**: CRUD abstraction — eliminates CRUD boilerplate, typed generics; key v0 improvement
- **ARQ 0.26+**: Task queue — async-native Redis queue, simpler than Celery for this stack
- **Next.js 15 + React 19**: Frontend framework — App Router stable, RSC, middleware-based auth
- **TanStack Query v5**: Server state — replaces v0's manual fetch, adds caching + optimistic updates
- **PostgreSQL 16+**: Primary database — JSONB, full-text search, pgvector-ready for future embeddings
- **Redis 7+**: Cache + queue + rate limiting — three logical namespaces on single instance
- **MinIO**: File storage — S3-compatible, self-hosted, handles document files

### Expected Features

Features are organized in a strict dependency chain: Auth → Tier/ACL → Projects → Documents → AI Features. v1 delivers the SaaS foundation (table stakes); document and AI features follow in v2+.

See full details: [`FEATURES.md`](./FEATURES.md)

**Must have — SaaS foundation (v1):**
- Auth system (register, login, OAuth Google, password reset) — users expect this from any SaaS
- Email verification enforcement — required for account security and recovery
- Role-based access + tier/subscription system — enables monetization and feature gating
- Rate limiting (tier-aware, Redis-backed) — protects infrastructure from abuse
- Project/workspace CRUD with resource-level ACL (owner/editor/viewer) — core data model
- Admin dashboard (user management, tier configuration) — required for operations
- i18n (EN + VI minimum), dark/light theme, responsive UI — table stakes for modern SaaS
- Health check, CORS config, API versioning, structured error handling — infrastructure requirements

**Should have — document platform (v2):**
- Document upload (multi-format), in-app document viewer, document listing/management
- AI Q&A with citations, document summarization, cross-document search
- QuasarFlow integration (real, replacing v1 stubs)

**Differentiators — competitive advantage (v3+):**
- AI document editing (visual + chat) — PAPERY's primary differentiator
- Structure-preserving translation — unique capability; most tools lose formatting
- Multi-agent research workflows — end-to-end research → formatted report
- Template system + document generation

**Defer (explicitly not building):**
- Real-time collaborative editing (CRDT/OT complexity — not core value)
- Built-in LLM hosting (QuasarFlow handles all AI)
- Mobile native app (responsive web covers mobile use cases)
- Version control for documents (complex, low ROI for v1-v2)

### Architecture Approach

PAPERY follows the **"AI-Delegated Layered Monolith"** pattern: a single FastAPI backend organized in strict layers (Router → Service → CRUD → Schema → Model) with a clean API contract to QuasarFlow for all AI processing. The critical addition over v0 is the **Service Layer** — where business logic, cross-resource operations, and QuasarFlow delegation live. Frontend is a Next.js 15 App Router application with locale-dynamic routing, BFF proxy for auth flows, and TanStack Query for server state. Infrastructure is PostgreSQL + Redis (three namespaces) + MinIO, all containerized with Docker Compose. Deployment splits: Vercel for frontend (zero-config Next.js), VPS + Docker Compose for backend (full control).

See full details: [`ARCHITECTURE.md`](./ARCHITECTURE.md)

**Major components:**
1. **Next.js Frontend** — UI rendering, client routing, i18n, auth cookie management, BFF proxy
2. **FastAPI Application Layer** — API routers, auth/permissions (Depends chain), Service Layer (business logic + AI delegation), CRUD layer (fastcrud + SQLAlchemy async)
3. **Schema Layer (Pydantic v2)** — strict read/create/update/internal separation; validation boundaries between layers
4. **Data & Infrastructure Layer** — PostgreSQL (primary store), Redis (cache + queue + rate limit), MinIO (file storage), ARQ Worker (background tasks)
5. **QuasarFlow Client (services/quasarflow/)** — typed HTTP client abstracting all AI API calls; starts as stub, swapped with real implementation in v2
6. **AI Action Executor (services/ai_action/)** — maps structured QuasarFlow results into concrete CRUD operations

### Critical Pitfalls

Derived from v0 post-mortem and SaaS security best practices. Full list in [`PITFALLS.md`](./PITFALLS.md).

1. **JWT in response body instead of HttpOnly cookie** (Critical / PIT-02) — store tokens ONLY in HttpOnly, Secure, SameSite=Lax cookies; never expose to JavaScript. v0 sent refresh tokens in response body.
2. **Migrations gitignored** (Critical / PIT-07) — migration files are code; commit and review them. CI must run `alembic check`. v0 had `migrations/versions/` in `.gitignore`.
3. **Skipping the Service Layer** (High / PIT-05) — establish Router → Service → CRUD from the first endpoint. v0 had business logic directly in routers; this becomes a major refactor at scale.
4. **i18n as afterthought** (Medium / PIT-11) — set up `next-intl` before writing the first UI component; every visible string through `t()` from day one. Retrofitting is extremely expensive.
5. **Synchronous AI calls in request path** (High / PIT-06) — all QuasarFlow calls must use background tasks (ARQ) + SSE/polling; never block the HTTP request-response cycle for AI operations.
6. **Default passwords / dev config in production** (Critical / PIT-01, High / PIT-15) — `CHANGE_ME` placeholders only; fail-fast on startup if detected; separate Docker Compose configs for dev vs prod.
7. **Redis without namespace isolation** (Medium / PIT-08) — use separate DB numbers or strict key prefixes (`cache:`, `queue:`, `rl:`); v0 used a single namespace causing key collision risk.

---

## Implications for Roadmap

Based on research, the build order is strictly dependency-driven. The SaaS foundation must be complete before any document or AI features are built, because every downstream feature depends on auth, tiers, ACL, and projects.

### Phase 1: Backend Foundation
**Rationale:** Zero dependencies — this is the base layer everything else builds on. Establishes infrastructure, security patterns, and data models correctly from day one.
**Delivers:** Docker Compose stack (PostgreSQL + Redis + MinIO), SQLAlchemy models with SoftDeleteMixin + dual-ID strategy, Pydantic schemas (Read/Create/Update/Internal), core config (Pydantic Settings), JWT security (HttpOnly cookies), core DB/Redis/MinIO clients, ARQ worker setup.
**Addresses:** Auth system, infrastructure (FEATURES.md §1.1)
**Avoids:** PIT-01 (default passwords), PIT-02 (JWT in body), PIT-07 (migrations gitignored), PIT-08 (Redis namespaces), PIT-13 (soft delete inconsistency), PIT-15 (dev config in prod), PIT-16 (no health checks)

### Phase 2: Auth & Tier System
**Rationale:** Auth is the prerequisite for every other backend feature. Tier and permission systems must be designed before any resource endpoints, or they will need to be retrofitted.
**Delivers:** Registration/login/logout/OAuth endpoints, email verification (enforced), JWT rotation + Redis blacklist, RBAC (superuser + regular), tier model + rate limit model, centralized feature flags (tier-based), admin endpoints for tier management.
**Addresses:** Auth, tier/subscription, rate limiting (FEATURES.md §1.1)
**Avoids:** PIT-03 (missing email verification), PIT-04 (permissive CORS), PIT-05 (service layer — establish pattern here), PIT-12 (tier without feature flags), PIT-14 (monolithic admin panel)

### Phase 3: Project System & ACL
**Rationale:** Projects are the top-level container for all user data. ACL must be built before documents and chat, as both inherit the same permission model.
**Delivers:** Project CRUD endpoints, resource-level ACL model (AccessControl table), ACL management endpoints, permission check Depends() chain (JWT → role → tier → ACL), QuasarFlow client stub (typed interface, mock responses).
**Addresses:** Project/workspace CRUD, resource-level permissions (FEATURES.md §1.1)
**Uses:** Service Layer pattern established in Phase 2 (STACK.md)
**Implements:** Tiered SaaS with ACL-Based Access Control (ARCHITECTURE.md Pattern 3)

### Phase 4: Frontend Foundation
**Rationale:** With backend API stable (Phases 1-3), frontend can be built in parallel. Foundational setup (i18n, auth, routing, HTTP client) must precede all UI features.
**Delivers:** Next.js 15 App Router with locale-dynamic routing (`[locale]/(auth)`, `[locale]/(protect)`, `[locale]/(home)`), edge middleware (auth + locale), HTTP client (`lib/http.ts`), TanStack Query setup, Zustand stores (auth, user, theme), BFF route handlers (auth proxy), auth pages (login, register, forgot-password), layout + shadcn/ui theme system.
**Addresses:** i18n (EN+VI), responsive UI, dark/light theme (FEATURES.md §1.1)
**Avoids:** PIT-09 (no server state management — TanStack Query from day one), PIT-10 (Zustand sprawl — 3-5 stores max), PIT-11 (i18n afterthought — next-intl before first component)

### Phase 5: Dashboard & Admin UI
**Rationale:** Core user-facing flows (project management) and operator tooling (admin panel) complete the v1 product.
**Delivers:** Dashboard (project list, create/edit project, ACL management), admin panel (separate route group `/[locale]/admin/`), user management, tier configuration UI, Zod schemas for all API contracts.
**Addresses:** Admin dashboard, project system UI (FEATURES.md §1.1)
**Implements:** Separation of admin vs user route groups (ARCHITECTURE.md, avoids Anti-Pattern 3)

### Phase 6: Document System
**Rationale:** Documents depend on projects + ACL (Phase 3) and frontend foundation (Phase 4). This phase establishes the document data model and storage integration.
**Delivers:** Document upload (multipart POST → MIME validation → MinIO), document model + ACL entries, document listing/management UI, basic document viewer, presigned URL flow (client uploads directly to MinIO).
**Addresses:** Document upload, document listing/management (FEATURES.md §1.2)
**Uses:** MinIO S3-compatible SDK, ARQ background tasks for async processing (STACK.md §1.3)

### Phase 7: AI Integration (QuasarFlow)
**Rationale:** Requires stable document model (Phase 6) and QuasarFlow API to be ready. The stub interface from Phase 3 is replaced with a real implementation.
**Delivers:** Real QuasarFlow client implementation, AI action executor, chat session/message endpoints, chat UI (three-panel layout), SSE streaming for AI responses, AI Q&A with citations, document summarization, citation panel (click → jump to source).
**Addresses:** AI Q&A, citations, summarization (FEATURES.md §1.2)
**Avoids:** PIT-06 (synchronous AI calls — SSE + background tasks)
**Implements:** AI Service Delegation / Action Executor pattern (ARCHITECTURE.md Pattern 1)

### Phase 8: Advanced AI Features
**Rationale:** Built on a proven AI integration layer (Phase 7). These are PAPERY's primary competitive differentiators.
**Delivers:** Structure-preserving document translation, AI document editing (visual + chat commands), multi-agent research workflows → formatted reports, template system + document generation, cross-document analysis.
**Addresses:** All differentiator features (FEATURES.md §1.3)

---

### Phase Ordering Rationale

- **Phases 1-3 before anything else:** Authentication, authorization, tiers, and ACL are load-bearing infrastructure. Every feature above depends on them. Getting these wrong means rebuilding from the middle.
- **Phase 4 can overlap Phase 3:** Once the backend API contract (OpenAPI) is agreed upon, frontend work can proceed in parallel. BFF proxy and auth flows require only Phase 2 completion.
- **Phase 6 before Phase 7:** The document data model and storage integration must be stable before AI features can reference documents. QuasarFlow integration requires real document refs to be meaningful.
- **Phase 7 is decoupled by design:** The stub client (Phase 3) allows Phases 1-6 to ship without AI features. Phase 7 swaps the stub — no other code changes.
- **Phase 8 last:** Advanced AI features are high-complexity, high-value — they should be built on a proven document + AI integration foundation, not rushed in early.

---

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 7 (AI Integration):** QuasarFlow API contract needs formal specification before implementation. SSE streaming patterns in FastAPI + Next.js need validation. Circuit-breaker library choice (tenacity? custom?) needs evaluation.
- **Phase 6 (Document System):** Document viewer implementation is high-complexity — PDF.js integration, per-format rendering strategies, and streaming large files need dedicated research.
- **Phase 8 (Advanced AI):** Multi-agent workflow orchestration patterns and template engine selection are unresolved. Needs dedicated research sprint when Phase 7 is stable.

Phases with standard patterns (lower research risk):
- **Phase 1 (Backend Foundation):** Well-documented — FastAPI + SQLAlchemy + Alembic + Docker Compose patterns are established. v0 provides strong prior art.
- **Phase 2 (Auth):** JWT + OAuth2 patterns are well-documented in FastAPI ecosystem. BFF cookie pattern is established.
- **Phase 4 (Frontend Foundation):** Next.js 15 App Router + next-intl + TanStack Query + shadcn/ui are all well-documented with active communities.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Proven in v0 + verified against 2025-2026 ecosystem. Key upgrades (TanStack Query v5, ARQ, fastcrud) are well-documented. |
| Features | HIGH | Competitive analysis + v0 learning. Feature dependency tree is well-understood. |
| Architecture | HIGH | Industry-standard patterns (Service Layer, Layered Monolith, ACL). v0 validates the base approach; v1 adds the missing Service Layer. |
| Pitfalls | HIGH | Majority sourced from v0 post-mortem (concrete, already encountered). Security pitfalls validated against FastAPI/Next.js community. |

**Overall confidence:** HIGH

### Gaps to Address

- **QuasarFlow API contract:** PAPERY's entire AI integration depends on QuasarFlow's API schema. This contract must be formally defined before Phase 7 begins. Risk: if QuasarFlow changes structure, PAPERY's action executor layer needs updates. Mitigation: freeze contract early, version it.
- **Document viewer depth:** The "document viewer" feature is high-complexity with significant variance depending on format (PDF vs DOCX vs Excel). Exact scope and library choices need a dedicated research spike during Phase 6 planning.
- **Deployment split (Vercel + VPS):** The frontend-on-Vercel + backend-on-VPS split adds deployment complexity (CORS, cookie domains, secrets management). Validate the exact deployment topology before Phase 4 ships to production.
- **MinIO vs managed S3:** MinIO is Medium confidence (good for self-host; could switch to AWS S3 in production). The decision point is at Phase 6 deployment — evaluate based on operational overhead vs cost.

---

## Sources

### Primary (HIGH confidence)
- `PAPERY v0 codebase` (`.planning/codebase/`) — architecture decisions, post-mortem, confirmed pitfalls
- FastAPI official documentation — dependency injection, async patterns, OAuth2
- SQLAlchemy 2.0 official documentation — async mapped columns, session management
- Next.js 15 official documentation — App Router, Server Components, middleware
- TanStack Query v5 official documentation — simplified API, TypeScript improvements

### Secondary (MEDIUM confidence)
- `.reference/open-notebook/` — document AI platform architecture patterns (reference only, not copied)
- ARQ documentation — async Redis queue patterns vs Celery
- fastcrud documentation — CRUD abstraction patterns for SQLAlchemy
- next-intl v4 documentation — App Router native i18n integration
- MinIO documentation — S3-compatible self-hosted storage

### Tertiary (LOW confidence)
- SaaS architecture community patterns — multi-tenant tier/ACL models, modular monolith patterns
- Industry references — Sam Newman (Modular Monolith), Martin Fowler (Service Layer pattern)

---

*Research completed: 2026-04-01*
*Ready for roadmap: yes*
