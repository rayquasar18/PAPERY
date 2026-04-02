# PAPERY

## What This Is

PAPERY is an AI-powered document intelligence platform built as a SaaS product. Users upload documents (PDF, DOCX, XLSX, PPTX, CSV, TXT, Markdown), ask questions, get cited answers, generate reports, translate with structure preservation, and edit documents collaboratively with AI — all in one place. The AI processing is handled by a separate service (QuasarFlow), while PAPERY owns the full user experience, document management, and action execution.

## Core Value

Users can work with any document intelligently — ask questions, get accurate cited answers, and have AI directly modify their documents — through a polished, production-ready SaaS platform.

## Requirements

### Validated

- [x] Backend infrastructure with best practices (FastAPI, async, layered architecture, migrations) — Validated in Phase 1: Backend Core Infrastructure
- [x] Docker Compose development environment (PostgreSQL, Redis, MinIO, backend, worker) — Validated in Phase 1: Backend Core Infrastructure
- [x] File storage integration (MinIO/S3-compatible) for document uploads — Validated in Phase 1: Backend Core Infrastructure
- [x] API versioning, structured error handling — Validated in Phase 2: Error Handling, API Structure & Health
- [x] Deployment-ready configuration (production Docker image) — Validated in Phase 2: Error Handling, API Structure & Health

### Active

- [ ] Full authentication system (register, login, logout, email verification, password reset, OAuth)
- [ ] User tier system with role-based access control (admin, regular users, tier-based permissions)
- [ ] Admin panel for managing users, tiers, rate limits, and system configuration
- [ ] Project system (CRUD, ACL-based access control per resource)
- [ ] Frontend infrastructure with best practices (Next.js 15, App Router, i18n, Zustand, Zod validation)
- [ ] Rate limiting (middleware + tier-based enforcement)
- [ ] Background task processing (ARQ worker)
- [ ] Deployment-ready configuration (Vercel for frontend)
- [ ] Integration point for external AI Service (QuasarFlow API) — stub/interface ready

### Out of Scope

- AI/LLM logic — handled by QuasarFlow service (separate repo)
- Document Q&A with citations — v2 (depends on QuasarFlow API being ready)
- Document editing (AI-powered add/edit/remove) — v2
- Multi-agent research workflows — v2
- Template system and formatted document generation — v2
- Multi-language document translation with structure preservation — v2
- Marketplace for community templates — v2+
- Knowledge graph and topic clustering — v2+
- Mobile app — web-first

## Context

**Architecture:** Full-stack SaaS — React/Next.js 15 frontend + Python/FastAPI backend + PostgreSQL + Redis + MinIO. Follows layered monolith pattern (Router → Dependencies → CRUD → Schema → Model).

**AI Service separation:** PAPERY does not contain LLM/AI logic. All AI processing is delegated to QuasarFlow (quasarflow.com/) via API calls. Flow: Frontend → PAPERY Backend → QuasarFlow API → AI processes → returns result → PAPERY Backend executes actions (CRUD, document modifications, response rendering) → Frontend updates.

**Previous work:** A v0 implementation existed (142 commits) but was reset on 2026-03-31 for a clean start. Architecture decisions from v0 are preserved in `.planning/codebase/` documents and inform v1 design. Key patterns to carry forward: dual ID strategy (int internal + UUID public), soft deletes, ACL-based access control, schema separation (Read/Create/Update/Internal variants).

**Reference projects:** `.reference/open-notebook/` (Open Notebook — open-source document AI platform) for architecture patterns. Also inspired by Google NotebookLM for UX concepts. PAPERY differentiates by offering direct document editing (both visual editor and chat commands) alongside Q&A capabilities.

**Tech stack decisions (from v0, carrying forward):**
- Backend: FastAPI (latest), SQLAlchemy 2.0 async, fastcrud, Pydantic v2, Alembic, ARQ
- Frontend: Next.js 15, React 19, TypeScript, Zustand, Zod, next-intl, Shadcn/ui
- Infrastructure: PostgreSQL, Redis (cache + queue + rate limit), MinIO (S3-compatible file storage)
- Auth: JWT (access + refresh tokens), bcrypt, email verification, OAuth (Google, GitHub)

**Target audience:** Public/community users — SaaS model with tiered access (free, pro, enterprise).

**Deployment:** Vercel (frontend) + VPS with Docker (backend, PostgreSQL, Redis, MinIO, worker). Enterprise-grade setup.

## Constraints

- **License:** CC BY-NC 4.0 — non-commercial use only
- **AI dependency:** All AI features depend on QuasarFlow API availability; v1 must be functional without it
- **Language:** Code in English, user communication in Vietnamese
- **Reference isolation:** `.reference/` is read-only inspiration — no code copying or importing
- **Git workflow:** Gitflow branching, immediate commit+push, descriptive messages

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate AI Service (QuasarFlow) | Decouple AI complexity from document platform; allows independent scaling and development | — Pending |
| FastAPI + Next.js 15 stack (from v0) | Proven async performance, modern React features, strong typing at both layers | — Pending |
| SaaS-first with tier system | Target public community users, monetization-ready architecture | — Pending |
| v1 = Infrastructure + Auth + Project (no AI features) | Ship solid foundation first; AI features depend on QuasarFlow readiness | — Pending |
| Dual editor approach (visual + chat) for document editing | Maximum flexibility for users — different workflows for different contexts | — Pending |
| Clean restart from v0 | Fresh codebase with latest versions; carry forward architectural lessons, not code | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-03 after Phase 2 completion*
