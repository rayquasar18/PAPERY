# Phase 10: Dashboard, Admin UI & QuasarFlow Stubs - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Build v1 user dashboard UI (project management surface), admin dashboard UI, and QuasarFlow integration stubs on top of existing backend APIs and frontend foundation. This phase also delivers async AI-call simulation flow (via worker queue) and CI verification pipeline for consistent delivery quality.

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` — Phase 10 goal, requirement mapping (QFLOW-01..04, INFRA-05, INFRA-13), and success criteria.
- `.planning/REQUIREMENTS.md` — Canonical requirement definitions for QFLOW and infra CI/worker requirements.
- `.planning/PROJECT.md` — Product constraints and v1 scope boundaries.

### Prior Phase Decisions That Constrain Phase 10
- `.planning/phases/09-frontend-foundation-auth-ui/09-CONTEXT.md` — Frontend stack, layout shell, auth middleware, i18n, and UX conventions.
- `.planning/phases/07-admin-panel-backend/07-CONTEXT.md` — Admin backend route structure and domain semantics (users/tiers/rate-limits/settings).
- `.planning/phases/08-project-system-acl/08-CONTEXT.md` — Project listing/search/member semantics consumed by dashboard UI.

### Existing Code & Integration Points
- `frontend/src/app/[locale]/(dashboard)/layout.tsx` — Current dashboard route shell.
- `frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx` — Current dashboard page integration point.
- `frontend/src/app/[locale]/(dashboard)/layout-client.tsx` — Client layout behavior for dashboard group.
- `frontend/src/components/layout/app-sidebar.tsx` — Shared sidebar/navigation pattern.
- `frontend/src/components/layout/top-bar.tsx` — Header/top-bar pattern for dashboard/admin UX consistency.
- `frontend/src/proxy.ts` — Route protection/proxy behavior baseline.
- `frontend/src/lib/api/client.ts` — Typed API client baseline and interception points.
- `backend/app/main.py` — Router/worker integration entry point.
- `backend/app/api/v1/admin/settings.py` — Existing admin domain route style reference.
- `backend/app/services/settings_service.py` — Service/repository pattern for admin settings behavior.

### Codebase Guidance Docs
- `.planning/codebase/STRUCTURE.md` — Intended app/module structure and naming boundaries.
- `.planning/codebase/CONVENTIONS.md` — Naming, typing, and commit conventions.
- `.planning/codebase/STACK.md` — Stack-level constraints and alignment.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Frontend already has dashboard route group, sidebar, top bar, auth flow pages, and API client primitives that can be reused for phase 10 UI surfaces.
- Backend already has admin backend endpoints/domain patterns (Phase 7) and project ACL/listing domain (Phase 8) to be consumed by dashboard/admin UI.

### Established Patterns
- Single Next.js app with locale route prefix and protected route behaviors already exists.
- Layered backend architecture and class-based service/repository patterns are established and should be preserved for QFlow stub orchestration.
- Existing frontend state/query foundations (Query client + stores + auth hooks) support adding dashboard/admin feature modules without new app split.

### Integration Points
- Add admin UI route group under existing localized app tree with superuser-only gate.
- Connect dashboard project list/actions to current backend project endpoints and ACL semantics.
- Introduce QuasarFlow abstraction + stub provider in backend service layer and wire async flow through worker/task orchestration.
- Add GitHub Actions workflows for verify-only CI at repository root.

</code_context>

<specifics>
## Specific Ideas

- Admin dashboard should be isolated by access and route boundaries, but still live in the same frontend app for consistency and delivery speed.
- Keep v1 QFlow transport operationally simple (polling-first), then evolve to SSE later without breaking API contracts.
- Prioritize practical usability over overbuilding: core full admin modules with essential operations first.

</specifics>

<deferred>
## Deferred Ideas

- Separate standalone admin frontend application (e.g., dedicated React/Vite codebase).
- SSE-as-default transport and dual-mode transport in the same phase.
- Auto-deploy pipeline in Phase 10 (deployment automation deferred beyond verify-only CI).

</deferred>

---

*Phase: 10-dashboard-admin-ui-quasarflow-stubs*
*Context gathered: 2026-04-27*
