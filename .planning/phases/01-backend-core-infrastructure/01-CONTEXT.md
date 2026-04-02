# Phase 1: Backend Core Infrastructure - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the foundational backend skeleton — project structure, database connections, Redis, MinIO, configuration system, Docker Compose dev environment, and core patterns (dual-ID, soft delete, layered architecture). This phase creates the monorepo structure, all infrastructure services, and the architectural foundation that every subsequent phase depends on.

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- **D-01:** Monorepo layout following Dify enterprise pattern — `backend/`, `frontend/`, `docker/`, `scripts/`, `Makefile` at root
- **D-02:** Backend uses flat `backend/app/` structure (Dify-style, not nested `src/app/`). Directories: `api/v1/`, `core/`, `models/`, `schemas/`, `crud/`, `services/`, `extensions/`, `exceptions/`
- **D-03:** Package manager: **uv** (Rust-based, fastest available, Dify has migrated to uv). Lock file: `uv.lock`, config: `pyproject.toml`
- **D-04:** Reference project **Dify** cloned to `.reference/dify/` for enterprise architecture patterns. Follow Dify's enterprise infrastructure patterns but with modern tech stack (FastAPI, Pydantic v2, SQLAlchemy 2.0 async, fastcrud)

### Database & Migrations
- **D-05:** PostgreSQL **17** (latest stable, JSON improvements, better logical replication)
- **D-06:** Alembic with **auto-generate** workflow — generate from model changes, review before apply
- **D-07:** Database naming: **snake_case** everywhere (tables, columns) — standard PostgreSQL convention
- **D-08:** Seed data via **CLI scripts** in `scripts/` directory (Dify-style) — create admin user, default tiers, test data
- **D-09:** SQLAlchemy **full enterprise pool config** (Dify-style) — pool_size, max_overflow, pool_recycle, pool_pre_ping, pool_timeout all configurable via environment variables
- **D-10:** Testing database: **ephemeral** — each test run creates/drops a fresh database for isolation
- **D-11:** Alembic migration files **committed to git** — enables team sync and CI auto-migration

### Docker Compose Setup
- **D-12:** **Split Docker Compose** (Dify-style):
  - `docker/docker-compose.yaml` — Full stack for production
  - `docker/docker-compose.middleware.yaml` — DB + Redis + MinIO only for dev
  - Dev flow: middleware containers + local backend/frontend (uv/pnpm) for fast hot-reload
- **D-13:** **Split Dockerfiles** — `Dockerfile.dev` (quick build) + `Dockerfile` (multi-stage production, slim)
- **D-14:** **Makefile** for dev environment management (Dify-style):
  - `make dev-setup` — one-command bootstrap (copy env, start middleware, install deps, run migrations)
  - `make dev-clean` — teardown containers and volumes
  - `make test`, `make lint`, `make build`, `make migrate`, `make seed`

### Config & Environment Variables
- **D-15:** **Modular Pydantic Settings** (Dify-style) — separate config modules:
  - `backend/app/core/config/` with `app.py`, `database.py`, `redis.py`, `minio.py`, `security.py`, `email.py`, `cors.py`
  - Composed into single `AppConfig` class via multiple inheritance
- **D-16:** **Service prefix** naming for env vars: `POSTGRES_*`, `REDIS_CACHE_*`, `REDIS_QUEUE_*`, `REDIS_RATE_LIMIT_*`, `MINIO_*`, `SMTP_*`, `SECRET_KEY`, `APP_*`
- **D-17:** **Single root `.env.example`** containing all env vars for all components (not per-component like Dify)
- **D-18:** **Strict startup validation** — app refuses to start if required env vars are missing or contain placeholder values. Pydantic validators reject known placeholders (`changeme`, `secret`, `sk-xxx`) and enforce minimum security (e.g., SECRET_KEY >= 32 chars)

### Claude's Discretion
- Extensions init pattern (how to initialize DB, Redis, MinIO connections at startup) — follow FastAPI lifespan pattern adapted from Dify's extension approach
- Logging setup and levels — standard structured logging
- Test fixtures and conftest.py organization
- Pre-commit hook configuration (ruff, mypy)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Enterprise Architecture Reference
- `.reference/dify/` — Enterprise AI platform (Dify). Study file structure, Docker setup, config patterns, Makefile, extensions. **Do NOT copy code** — learn patterns and implement independently for FastAPI
- `.reference/dify/api/configs/` — Modular Pydantic Settings pattern (multiple inheritance composition)
- `.reference/dify/api/extensions/` — Extension init pattern (ext_database.py, ext_redis.py, ext_storage.py)
- `.reference/dify/docker/` — Docker Compose split (middleware vs full stack), env file strategy
- `.reference/dify/Makefile` — Dev environment management (dev-setup, dev-clean, prepare-*)
- `.reference/dify/api/pyproject.toml` — uv-based dependency management

### Project Documentation
- `.planning/ROADMAP.md` — Phase 1 requirements (INFRA-01, 02, 03, 04, 09, 11, 14, 15) and success criteria
- `.planning/REQUIREMENTS.md` — Full requirement details and traceability
- `.planning/codebase/ARCHITECTURE.md` — v0 architectural patterns to carry forward (layered monolith, extension points)
- `.planning/codebase/CONVENTIONS.md` — Code style and naming conventions

### v0 Architecture Patterns (carry forward, don't copy)
- `.planning/codebase/ARCHITECTURE.md` §3 — Backend layers (Router → Dependencies → CRUD → Schema → Model)
- `.planning/codebase/ARCHITECTURE.md` §3.5 — Schema separation pattern (Read/ReadInternal/Create/CreateInternal/Update/Delete)
- `.planning/codebase/ARCHITECTURE.md` §3.6 — Model mixins (UUIDMixin, TimestampMixin, SoftDeleteMixin)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No application code exists — this is a greenfield phase
- Scaffold files exist: README.md, CLAUDE.md, CONTRIBUTING.md, .gitignore, LICENSE, docs/

### Established Patterns
- v0 architecture patterns documented in `.planning/codebase/ARCHITECTURE.md` — proven layered architecture to follow
- Dify enterprise patterns available in `.reference/dify/` — config modularization, Docker split, Makefile automation

### Integration Points
- Phase 2 will build on: error handling, API versioning, health checks — needs the FastAPI app, config, and Docker setup from this phase
- Phase 3 will build on: JWT security, user model, Redis token blacklist — needs database, Redis, models from this phase
- All subsequent phases depend on the patterns established here (dual-ID, soft delete, layered CRUD)

</code_context>

<specifics>
## Specific Ideas

- **Follow Dify enterprise patterns** — user explicitly wants Dify-grade infrastructure quality. Study Dify's file organization, Docker patterns, config management, and Makefile automation
- **Modern tech stack** — while following Dify patterns, use latest technologies: FastAPI (not Flask), Pydantic v2 (not v1), SQLAlchemy 2.0 async (not sync), uv (not pip), fastcrud for repository pattern
- **Python 3.12+** required for latest type hint features and performance improvements

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-backend-core-infrastructure*
*Context gathered: 2026-04-02*
