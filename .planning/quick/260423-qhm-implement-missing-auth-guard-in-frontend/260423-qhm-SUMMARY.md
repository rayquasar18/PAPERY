---
quick_id: 260423-qhm
description: "Implement missing locale-aware auth guard in Next.js proxy for protected frontend routes"
completed: 2026-04-23T12:34:00Z
duration: "~18m"
tasks_completed: 3
tasks_total: 3
key_files:
  modified:
    - frontend/src/proxy.ts
  created:
    - .planning/quick/260423-qhm-implement-missing-auth-guard-in-frontend/260423-qhm-SUMMARY.md
---

# Quick Task 260423-qhm: Summary

**One-liner:** Added a Next.js 16 proxy auth gate that protects `/dashboard`, `/projects`, and `/settings` (localized and non-localized), redirects unauthenticated traffic to `/{locale}/login?redirect=...`, and preserves next-intl middleware behavior.

## Completed Tasks

| Task | Description | Commit | Key Changes |
|------|-------------|--------|-------------|
| 1 | Add localized auth guard to proxy while preserving next-intl | `943848a` | Implemented route normalization, protected-route detection, locale-aware login redirects, and auth/public route loop prevention in `frontend/src/proxy.ts` |
| 2 | Validate edge-case matching and lint safety | `943848a` | Confirmed strict root matching (`/settings` yes, `/settingss` no), trailing slash handling, nested path coverage, and no ESLint config changes required |
| 3 | Run final checks and write summary | `pending` | Recorded focused lint pass, full lint outcome, and final behavior details in this summary |

## Changes Summary

### `frontend/src/proxy.ts`
- Kept next-intl as the middleware source of truth via `createMiddleware(routing)`.
- Added explicit protected route roots:
  - `/dashboard`
  - `/projects`
  - `/settings`
- Added path normalization and locale-prefix stripping so matching works for:
  - non-localized paths (`/dashboard`, `/projects/abc`, `/settings/profile`)
  - localized paths (`/en/dashboard`, `/vi/settings/profile?tab=security`)
- Added exact-root-or-descendant matcher to avoid false positives:
  - protected: `/settings` and `/settings/...`
  - not protected: `/settingss`, `/projects-public`
- Added locale resolution for redirects:
  - use locale prefix from pathname when present
  - otherwise use locale cookie when valid
  - fallback to `routing.defaultLocale`
- Added unauthenticated guard based on `access_token` cookie presence.
- Added login redirect with preserved destination:
  - target: `/{locale}/login`
  - query: `redirect=<original pathname + original search>`
- Preserved next-intl behavior for pass-through paths by delegating to `intlMiddleware(request)`.
- Added loop prevention for auth pages carrying an existing `redirect` query.

## Threat Model Mitigation Coverage

- **T-quick-01 (Spoofing):** Guard decision uses expected auth cookie signal (`access_token`) and does not trust pathname alone.
- **T-quick-02 (Tampering):** `redirect` is built from current request pathname + query only, and encoded via URLSearchParams (no external origin input).
- **T-quick-03 (DoS / loops):** Auth routes with `redirect` are exempt from re-wrapping; non-protected and public routes pass through.
- **T-quick-04 (Info disclosure):** Protected route families are blocked at proxy layer before rendering.

## Verification

### 1) Focused proxy lint
- Command: `cd /Users/mqcbook/Documents/github/my-source/PAPERY/frontend && npm run lint -- src/proxy.ts`
- Result: **PASS**
- Notes: npm emitted existing project config warnings (`shamefully-hoist`, `strict-peer-dependencies`) but lint passed for `src/proxy.ts`.

### 2) Full frontend lint
- Command: `cd /Users/mqcbook/Documents/github/my-source/PAPERY/frontend && npm run lint`
- Result: **FAIL (pre-existing, out-of-scope issues)**
- Existing errors/warnings detected in unrelated files:
  - `src/components/auth/register-form.tsx` (`@next/next/no-html-link-for-pages`, `react-hooks/incompatible-library`)
  - `src/components/data-table.tsx` (`react-hooks/incompatible-library`)
  - `src/components/layout/theme-toggle.tsx` (`react-hooks/set-state-in-effect`)
  - `src/components/ui/sidebar.tsx` (`react-hooks/purity`)
  - `src/hooks/use-media-query.ts` (`react-hooks/set-state-in-effect`)

These issues were not introduced by this task and were left unchanged per scope boundary.

## Deviations from Plan

### Auto-fixed / auto-applied clarifications
1. **[Rule 2 - Missing critical functionality]** Locale fallback now checks locale cookie before default locale for non-localized protected routes.
   - **Reason:** Prevent redirecting users to a wrong locale when they previously selected another locale.
   - **Files:** `frontend/src/proxy.ts`
   - **Commit:** `943848a`

2. **[Rule 2 - Missing critical functionality]** Protected-route matcher hardened to exact-root-or-descendant semantics.
   - **Reason:** Prevent accidental protection of similarly prefixed public paths.
   - **Files:** `frontend/src/proxy.ts`
   - **Commit:** `943848a`

## Deferred Issues (Out of Scope)

- Full frontend lint currently fails due to pre-existing issues outside `frontend/src/proxy.ts`.
- No changes were made to `frontend/eslint.config.mjs` because focused lint for the proxy file already works correctly.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: `/Users/mqcbook/Documents/github/my-source/PAPERY/frontend/src/proxy.ts`
- FOUND: `/Users/mqcbook/Documents/github/my-source/PAPERY/.planning/quick/260423-qhm-implement-missing-auth-guard-in-frontend/260423-qhm-SUMMARY.md`
- FOUND: commit `943848a`
