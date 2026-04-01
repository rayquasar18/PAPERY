# Architecture Research

**Domain:** AI-Powered Document Intelligence SaaS Platform
**Researched:** 2026-04-01
**Confidence:** HIGH

---

## Standard Architecture

### System Overview

PAPERY's architecture follows the **"AI-Delegated Layered Monolith"** pattern — a full-stack SaaS platform where the core application handles user management, document storage, permissions, and UI rendering, while AI/LLM processing is fully delegated to an external service (QuasarFlow) via API.

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                             │
│                 Next.js 15 (React 19, TypeScript)                   │
│    App Router + SSR  |  Zustand  |  next-intl  |  Shadcn/ui        │
│    BFF Route Handlers  |  Zod Validation  |  Edge Middleware        │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTPS/REST (JSON)
                            │ JWT Cookies (access + refresh)
┌───────────────────────────▼─────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
│                   FastAPI (Python 3.12, async)                      │
│                                                                     │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ API      │  │ Auth &       │  │ Service  │  │ QuasarFlow    │   │
│  │ Routers  │  │ Permissions  │  │ Layer    │  │ Client        │   │
│  │ (v1/)    │  │ (JWT+ACL)    │  │ (Biz)   │  │ (AI Proxy)    │   │
│  └────┬─────┘  └──────┬───────┘  └────┬─────┘  └──────┬────────┘   │
│       │               │               │               │            │
│  ┌────▼───────────────▼───────────────▼────┐     ┌────▼─────────┐  │
│  │         CRUD / Repository Layer         │     │  External    │  │
│  │     (fastcrud + SQLAlchemy 2.0 async)   │     │  AI Service  │  │
│  └─────────────────────┬───────────────────┘     │  (QuasarFlow)│  │
│                        │                          └──────────────┘  │
├────────────────────────┼────────────────────────────────────────────┤
│                  DATA & INFRASTRUCTURE LAYER                        │
│                                                                     │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌────────────────┐   │
│  │PostgreSQL │  │  Redis     │  │  MinIO    │  │  ARQ Worker   │   │
│  │(Primary   │  │(Cache +   │  │(S3-compat │  │(Background    │   │
│  │ Store)    │  │ Queue +   │  │ File      │  │ Tasks)        │   │
│  │           │  │ Rate Lmt) │  │ Storage)  │  │               │   │
│  └───────────┘  └───────────┘  └───────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                                        │
                                               ┌────────▼────────┐
                                               │   QuasarFlow    │
                                               │   AI Service    │
                                               │   (External)    │
                                               │                 │
                                               │  - LLM routing  │
                                               │  - RAG pipeline │
                                               │  - Embeddings   │
                                               │  - Agents       │
                                               └─────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Next.js Frontend** | UI rendering, client routing, i18n, auth cookie management, BFF proxy | App Router with locale-dynamic segments, Zustand stores, Zod validation |
| **API Routers** | HTTP interface, request validation, response formatting, API versioning | FastAPI routers per resource (`/api/v1/users`, `/api/v1/projects`, etc.) |
| **Auth & Permissions** | JWT verification, role-based access, resource-level ACL, rate limiting | FastAPI `Depends()` chain: JWT decode -> user load -> ACL check -> rate limit |
| **Service Layer** | Business logic orchestration, workflow coordination, AI delegation | Python async service classes coordinating CRUD + external API calls |
| **QuasarFlow Client** | AI API abstraction, request/response transformation, retry/circuit-breaker | Typed HTTP client wrapping QuasarFlow REST API with error mapping |
| **CRUD Layer** | Database operations, query building, pagination | fastcrud generics wrapping SQLAlchemy async queries |
| **Schema Layer** | Data validation, serialization boundaries (Read/Create/Update/Internal) | Pydantic v2 models with strict separation of public vs internal fields |
| **Model Layer** | ORM definitions, table relationships, shared mixins | SQLAlchemy 2.0 declarative models with UUID, Timestamp, SoftDelete mixins |
| **PostgreSQL** | Primary persistent storage, relational data, ACID transactions | Async via asyncpg, Alembic migrations, dual ID strategy (int + UUID) |
| **Redis** | Caching, task queue broker, rate limit counters, token blacklist | Three logical namespaces (cache, queue, rate_limit) on single instance |
| **MinIO** | Document file storage, presigned URL generation | S3-compatible API, UUID-keyed file paths, MIME type validation |
| **ARQ Worker** | Background job processing (doc parsing, email, async operations) | Redis-backed async worker with task functions defined in core/worker/ |
| **QuasarFlow (External)** | All AI/LLM processing: Q&A, RAG, embeddings, agents, translation | Separate service with its own infra; PAPERY is the "action executor" |

---

## Recommended Project Structure

```
PAPERY/
├── backend/                          # Python/FastAPI backend service
│   ├── src/
│   │   ├── app/
│   │   │   ├── main.py              # FastAPI app entry point
│   │   │   ├── api/                  # HTTP interface layer
│   │   │   │   ├── dependencies.py   # Auth, DB session, rate limit injection
│   │   │   │   └── v1/              # Versioned endpoints (one file per resource)
│   │   │   ├── services/            # Business logic + AI delegation (KEY LAYER)
│   │   │   │   ├── quasarflow/      # QuasarFlow API client + DTOs
│   │   │   │   ├── document/        # Document processing orchestration
│   │   │   │   └── ai_action/       # AI result -> action execution mapping
│   │   │   ├── crud/                # fastcrud repository layer
│   │   │   ├── schemas/             # Pydantic v2 schemas (Read/Create/Update/Internal)
│   │   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── core/                # Infrastructure (config, security, DB, Redis, MinIO)
│   │   │   │   ├── db/              # Database, Redis, MinIO clients + mixins
│   │   │   │   ├── utils/           # Cache, queue, rate limit, email helpers
│   │   │   │   ├── worker/          # ARQ background task definitions
│   │   │   │   ├── exceptions/      # Custom HTTP exceptions
│   │   │   │   └── middleware/       # HTTP cache, logging middleware
│   │   │   └── middleware/           # Request-level middleware
│   │   ├── migrations/              # Alembic async migrations
│   │   └── scripts/                 # Bootstrap scripts (superuser, tiers)
│   ├── tests/                       # pytest test suite
│   ├── Dockerfile                   # API server container
│   ├── Dockerfile.worker            # Background worker container
│   └── docker-compose.yml           # Full local stack
│
├── frontend/                        # Next.js 15 frontend application
│   └── src/
│       ├── app/                     # App Router (locale-dynamic)
│       │   ├── [locale]/
│       │   │   ├── (home)/          # Public marketing (landing, pricing, FAQ)
│       │   │   ├── (auth)/          # Unauthenticated routes (login, register)
│       │   │   └── (protect)/       # Authenticated routes (dashboard, chat, documents)
│       │   └── api/                 # BFF route handlers + client API modules
│       ├── components/              # Shared UI components
│       ├── hooks/                   # Custom React hooks (CRUD, scroll, etc.)
│       ├── lib/                     # Pure utilities (HTTP client, token, error)
│       ├── store/                   # Zustand global state
│       ├── schemas/                 # Zod validation schemas
│       ├── context/                 # React context providers (auth, user, theme)
│       └── locale/                  # i18n translation files (en, vi)
│
├── .planning/                       # AI planning workspace (not shipped)
├── .reference/                      # Read-only reference repos (gitignored)
└── docs/                            # Project documentation
```

### Structure Rationale

- **`backend/src/app/services/`:** The critical new layer between routers and CRUD. This is where business logic lives — especially the QuasarFlow client abstraction and AI action execution. In v0, routers called CRUD directly; v1 needs this service layer for AI integration complexity.
- **`backend/src/app/services/quasarflow/`:** Isolated client module for external AI API. Contains typed DTOs, HTTP client, retry logic, error mapping. Changing AI providers = changing only this module.
- **`backend/src/app/services/ai_action/`:** Maps AI results (from QuasarFlow) into concrete CRUD operations. "Add paragraph to document" AI result becomes actual document mutation here.
- **`frontend/src/app/[locale]/(protect)/`:** All authenticated features grouped. Chat interface is the most complex UI (three-panel layout). Document viewer and dashboard are simpler.
- **`frontend/src/app/api/`:** BFF (Backend-for-Frontend) layer. Auth-related routes proxy through here for cookie management. Other API calls go directly to backend.

---

## Architectural Patterns

### Pattern 1: AI Service Delegation (Action Executor Pattern)

**What:** PAPERY delegates all AI/LLM processing to QuasarFlow via API. QuasarFlow returns structured results (not raw LLM text). PAPERY interprets these results and executes concrete actions (CRUD operations, document mutations, response rendering).

**When to use:** When AI logic is complex enough to warrant a separate service, or when the AI service is developed independently and serves multiple consumers.

**Trade-offs:**
- (+) Clean separation of concerns — PAPERY team focuses on UX/platform, QuasarFlow team on AI
- (+) Independent scaling — AI workloads scale separately from CRUD operations
- (+) AI provider flexibility — QuasarFlow can switch LLM providers without PAPERY changes
- (+) v1 can ship without AI features being ready (stub the interface)
- (-) Network latency added for every AI call
- (-) Error handling complexity (timeout, retry, circuit breaker needed)
- (-) Debugging spans two services

**Data Flow:**
```
User asks question about document
    |
    v
Frontend --> PAPERY Backend
    |
    v
Service Layer: Build QuasarFlow request
    - Attach document context (file refs, extracted text)
    - Attach user preferences (language, tier limits)
    - Attach action schema (what PAPERY can execute)
    |
    v
QuasarFlow API: AI processes request
    - RAG pipeline: retrieves relevant chunks
    - LLM generates answer with citations
    - Returns structured result (answer, citations, suggested actions)
    |
    v
PAPERY Service Layer: Execute actions
    - Store chat message with citations (CRUD)
    - Update document if AI suggested edits (CRUD)
    - Log usage for rate limiting (Redis)
    |
    v
Frontend: Render response with citations
```

**Interface Contract (QuasarFlow Client):**
```python
# backend/src/app/services/quasarflow/client.py
class QuasarFlowClient:
    """Typed HTTP client for QuasarFlow AI Service API."""

    async def ask_document(
        self,
        document_refs: list[DocumentRef],
        question: str,
        conversation_history: list[Message],
        user_context: UserContext,
    ) -> AskResult:
        """Q&A with document citations."""
        ...

    async def suggest_edits(
        self,
        document_ref: DocumentRef,
        instruction: str,
        user_context: UserContext,
    ) -> EditSuggestion:
        """AI-suggested document edits."""
        ...

    async def translate_document(
        self,
        document_ref: DocumentRef,
        target_language: str,
        preserve_structure: bool,
    ) -> TranslationResult:
        """Structure-preserving document translation."""
        ...
```

### Pattern 2: Layered Monolith with Service Layer

**What:** A single deployable backend application organized in strict layers with one-way dependency flow. The key addition for v1 is a proper **Service Layer** between API routers and CRUD.

**When to use:** Always, for a SaaS product at this scale. The layers provide testability, separation of concerns, and a clear path to extraction if needed later.

**Trade-offs:**
- (+) Single deployment unit — simple to deploy, debug, and reason about
- (+) Shared database transaction context across operations
- (+) Layers can be extracted to separate services later (modular monolith -> microservices)
- (-) All code ships together — one bad deploy affects everything
- (-) Requires discipline to maintain layer boundaries

**Layer Dependency Flow (v1 — adds Service Layer to v0):**
```
Router (API Layer)
    |  depends on
    v
Dependencies (Auth, DB Session, Rate Limit)
    |  injected into
    v
Service Layer (NEW in v1 — business logic, AI delegation)
    |  depends on
    v
CRUD Layer (fastcrud repository operations)
    |  depends on
    v
Schema Layer (Pydantic v2 — validation boundaries)
    |  used by
    v
Model Layer (SQLAlchemy ORM — DB tables)
    |  persisted in
    v
Database (PostgreSQL via asyncpg)
```

**Import Rules (strict one-way flow):**
```
api/v1/     --> dependencies, services/, schemas/
services/   --> crud/, schemas/, models/, core/, quasarflow/
crud/       --> models/, schemas/, core/db/
models/     --> core/db/models.py only
schemas/    --> nothing internal (pure Pydantic)
core/       --> core/ siblings only
```

### Pattern 3: Tiered SaaS with ACL-Based Access Control

**What:** A hybrid permission system combining role-based tiers (free/pro/enterprise) with resource-level ACL (per-project, per-document access control).

**When to use:** SaaS products where both subscription-level features AND resource-level sharing/collaboration exist.

**Trade-offs:**
- (+) Fine-grained control — tier limits features/rates, ACL limits resource access
- (+) Collaboration-ready — ACL supports sharing resources between users
- (+) Admin manageability — tiers managed globally, ACL managed per-resource
- (-) Two permission systems to check on every request
- (-) More complex query patterns (join user -> tier -> rate_limit -> ACL)

**Permission Check Flow:**
```
Incoming Request
    |
    v
[1] JWT Verification (is token valid?)
    |
    v
[2] User Loading (get user from DB, check is_deleted, email_verified)
    |
    v
[3] Role Check (is_superuser? -> bypass all below)
    |
    v
[4] Tier Check (user.tier -> rate limits, feature gates)
    |   - Check rate limit counter in Redis for this endpoint + tier
    |   - Check feature availability for this tier
    |
    v
[5] ACL Check (does user have permission for this specific resource?)
    |   - Query access_control table: (user_id, resource_uuid, resource_type)
    |   - Permission types: owner, editor, viewer
    |
    v
[6] Operation proceeds
```

**Data Model:**
```
Tier
  id, name, description
  e.g.: {name: "free", ...}, {name: "pro", ...}, {name: "enterprise", ...}

RateLimit
  id, tier_id (FK), path, limit, period
  e.g.: {tier: "free", path: "/api/v1/chat", limit: 10, period: "hour"}

User
  id, uuid, tier_id (FK), is_superuser, email, ...

AccessControl
  id, user_id (FK), resource_uuid, resource_type, permission_type
  e.g.: {user: 1, resource_uuid: "proj-xxx", resource_type: "project", permission: "owner"}
```

### Pattern 4: Dual ID Strategy

**What:** Every entity has two identifiers: an auto-increment `id` (integer, internal) and a random `uuid` (UUID4, public API). Internal operations use `id` for performance; all public API responses expose only `uuid`.

**When to use:** Any public-facing API where enumeration attacks are a concern.

**Trade-offs:**
- (+) Prevents sequential ID enumeration (can't guess `/users/2` from `/users/1`)
- (+) Integer PKs are faster for joins and indexes
- (+) UUIDs are safe to expose in URLs, logs, error messages
- (-) Slightly more storage per row (extra UUID column)
- (-) Need to map UUID -> internal ID on every public API request

---

## Data Flow

### Request Flow (Standard CRUD)

```
User Action (click, form submit)
    |
    v
React Component --> Custom Hook (use-create, use-get, etc.)
    |
    v
HTTP Client (lib/http.ts — axios with auto Bearer token)
    |
    v
[Optional] BFF Route Handler (for auth-sensitive ops like login/logout)
    |
    v
FastAPI Router (/api/v1/resource)
    |
    v
Dependencies Layer:
    - get_current_user() (JWT verify -> UserReadInternal)
    - rate_limiter() (Redis counter check)
    - async_get_db() (AsyncSession from pool)
    |
    v
Service Layer (business logic, validation beyond schema)
    |
    v
CRUD Layer (fastcrud.create/get/update/delete)
    |
    v
PostgreSQL (asyncpg)
    |
    v
Response: Schema.Read -> JSON -> HTTP Client -> Zod validate -> Zustand store -> UI re-render
```

### Request Flow (AI-Powered Feature)

```
User asks question in chat UI
    |
    v
Frontend: POST /api/v1/chat_messages/ {content: "...", session_uuid: "..."}
    |
    v
PAPERY Backend:
    [1] Auth + ACL check (user can access this chat session?)
    [2] Rate limit check (user tier allows this request?)
    [3] Save user message to DB (ChatMessage CRUD)
    [4] Load conversation context (previous messages, document refs)
    |
    v
QuasarFlow Client:
    [5] POST quasarflow.com/api/v1/ask
        Body: {documents, question, history, config}
    [6] QuasarFlow: RAG pipeline + LLM processing
    [7] Returns: {answer, citations[], suggested_actions[]}
    |
    v
PAPERY Backend (Action Execution):
    [8] Save AI response as ChatMessage with citations
    [9] Execute any suggested_actions (e.g., highlight document sections)
    [10] Update usage counters in Redis
    |
    v
Frontend: Render answer with clickable citation links
```

### State Management

```
Server State (PostgreSQL)
    |
    v (fetched via REST API)
    |
Custom Hooks (use-get, use-gets, use-create, use-update, use-delete)
    |
    v (normalizes + validates via Zod)
    |
Zustand Stores (chat-list, project-list)
    |
    v (subscribe)
    |
React Components (re-render on store change)

---

React Context (non-API state):
    - AuthContext: user identity, login/logout
    - UserContext: user profile data
    - ThemeContext: light/dark/system
```

### Key Data Flows

1. **Document Upload Flow:** Client multipart POST -> Backend validates MIME -> MinIO stores file (UUID key) -> DB record created (Document model) -> ACL entry created -> [Future: ARQ worker triggers parsing -> QuasarFlow processes -> embeddings stored]

2. **Authentication Flow:** Login form -> BFF route handler -> Backend /auth/login -> JWT pair generated (access 30min + refresh 7d) -> Set as HTTP-only cookies -> Middleware auto-refreshes on 401 -> Redis token blacklist on logout

3. **AI Q&A Flow:** User question -> Backend loads context (docs, history) -> QuasarFlow API call -> Structured result (answer + citations) -> Backend saves + executes actions -> Frontend renders with citation links

4. **Tier-Gated Feature Flow:** Request arrives -> JWT decoded -> User loaded with tier -> Rate limit checked against tier rules in Redis -> Feature gate checked (tier.features) -> Proceed or 429/403

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Layered monolith is perfect. Single Docker Compose stack. PostgreSQL handles all queries. Redis handles rate limits + cache. MinIO handles file storage. |
| 1k-10k users | Add read replicas for PostgreSQL. Add Redis Cluster. Put Nginx/Caddy in front for TLS + static caching. Monitor ARQ worker queue depth — may need multiple workers. |
| 10k-100k users | Connection pooling critical (PgBouncer). Consider extracting QuasarFlow client calls to dedicated worker processes. Add CDN (Cloudflare) for frontend. Database: read-write split, table partitioning for chat_messages. |
| 100k+ users | Consider extracting document processing into its own service. Database sharding by project/tenant. Dedicated queue service (not just Redis). Load balancer for multiple backend instances. |

### Scaling Priorities

1. **First bottleneck: Database connections.** FastAPI async + SQLAlchemy async pool handles many concurrent requests, but PostgreSQL has a connection limit. Fix: PgBouncer (connection pooler) in front of PostgreSQL. Add early — it's transparent.

2. **Second bottleneck: Background worker throughput.** Document processing, email sending, and QuasarFlow callbacks compete for worker capacity. Fix: Scale ARQ workers horizontally (multiple Docker containers). Separate queues by priority (fast: email, slow: doc processing).

3. **Third bottleneck: QuasarFlow API latency.** AI calls are inherently slow (seconds, not milliseconds). Fix: Streaming responses (SSE), optimistic UI updates, background processing with webhook callbacks instead of synchronous waits.

4. **Fourth bottleneck: File storage I/O.** Large document uploads and downloads. Fix: Presigned URLs (MinIO generates URL, client uploads directly — bypasses backend). CDN for frequently accessed documents.

---

## Anti-Patterns

### Anti-Pattern 1: Embedding AI Logic in the Application Layer

**What people do:** Put LLM prompts, RAG retrieval, embedding generation, and agent orchestration directly in FastAPI route handlers or service layer.
**Why it's wrong:** AI logic evolves at a completely different pace than CRUD logic. Tight coupling means every AI experiment requires redeploying the entire platform. LLM dependencies (langchain, transformers, torch) bloat the backend image.
**Do this instead:** Delegate all AI to QuasarFlow via a clean API contract. PAPERY's service layer only knows how to call the QuasarFlow client and execute the structured results. If QuasarFlow is down, PAPERY still serves documents, chat history, and all non-AI features.

### Anti-Pattern 2: Skipping the Service Layer (Router -> CRUD Direct)

**What people do:** FastAPI routers call CRUD functions directly, putting business logic inline in route handlers.
**Why it's wrong:** Works fine for simple CRUD, but falls apart when operations span multiple resources, require external API calls, or need transaction coordination. Results in fat router files, duplicated logic, and untestable business rules.
**Do this instead:** Add a Service Layer between routers and CRUD. Routers handle HTTP concerns (request parsing, response formatting). Services handle business logic (permission checks beyond ACL, cross-resource operations, QuasarFlow calls, event emission). CRUD handles database queries only.

### Anti-Pattern 3: Monolithic Permission Checks

**What people do:** Check all permissions (auth, role, tier, rate limit, ACL) in a single massive dependency function.
**Why it's wrong:** Different endpoints need different permission combinations. A public endpoint needs no auth. An admin endpoint needs auth + superuser. A resource endpoint needs auth + ACL. Monolithic check forces all-or-nothing.
**Do this instead:** Compose permission checks as a chain of FastAPI `Depends()`:
- `get_current_user` — JWT only
- `get_current_superuser` — JWT + superuser
- `check_resource_acl(resource_type)` — JWT + ACL for specific resource
- `rate_limiter(path)` — tier-based rate limiting
Routers pick exactly the dependencies they need.

### Anti-Pattern 4: Synchronous AI Calls in Request Path

**What people do:** Call QuasarFlow API synchronously in the HTTP request-response cycle, making the user wait 5-30 seconds for an AI response.
**Why it's wrong:** Long-running requests tie up server connections, cause timeouts, and create terrible UX.
**Do this instead:** Use one of:
- **SSE (Server-Sent Events):** Stream partial results as they arrive from QuasarFlow
- **Background task + polling:** Submit job, return job ID, frontend polls for completion
- **WebSocket:** For real-time bidirectional communication (chat interface)
PAPERY should support SSE for chat responses (streaming tokens) and background tasks for heavy operations (document translation, report generation).

### Anti-Pattern 5: Sharing Pydantic Schemas Between Frontend and Backend

**What people do:** Try to auto-generate TypeScript types from Pydantic schemas (or vice versa) to keep them in sync.
**Why it's wrong:** Sounds efficient but creates tight coupling. Frontend and backend evolve at different speeds. Auto-generated types are often not idiomatic TypeScript. Frontend may need different shapes (flattened, denormalized) than backend.
**Do this instead:** Define Zod schemas on the frontend independently. They should match the API contract but be owned by the frontend team. Use OpenAPI spec as the source of truth for the contract, not code generation.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **QuasarFlow API** | Typed HTTP client in `services/quasarflow/` with retry, circuit breaker, timeout | Primary AI integration. Design client interface first (stub), implement AI later. PAPERY v1 ships with stubs returning mock data. |
| **SMTP (Email)** | Async email via `core/utils/email.py` | Verification, password reset. Use background worker for sending (never block request). |
| **Google OAuth** | OAuth2 authorization code flow via `/api/v1/auth/google` | Redirect-based. Store OAuth tokens, link to user account. |
| **GitHub OAuth** | OAuth2 authorization code flow via `/api/v1/auth/github` | Same pattern as Google OAuth. |
| **MinIO/S3** | S3-compatible SDK in `core/db/minio.py` | Presigned URLs for upload/download. MIME type validation. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Frontend <-> Backend | REST API (JSON over HTTPS) | JWT cookies for auth. API versioning (/api/v1/). BFF proxy for auth flows. |
| Backend <-> PostgreSQL | SQLAlchemy 2.0 async (asyncpg driver) | Connection pooling. Alembic migrations. Soft deletes everywhere. |
| Backend <-> Redis | Direct async connection (aioredis) | Three logical namespaces: cache, queue, rate_limit. Token blacklist. |
| Backend <-> MinIO | S3 SDK (aioboto3 or miniopy-async) | Bucket per environment. UUID-based file keys. |
| Backend <-> ARQ Worker | Redis queue (ARQ protocol) | Worker shares models/schemas/crud code with backend. Separate Docker container. |
| Backend <-> QuasarFlow | HTTP REST API (typed client) | Async calls. Timeout handling. Circuit breaker for resilience. |
| Router <-> Service | Direct function call (same process) | Service receives typed inputs, returns typed outputs. No HTTP overhead. |
| Service <-> CRUD | Direct function call (same process) | CRUD receives DB session + typed schemas. Returns ORM models or typed results. |

---

## Build Order (Dependency-Driven)

The following build order respects component dependencies — each phase builds on the previous:

```
Phase 1: Foundation (no dependencies)
    ├── PostgreSQL + Redis + MinIO setup (Docker Compose)
    ├── SQLAlchemy models + Alembic migrations
    ├── Pydantic schemas (Read/Create/Update/Internal)
    ├── Core config (Pydantic-settings)
    ├── Core security (JWT, bcrypt)
    └── Core DB/Redis/MinIO clients

Phase 2: Data Access (depends on Phase 1)
    ├── CRUD layer (fastcrud instances per resource)
    ├── Custom exceptions
    └── Utility modules (cache, rate_limit, email)

Phase 3: API Layer (depends on Phase 2)
    ├── Dependencies (auth, DB session, rate limiter)
    ├── Auth endpoints (login, register, refresh, logout, OAuth)
    ├── User endpoints (CRUD, profile)
    ├── Tier + RateLimit admin endpoints
    └── FastAPI app factory + lifespan + middleware

Phase 4: Domain Features (depends on Phase 3)
    ├── Project endpoints (CRUD + ACL)
    ├── Document endpoints (upload + CRUD + ACL)
    ├── Chat session/message endpoints (CRUD + ACL)
    ├── ACL management endpoints
    └── ARQ worker setup + background tasks

Phase 5: Frontend Foundation (depends on Phase 3 API being stable)
    ├── Next.js 15 setup + App Router + i18n
    ├── Edge middleware (auth + locale)
    ├── HTTP client (lib/http.ts)
    ├── Auth pages (login, register, forgot-password)
    ├── BFF route handlers (auth proxy)
    └── Layout + theme + shared components

Phase 6: Frontend Features (depends on Phase 4 + 5)
    ├── Dashboard (project list, create project)
    ├── Chat interface (three-panel layout)
    ├── Document viewer
    ├── Zustand stores + custom hooks
    └── Zod schemas + validation

Phase 7: AI Integration (depends on Phase 4 + QuasarFlow API readiness)
    ├── QuasarFlow client (services/quasarflow/)
    ├── AI action executor (services/ai_action/)
    ├── Chat streaming (SSE)
    ├── Document Q&A with citations
    └── Document editing via AI commands

Phase 8: Advanced Features (depends on Phase 7)
    ├── Multi-agent research workflows
    ├── Template system + formatted output generation
    ├── Document translation with structure preservation
    ├── Knowledge graph / topic clustering
    └── Marketplace for community templates
```

**Key Dependency Insight:** Phases 1-4 (backend) and Phase 5 (frontend foundation) can be developed in parallel once the API contract is agreed upon. Phase 7 (AI integration) is decoupled from Phases 1-6 by design — PAPERY v1 ships without AI features, and the QuasarFlow client starts as a stub interface.

---

## Sources

- PAPERY v0 architecture analysis (`.planning/codebase/ARCHITECTURE.md`)
- PAPERY v0 directory structure (`.planning/codebase/STRUCTURE.md`)
- Open Notebook reference architecture (`.reference/open-notebook/`)
- FastAPI documentation: Dependency injection, async patterns
- Industry patterns: Modular monolith (Sam Newman), Service Layer pattern (Martin Fowler), API Gateway pattern
- SaaS architecture: Multi-tenant patterns, tier-based rate limiting, RBAC + ABAC hybrid models

---
*Architecture research for: AI-Powered Document Intelligence SaaS Platform*
*Researched: 2026-04-01*
