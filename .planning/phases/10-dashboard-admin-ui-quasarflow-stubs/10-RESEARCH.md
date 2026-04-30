# Phase 10: Dashboard, Admin UI & QuasarFlow Stubs - Research

**Researched:** 2026-04-28
**Domain:** Next.js dashboard/admin surfaces + FastAPI async AI-stub orchestration + CI verify pipeline
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Dashboard UX
- **D-01:** Use **hybrid layout** for project dashboard: table/list-first interaction with the ability to switch to card view.
- **D-02:** Toolbar scope for this phase is **Search + Sort only** (no advanced filter set in this phase).
- **D-03:** Empty state must be **actionable**: clear message + prominent CTA to create project.

### Admin UI Architecture & Scope
- **D-04:** Keep **one shared Next.js frontend codebase** (no separate React/Vite admin app in this phase).
- **D-05:** Separate user/admin surfaces by route and access boundary (`/(dashboard)` vs `/(admin)`) with superuser guard.
- **D-06:** Admin UI scope is **Core full** in this phase: users, tiers, rate-limits, and settings modules at production-ready basic level (list/detail/edit), excluding advanced analytics-heavy add-ons.

### QuasarFlow Async Stub Flow
- **D-07:** Default async status transport is **polling-first** for v1; keep contract extensible for future SSE upgrade.
- **D-08:** Retry policy is **light retry**: explicit timeout + bounded retries with backoff, then terminal failed status with manual retry from UI.

### CI/CD Policy
- **D-09:** Implement **verify-only CI** in this phase: lint, type-check, test, build on PR/push. Deployment automation is deferred.

### Claude's Discretion
- Exact polling interval/backoff constants and max retry count, as long as D-07 and D-08 are preserved.
- Concrete component composition for dashboard/admin pages inside existing frontend architecture.
- Exact GitHub Actions workflow decomposition (single workflow vs split jobs) while preserving D-09.

### Deferred Ideas (OUT OF SCOPE)
- Separate standalone admin frontend application (e.g., dedicated React/Vite codebase).
- SSE-as-default transport and dual-mode transport in the same phase.
- Auto-deploy pipeline in Phase 10 (deployment automation deferred beyond verify-only CI).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QFLOW-01 | Abstract QuasarFlow client interface | Architecture slice A2 defines provider interface + typed DTO boundaries |
| QFLOW-02 | Mock/stub implementation with realistic fake data | Architecture slice A2 + code example for deterministic stub responses |
| QFLOW-03 | Timeout/retry/circuit-breaker patterns | Architecture slice A3 + pitfalls/mitigations for bounded retry + open-state behavior |
| QFLOW-04 | Async pattern via queue + polling/SSE-ready | Architecture slice A1 + A3 define submit/status endpoints + polling contract |
| INFRA-05 | ARQ background task worker for async processing | Backend integration points identify current gap (`app/worker` placeholder) and required worker wiring |
| INFRA-13 | CI/CD verify pipeline (lint/type/test/build) | Validation architecture + Environment availability + workflow matrix |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Keep single PAPERY codebase conventions; no copying/importing from `.reference/` repositories. [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/CLAUDE.md]
- Preserve layered backend pattern (Router → Service → Repository → Model) and avoid direct ORM usage from service callers beyond repository abstraction. [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/CLAUDE.md]
- Use English in code/comments/docs artifacts; user communication remains Vietnamese. [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/CLAUDE.md]
- Never commit secrets or `.env`-style credentials. [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/CLAUDE.md]
- Frontend work must account for Next.js version-specific behavior; consult installed Next.js docs under `node_modules/next/dist/docs/` before implementation. [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/frontend/AGENTS.md]

## Summary

Phase 10 should be planned as three implementation slices running against existing foundations: (1) dashboard/admin UI integration in current Next.js app, (2) backend async QuasarFlow stub pipeline (enqueue + status), and (3) repository-level verify CI workflow. Existing code already provides strong anchors: localized route groups, auth/proxy guard, axios client with refresh queue, `/api/v1/admin/*` backend routes, and project list/member/invite APIs. [VERIFIED: codebase read]

The largest execution risk is not UI scaffolding; it is async orchestration completeness. ARQ requirement (INFRA-05) is currently unmet by executable worker tasks (only placeholder worker module exists), so planner should create explicit Wave 0 tasks for worker bootstrapping, queue contract, and task status persistence before wiring frontend polling. [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/worker/__init__.py]

**Primary recommendation:** Implement polling-first job contract (`POST submit` + `GET status/{job_id}`) with bounded retry and terminal states, then layer dashboard/admin pages on existing route/layout shells. [VERIFIED: 10-CONTEXT D-07/D-08]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 16.2.4 | Frontend app/router for dashboard + admin UI | Already active in repo and aligned with Phase 9 decisions. [VERIFIED: npm registry + frontend/package.json] |
| react | 19.2.5 | UI rendering/runtime | Existing codebase baseline for all UI modules. [VERIFIED: npm registry + frontend/package.json] |
| @tanstack/react-query | 5.100.5 | Query/mutation cache for dashboard/admin data | Existing foundation; ideal for polling status queries. [VERIFIED: npm registry + frontend/package.json] |
| axios | 1.15.2 | HTTP client/interceptors | Existing refresh/retry queue base already implemented. [VERIFIED: npm registry + frontend/src/lib/api/client.ts] |
| FastAPI | 0.128.8 (latest available) | Backend API for async submit/status endpoints | Existing backend framework and router aggregation already in place. [VERIFIED: pip index + backend/app/api/v1/__init__.py] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| zod | 4.3.6 | Runtime contract validation (responses/forms) | Validate job status payloads and admin forms. [VERIFIED: npm registry + frontend/package.json] |
| react-hook-form + @hookform/resolvers | 7.74.0 / 5.2.2 | Form control + zod resolver | Admin edit forms (users/tiers/rate-limits/settings). [VERIFIED: npm registry] |
| zustand | 5.0.12 | Client-only view state (view mode, panel states) | Dashboard list/card toggle and local UI state. [VERIFIED: npm registry + frontend/package.json] |
| sqlalchemy | 2.0.49 (latest available) | Persistence for async job records | Required if task status is stored in DB table. [VERIFIED: pip index + backend dependencies] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polling-first status transport | SSE-first | Conflicts with locked D-07 for this phase scope. [VERIFIED: 10-CONTEXT] |
| Shared Next.js app for admin | Separate admin SPA | Conflicts with locked D-04 and increases auth/routing duplication. [VERIFIED: 10-CONTEXT] |

**Installation (delta only if missing):**
```bash
# frontend (already present in package.json)
pnpm install

# backend (already declared in pyproject)
uv sync
```

## Architecture Patterns

### Recommended Project Structure
```text
frontend/src/app/[locale]/
├── (dashboard)/projects/            # User project list + actions UI
├── (admin)/users/                   # Admin user management pages
├── (admin)/tiers/                   # Admin tier pages
├── (admin)/rate-limits/             # Admin rule pages
└── (admin)/settings/                # Admin settings pages

backend/app/
├── services/quasarflow/             # Interface + stub + resiliency wrapper
├── worker/tasks/                    # ARQ job handlers
├── api/v1/ai_jobs.py                # submit/status endpoints
└── repositories/ai_job_repository.py# task status persistence
```

### Architecture Slice A1: Dashboard/Admin UI Integration
**What:** Reuse existing `(dashboard)` shell and add `(admin)` route group with superuser guard in proxy/middleware and server-side page gate. [VERIFIED: frontend route/layout files + backend admin router]
**When to use:** QFLOW-independent UI milestones and all admin modules from D-06.

### Architecture Slice A2: QuasarFlow Interface + Stub Provider
**What:** Define typed abstract client interface (submit-like methods + typed result DTOs), then implement deterministic mock provider returning realistic statuses/data. [VERIFIED: QFLOW-01/02 requirement text]
**When to use:** Before real QuasarFlow integration; keeps adapter swap low-risk.

### Architecture Slice A3: Async Orchestration Contract
**What:**
- `POST /api/v1/ai-jobs` returns `{job_id, status=pending}`
- Worker consumes queue, calls stub client with timeout + bounded retry
- `GET /api/v1/ai-jobs/{job_id}` returns terminal/non-terminal status for frontend polling
- Status enum: `pending | running | succeeded | failed | timed_out` [ASSUMED]

**When to use:** QFLOW-04 and INFRA-05 implementation.

### Anti-Patterns to Avoid
- **Direct UI calls to long-running AI endpoints:** breaks D-07 polling-first async contract and causes request timeouts. [VERIFIED: 10-CONTEXT]
- **Building separate admin frontend app:** violates D-04 and duplicates auth/i18n stack. [VERIFIED: 10-CONTEXT]
- **Unbounded retries in worker:** can stall queue and hide terminal failures from UI. [VERIFIED: D-08 + QFLOW-03]

## Existing Integration Points (Codebase)

### Frontend
- Dashboard shell entry: `frontend/src/app/[locale]/(dashboard)/layout.tsx` + `layout-client.tsx`. [VERIFIED: codebase read]
- Current dashboard page placeholder: `frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx`. [VERIFIED: codebase read]
- Shared navigation/header components: `components/layout/app-sidebar.tsx`, `top-bar.tsx`. [VERIFIED: codebase read]
- Route guard/proxy baseline: `frontend/src/proxy.ts` (protected roots currently `/dashboard`, `/projects`, `/settings`). [VERIFIED: codebase read]
- API interceptor baseline: `frontend/src/lib/api/client.ts` (401 refresh queue + `withCredentials`). [VERIFIED: codebase read]

### Backend
- API aggregate mount: `backend/app/api/v1/__init__.py` includes `admin_router` and `projects_router`. [VERIFIED: codebase read]
- Admin route group + superuser dependency: `backend/app/api/v1/admin/__init__.py`. [VERIFIED: codebase read]
- Existing admin module style: `backend/app/api/v1/admin/settings.py` + `services/settings_service.py`. [VERIFIED: codebase read]
- Existing project list/member/invite endpoints: `backend/app/api/v1/projects.py` + `services/project_service.py`. [VERIFIED: codebase read]
- Worker gap: `backend/app/worker/__init__.py` contains only module docstring (no executable tasks). [VERIFIED: codebase read]

## Don’t Hand-Roll

| Problem | Don’t Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Frontend request dedup/polling cache | Custom in-memory polling manager | TanStack Query polling (`refetchInterval`) | Reduces stale-state/race bugs. [VERIFIED: package + existing stack] |
| Auth refresh queue | New token refresh mechanism | Existing axios interceptor queue | Already handles concurrent 401 replay safely. [VERIFIED: frontend/src/lib/api/client.ts] |
| Admin authorization in UI only | Client-only role checks | Backend superuser gate + route-level frontend guard | Prevents privilege bypass. [VERIFIED: backend admin router] |
| Retry/circuit logic | Ad-hoc loops in handlers | Central resiliency wrapper service | Keeps retry policy consistent with D-08. [VERIFIED: 10-CONTEXT] |

## Common Pitfalls

1. **Mismatch between backend status model and frontend polling parser**
   - Mitigation: shared zod schema for job status response in frontend + pydantic schema in backend. [VERIFIED: stack + patterns]
2. **Overloading `/dashboard` page with all modules**
   - Mitigation: route-segment each module (`projects`, `admin/users`, etc.) and keep shell components thin. [VERIFIED: existing app router structure]
3. **Assuming CI exists because dependencies exist**
   - Mitigation: create root `.github/workflows` pipeline explicitly (current repo has none outside dependencies/reference dirs). [VERIFIED: glob results]
4. **Queue integration without status persistence**
   - Mitigation: persist job metadata/result/error so polling has stable source of truth. [ASSUMED]

## Runtime State Inventory

Not a rename/refactor/migration phase; runtime string/state migration audit is **not required** for this phase scope. [VERIFIED: phase goal in ROADMAP]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node | Frontend lint/build/typecheck | ✓ | v25.8.0 | — |
| npm | Registry/scripts | ✓ | 11.11.0 | — |
| pnpm | Frontend package manager decision | ✓ | 9.15.9 | npm (temporary only) |
| python3 | Backend tests/type/lint | ✓ | 3.9.6 | none (project requires >=3.12) |
| uv | Backend env/package execution | ✓ | 0.10.9 | pip/venv (slower, less aligned) |
| docker | Build/compose validation | ✓ | 29.2.1 | local non-container runs |
| gh | CI workflow ops/PR checks | ✓ | 2.88.1 | GitHub web UI |

**Missing dependencies with no fallback:**
- Python 3.12 runtime is not confirmed on host (current `python3` is 3.9.6, below backend requirement). [VERIFIED: pyproject.toml + environment probe]

**Missing dependencies with fallback:**
- None blocking besides Python version mismatch.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Backend: pytest 8.x; Frontend: no test runner script detected yet |
| Config file | Backend: `pyproject.toml` (`[tool.pytest.ini_options]`); Frontend: none |
| Quick run command | `cd backend && uv run pytest -q tests/test_project_acl.py tests/test_project_listing.py` |
| Full suite command | `cd backend && uv run pytest` + `cd frontend && pnpm lint && pnpm build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QFLOW-01 | Typed QuasarFlow interface methods compile and are used by service | unit/type | `cd backend && uv run mypy app/` | ❌ Wave 0 |
| QFLOW-02 | Stub returns realistic deterministic payloads | unit | `cd backend && uv run pytest tests/test_quasarflow_stub.py -q` | ❌ Wave 0 |
| QFLOW-03 | Timeout/retry/circuit transitions to terminal failure | unit/integration | `cd backend && uv run pytest tests/test_quasarflow_resilience.py -q` | ❌ Wave 0 |
| QFLOW-04 | Submit→queue→status polling path works | integration | `cd backend && uv run pytest tests/test_ai_job_flow.py -q` | ❌ Wave 0 |
| INFRA-05 | ARQ worker processes queued job functions | integration | `cd backend && uv run pytest tests/test_worker_tasks.py -q` | ❌ Wave 0 |
| INFRA-13 | Verify CI runs lint/type/test/build | pipeline smoke | `pnpm lint && pnpm build && cd backend && uv run ruff check . && uv run mypy app/ && uv run pytest -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** targeted command for modified module (`pytest -q <target>` + relevant lint/typecheck)
- **Per wave merge:** backend full pytest + frontend lint/build
- **Phase gate:** all required commands green in local + GitHub Actions verify workflow

### Wave 0 Gaps
- [ ] `backend/tests/test_quasarflow_stub.py`
- [ ] `backend/tests/test_quasarflow_resilience.py`
- [ ] `backend/tests/test_ai_job_flow.py`
- [ ] `backend/tests/test_worker_tasks.py`
- [ ] Frontend test framework decision/script (`test`) for UI modules
- [ ] `.github/workflows/verify.yml` (or split verify workflows)

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing JWT HttpOnly-cookie auth + refresh flow |
| V3 Session Management | yes | Existing refresh + token invalidation patterns |
| V4 Access Control | yes | Backend superuser dependency for `/admin/*` + project ACL dependencies |
| V5 Input Validation | yes | Pydantic (backend) + Zod (frontend) |
| V6 Cryptography | yes | Existing backend crypto libs (`python-jose`, passlib); no custom crypto |

### Known Threat Patterns for this phase
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Privilege escalation into admin routes | Elevation of Privilege | Enforce backend superuser checks; do not rely on client role checks only |
| Polling endpoint job-id enumeration | Information Disclosure | Use UUID job IDs + ownership checks in status endpoint [ASSUMED] |
| Retry storm under upstream failures | DoS | Bounded retry + backoff + circuit breaker open state |
| Stub payload injection into UI rendering | Tampering/XSS | Strict schema validation + escaped rendering |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Synchronous long-running HTTP AI calls | Queue-based async with status polling | Current SaaS standard [ASSUMED] | Better UX/reliability under variable latency |
| Separate admin SPA | Single app route-group partitioning | Current project locked decision (2026-04-27) | Lower operational overhead; shared auth/i18n/design system |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommended status enum includes `timed_out` as explicit terminal state | Architecture Slice A3 | UI/back-end contract mismatch |
| A2 | AI job metadata/status should persist in DB for polling stability | Common Pitfalls | Rework if team chooses Redis-only ephemeral state |
| A3 | Status endpoint should enforce owner scoping on job_id | Security Domain | Potential data leakage risk if omitted |
| A4 | Queue-based async pattern is prevailing standard for external AI latency | State of the Art | Low (mostly rationale quality) |

## Open Questions

1. Should AI job status be persisted in PostgreSQL table, Redis hash, or both?
2. What exact poll interval/backoff constants should be defaulted (e.g., 2s→5s→10s)?
3. Should frontend admin module get dedicated e2e tests now, or defer to post-phase stabilization?

## Sources

### Primary (HIGH confidence)
- Project context/decisions: `/Users/mqcbook/Documents/github/my-source/PAPERY/.planning/phases/10-dashboard-admin-ui-quasarflow-stubs/10-CONTEXT.md`
- Roadmap + requirement mapping: `/Users/mqcbook/Documents/github/my-source/PAPERY/.planning/ROADMAP.md`, `/Users/mqcbook/Documents/github/my-source/PAPERY/.planning/REQUIREMENTS.md`
- Frontend integration files: 
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/frontend/src/app/[locale]/(dashboard)/layout.tsx`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/frontend/src/app/[locale]/(dashboard)/layout-client.tsx`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/frontend/src/lib/api/client.ts`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/frontend/src/proxy.ts`
- Backend integration files:
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/v1/__init__.py`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/v1/admin/__init__.py`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/v1/admin/settings.py`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/v1/projects.py`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/services/project_service.py`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/services/settings_service.py`
  - `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/worker/__init__.py`
- Version verification from registries:
  - `npm view <pkg> version` outputs captured 2026-04-28
  - `python3 -m pip index versions <pkg>` outputs captured 2026-04-28

### Secondary (MEDIUM confidence)
- Environment probes via CLI (`node --version`, `pnpm --version`, `python3 --version`, etc.) on 2026-04-28.

### Tertiary (LOW confidence)
- Industry “state-of-the-art” generalizations explicitly tagged [ASSUMED].

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (direct repo + registry verification)
- Architecture: MEDIUM (integration points verified; async storage choices still open)
- Pitfalls: MEDIUM (partly inferred from common async/UI patterns)

**Research date:** 2026-04-28
**Valid until:** 2026-05-28
