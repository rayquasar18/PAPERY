# Requirements: PAPERY

**Defined:** 2026-04-01
**Core Value:** Users can work with any document intelligently — ask questions, get accurate cited answers, and have AI directly modify their documents — through a polished, production-ready SaaS platform.

## v1 Requirements

Requirements for initial release — SaaS foundation. Each maps to roadmap phases.

### Authentication

- [ ] **AUTH-01**: User can sign up with email and password
- [ ] **AUTH-02**: User receives email verification after signup; account is restricted until verified
- [ ] **AUTH-03**: User can log in with email and password; receives JWT access + refresh tokens via HttpOnly cookies
- [ ] **AUTH-04**: User session persists across browser refresh via automatic token refresh
- [ ] **AUTH-05**: User can log out; tokens are blacklisted in Redis
- [ ] **AUTH-06**: User can reset password via secure time-limited email link
- [ ] **AUTH-07**: User can sign up / log in via Google OAuth
- [ ] **AUTH-08**: User can sign up / log in via GitHub OAuth
- [ ] **AUTH-09**: Refresh token rotation — each refresh issues new token pair and invalidates old

### User & Profile

- [ ] **USER-01**: User can view own profile (name, email, avatar, tier, created date)
- [ ] **USER-02**: User can edit own profile (display name, avatar)
- [ ] **USER-03**: User can change password (requires current password)
- [ ] **USER-04**: User can delete own account (soft delete with grace period)

### Tier & Permissions

- [ ] **TIER-01**: System supports multiple tiers (free, pro, enterprise) with configurable feature limits
- [ ] **TIER-02**: Each tier maps to feature flags (centralized, not hardcoded in business logic)
- [ ] **TIER-03**: Rate limiting is tier-aware — different limits per endpoint per tier
- [ ] **TIER-04**: Tier upgrades/downgrades update user permissions immediately
- [ ] **TIER-05**: Billing integration (Stripe) — user can subscribe, upgrade, downgrade, cancel
- [ ] **TIER-06**: Webhook handling for Stripe events (payment success, failure, cancellation)

### Admin Panel

- [ ] **ADMIN-01**: Superuser can view and search all users
- [ ] **ADMIN-02**: Superuser can activate/deactivate/ban user accounts
- [ ] **ADMIN-03**: Superuser can create/edit/delete tiers and their feature flags
- [ ] **ADMIN-04**: Superuser can create/edit/delete rate limit rules per tier per endpoint
- [ ] **ADMIN-05**: Superuser can view system configuration and modify runtime settings
- [ ] **ADMIN-06**: Admin panel is a separate route group with superuser-only middleware

### Project System

- [x] **PROJ-01**: User can create a project (name, description)
- [x] **PROJ-02**: User can view, edit, and soft-delete own projects
- [ ] **PROJ-03**: Project has ACL — owner, editor, viewer roles
- [ ] **PROJ-04**: Owner can invite users to project via invite link or email
- [ ] **PROJ-05**: Owner can change member roles or remove members
- [ ] **PROJ-06**: User can list and search own projects (owned + shared with)

### Backend Infrastructure

- [x] **INFRA-01**: FastAPI backend with layered architecture (Router → Service → CRUD → Schema → Model)
- [x] **INFRA-02**: PostgreSQL 16+ with SQLAlchemy 2.0 async ORM and Alembic migrations (committed to git)
- [x] **INFRA-03**: Redis 7+ with namespace isolation (cache db=0, queue db=1, rate_limit db=2)
- [x] **INFRA-04**: MinIO file storage with presigned URL support
- [ ] **INFRA-05**: ARQ background task worker for async processing
- [ ] **INFRA-06**: Structured error handling with custom exception hierarchy and consistent API error format
- [ ] **INFRA-07**: API versioning at /api/v1/ with OpenAPI auto-documentation
- [ ] **INFRA-08**: Health check endpoints (/health for liveness, /ready for deep checks)
- [x] **INFRA-09**: Environment-based configuration (Pydantic Settings) with startup validation (reject placeholder values)
- [ ] **INFRA-10**: CORS configuration — explicit origin allowlist from environment, never wildcard in production
- [x] **INFRA-11**: Docker Compose development environment (backend, worker, PostgreSQL, Redis, MinIO)
- [ ] **INFRA-12**: Production-optimized Docker images (multi-stage build, no --reload, proper workers)
- [ ] **INFRA-13**: Verify-only CI pipeline via GitHub Actions (lint, type check, test, build) with deployment automation explicitly deferred
- [x] **INFRA-14**: Dual ID strategy — int id (internal) + UUID (public API)
- [x] **INFRA-15**: Soft delete mixin on all core entities (never hard delete)

### Frontend Foundation

- [ ] **FRONT-01**: Next.js 16 + React 19 App Router setup with TypeScript strict mode
- [ ] **FRONT-02**: Internationalization from day one via next-intl (EN + VI minimum)
- [ ] **FRONT-03**: Dark/light/system theme with user preference persistence
- [ ] **FRONT-04**: Responsive layout (mobile + tablet + desktop) via Tailwind CSS
- [ ] **FRONT-05**: TanStack Query v5 for server state management (caching, background refetch, mutations)
- [ ] **FRONT-06**: Zustand v5 for client-only state (UI preferences, sidebar state) — max 3-5 stores
- [ ] **FRONT-07**: Zod v4 for runtime validation of API responses and form inputs
- [ ] **FRONT-08**: Auth middleware — cookie-based JWT, auto-refresh on 401, route protection
- [ ] **FRONT-09**: shadcn/ui component library setup (Radix UI primitives, accessible)
- [ ] **FRONT-10**: HTTP client with typed API calls, Bearer token injection, error normalization
- [ ] **FRONT-11**: React Hook Form + Zod resolver for all form handling

### QuasarFlow Integration

- [ ] **QFLOW-01**: Abstract QuasarFlow client interface (base class with typed methods)
- [ ] **QFLOW-02**: Mock/stub implementation for development (returns realistic fake data)
- [ ] **QFLOW-03**: Error handling patterns — timeout, retry, circuit breaker
- [ ] **QFLOW-04**: Async pattern — AI calls go through ARQ task queue, frontend polls or SSE for results

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Document System

- **DOC-01**: User can upload documents (PDF, DOCX, XLSX, PPTX, CSV, TXT, Markdown)
- **DOC-02**: Document viewer with in-app rendering per format
- **DOC-03**: Document listing, search, and management within projects
- **DOC-04**: Background document parsing pipeline (text extraction, metadata)

### AI Q&A & Research

- **AIQ-01**: User can ask questions about uploaded documents
- **AIQ-02**: AI responses include precise citations to source material
- **AIQ-03**: Interactive citation panel — click to jump to source location
- **AIQ-04**: Document summarization and key takeaway extraction
- **AIQ-05**: Cross-document analysis (patterns, contradictions, connections)

### AI Document Editing

- **EDIT-01**: AI can suggest edits directly in visual editor (track changes style)
- **EDIT-02**: User can give chat commands to modify documents ("rewrite section X")
- **EDIT-03**: Full undo/redo for all AI edits
- **EDIT-04**: Structure-preserving operations (maintain formatting, layout, tables)

### Translation

- **TRANS-01**: Translate entire documents across languages
- **TRANS-02**: Preserve original structure and formatting during translation

### Advanced Features

- **ADV-01**: Multi-agent research workflows (question → research → polished report)
- **ADV-02**: Template system for formatted document generation
- **ADV-03**: Community marketplace for templates
- **ADV-04**: Knowledge graph and topic clustering

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time collaborative editing (Google Docs CRDT/OT) | Extremely complex, not core for v1-v2. Single-user-at-a-time is sufficient |
| Built-in LLM hosting | All AI logic handled by QuasarFlow. PAPERY is the consumer |
| Mobile native app | Web-first with responsive design. Native app only if demand proves it |
| Offline mode | Document AI requires internet. Don't over-engineer offline sync |
| Social features (comments, likes, followers) | Not a social platform. Collaboration via project ACL |
| Document version control (full git-style) | Complex, low ROI. Simple undo/redo is sufficient |
| 2FA (two-factor authentication) | Nice-to-have for v2, not blocking for launch |

## Traceability

Complete mapping of all v1 requirements to roadmap phases.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 3: Authentication — Core Flows | ⬜ Not started |
| AUTH-02 | Phase 3: Authentication — Core Flows | ⬜ Not started |
| AUTH-03 | Phase 3: Authentication — Core Flows | ⬜ Not started |
| AUTH-04 | Phase 3: Authentication — Core Flows | ⬜ Not started |
| AUTH-05 | Phase 3: Authentication — Core Flows | ⬜ Not started |
| AUTH-06 | Phase 4: Authentication — Advanced & Password | ⬜ Not started |
| AUTH-07 | Phase 4: Authentication — Advanced & Password | ⬜ Not started |
| AUTH-08 | Phase 4: Authentication — Advanced & Password | ⬜ Not started |
| AUTH-09 | Phase 3: Authentication — Core Flows | ⬜ Not started |
| USER-01 | Phase 5: User Profile & Account Management | ⬜ Not started |
| USER-02 | Phase 5: User Profile & Account Management | ⬜ Not started |
| USER-03 | Phase 4: Authentication — Advanced & Password | ⬜ Not started |
| USER-04 | Phase 5: User Profile & Account Management | ⬜ Not started |
| TIER-01 | Phase 6: Tier System & Permissions | ⬜ Not started |
| TIER-02 | Phase 6: Tier System & Permissions | ⬜ Not started |
| TIER-03 | Phase 6: Tier System & Permissions | ⬜ Not started |
| TIER-04 | Phase 6: Tier System & Permissions | ⬜ Not started |
| TIER-05 | Phase 6: Tier System & Permissions | ⬜ Not started |
| TIER-06 | Phase 6: Tier System & Permissions | ⬜ Not started |
| ADMIN-01 | Phase 7: Admin Panel (Backend) | ⬜ Not started |
| ADMIN-02 | Phase 7: Admin Panel (Backend) | ⬜ Not started |
| ADMIN-03 | Phase 7: Admin Panel (Backend) | ⬜ Not started |
| ADMIN-04 | Phase 7: Admin Panel (Backend) | ⬜ Not started |
| ADMIN-05 | Phase 7: Admin Panel (Backend) | ⬜ Not started |
| ADMIN-06 | Phase 7: Admin Panel (Backend) | ⬜ Not started |
| PROJ-01 | Phase 8: Project System & ACL | ✅ Complete (08-01) |
| PROJ-02 | Phase 8: Project System & ACL | ✅ Complete (08-01) |
| PROJ-03 | Phase 8: Project System & ACL | ⬜ Not started |
| PROJ-04 | Phase 8: Project System & ACL | ⬜ Not started |
| PROJ-05 | Phase 8: Project System & ACL | ⬜ Not started |
| PROJ-06 | Phase 8: Project System & ACL | ⬜ Not started |
| INFRA-01 | Phase 1: Backend Core Infrastructure | ⬜ Not started |
| INFRA-02 | Phase 1: Backend Core Infrastructure | ⬜ Not started |
| INFRA-03 | Phase 1: Backend Core Infrastructure | ⬜ Not started |
| INFRA-04 | Phase 1: Backend Core Infrastructure | ⬜ Not started |
| INFRA-05 | Phase 10: Dashboard, Admin UI & QFlow Stubs | ⬜ Not started |
| INFRA-06 | Phase 2: Error Handling, API Structure & Health | ⬜ Not started |
| INFRA-07 | Phase 2: Error Handling, API Structure & Health | ⬜ Not started |
| INFRA-08 | Phase 2: Error Handling, API Structure & Health | ⬜ Not started |
| INFRA-09 | Phase 1: Backend Core Infrastructure | ⬜ Not started |
| INFRA-10 | Phase 2: Error Handling, API Structure & Health | ⬜ Not started |
| INFRA-11 | Phase 1: Backend Core Infrastructure | ⬜ Not started |
| INFRA-12 | Phase 2: Error Handling, API Structure & Health | ⬜ Not started |
| INFRA-13 | Phase 10: Dashboard, Admin UI & QFlow Stubs | ⬜ Not started |
| INFRA-14 | Phase 1: Backend Core Infrastructure | ⬜ Not started |
| INFRA-15 | Phase 1: Backend Core Infrastructure | ⬜ Not started |
| FRONT-01 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-02 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-03 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-04 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-05 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-06 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-07 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-08 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-09 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-10 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| FRONT-11 | Phase 9: Frontend Foundation & Auth UI | ⬜ Not started |
| QFLOW-01 | Phase 10: Dashboard, Admin UI & QFlow Stubs | ⬜ Not started |
| QFLOW-02 | Phase 10: Dashboard, Admin UI & QFlow Stubs | ⬜ Not started |
| QFLOW-03 | Phase 10: Dashboard, Admin UI & QFlow Stubs | ⬜ Not started |
| QFLOW-04 | Phase 10: Dashboard, Admin UI & QFlow Stubs | ⬜ Not started |

**Coverage:**
- v1 requirements: 61 total
- Mapped to phases: 61 ✅
- Unmapped: 0

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 — traceability populated after roadmap creation*
