---
phase: quick
plan: 260413-3ew
subsystem: frontend
tags: [refactor, directory-structure, i18n, auth, imports]
dependency_graph:
  requires: []
  provides:
    - "hooks/, schemas/, stores/, types/ at top-level src/ (cleaner imports)"
    - "lib/i18n/ inside lib/ (infrastructure separation)"
    - "AUTH-AUDIT.md with 10 findings and action backlog"
  affects:
    - "All frontend components importing from @/lib/hooks/, @/lib/schemas/, @/lib/stores/, @/lib/types/"
    - "All files importing from @/i18n/"
tech_stack:
  added: []
  patterns:
    - "Domain concerns (hooks, schemas, stores, types) at src/ top-level"
    - "Infrastructure (api, i18n, utils) inside lib/"
key_files:
  created:
    - .planning/quick/260413-3ew-restructure-frontend-lib-directory-and-a/AUTH-AUDIT.md
  moved:
    - frontend/src/lib/hooks/ -> frontend/src/hooks/
    - frontend/src/lib/schemas/ -> frontend/src/schemas/
    - frontend/src/lib/stores/ -> frontend/src/stores/
    - frontend/src/lib/types/ -> frontend/src/types/
    - frontend/src/i18n/ -> frontend/src/lib/i18n/
  modified:
    - frontend/next.config.ts
    - frontend/src/lib/api/auth.ts
    - frontend/src/lib/api/client.ts
    - frontend/src/proxy.ts
    - frontend/src/lib/i18n/request.ts
    - frontend/src/lib/i18n/global.d.ts
decisions:
  - "lib/ is now purely infrastructure: api/, i18n/, utils.ts only"
  - "Domain hooks/schemas/stores/types promoted to src/ top-level for discoverability"
  - "Locale-aware redirect applied to client.ts as LOW-severity fix from audit"
  - "Proxy auth guard deferred (MEDIUM finding) — by design, tracked in AUTH-AUDIT.md"
metrics:
  duration: "~25min"
  completed_date: "2026-04-13"
  tasks: 3
  files_changed: 40
---

# Quick Task 260413-3ew: Restructure Frontend lib/ Directory and Auth Audit Summary

**One-liner:** Promoted hooks/schemas/stores/types out of lib/ to top-level src/, moved i18n into lib/, updated 40+ import sites with zero TypeScript errors, and documented 10 auth-flow findings with severity ratings.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Move directories and update all import paths | 29975cd | 39 files (git mv + import updates) |
| 2 | Audit auth proxy flow and document findings | 3c2090a | AUTH-AUDIT.md (230 lines, 10 findings) |
| 3 | Build verification and locale-aware redirect fix | f33d492 | frontend/src/lib/api/client.ts |

---

## Directory Structure (After)

```
frontend/src/
  hooks/          <- was lib/hooks/
    use-auth.ts
    use-media-query.ts
    use-mobile.ts
  schemas/        <- was lib/schemas/
    auth.ts
  stores/         <- was lib/stores/
    sidebar-store.ts
    ui-store.ts
  types/          <- was lib/types/
    api.ts
    axios.d.ts
  lib/            <- infrastructure only
    api/
    i18n/         <- was src/i18n/
      routing.ts
      navigation.ts
      request.ts
      global.d.ts
    utils.ts
  locale/         <- untouched
  app/
  components/
  proxy.ts
```

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Auth Audit Summary (10 Findings)

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| A | Token refresh race condition — queue pattern correct | INFO | OK |
| B | Redirect loop risk — _retry flag prevents infinite loop | INFO | OK |
| C | Login redirect locale-unaware (double redirect) | LOW | FIXED in T3 |
| D | SSR safety — window guard and module-scope instance both safe | INFO | OK |
| E | CORS/withCredentials — specific origin required in backend | LOW | DEFERRED |
| F | Schema validation gap — registerSchema regex missing | LOW | DEFERRED |
| G | Fragile error casting instead of normalizeError() | LOW | DEFERRED |
| H | Proxy has no auth guard — client-side only | MEDIUM | DEFERRED |
| I | queryClient.clear() on logout — correct | INFO | OK |
| J | OAuth window.location only in client components — safe | INFO | OK |

Full details: `.planning/quick/260413-3ew-restructure-frontend-lib-directory-and-a/AUTH-AUDIT.md`

---

## Verification Results

- `npx tsc --noEmit`: 0 errors
- `npm run build`: SUCCESS — all routes prerendered correctly
- Stale imports check: 0 results for `@/lib/hooks`, `@/lib/schemas`, `@/lib/stores`, `@/lib/types`, `@/i18n/`
- Old directories confirmed deleted: `src/lib/hooks/`, `src/lib/schemas/`, `src/lib/stores/`, `src/lib/types/`, `src/i18n/`

---

## Known Stubs

None introduced by this task. The task was a pure refactor — no new UI or data flows.

---

## Threat Flags

None. This task contained no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. The proxy auth guard gap (Finding H) was already known and pre-existed this task.

---

## Self-Check: PASSED

- AUTH-AUDIT.md exists: FOUND
- commit 29975cd exists: FOUND
- commit 3c2090a exists: FOUND
- commit f33d492 exists: FOUND
- frontend/src/hooks/use-auth.ts exists: FOUND
- frontend/src/schemas/auth.ts exists: FOUND
- frontend/src/lib/i18n/routing.ts exists: FOUND
- frontend/src/lib/i18n/request.ts exists: FOUND
