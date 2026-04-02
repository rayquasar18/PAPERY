# Stack Research — PAPERY

> AI-Powered Document Intelligence SaaS Platform
> Research date: 2026-04-01

---

## 1. Recommended Stack

### 1.1 Backend — Python / FastAPI

| Component | Recommendation | Version | Rationale |
|-----------|---------------|---------|-----------|
| **Runtime** | Python | 3.12+ | Latest stable, performance improvements, better error messages |
| **Web Framework** | FastAPI | 0.115+ | Async-native, Pydantic v2 integration, OpenAPI auto-docs |
| **ORM** | SQLAlchemy | 2.0+ | Async support, type-safe mapped columns, mature ecosystem |
| **CRUD Abstraction** | fastcrud | 0.15+ | Eliminates CRUD boilerplate, typed generics, filter support |
| **Validation** | Pydantic | 2.9+ | V2 performance (5-50x faster), strict/lax modes, settings |
| **Migrations** | Alembic | 1.14+ | Async migration support, autogenerate from models |
| **Task Queue** | ARQ | 0.26+ | Async-native Redis queue, simpler than Celery for async apps |
| **Auth** | python-jose + bcrypt | — | JWT encode/decode, password hashing |
| **Email** | fastapi-mail | — | Async SMTP, Jinja2 templates |
| **Linting** | Ruff | 0.8+ | Replaces flake8+isort+black, extremely fast |
| **Type Checking** | mypy | 1.13+ | Strict mode, SQLAlchemy plugin |
| **Testing** | pytest + pytest-asyncio | — | Async test support, fixtures, parametrize |

**Why NOT Django:** FastAPI is better suited for async document processing, external API delegation (QuasarFlow), and modern Python patterns. Django's ORM is sync-first and its admin panel isn't needed (custom admin in Next.js).

**Why NOT Celery:** ARQ is async-native, simpler configuration, and Redis-only (which is already in the stack). Celery adds complexity with broker/backend configuration.

### 1.2 Frontend — Next.js / React

| Component | Recommendation | Version | Rationale |
|-----------|---------------|---------|-----------|
| **Framework** | Next.js | 15+ | App Router stable, React Server Components, middleware |
| **UI Library** | React | 19+ | Concurrent features, use() hook, Server Components |
| **Language** | TypeScript | 5.7+ | Strict mode, satisfies operator, better inference |
| **Styling** | Tailwind CSS | 4.0+ | Utility-first, JIT compilation, design system via config |
| **Components** | shadcn/ui | latest | Radix UI primitives, accessible, copy-paste ownership |
| **State (client)** | Zustand | 5.0+ | Minimal boilerplate, TypeScript-first, middleware |
| **State (server)** | TanStack Query | 5.60+ | Server state caching, mutations, optimistic updates |
| **Validation** | Zod | 3.24+ | TypeScript inference, schema composition, transform |
| **i18n** | next-intl | 4.0+ | App Router native, type-safe, ICU message format |
| **HTTP Client** | ky or axios | — | ky: lighter, modern; axios: interceptors, wider adoption |
| **Forms** | React Hook Form + Zod | — | Performance, Zod resolver integration |
| **Icons** | Lucide React | — | Tree-shakeable, consistent design, shadcn default |
| **Testing** | Vitest + Testing Library | — | Fast, Vite-powered, component testing |

**Why NOT React Query v4:** TanStack Query v5 has breaking improvements — simplified API, better TypeScript, suspense support.

**Why NOT Redux:** Zustand covers 95% of client state needs with 10% of the boilerplate. Redux Toolkit is overkill for this use case.

### 1.3 Infrastructure

| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| **Database** | PostgreSQL 16+ | JSONB for flexible metadata, full-text search, pgvector-ready for future |
| **Cache/Queue** | Redis 7+ | Three logical namespaces: cache, task queue (ARQ), rate limiting |
| **File Storage** | MinIO | S3-compatible, self-hosted, handles document files |
| **Reverse Proxy** | Caddy or Nginx | Caddy: auto HTTPS; Nginx: proven, more config options |
| **Containerization** | Docker + Docker Compose | Dev environment parity, easy deployment |
| **Frontend Deploy** | Vercel | Zero-config Next.js, edge functions, preview deployments |
| **Backend Deploy** | VPS + Docker Compose | Full control, cost-effective for SaaS |
| **CI/CD** | GitHub Actions | Native GitHub integration, marketplace actions |

### 1.4 AI Integration Layer

| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| **AI Service** | QuasarFlow (external) | Separate repo, separate deployment, API-based |
| **Integration Pattern** | HTTP client + async polling | Non-blocking, timeout handling, retry logic |
| **Interface** | Abstract base class | Easy to swap/mock AI service during development |
| **Contract** | OpenAPI schema | Type-safe request/response between PAPERY ↔ QuasarFlow |

---

## 2. Version Pinning Strategy

```
# Backend — pin major.minor, allow patch
fastapi>=0.115,<1.0
sqlalchemy>=2.0,<3.0
pydantic>=2.9,<3.0
alembic>=1.14,<2.0

# Frontend — pin major
next@^15
react@^19
typescript@^5.7
```

---

## 3. What NOT to Use

| Technology | Reason |
|-----------|--------|
| **Django** | Sync-first ORM, heavyweight for API-only backend |
| **Express.js** | Python backend already chosen, no need for Node backend |
| **Prisma** | Python backend, Prisma is Node/TypeScript only |
| **MongoDB** | Relational data (users, projects, tiers, ACL) needs PostgreSQL |
| **Supabase** | Adds vendor lock-in, PAPERY needs custom auth/tier logic |
| **Firebase** | Not self-hostable, vendor lock-in |
| **tRPC** | Cross-language (Python BE + TS FE), REST is simpler |
| **GraphQL** | Adds complexity without clear benefit for this use case |
| **Celery** | ARQ is simpler, async-native, sufficient for document tasks |

---

## 4. Confidence Levels

| Decision | Confidence | Notes |
|----------|-----------|-------|
| FastAPI + Next.js 15 | **High** | Proven in v0, strong ecosystem |
| PostgreSQL + Redis | **High** | Industry standard for SaaS |
| SQLAlchemy 2.0 + Alembic | **High** | Best async ORM for Python |
| TanStack Query (new vs v0) | **High** | Major improvement over manual fetch |
| shadcn/ui | **High** | Dominant React component approach |
| ARQ over Celery | **Medium** | Simpler but less proven at scale |
| MinIO | **Medium** | Good for self-host, could switch to S3 in production |
| Vercel + VPS split | **Medium** | Works well but adds deployment complexity |

---

*Research based on 2025-2026 ecosystem analysis, v0 architecture decisions, and project requirements.*
