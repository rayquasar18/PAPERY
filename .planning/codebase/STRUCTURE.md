# PAPERY — Directory Structure & Naming Conventions

> **Status:** Greenfield (post-reset). The project was fully wiped on 2026-03-31.
> This document records the **canonical intended structure** — derived from:
> 1. The v0 implementation visible in git history (pre-reset commits)
> 2. Product vision and feature roadmap in `README.md` + `CLAUDE.md`
> 3. Current skeleton files and git infrastructure already in place

---

## 1. Current State (After Reset)

```
PAPERY/                              ← Project root
├── .git/                            ← Git repository (managed)
├── .gitignore                       ← Python + Node + Next.js patterns
├── .gitattributes                   ← Line ending normalization
├── .planning/                       ← AI planning workspace
│   ├── config.json                  ← Model profile for planning agents
│   └── codebase/                    ← Codebase analysis documents
│       ├── ARCHITECTURE.md          ← This project's architecture
│       └── STRUCTURE.md             ← This file
├── .reference/                      ← READ-ONLY reference repos (gitignored)
│   └── open-notebook/               ← Architecture reference only
├── docs/                            ← Project documentation & assets
│   └── images/
│       └── papery_logo.png
├── CLAUDE.md                        ← AI agent instructions (mandatory)
├── CODE_OF_CONDUCT.md               ← Community guidelines
├── CONTRIBUTING.md                  ← Contribution guidelines
├── LICENSE                          ← CC BY-NC 4.0
└── README.md                        ← Project description, roadmap, tech stack
```

**Branches in use:**

| Branch | Purpose |
|--------|---------|
| `main` | Production-stable |
| `develop` | Integration |
| `feature/base` | (stub) Feature work base |
| `hotfix/base` | (stub) Hotfix base |
| `release/v1` | (stub) v1 release |
| `release/v2` | (stub) v2 release |
| `staging` | Pre-prod testing |

---

## 2. Target Full Structure (To Be Built)

This is the **canonical directory layout** the implementation will grow into, based on the v0 architecture and product roadmap.

```
PAPERY/
├── backend/                         ← Python/FastAPI backend service
│   ├── Dockerfile                   ← API server container
│   ├── Dockerfile.worker            ← Background worker container
│   ├── docker-compose.yml           ← Full local stack (db, redis, minio, web, worker)
│   ├── pyproject.toml               ← Python project config, Poetry dependencies
│   ├── mypy.ini                     ← Type checking config
│   ├── default.conf                 ← Nginx config (optional proxy)
│   └── src/
│       ├── .env                     ← Runtime secrets (gitignored)
│       ├── .env.example             ← Template with all required vars
│       ├── alembic.ini              ← Alembic migration config
│       ├── __init__.py
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py              ← FastAPI app entry point
│       │   │
│       │   ├── api/                 ← HTTP interface layer
│       │   │   ├── __init__.py      ← Top-level /api router
│       │   │   ├── dependencies.py  ← FastAPI Depends() providers
│       │   │   └── v1/             ← Versioned endpoints
│       │   │       ├── __init__.py  ← /api/v1 router aggregator
│       │   │       ├── auth.py
│       │   │       ├── users.py
│       │   │       ├── projects.py
│       │   │       ├── documents.py
│       │   │       ├── chat_sessions.py
│       │   │       ├── chat_messages.py
│       │   │       ├── tasks.py
│       │   │       ├── tiers.py
│       │   │       └── rate_limits.py
│       │   │
│       │   ├── core/               ← Infrastructure & cross-cutting concerns
│       │   │   ├── __init__.py
│       │   │   ├── config.py       ← Pydantic-settings config classes
│       │   │   ├── logger.py       ← Structured logging
│       │   │   ├── security.py     ← JWT, bcrypt, OAuth2 scheme
│       │   │   ├── setup.py        ← App factory, lifespan, middleware
│       │   │   ├── db/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── database.py        ← SQLAlchemy async engine + session
│       │   │   │   ├── models.py          ← Shared ORM mixins (UUID, Timestamp, SoftDelete)
│       │   │   │   ├── redis.py           ← Redis singleton client
│       │   │   │   ├── minio.py           ← MinIO singleton client
│       │   │   │   ├── token_blacklist.py ← JWT logout invalidation
│       │   │   │   └── crud_token_blacklist.py
│       │   │   ├── exceptions/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── http_exceptions.py   ← Custom HTTP error classes
│       │   │   │   └── cache_exceptions.py
│       │   │   ├── utils/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── cache.py      ← Response caching helpers
│       │   │   │   ├── queue.py      ← ARQ task queue helpers
│       │   │   │   ├── rate_limit.py ← Redis rate limit enforcement
│       │   │   │   └── email.py      ← SMTP email (verify, reset password)
│       │   │   └── worker/
│       │   │       ├── __init__.py
│       │   │       ├── settings.py   ← ARQ WorkerSettings
│       │   │       └── functions.py  ← Background task definitions
│       │   │
│       │   ├── models/             ← SQLAlchemy ORM model definitions
│       │   │   ├── __init__.py     ← Imports all models (for Alembic discovery)
│       │   │   ├── user.py
│       │   │   ├── project.py
│       │   │   ├── document.py
│       │   │   ├── chat_session.py
│       │   │   ├── chat_message.py
│       │   │   ├── message_document.py  ← M2M join table
│       │   │   ├── access_control.py
│       │   │   ├── tier.py
│       │   │   └── rate_limit.py
│       │   │
│       │   ├── schemas/            ← Pydantic v2 request/response schemas
│       │   │   ├── __init__.py
│       │   │   ├── auth.py
│       │   │   ├── user.py
│       │   │   ├── project.py
│       │   │   ├── document.py
│       │   │   ├── chat_session.py
│       │   │   ├── chat_message.py
│       │   │   ├── access_control.py
│       │   │   ├── tier.py
│       │   │   ├── rate_limit.py
│       │   │   ├── job.py          ← Background task response schema
│       │   │   └── utils.py        ← APIResponse, PaginatedAPIResponse wrappers
│       │   │
│       │   ├── crud/               ← fastcrud repository layer
│       │   │   ├── __init__.py
│       │   │   ├── crud_users.py
│       │   │   ├── crud_projects.py
│       │   │   ├── crud_documents.py
│       │   │   ├── crud_chat_session.py
│       │   │   ├── crud_chat_message.py
│       │   │   ├── access_controls.py  ← ACL-aware CRUD
│       │   │   ├── crud_tiers.py
│       │   │   └── crud_rate_limits.py
│       │   │
│       │   ├── services/           ← Business logic / AI pipeline (growing)
│       │   │   └── document/
│       │   │       ├── document.py        ← Document orchestration
│       │   │       ├── read-document.py   ← Text extraction
│       │   │       └── layout-document.py ← Layout/structure analysis
│       │   │
│       │   └── middleware/
│       │       └── client_cache_middleware.py ← HTTP cache-control headers
│       │
│       ├── migrations/             ← Alembic migration scripts
│       │   ├── README
│       │   ├── env.py              ← Async migration runner
│       │   ├── script.py.mako      ← Migration file template
│       │   └── versions/           ← Generated migration files (gitignored)
│       │
│       └── scripts/                ← Bootstrap / utility scripts
│           ├── create_first_superuser.py
│           ├── create_first_tier.py
│           └── check_and_run_migrations.sh
│
├── tests/                          ← Backend test suite
│   ├── __init__.py
│   ├── conftest.py                 ← pytest fixtures (db, client, test user)
│   ├── helpers/
│   │   ├── generators.py           ← Fake data generators (Faker)
│   │   └── mocks.py                ← Mock objects
│   └── test_user.py                ← User API tests (and other test_*.py)
│
├── frontend/                       ← Next.js 15 frontend application
│   ├── Dockerfile                  ← Production container (standalone output)
│   ├── next.config.ts              ← Next.js config (bundle analyzer, next-intl)
│   ├── package.json                ← npm dependencies
│   ├── tsconfig.json               ← TypeScript config
│   ├── eslint.config.mjs           ← ESLint rules
│   ├── postcss.config.mjs          ← PostCSS (Tailwind)
│   ├── components.json             ← Shadcn/ui config
│   ├── tailwind.config.ts          ← Tailwind v4 config
│   └── src/
│       ├── middleware.ts            ← Edge middleware (auth + i18n)
│       │
│       ├── app/                    ← Next.js App Router
│       │   ├── [locale]/           ← Locale-dynamic root segment
│       │   │   ├── layout.tsx      ← Root layout (providers, fonts)
│       │   │   ├── page.tsx        ← Root redirect
│       │   │   ├── globals.css     ← Global styles + Tailwind base
│       │   │   ├── fonts/          ← Self-hosted fonts (Geist)
│       │   │   │
│       │   │   ├── (home)/         ← Public marketing routes
│       │   │   │   ├── layout.tsx
│       │   │   │   ├── page.tsx    ← Landing page
│       │   │   │   └── components/
│       │   │   │       ├── hero-section.tsx
│       │   │   │       ├── features-section.tsx
│       │   │   │       ├── how-it-works-section.tsx
│       │   │   │       ├── pricing-section.tsx
│       │   │   │       ├── faq-section.tsx
│       │   │   │       ├── cta-section.tsx
│       │   │   │       ├── newsletter-section.tsx
│       │   │   │       ├── header.tsx
│       │   │   │       └── footer.tsx
│       │   │   │
│       │   │   ├── (auth)/         ← Unauthenticated-only routes
│       │   │   │   ├── layout.tsx
│       │   │   │   ├── login/page.tsx
│       │   │   │   ├── register/page.tsx
│       │   │   │   ├── forgot-password/page.tsx
│       │   │   │   ├── reset-password/page.tsx
│       │   │   │   ├── confirm-email/page.tsx
│       │   │   │   └── confirm-account/page.tsx
│       │   │   │
│       │   │   └── (protect)/      ← Authenticated-only routes
│       │   │       ├── dashboard/
│       │   │       │   ├── layout.tsx
│       │   │       │   ├── page.tsx
│       │   │       │   └── components/
│       │   │       │       ├── project-list.tsx
│       │   │       │       ├── create-project.tsx
│       │   │       │       ├── sort-button.tsx
│       │   │       │       └── project-list-skeleton.tsx
│       │   │       ├── chat/
│       │   │       │   ├── layout.tsx
│       │   │       │   ├── [[...id]]/page.tsx   ← Catch-all for session routing
│       │   │       │   └── components/
│       │   │       │       ├── chat-arena/
│       │   │       │       │   ├── chat-arena-index.tsx
│       │   │       │       │   ├── chat-ui.tsx
│       │   │       │       │   └── header-chat.tsx
│       │   │       │       └── sidebar/
│       │   │       │           ├── sidebar.tsx
│       │   │       │           ├── sidebar-function-left/
│       │   │       │           │   ├── project-switcher.tsx
│       │   │       │           │   ├── chat-list.tsx
│       │   │       │           │   ├── chat-list-items.tsx
│       │   │       │           │   ├── chat-config.tsx
│       │   │       │           │   └── dialog/
│       │   │       │           │       ├── agents-dialog.tsx
│       │   │       │           │       ├── models-dialog.tsx
│       │   │       │           │       ├── playground-dialog.tsx
│       │   │       │           │       └── settings-dialog.tsx
│       │   │       │           └── sidebar-document-right/
│       │   │       │               ├── document-header.tsx
│       │   │       │               ├── file-list.tsx
│       │   │       │               ├── file-list-item.jsx
│       │   │       │               ├── file-uploader.tsx
│       │   │       │               ├── file-icon.jsx
│       │   │       │               └── dropdown-menu.jsx
│       │   │       └── document/
│       │   │           └── page.tsx
│       │   │
│       │   └── api/                ← Next.js Route Handlers (BFF)
│       │       ├── client/         ← Client-side API call modules
│       │       │   ├── auth.api.ts
│       │       │   ├── chat-list.api.ts
│       │       │   ├── project-list.api.ts
│       │       │   └── user-api.ts
│       │       └── endpoints/      ← Server-side proxy routes
│       │           └── auth/
│       │               ├── login/route.ts
│       │               ├── logout/route.ts
│       │               ├── register/route.ts
│       │               ├── me/route.ts
│       │               └── google/callback/route.ts
│       │
│       ├── actions/                ← Next.js Server Actions
│       │   ├── auth-action.ts
│       │   ├── user-action.ts
│       │   └── theme-action.ts
│       │
│       ├── components/             ← Shared UI components
│       │   ├── header.tsx
│       │   ├── nav-user.tsx
│       │   ├── language-switcher.tsx
│       │   ├── theme-switcher.tsx
│       │   ├── project-dialog.tsx
│       │   └── guide-dialog.tsx
│       │
│       ├── context/                ← React context providers
│       │   ├── auth-context.tsx
│       │   ├── user-context.tsx
│       │   └── theme-context.tsx
│       │
│       ├── hooks/                  ← Custom React hooks
│       │   ├── use-get.ts          ← Single resource fetch
│       │   ├── use-gets.ts         ← List fetch + store sync
│       │   ├── use-create.ts       ← POST resource
│       │   ├── use-update.ts       ← PUT/PATCH resource
│       │   ├── use-delete.ts       ← DELETE resource
│       │   ├── use-query.ts        ← Generic query hook
│       │   ├── use-notification.ts ← Toast notifications
│       │   ├── use-auto-scroll.ts  ← Chat scroll behavior
│       │   ├── use-autosize-textarea.ts
│       │   ├── use-copy-to-clipboard.ts
│       │   ├── use-audio-recording.ts
│       │   └── token-refresher.ts  ← Silent JWT refresh
│       │
│       ├── lib/                    ← Pure utility modules
│       │   ├── http.ts             ← Axios wrapper (typed, versioned)
│       │   ├── token.ts            ← JWT decode helpers
│       │   ├── error.ts            ← Error normalization
│       │   ├── cache.ts            ← Client-side cache helpers
│       │   ├── themes.ts           ← Theme definitions
│       │   ├── audio-utils.ts      ← Audio recording utilities
│       │   └── next-intl/
│       │       ├── routing.ts      ← defineRouting config
│       │       ├── request.ts      ← Server-side locale resolution
│       │       └── navigation.ts   ← Typed Link/redirect helpers
│       │
│       ├── schemas/                ← Zod validation schemas
│       │   ├── auth.schemas.ts
│       │   ├── user.schemas.ts
│       │   ├── project-list.schemas.ts
│       │   └── chat-list.schemas.ts
│       │
│       ├── store/                  ← Zustand global state
│       │   ├── chat-list.store.ts
│       │   └── project-list.store.ts
│       │
│       ├── constants/
│       │   └── language.ts         ← Locale constants (SUPPORTED_LOCALES, etc.)
│       │
│       ├── services/               ← API service modules (business-logic wrappers)
│       │   └── user.ts
│       │
│       └── locale/                 ← i18n translation files
│           ├── en.json
│           └── vi.json
│
├── docs/                           ← Project documentation
│   └── images/
│       └── papery_logo.png
│
├── .planning/                      ← AI agent planning workspace
│   ├── config.json
│   └── codebase/
│       ├── ARCHITECTURE.md
│       └── STRUCTURE.md
│
├── .reference/                     ← READ-ONLY reference repos (gitignored)
│
├── CLAUDE.md                       ← AI agent instructions
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
└── .gitignore
```

---

## 3. Key Location Reference

| Need | Location |
|------|---------|
| Backend entry point | `backend/src/app/main.py` |
| Backend app factory | `backend/src/app/core/setup.py` |
| API route definitions | `backend/src/app/api/v1/*.py` |
| Auth & injection | `backend/src/app/api/dependencies.py` |
| Database models | `backend/src/app/models/` |
| Pydantic schemas | `backend/src/app/schemas/` |
| CRUD operations | `backend/src/app/crud/` |
| Config / secrets | `backend/src/.env` (gitignored) |
| Config template | `backend/src/.env.example` |
| DB migrations | `backend/src/migrations/` |
| Bootstrap scripts | `backend/src/scripts/` |
| Background tasks | `backend/src/app/core/worker/` |
| Frontend entry | `frontend/src/app/[locale]/layout.tsx` |
| Auth middleware | `frontend/src/middleware.ts` |
| HTTP client | `frontend/src/lib/http.ts` |
| API call modules | `frontend/src/app/api/client/` |
| State stores | `frontend/src/store/` |
| Custom hooks | `frontend/src/hooks/` |
| Shared components | `frontend/src/components/` |
| i18n translations | `frontend/src/locale/` |
| Zod schemas | `frontend/src/schemas/` |
| Environment vars | `frontend/.env.local` (gitignored) |

---

## 4. Naming Conventions

### 4.1 Backend (Python)

| Element | Convention | Example |
|---------|-----------|---------|
| Files | `snake_case` | `crud_users.py`, `chat_session.py` |
| Classes | `PascalCase` | `User`, `CRUDUser`, `ChatSession` |
| Functions | `snake_case` | `get_current_user()`, `create_tables()` |
| Variables | `snake_case` | `crud_users`, `token_data` |
| Constants | `UPPER_SNAKE` | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Pydantic schemas | `PascalCase + suffix` | `UserRead`, `UserCreateInternal`, `UserReadInternal` |
| CRUD instances | `crud_<resource>` | `crud_users`, `crud_documents` |
| Router vars | `<resource>_router` | `auth_router`, `projects_router` |
| DB model tables | `snake_case` (singular) | `"user"`, `"chat_session"`, `"message_document"` |
| API routes | `snake_case` (plural) | `/users/`, `/chat_sessions/`, `/documents/` |

### 4.2 Frontend (TypeScript)

| Element | Convention | Example |
|---------|-----------|---------|
| Files (components) | `kebab-case.tsx` | `chat-ui.tsx`, `file-uploader.tsx` |
| Files (hooks) | `use-<name>.ts` | `use-create.ts`, `use-auto-scroll.ts` |
| Files (stores) | `<name>.store.ts` | `chat-list.store.ts` |
| Files (schemas) | `<name>.schemas.ts` | `auth.schemas.ts` |
| Files (API modules) | `<name>.api.ts` | `auth.api.ts`, `project-list.api.ts` |
| Components | `PascalCase` | `FileUploader`, `ChatArena`, `ProjectSwitcher` |
| Hook functions | `use<Name>` | `useListChatStore`, `useAutoScroll` |
| Types / Interfaces | `PascalCase` | `ListChatState`, `ChatPropsBase` |
| Type suffixes | `<Name>Type` | `ListChatType`, `ListProjectType` |
| Constants | `UPPER_SNAKE` | `SUPPORTED_LOCALES`, `DEFAULT_LOCALE` |
| Zustand stores | `use<Entity>Store` | `useListChatStore`, `useListProjectStore` |
| Context providers | `<Name>Provider` | `AuthProvider`, `ThemeProvider` |
| Route groups | `(kebab-case)` | `(auth)`, `(protect)`, `(home)` |
| Dynamic segments | `[kebab-case]` | `[locale]`, `[[...id]]` |

### 4.3 Git

| Element | Convention | Example |
|---------|-----------|---------|
| Branch names | `<type>/<description>` | `feature/pdf-parser`, `hotfix/auth-crash` |
| Commit message | `<type>: <description>` | `feat: add document upload endpoint` |
| Commit types | `feat\|fix\|refactor\|docs\|test\|chore\|style\|perf\|ci` | — |

### 4.4 Environment Variables

| Scope | Convention | Example |
|-------|-----------|---------|
| Backend | `UPPER_SNAKE` | `POSTGRES_USER`, `REDIS_CACHE_HOST` |
| Frontend (server-only) | `UPPER_SNAKE` | `BACKEND_API_URL` |
| Frontend (client-exposed) | `NEXT_PUBLIC_UPPER_SNAKE` | `NEXT_PUBLIC_BACKEND_API_URL` |

---

## 5. Module Boundaries & Import Rules

### Backend

```
api/v1/ → imports from: crud/, schemas/, models/, core/
crud/   → imports from: models/, schemas/, core/db/
models/ → imports from: core/db/models.py only
schemas/→ imports from: nothing internal (pure Pydantic)
core/   → imports from: nothing internal except core/ siblings
services/ → imports from: crud/, schemas/, models/, core/
```

**Rules:**
- Routers never import from other routers
- Models never import from schemas or crud
- No circular imports — dependency flows downward only

### Frontend

```
app/[locale]/       → imports from: components/, hooks/, lib/, store/, schemas/
components/         → imports from: lib/, hooks/, store/, schemas/
hooks/              → imports from: lib/, store/, schemas/
store/              → imports from: schemas/ only
lib/                → no internal imports
schemas/            → no internal imports
```

**Rules:**
- No server component imports inside `'use client'` boundaries
- Hooks only in Client Components
- `lib/` modules are pure utilities with no framework dependencies

---

## 6. Special Directories

### `.planning/` — AI Planning Workspace

Used exclusively by AI agents (Claude Code) for project planning:
- Not shipped in production
- Not imported by any source code
- Contains planning configs, codebase analysis, roadmaps, and task plans

### `.reference/` — Read-Only Reference Material

- Gitignored (local only, not tracked)
- Contains cloned repos for architecture reference only
- **Never** import, copy, or reference paths from here in PAPERY code

### `backend/src/app/services/` — AI/Processing Pipeline

This directory is the designated home for:
- Document parsing and text extraction
- Layout and structure analysis
- Future: RAG pipeline, embedding generation, citation indexing
- Future: LLM service integration, agent orchestration
