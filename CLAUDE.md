# CLAUDE.md — Project Instructions for AI Agents

> These instructions are **mandatory**. They override any default behavior.

## Project Overview

PAPERY is an AI-powered document intelligence platform. It helps users work with documents (PDF, DOCX, Excel, etc.) for research, Q&A, learning, extraction, citation, summarization, insight generation, multi-language translation (preserving document structure), and multi-agent research workflows that produce formatted outputs (scientific reports, templates, marketplace rules, etc.).

**This project is licensed under CC BY-NC 4.0 — commercial use is strictly prohibited.**

---

## 1. Git Workflow — MANDATORY

### 1.1 Commit Immediately After Every Change

- **Every code change MUST be committed and pushed immediately** — no batching, no waiting.
- One logical change = one commit. Do not accumulate uncommitted work.
- Write clear, descriptive commit messages (English) explaining the "why", not just the "what".
- Always push to the correct remote branch right after committing.

### 1.2 Branch Strategy (Gitflow)

| Branch | Purpose | Base | Merges into |
|---|---|---|---|
| `main` | Production-ready, stable releases | — | — |
| `develop` | Integration branch for features | `main` | `main` (via release) |
| `feature/*` | New features | `develop` | `develop` |
| `hotfix/*` | Urgent production fixes | `main` | `main` + `develop` |
| `release/*` | Release preparation & QA | `develop` | `main` + `develop` |
| `staging` | Pre-production testing | `develop` | — |

**Rules:**
- Never commit directly to `main` — only via `hotfix/*` or `release/*` merges.
- All feature work goes on `feature/<name>` branched from `develop`.
- Hotfixes branch from `main`, merge back to both `main` and `develop`.
- Always use descriptive branch names: `feature/pdf-parser`, `hotfix/auth-crash`, `release/v1.2`.
- Delete feature/hotfix branches after merge.

### 1.3 Commit Message Format

```
<type>: <short description>

<optional body explaining why>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`, `perf`, `ci`

---

## 2. `.reference/` Directory — READ-ONLY REFERENCE

### 2.1 Absolute Isolation

- `.reference/` contains cloned repositories and documents **for reference only**.
- These are **completely independent** from PAPERY source code.
- **NEVER** import, copy, symlink, or directly use any code from `.reference/` in the project.
- **NEVER** modify any file inside `.reference/`.
- **NEVER** let reference repos influence the project's dependency tree, configs, or structure.
- Reference material is for **reading, understanding patterns, and learning approaches** — then implement independently in PAPERY.

### 2.2 What's Inside

- `open-notebook/` — Open source document AI platform (architecture reference)
- Additional repos or documents may be added over time.

### 2.3 How to Use References

✅ DO: Read code to understand architectural patterns and approaches.
✅ DO: Learn from their solutions to similar problems.
✅ DO: Use as inspiration for PAPERY's own independent implementation.
❌ DON'T: Copy-paste code from references.
❌ DON'T: Add reference repos as git submodules or dependencies.
❌ DON'T: Reference their file paths in any PAPERY source file or config.

---

## 3. Code Quality

- Write clean, well-documented, production-quality code.
- Follow existing project conventions and patterns.
- Include type hints (Python) / TypeScript types (frontend).
- Write tests for new features and bug fixes.
- Handle errors gracefully — never silently swallow exceptions.

---

## 4. Communication

- When explaining, asking questions, or communicating with the user: **always use Vietnamese (Tiếng Việt)**.
- Code, comments, commit messages, documentation, and technical content: **English**.

---

## 5. Security

- Never commit secrets, API keys, tokens, or credentials.
- Use `.env` files for environment variables (already in `.gitignore`).
- Never commit `.env`, `credentials.json`, or similar files.

---

## 6. Project Naming

- This project is **PAPERY** — an independent, original project.
- Do not reference, mention, or compare to any specific commercial product names in the codebase or documentation.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**PAPERY**

PAPERY is an AI-powered document intelligence platform built as a SaaS product. Users upload documents (PDF, DOCX, XLSX, PPTX, CSV, TXT, Markdown), ask questions, get cited answers, generate reports, translate with structure preservation, and edit documents collaboratively with AI — all in one place. The AI processing is handled by a separate service (QuasarFlow), while PAPERY owns the full user experience, document management, and action execution.

**Core Value:** Users can work with any document intelligently — ask questions, get accurate cited answers, and have AI directly modify their documents — through a polished, production-ready SaaS platform.

### Constraints

- **License:** CC BY-NC 4.0 — non-commercial use only
- **AI dependency:** All AI features depend on QuasarFlow API availability; v1 must be functional without it
- **Language:** Code in English, user communication in Vietnamese
- **Reference isolation:** `.reference/` is read-only inspiration — no code copying or importing
- **Git workflow:** Gitflow branching, immediate commit+push, descriptive messages
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## 1. Project State
| Artifact | Exists? | Notes |
|---|---|---|
| Application source code | ❌ | Not yet written |
| `package.json` / `pyproject.toml` | ❌ | Not yet created |
| Docker / CI config | ❌ | Not yet created |
| Project scaffold files | ✅ | `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `.gitignore`, `LICENSE` |
| Planning config | ✅ | `.planning/config.json` — AI agent model profiles |
| Reference material | ✅ | `.reference/open-notebook/` — read-only architectural reference |
## 2. Confirmed: Languages & Runtimes
### 2.1 Python (Backend)
| Signal | Detail |
|---|---|
| `__pycache__/`, `*.pyc`, `*.pyo` | Python bytecode |
| `.venv/`, `venv/`, `env/` | Python virtual environments |
| `poetry.lock` (ignored), `.pdm.toml` | Poetry / PDM package managers |
| `celerybeat-schedule`, `celerybeat.pid` | Celery task queue |
| `db.sqlite3` | SQLite (Django or similar) |
| `local_settings.py` | Django-style local settings pattern |
| `migrations/versions/` | Alembic database migrations |
| `.mypy_cache/`, `.pyre/`, `.pytype/` | Python type checkers |
| `pytest` cache (`.pytest_cache/`) | Python testing framework |
| `.ipynb_checkpoints` | Jupyter notebooks |
### 2.2 TypeScript / JavaScript (Frontend)
| Signal | Detail |
|---|---|
| `/.next/`, `/out/` | Next.js build outputs |
| `/node_modules/` | Node.js packages |
| `*.tsbuildinfo`, `next-env.d.ts` | TypeScript / Next.js generated files |
| `.vercel` | Vercel deployment |
| `npm-debug.log*`, `yarn-debug.log*`, `yarn-error.log*` | npm / Yarn package managers |
| `/.pnp`, `.pnp.js`, `.yarn/install-state.gz` | Yarn PnP mode |
| `/coverage` | Test coverage output |
## 3. Planned: Framework Stack (Inferred)
### 3.1 Backend
| Component | Technology | Confidence | Basis |
|---|---|---|---|
| Language | Python 3.11+ | High | `.gitignore` signals |
| Web framework | FastAPI | Medium | Alembic migrations signal + reference architecture |
| Task queue | Celery | Medium | `celerybeat-*` in `.gitignore` |
| Database migrations | Alembic | Medium | `migrations/versions/` in `.gitignore` |
| Package manager | Poetry or PDM | Medium | Both in `.gitignore` |
| Testing | Pytest | High | `.pytest_cache/` in `.gitignore` |
| Type checking | Mypy | Medium | `.mypy_cache/` in `.gitignore` |
| Notebooks/exploration | Jupyter | Low | `.ipynb_checkpoints` in `.gitignore` |
### 3.2 Frontend
| Component | Technology | Confidence | Basis |
|---|---|---|---|
| Language | TypeScript | High | `*.tsbuildinfo`, `next-env.d.ts` in `.gitignore` |
| Framework | Next.js | High | `/.next/`, `next-env.d.ts` in `.gitignore` |
| Runtime | Node.js | High | `/node_modules/` in `.gitignore` |
| Package manager | npm or Yarn | High | lock file patterns in `.gitignore` |
| Deployment target | Vercel (optional) | Low | `.vercel` in `.gitignore` |
### 3.3 AI / ML Layer (Planned)
| Feature | Technology Options | Notes |
|---|---|---|
| LLM orchestration | LangChain / LangGraph | Multi-agent research workflows required |
| Embedding & vector search | OpenAI, Cohere, or local | Semantic Q&A, cross-doc analysis |
| Document parsing | pdfplumber, python-docx, openpyxl | PDF, DOCX, XLSX support listed in README |
| Multi-language translation | LLM-based or DeepL | Structure-preserving translation |
| OCR (if needed) | Tesseract, Surya, or cloud OCR | For scanned PDFs |
## 4. Configuration
### 4.1 Environment Variables
- AI provider API keys (OpenAI, Anthropic, Google, etc.)
- Database connection strings
- JWT/auth secrets
- Storage configuration (S3 or local)
### 4.2 Planning Agent Config
## 5. Development Tooling (Inferred)
| Tool | Signal |
|---|---|
| `ruff` | Expected (standard Python linter for modern projects) |
| `mypy` | `.mypy_cache/` in `.gitignore` |
| `pytest` | `.pytest_cache/` in `.gitignore` |
| `pre-commit` | Likely (common in Python projects using ruff + mypy) |
| `docker` / `docker compose` | Likely (not yet confirmed) |
## 6. Architecture Overview (Planned)
## 7. Open Decisions
- [ ] Primary database: PostgreSQL vs SurrealDB vs other
- [ ] Vector store: pgvector vs Qdrant vs Weaviate vs Chroma
- [ ] File storage: Local filesystem vs S3-compatible
- [ ] Auth system: Clerk / Auth.js / Supabase Auth / custom JWT
- [ ] Task queue: Celery+Redis vs native async vs BullMQ (Node)
- [ ] Frontend styling: Tailwind CSS vs other
- [ ] Component library: Shadcn/ui vs Radix vs other
- [ ] Container orchestration: Docker Compose vs Kubernetes
- [ ] CI/CD: GitHub Actions vs other
- [ ] Monorepo vs multi-repo structure
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Status
- `CLAUDE.md` project instructions
- `CONTRIBUTING.md` guidelines
- `.gitignore` signals (Python + Next.js patterns)
- `.reference/open-notebook/` architecture patterns
## Planned Code Style
### Python (Backend)
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes
- **Type hints:** Required on all functions (per CLAUDE.md)
- **Error handling:** Never silently swallow exceptions (per CLAUDE.md)
- **Comments/code:** English only
- **Linting:** Ruff (inferred from reference project)
- **Type checking:** mypy (inferred from `.mypy_cache/` in `.gitignore`)
### TypeScript (Frontend)
- **Naming:** `kebab-case` files, `PascalCase` components
- **Types:** TypeScript types required (per CLAUDE.md)
- **Style:** Likely Tailwind CSS (inferred from reference project patterns)
### Git Conventions
- **Commit format:** `<type>: <description>` (feat, fix, refactor, docs, test, chore, style, perf, ci)
- **Co-author:** `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- **Branch strategy:** Gitflow (main, develop, feature/*, hotfix/*, release/*)
- **Commit frequency:** Every change committed and pushed immediately
### Communication
- **User-facing:** Vietnamese (Tiếng Việt)
- **Code/docs/commits:** English
## Patterns to Establish
- [ ] API error response format
- [ ] Logging strategy and levels
- [ ] Environment variable naming
- [ ] Database naming conventions
- [ ] Component file structure (frontend)
- [ ] State management patterns
- [ ] API client patterns
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## 1. System Overview
- A **React/Next.js** frontend (SPA + SSR)
- A **Python/FastAPI** backend (async REST API)
- A **PostgreSQL** relational database
- **Redis** for caching, task queuing, and rate limiting
- **MinIO** (S3-compatible) for raw file storage
- An **async task worker** (ARQ/Celery) for background document processing
- Future: AI/LLM service layer and multi-agent orchestration
```
```
## 2. Architectural Pattern
### Overall: Layered Monolith (Modular Monolith → Microservices-ready)
```
```
### Frontend: Feature-scoped App Router Structure
```
```
## 3. Backend Layers in Detail
### 3.1 Entry Point
```
```
- Initializes Redis connections (cache, queue, rate limiter)
- Initializes MinIO bucket (file storage)
- Runs DB table creation (development mode)
### 3.2 API / Router Layer (`app/api/v1/`)
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
```python
```
- Every resource (project, document, chat_session) has ACL entries
- Before any resource operation, ACL is checked: `crud_access_controls.exists(resource_uuid, user_id)`
- Superusers bypass ACL checks
### 3.4 Repository Layer (`app/repositories/`)

**Rule: ALL database queries MUST go through repositories. Services MUST NOT use SQLAlchemy directly.**

```
API → Service (business logic) → Repository (data access) → SQLAlchemy / DB
```

- `base.py` — `BaseRepository[ModelType]` generic async CRUD:
  - `get(**filters)` — single record by any field: `repo.get(email="x")`, `repo.get(uuid=u)`
  - `get_multi(skip, limit, **filters)` — paginated list with optional filters
  - `create(instance)` — add + commit + refresh
  - `update(instance)` — commit + refresh
  - `soft_delete(instance)` — set `deleted_at` timestamp
  - `delete(instance)` — hard delete (permanent, use with caution)
  - Soft-delete filtering (`deleted_at IS NULL`) is applied automatically
- `user_repository.py` — `UserRepository(BaseRepository[User])` with `create_user(...)` convenience method
- Future: `project_repository.py`, `document_repository.py`, etc.

**When adding a new model:**
1. Create `app/repositories/<model>_repository.py` inheriting `BaseRepository[Model]`
2. Add domain-specific convenience methods (like `create_user`) only if needed
3. Use `get(**filters)` for all lookups — do NOT create `get_by_<field>` methods
### 3.5 Schema Layer (`app/schemas/`)
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
```python
```
```
```
### 3.7 Core & Infrastructure (`app/core/`, `app/configs/`, `app/infra/`, `app/services/`, `app/utils/`, `app/worker/`)

**`app/core/`** — Foundation only (DB + exceptions):
| Module | Responsibility |
|--------|---------------|
| `db/session.py` | SQLAlchemy async engine + session factory |
| `exceptions/` | PaperyHTTPException + convenience subclasses (401, 403, 404, 409, 429) |
| `security.py` | JWT encode/decode, bcrypt hashing, token blacklist, token families |

**`app/configs/`** — Pydantic-settings config classes:
| Module | Responsibility |
|--------|---------------|
| `app.py`, `database.py`, `redis.py`, `minio.py`, `security.py`, `email.py`, `cors.py`, `admin.py` | Composed into `settings` singleton |

**`app/infra/`** — External service clients:
| Module | Responsibility |
|--------|---------------|
| `redis/client.py` | Redis singleton (cache, queue, rate limit — three logical DBs) |
| `minio/client.py` | MinIO singleton, bucket management, presigned URLs |

**`app/services/`** — Business logic layer (calls repositories, raises domain exceptions):
| Module | Responsibility |
|--------|---------------|
| `auth_service.py` | Registration, login, logout, token rotation, email verification, superuser bootstrap |

**`app/utils/`** — Shared utilities:
| Module | Responsibility |
|--------|---------------|
| `email.py` | SMTP email delivery |
| `rate_limit.py` | Redis rate limit enforcement |

**`app/middleware/`** — HTTP middleware:
| Module | Responsibility |
|--------|---------------|
| `request_id.py` | X-Request-ID header injection |

**`app/worker/`** — Background job definitions (ARQ):
### 3.8 Migrations (`migrations/`)
- `env.py` — async migration runner
- `versions/` — gitignored; scripts in `scripts/` bootstrap initial data
## 4. Frontend Layers in Detail
### 4.1 Entry Points
```
```
### 4.2 Route Groups
```
```
### 4.3 Data Flow (Frontend)
```
```
### 4.4 State Management
- `store/chat-list.store.ts` — chat sessions list, selected chat, sort order
- `store/project-list.store.ts` — projects list, selected project
- `context/auth-context.tsx` — user identity, login/logout
- `context/user-context.tsx` — user profile data
- `context/theme-context.tsx` — light/dark/system preference
### 4.5 HTTP Client (`lib/http.ts`)
```typescript
```
- Automatic Bearer token injection (cookie-read, SSR + client-side)
- API versioning via `API_VERSION` env var
- Centralized error normalization (`lib/error.ts`)
- Token refresh on 401 (`hooks/token-refresher.ts`)
### 4.6 Schema Validation (`schemas/`)
- `auth.schemas.ts` — login, register, token response
- `project-list.schemas.ts` — project list items
- `chat-list.schemas.ts` — chat session items
- `user.schemas.ts` — user profile
### 4.7 Key UI Components (Chat Interface)
```
```
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
## 6. Cross-Cutting Concerns
### 6.1 Authentication & Authorization
- **Mechanism:** JWT (HS256) access tokens (30min) + refresh tokens (7 days) stored as HTTP-only cookies
- **Auth types:** Local (email/password), Google OAuth, GitHub OAuth
- **Authorization:** Role-based (regular user vs superuser) + resource-level ACL
- **Token blacklist:** Redis-backed logout invalidation
- **Email verification:** Required before account activation
### 6.2 Rate Limiting
- Users belong to a `Tier` (e.g., "free", "pro")
- Each tier has per-endpoint `RateLimit` rules (requests / time window)
- Redis counters track usage per user/IP per endpoint
- Default limits apply when no tier-specific rule exists
### 6.3 File Storage
### 6.4 Internationalization
- **Backend:** locale-aware email templates (Jinja2)
- **Frontend:** `next-intl` with locale-prefixed routing (`/en/`, `/vi/`, `/fr/`)
- Translation files: `frontend/src/locale/en.json`, `vi.json`
- Language switcher component in UI
### 6.5 Soft Deletes
## 7. Planned Architecture Additions
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
<!-- GSD:architecture-end -->