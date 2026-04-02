# PAPERY — Architecture Document

> **Status:** Pre-implementation (greenfield). The codebase was fully reset on 2026-03-31.
> This document captures the **intended architecture** derived from:
> 1. The product vision in `README.md` and `CLAUDE.md`
> 2. The **previous v0 implementation** still visible in git history (pre-reset commits)
> 3. The `.planning/` configuration and `.gitignore` signals

---

## 1. System Overview

PAPERY is an AI-powered document intelligence platform. It is designed as a **full-stack web application** with:

- A **React/Next.js** frontend (SPA + SSR)
- A **Python/FastAPI** backend (async REST API)
- A **PostgreSQL** relational database
- **Redis** for caching, task queuing, and rate limiting
- **MinIO** (S3-compatible) for raw file storage
- An **async task worker** (ARQ/Celery) for background document processing
- Future: AI/LLM service layer and multi-agent orchestration

```
┌──────────────────────────────────────────────────────────┐
│                        CLIENT                             │
│              Next.js 15 (React 19, TypeScript)            │
│   SSR + Client Rendering │ next-intl (i18n) │ Zustand     │
└──────────────────┬───────────────────────────────────────┘
                   │ HTTPS / REST (JSON)
                   │ Cookie-based JWT (access + refresh)
┌──────────────────▼───────────────────────────────────────┐
│                    API GATEWAY LAYER                       │
│            FastAPI (Python 3.12, async)                    │
│   /api/v1  │  OAuth2 Bearer + Refresh  │  Rate Limiting   │
└───┬─────────────┬──────────────┬───────────────┬──────────┘
    │             │              │               │
    ▼             ▼              ▼               ▼
┌───────┐   ┌─────────┐   ┌──────────┐   ┌───────────┐
│  DB   │   │  Redis  │   │  MinIO   │   │  Worker   │
│Postgres│  │Cache/Q  │   │(Files)   │   │(ARQ/Celery│
│SQLAlchemy  │Rate Lmt │   │S3-compat │   │Background │
└───────┘   └─────────┘   └──────────┘   └───────────┘
                                                │
                                         ┌──────▼──────┐
                                         │  AI Layer   │
                                         │ LLM / Agent │
                                         │ (Planned)   │
                                         └─────────────┘
```

---

## 2. Architectural Pattern

### Overall: Layered Monolith (Modular Monolith → Microservices-ready)

The previous v0 backend followed a **clean layered architecture** within a single FastAPI application:

```
HTTP Request
    │
    ▼
[Router / API Layer]          ← FastAPI routers, path params, request validation
    │
    ▼
[Dependencies Layer]          ← Auth, DB session injection, rate limit enforcement
    │
    ▼
[CRUD / Repository Layer]     ← fastcrud wrappers, DB queries (no business logic)
    │
    ▼
[Schema Layer]                ← Pydantic v2 models (request/response/internal)
    │
    ▼
[Model Layer]                 ← SQLAlchemy ORM models (DB tables)
    │
    ▼
[Database]                    ← PostgreSQL via asyncpg
```

### Frontend: Feature-scoped App Router Structure

Next.js 15 App Router with locale-based routing:

```
URL Pattern: /{locale}/{route-group}/{feature}
             /en/dashboard
             /vi/(protect)/chat/[sessionId]
             /en/(auth)/login
```

---

## 3. Backend Layers in Detail

### 3.1 Entry Point

```
backend/src/app/main.py          ← FastAPI app instantiation
backend/src/app/core/setup.py    ← App factory, lifespan, middleware registration
backend/src/app/api/__init__.py  ← Top-level router (/api)
backend/src/app/api/v1/__init__.py ← Versioned router aggregator (/api/v1)
```

The `lifespan_factory` in `setup.py` manages startup/shutdown:
- Initializes Redis connections (cache, queue, rate limiter)
- Initializes MinIO bucket (file storage)
- Runs DB table creation (development mode)

### 3.2 API / Router Layer (`app/api/v1/`)

Each resource has a dedicated router file:

| File | Routes | Auth |
|------|--------|------|
| `auth.py` | Login, register, refresh, logout, Google OAuth | Public / Token |
| `users.py` | User CRUD, profile | JWT + superuser |
| `projects.py` | Project CRUD | JWT + ACL |
| `documents.py` | Document upload/CRUD, MinIO integration | JWT + ACL |
| `chat_sessions.py` | Chat session CRUD, message streaming | JWT + ACL |
| `chat_messages.py` | Message history, append | JWT + ACL |
| `tasks.py` | Background task status | JWT |
| `tiers.py` | Subscription tier management | Superuser |
| `rate_limits.py` | Rate limit rule management | Superuser |

### 3.3 Dependencies Layer (`app/api/dependencies.py`)

FastAPI `Depends()` injection chain:

```python
get_current_user()       ← Verifies JWT, loads UserReadInternal
get_optional_user()      ← Same but returns None if unauthenticated
get_current_superuser()  ← get_current_user + is_superuser check
rate_limiter()           ← Redis-backed per-user/IP rate limiting
async_get_db()           ← AsyncSession from SQLAlchemy connection pool
```

Access Control is enforced via an **ACL table** (`access_control`):
- Every resource (project, document, chat_session) has ACL entries
- Before any resource operation, ACL is checked: `crud_access_controls.exists(resource_uuid, user_id)`
- Superusers bypass ACL checks

### 3.4 CRUD / Repository Layer (`app/crud/`)

Built on **fastcrud** — typed CRUD operations wrapping SQLAlchemy:

```python
CRUDUser = FastCRUD[User, UserCreateInternal, UserUpdateInternal, ...]
crud_users = CRUDUser(User)

# Usage in router:
user = await crud_users.get(db=db, username="foo", is_deleted=False)
await crud_users.create(db=db, object=UserCreateInternal(...))
```

Each resource has its own CRUD module:
- `crud_users.py`, `crud_projects.py`, `crud_documents.py`
- `crud_chat_session.py`, `crud_chat_message.py`
- `crud_rate_limits.py`, `crud_tiers.py`
- `access_controls.py` — special ACL-aware CRUD

### 3.5 Schema Layer (`app/schemas/`)

Pydantic v2 schemas with strict separation of concerns:

| Schema suffix | Purpose |
|---------------|---------|
| `Read` | Public API response (safe fields only) |
| `ReadInternal` | Internal service use (includes sensitive fields) |
| `Create` | Public create request |
| `CreateInternal` | Internal create (adds computed fields) |
| `Update` | Partial update (all optional) |
| `Delete` | Soft-delete trigger |
| `AdminXxxRead` | Superuser-only extended view |

### 3.6 Model Layer (`app/models/`)

SQLAlchemy 2.0 ORM with declarative mapped columns and three shared mixins:

```python
class UUIDMixin:     # uuid: UUID — public-facing identifier
class TimestampMixin: # created_at, updated_at
class SoftDeleteMixin: # deleted_at, is_deleted (never hard-delete)
```

**Entity Relationship Summary:**

```
Tier ──< User ──< Project ──< ChatSession ──< ChatMessage
                     │                              │
                     └──< Document >────────────────┘
                                    (MessageDocument join table)

AccessControl: (user_id, resource_uuid, resource_type, permission_type)
RateLimit: (path, tier_id, limit, period)
```

### 3.7 Core Services (`app/core/`)

| Module | Responsibility |
|--------|---------------|
| `config.py` | Pydantic-settings config classes, composed into `settings` object |
| `security.py` | JWT encode/decode, bcrypt hashing, OAuth2 scheme |
| `db/database.py` | SQLAlchemy async engine + session factory |
| `db/redis.py` | Redis singleton (cache, queue, rate limit — three logical uses) |
| `db/minio.py` | MinIO singleton client, bucket management, presigned URL generation |
| `db/models.py` | Shared SQLAlchemy mixins (UUID, Timestamp, SoftDelete) |
| `db/token_blacklist.py` | Logout token invalidation via Redis |
| `utils/cache.py` | Response caching decorators / helpers |
| `utils/queue.py` | ARQ task queue helpers |
| `utils/rate_limit.py` | Redis rate limit enforcement logic |
| `utils/email.py` | SMTP email (account verification, password reset) |
| `worker/settings.py` | ARQ WorkerSettings for background job configuration |
| `worker/functions.py` | Background task function definitions |
| `middleware/` | Client-side HTTP cache headers middleware |
| `exceptions/` | Custom HTTP exceptions (401, 403, 404, 409, 429) |
| `logger.py` | Structured logging setup |

### 3.8 Migrations (`migrations/`)

Alembic with async support:
- `env.py` — async migration runner
- `versions/` — gitignored; scripts in `scripts/` bootstrap initial data

---

## 4. Frontend Layers in Detail

### 4.1 Entry Points

```
frontend/src/middleware.ts           ← Next.js edge middleware (auth + i18n)
frontend/src/app/[locale]/layout.tsx ← Root layout (providers, fonts, theme)
frontend/src/app/[locale]/page.tsx   ← Root redirect
```

The middleware chain:
1. `next-intl` locale detection and routing
2. JWT cookie validation (`access_token` + `refresh_token`)
3. Auto-refresh expired access tokens via `/api/v1/auth/refresh`
4. Redirect: unauthenticated → `/login`, authenticated + auth-route → `/dashboard`

### 4.2 Route Groups

```
[locale]/
├── (home)/              ← Public marketing (/, pricing, FAQ, hero)
│   └── components/      ← Landing page section components
├── (auth)/              ← Unauthenticated only
│   ├── login/
│   ├── register/
│   ├── forgot-password/
│   ├── reset-password/
│   ├── confirm-email/
│   └── confirm-account/
├── (protect)/           ← Authenticated only
│   ├── dashboard/       ← Project list, project management
│   ├── chat/[[...id]]/  ← Chat interface (catch-all for session routing)
│   └── document/        ← Document viewer
└── api/
    ├── client/          ← Client-side API call modules
    └── endpoints/       ← Next.js Route Handlers (BFF proxy to backend)
        └── auth/        ← Login, logout, register, me, Google OAuth
```

### 4.3 Data Flow (Frontend)

```
User Action
    │
    ▼
React Component
    │ calls
    ▼
Custom Hook (use-get.ts, use-create.ts, use-update.ts, use-delete.ts)
    │ calls
    ▼
HTTP Client (lib/http.ts — axios wrapper)
    │ → auto-attaches access_token from cookie
    │ → constructs URL: {BACKEND_URL}/api/{API_VERSION}/{path}
    ▼
Next.js Route Handler (api/endpoints/) [optional BFF layer]
    │  OR directly
    ▼
FastAPI Backend (/api/v1/...)
    │
    ▼
Response → Zod validation (schemas/) → Zustand store update → UI re-render
```

### 4.4 State Management

**Zustand stores** (global client state):
- `store/chat-list.store.ts` — chat sessions list, selected chat, sort order
- `store/project-list.store.ts` — projects list, selected project

**React Context** (auth/theme session):
- `context/auth-context.tsx` — user identity, login/logout
- `context/user-context.tsx` — user profile data
- `context/theme-context.tsx` — light/dark/system preference

**Server state** is fetched per-component via custom hooks (no React Query in v0; planned).

### 4.5 HTTP Client (`lib/http.ts`)

Typed axios wrapper supporting three API target types:

```typescript
enum APIType {
    BACKEND,   // → process.env.BACKEND_API_URL/api/v1/...
    FRONTEND,  // → same-origin Next.js route handlers
    EXTERNAL   // → arbitrary external URL
}
```

Features:
- Automatic Bearer token injection (cookie-read, SSR + client-side)
- API versioning via `API_VERSION` env var
- Centralized error normalization (`lib/error.ts`)
- Token refresh on 401 (`hooks/token-refresher.ts`)

### 4.6 Schema Validation (`schemas/`)

Zod schemas mirror backend Pydantic shapes:
- `auth.schemas.ts` — login, register, token response
- `project-list.schemas.ts` — project list items
- `chat-list.schemas.ts` — chat session items
- `user.schemas.ts` — user profile

### 4.7 Key UI Components (Chat Interface)

The chat feature (most complex UI) uses a three-panel layout:

```
┌─────────────────┬──────────────────────────┬─────────────────┐
│  Left Sidebar   │      Chat Arena          │  Right Sidebar  │
│ (Function)      │                          │ (Documents)     │
│                 │  MessageList             │                 │
│ - Project       │  MessageInput            │ - FileUploader  │
│   Switcher      │  PromptSuggestions       │ - FileList      │
│ - Chat List     │  Header (model select)   │ - DocumentView  │
│ - Chat Config   │                          │                 │
│ - Dialogs:      │                          │                 │
│   Agents/Models │                          │                 │
│   Playground    │                          │                 │
│   Settings      │                          │                 │
└─────────────────┴──────────────────────────┴─────────────────┘
```

---

## 5. Infrastructure / DevOps

### 5.1 Docker Compose Services (v0 reference)

| Service | Image | Port |
|---------|-------|------|
| `web` | Custom FastAPI image | 8000 |
| `worker` | Custom ARQ worker image | — |
| `db` | postgres:13 | 5432 |
| `redis` | redis:alpine | 6379 |
| MinIO | (planned) | 9000/9001 |

### 5.2 Environment Configuration

All secrets and config via `.env` file (gitignored). Key categories:

- `APP_*` — application metadata
- `POSTGRES_*` — database connection
- `REDIS_CACHE_*`, `REDIS_QUEUE_*`, `REDIS_RATE_LIMIT_*` — three Redis logical namespaces
- `SECRET_KEY`, `ALGORITHM`, `*_TOKEN_EXPIRE_*` — JWT signing
- `MINIO_*` — object storage
- `SMTP_*` — email delivery
- `ADMIN_*` — bootstrap superuser
- `ENVIRONMENT` — `local` | `staging` | `production`
- `CORS_ORIGINS` — allowed frontend origins

### 5.3 Frontend Environment

- `BACKEND_API_URL` / `NEXT_PUBLIC_BACKEND_API_URL` — backend base URL
- `API_VERSION` / `NEXT_PUBLIC_API_VERSION` — API version (default: `v1`)
- `NEXT_PUBLIC_*` — client-accessible vars

---

## 6. Cross-Cutting Concerns

### 6.1 Authentication & Authorization

- **Mechanism:** JWT (HS256) access tokens (30min) + refresh tokens (7 days) stored as HTTP-only cookies
- **Auth types:** Local (email/password), Google OAuth, GitHub OAuth
- **Authorization:** Role-based (regular user vs superuser) + resource-level ACL
- **Token blacklist:** Redis-backed logout invalidation
- **Email verification:** Required before account activation

### 6.2 Rate Limiting

Tiered rate limiting system:
- Users belong to a `Tier` (e.g., "free", "pro")
- Each tier has per-endpoint `RateLimit` rules (requests / time window)
- Redis counters track usage per user/IP per endpoint
- Default limits apply when no tier-specific rule exists

### 6.3 File Storage

Documents flow:
1. Client uploads file → `POST /api/v1/documents/` with multipart form
2. Backend validates MIME type against `DOCUMENT_MIME_TYPES` allowlist
3. File stored in MinIO bucket with UUID-based key
4. DB record created (`Document` model) with `file_path` → MinIO key
5. ACL entry created for the uploading user
6. Future: background worker triggers parsing/indexing pipeline

Supported in v0: PDF, DOCX (10MB limit)
Planned: XLSX, PPTX, CSV, TXT, Markdown

### 6.4 Internationalization

- **Backend:** locale-aware email templates (Jinja2)
- **Frontend:** `next-intl` with locale-prefixed routing (`/en/`, `/vi/`, `/fr/`)
- Translation files: `frontend/src/locale/en.json`, `vi.json`
- Language switcher component in UI

### 6.5 Soft Deletes

All core entities use `SoftDeleteMixin` — records are never physically deleted. Queries always filter `is_deleted=False`. This enables audit trails and data recovery.

---

## 7. Planned Architecture Additions

Based on the README roadmap, the following have no implementation yet:

| Feature | Architectural Implication |
|---------|--------------------------|
| Document parsing pipeline | Background worker + vector DB for embeddings |
| AI Q&A with citations | LLM service layer, RAG pipeline, citation index |
| Multi-agent research workflows | Agent orchestration (LangGraph or custom) |
| Template system | Template registry, structured document generation |
| Marketplace | Community content store, user-contributed templates |
| Knowledge graph | Graph DB or graph-structured embedding store |
| Document translation | Translation service integration, structure preservation |
| AI document editing | Diff-based edit proposals, human-in-the-loop approval |

---

## 8. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend framework | FastAPI (async) | High performance, native async, Pydantic integration |
| ORM | SQLAlchemy 2.0 (async) | Type-safe, mature, Alembic migration support |
| CRUD abstraction | fastcrud | Eliminates boilerplate, typed generics |
| File storage | MinIO (S3-compatible) | Self-hosted, S3 API compatible, scalable |
| Task queue | ARQ (+ Celery as backup) | Async-native Redis-based queue |
| Frontend framework | Next.js 15 | SSR + App Router, full-stack capability |
| UI components | Shadcn/ui (Radix UI) | Accessible, unstyled primitives, composable |
| State management | Zustand | Minimal, no boilerplate, TypeScript-first |
| Validation | Pydantic v2 (BE) + Zod (FE) | Runtime safety at both layers |
| Auth | JWT cookies | Secure, SSR-compatible, refresh token rotation |
| i18n | next-intl | Type-safe, App Router native |
| Identifier strategy | Dual: `id` (int, internal) + `uuid` (public API) | Prevents enumeration attacks |
