---
phase: 10-dashboard-admin-ui-quasarflow-stubs
plan: 03
subsystem: ui
tags: [nextjs, dashboard, admin, polling, zod, route-guards]
requires:
  - phase: 10-dashboard-admin-ui-quasarflow-stubs
    provides: Polling-first AI job backend contract and persisted async job lifecycle
provides:
  - Dashboard projects surface with list-first UX, cards toggle, and empty-state CTA
  - Frontend AI job polling client and zod-validated async status contract
  - Admin route partition under /admin/* inside the shared Next.js app
affects: [QFLOW-04, dashboard-projects-ui, admin-route-boundary, plan-10-04-verification]
tech-stack:
  added: []
  patterns:
    - Shared app admin partition via route group plus explicit /admin URL segment
    - Zod validation at frontend boundary for AI jobs and admin responses
    - Polling-ready frontend contract separated into dedicated API client modules
key-files:
  created:
    - frontend/src/app/[locale]/(dashboard)/projects/page.tsx
    - frontend/src/app/[locale]/(admin)/admin/layout.tsx
    - frontend/src/app/[locale]/(admin)/admin/users/page.tsx
    - frontend/src/app/[locale]/(admin)/admin/tiers/page.tsx
    - frontend/src/app/[locale]/(admin)/admin/rate-limits/page.tsx
    - frontend/src/app/[locale]/(admin)/admin/settings/page.tsx
    - frontend/src/lib/api/ai-jobs.ts
    - frontend/src/lib/api/admin.ts
    - frontend/src/schemas/ai-job.schemas.ts
    - frontend/src/schemas/admin.schemas.ts
  modified:
    - frontend/src/proxy.ts
    - frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx
    - frontend/src/components/layout/app-sidebar.tsx
    - frontend/src/locale/en.json
    - frontend/src/locale/vi.json
key-decisions:
  - "Kept the dashboard projects surface list-first with a cards toggle visible in the toolbar to preserve D-01 exactly."
  - "Moved admin pages under an explicit /admin URL segment after build verification exposed that route groups alone do not create URL boundaries."
  - "Used route-level auth cookie checks in admin layout plus shared proxy protection for the admin boundary instead of creating a second frontend app."
patterns-established:
  - "Admin route pattern: shared localized app plus /(admin)/admin/* filesystem path for URL + shell separation"
  - "Frontend polling pattern: dedicated aiJobsApi module with terminal-status helper and zod parsing before UI use"
requirements-completed: [QFLOW-04]
duration: 1h 12m
completed: 2026-04-30
---

# Phase 10 Plan 03: Dashboard and Admin UI Summary

**Shared Next.js dashboard/admin surfaces with projects-first UX, explicit /admin route partitioning, and polling-ready AI job frontend contracts.**

## Performance

- **Duration:** 1h 12m
- **Started:** 2026-04-30T07:50:00Z
- **Completed:** 2026-04-30T09:02:00Z
- **Tasks:** 3
- **Files modified:** 15

## Accomplishments

- Built the dashboard projects page with list/table-first default, search + sort only toolbar, cards toggle, and actionable empty-state CTA aligned to D-01/D-02/D-03.
- Added dedicated frontend AI job API/schema modules so dashboard/admin surfaces can poll the async backend contract from plan 10-02 safely.
- Added an admin route partition inside the shared app under `/[locale]/admin/*`, with proxy protection and route shell for users, tiers, rate limits, and settings pages.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build dashboard project surface with polling-ready AI job client** - `9a47cef` (merge)
2. **Task 2: Add /(admin) route group and core admin modules in shared app** - `9a47cef` (merge)
3. **Task 3: Validate dashboard/admin UX and access boundaries in browser** - approved by user

## Files Created/Modified

- `frontend/src/app/[locale]/(dashboard)/projects/page.tsx` - Projects UI with list-first table, cards toggle, search/sort toolbar, and empty-state CTA.
- `frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx` - Overview page updated to surface recent AI job statuses.
- `frontend/src/app/[locale]/(admin)/admin/layout.tsx` - Shared admin shell with auth-cookie gate.
- `frontend/src/app/[locale]/(admin)/admin/users/page.tsx` - Admin users surface.
- `frontend/src/app/[locale]/(admin)/admin/tiers/page.tsx` - Admin tiers surface.
- `frontend/src/app/[locale]/(admin)/admin/rate-limits/page.tsx` - Admin rate-limit rules surface.
- `frontend/src/app/[locale]/(admin)/admin/settings/page.tsx` - Admin settings surface.
- `frontend/src/lib/api/ai-jobs.ts` - Polling-ready AI jobs API client.
- `frontend/src/lib/api/admin.ts` - Admin API client wrappers.
- `frontend/src/schemas/ai-job.schemas.ts` - Zod AI job contract validation.
- `frontend/src/schemas/admin.schemas.ts` - Zod admin contract validation.
- `frontend/src/proxy.ts` - Extended protected roots to cover `/admin` and fixed Next 16 cookie typing.
- `frontend/src/components/layout/app-sidebar.tsx` - Added conditional admin nav entry for superusers.
- `frontend/src/locale/en.json` - Added admin navigation label.
- `frontend/src/locale/vi.json` - Added admin navigation label.

## Decisions Made

- Used a shared-app route partition instead of a separate admin frontend, matching D-04 while keeping auth/i18n/layout reuse.
- Left dashboard project data presentation intentionally basic and production-ready, without adding deferred advanced filters.
- Kept admin pages resilient when backend data cannot load by rendering safe fallback copy instead of breaking SSR.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected admin route boundary to produce real `/admin/*` URLs**
- **Found during:** Task 2 verification
- **Issue:** Initial `(admin)` route group created `/users`, `/tiers`, etc. because route groups do not add URL segments.
- **Fix:** Moved pages under `(admin)/admin/*` so the shared app preserves route grouping while exposing the required `/admin/*` boundary.
- **Files modified:** `frontend/src/app/[locale]/(admin)/admin/layout.tsx`, `frontend/src/app/[locale]/(admin)/admin/users/page.tsx`, `frontend/src/app/[locale]/(admin)/admin/tiers/page.tsx`, `frontend/src/app/[locale]/(admin)/admin/rate-limits/page.tsx`, `frontend/src/app/[locale]/(admin)/admin/settings/page.tsx`
- **Verification:** `pnpm build` route manifest shows `/[locale]/admin/users`, `/tiers`, `/rate-limits`, `/settings`.
- **Committed in:** `9a47cef`

**2. [Rule 3 - Blocking] Fixed Next 16 cookie typing in proxy middleware while expanding admin protection**
- **Found during:** Task 2 build verification
- **Issue:** `request.cookies.get(localeCookieConfig.name)` failed type-check because `name` can be undefined in current Next typing.
- **Fix:** Added explicit guard for `localeCookieConfig.name` before cookie access.
- **Files modified:** `frontend/src/proxy.ts`
- **Verification:** `pnpm build` passes.
- **Committed in:** `9a47cef`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were necessary to make the intended admin boundary and Next 16 build compatibility real. No scope creep.

## Issues Encountered

- Next 16 build validation surfaced a middleware typing mismatch unrelated to the new UI itself; this had to be fixed to keep the plan shippable.
- Route groups alone were insufficient for D-05 because URL segmentation must be explicit in the filesystem path.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10-04 can now validate frontend build/lint paths against concrete dashboard/admin routes.
- Dashboard/admin UI now has stable frontend contracts for async job polling and admin data wiring.

## Self-Check: PASSED

- Verified `pnpm build` passes on Next 16.2.3.
- Human checkpoint approved for dashboard/admin UX and route/access boundary review.
