---
phase: quick
plan: 260423-qhm
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/proxy.ts
  - frontend/eslint.config.mjs
  - .planning/quick/260423-qhm-implement-missing-auth-guard-in-frontend/260423-qhm-SUMMARY.md
autonomous: true
must_haves:
  truths:
    - "Unauthenticated requests to protected routes are redirected to the localized login page."
    - "Protected route guarding works for both localized paths (/en/dashboard) and non-localized paths (/dashboard)."
    - "Public auth pages and Next.js internals do not get trapped in redirect loops."
    - "next-intl locale detection and rewrite behavior remain intact after the auth guard is added."
  artifacts:
    - path: "frontend/src/proxy.ts"
      provides: "Combined next-intl + auth guard proxy for protected routes"
    - path: "frontend/eslint.config.mjs"
      provides: "Lint coverage for proxy file when needed"
    - path: ".planning/quick/260423-qhm-implement-missing-auth-guard-in-frontend/260423-qhm-SUMMARY.md"
      provides: "Execution summary for the quick task"
  key_links:
    - from: "frontend/src/proxy.ts"
      to: "@/lib/i18n/routing"
      via: "locale detection and intl middleware handoff"
      pattern: "createMiddleware\(routing\)"
    - from: "frontend/src/proxy.ts"
      to: "protected route matcher"
      via: "localized and non-localized pathname normalization"
      pattern: "dashboard|projects|settings"
    - from: "frontend/src/proxy.ts"
      to: "localized login redirect"
      via: "redirect query string preserving original target"
      pattern: "redirect="
---

<objective>
Implement the missing frontend auth guard in `frontend/src/proxy.ts` so unauthenticated users cannot access `/dashboard`, `/projects`, or `/settings`, while preserving `next-intl` behavior and redirecting to `/{locale}/login?redirect=...`.

Purpose: Close the gap identified in the earlier auth proxy audit so route protection happens at the edge before protected UI renders, without breaking localized routing.

Output: Updated proxy logic covering localized + non-localized protected paths, redirect-loop prevention, validation checks, and an execution summary.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/CLAUDE.md
@frontend/AGENTS.md
@frontend/src/proxy.ts
@.planning/quick/260413-3ew-restructure-frontend-lib-directory-and-a/260413-3ew-PLAN.md

<interfaces>
From `frontend/src/proxy.ts`:
```typescript
import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { routing } from '@/lib/i18n/routing';

const intlMiddleware = createMiddleware(routing);

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname } = request.nextUrl;

  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  return intlMiddleware(request) as NextResponse;
}
```

Planning notes for executor:
- Keep `next-intl` as the source of truth for locale handling; do not replace it with a custom locale parser when a middleware handoff can preserve existing behavior.
- Guard both localized paths (`/en/dashboard`, `/vi/projects/123`) and non-localized entry points (`/dashboard`, `/projects`, `/settings`) so deep links still land on the correct localized login page.
- Redirect-loop prevention is mandatory: never redirect login/auth pages, locale root pages, or already-redirected login requests back to login again.
- Preserve the full target path + query string in `redirect=` so post-login return flow remains possible.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add localized auth guard to proxy without breaking next-intl</name>
  <files>frontend/src/proxy.ts</files>
  <behavior>
    - Test 1: Request to `/dashboard`, `/projects`, or `/settings` without auth cookie redirects to `/{detected-locale}/login?redirect=...`.
    - Test 2: Request to `/en/dashboard` or `/vi/settings/profile?tab=security` without auth cookie redirects to the same locale login page and preserves the original pathname + query in `redirect=`.
    - Test 3: Request to `/en/login`, `/vi/register`, `/`, `/en`, Next internals, API routes, and static assets does not trigger the protected-route redirect.
    - Test 4: Authenticated requests with the expected cookie proceed through `next-intl` handling instead of being redirected.
  </behavior>
  <action>
Update `frontend/src/proxy.ts` to compose auth guarding with the existing `intlMiddleware` rather than replacing it. Keep the current short-circuit for `/_next`, `/api`, and static assets. Add explicit protected route detection for `/dashboard`, `/projects`, and `/settings`, including nested descendants, and normalize both localized and non-localized pathnames before matching.

Implement locale-aware redirect construction so unauthenticated access goes to `/{locale}/login?redirect={encodedOriginalPathAndSearch}`. Use the locale from the pathname when present, otherwise derive the default locale via the existing `routing` config or the i18n middleware result rather than hardcoding assumptions. Preserve search params in the redirect target.

Prevent redirect loops by exempting auth pages such as `/{locale}/login`, `/{locale}/register`, forgot/reset-password pages, locale roots, and non-protected public routes. Also ensure a request already targeting login with a `redirect` query is not rewrapped into another login redirect.

Read the relevant Next.js 16 docs under `frontend/node_modules/next/dist/docs/` before finalizing the proxy implementation, per `frontend/AGENTS.md`, so the proxy API and matcher usage stay compatible with this project’s version.
  </action>
  <verify>
    <automated>cd /Users/mqcbook/Documents/github/my-source/PAPERY/frontend && npm run lint -- src/proxy.ts</automated>
  </verify>
  <done>
    - `frontend/src/proxy.ts` guards `/dashboard`, `/projects`, and `/settings` for both localized and non-localized URLs.
    - Unauthenticated requests redirect to `/{locale}/login?redirect=...` with the original path/query preserved.
    - Public auth pages and public routes remain accessible with no redirect loop.
    - `next-intl` locale behavior still applies after the auth decision.
  </done>
</task>

<task type="auto">
  <name>Task 2: Cover edge cases and matcher safety for protected routing</name>
  <files>frontend/src/proxy.ts, frontend/eslint.config.mjs</files>
  <action>
Audit the final proxy implementation for edge cases that commonly break auth middleware: trailing slashes, nested protected paths, locale prefixes, non-localized direct visits, query-string preservation, and accidental prefix matches such as `/settingss` or `/projects-public`. Tighten the pathname matching logic so only the intended route roots and their descendants are protected.

Review the proxy matcher/export configuration and lint setup after the logic change. If lint cannot target `src/proxy.ts` cleanly because of current frontend configuration, make the minimal `frontend/eslint.config.mjs` adjustment required for this file to be checked without broad unrelated refactors. Do not broaden scope beyond enabling correct validation for the proxy change.
  </action>
  <verify>
    <automated>cd /Users/mqcbook/Documents/github/my-source/PAPERY/frontend && npm run lint</automated>
  </verify>
  <done>
    - Protected-route matching excludes false positives and handles nested children safely.
    - Redirect target encoding preserves path and query string across localized and non-localized requests.
    - Lint configuration, if touched, is minimally updated and only in service of validating the proxy change.
  </done>
</task>

<task type="auto">
  <name>Task 3: Run final checks and write execution summary</name>
  <files>.planning/quick/260423-qhm-implement-missing-auth-guard-in-frontend/260423-qhm-SUMMARY.md</files>
  <action>
Run the focused validation commands after implementation is complete and confirm the proxy behavior in the summary. The summary must explicitly record: protected paths covered, how localized and non-localized routes are normalized, how login redirect-loop prevention works, and which auth cookie signal the proxy uses to decide authenticated vs unauthenticated flow.

Create `.planning/quick/260423-qhm-implement-missing-auth-guard-in-frontend/260423-qhm-SUMMARY.md` using the standard quick-task summary format after checks pass.
  </action>
  <verify>
    <automated>test -f /Users/mqcbook/Documents/github/my-source/PAPERY/.planning/quick/260423-qhm-implement-missing-auth-guard-in-frontend/260423-qhm-SUMMARY.md</automated>
  </verify>
  <done>
    - Validation commands have been run and captured in the summary.
    - Summary documents localized/non-localized handling and redirect-loop prevention.
    - Quick task has a clear handoff artifact for follow-up review.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Browser request -> Next.js proxy | Untrusted pathname, search params, and cookies determine redirect vs pass-through behavior |
| Next.js proxy -> localized auth routes | Redirect target must not create open redirect or loop behavior |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-quick-01 | Spoofing | `frontend/src/proxy.ts` auth cookie check | mitigate | Check only the project’s expected auth cookie presence and treat missing cookie as unauthenticated without trusting pathname alone |
| T-quick-02 | Tampering | `redirect` query construction | mitigate | Build redirect from current pathname + search only, URL-encode it, and avoid accepting an external redirect origin |
| T-quick-03 | Denial of Service | login redirect flow | mitigate | Exempt login/auth/public pages and already-safe paths to prevent infinite redirect loops |
| T-quick-04 | Information Disclosure | protected route access before auth | mitigate | Enforce route-level redirect in proxy for `/dashboard`, `/projects`, and `/settings` before page rendering |
</threat_model>

<verification>
- `cd /Users/mqcbook/Documents/github/my-source/PAPERY/frontend && npm run lint -- src/proxy.ts`
- `cd /Users/mqcbook/Documents/github/my-source/PAPERY/frontend && npm run lint`
- Summary file exists at `.planning/quick/260423-qhm-implement-missing-auth-guard-in-frontend/260423-qhm-SUMMARY.md`
</verification>

<success_criteria>
- `frontend/src/proxy.ts` protects `/dashboard`, `/projects`, and `/settings` for both localized and non-localized URLs.
- Unauthenticated users are redirected to `/{locale}/login?redirect=...` with the original target preserved.
- `next-intl` behavior remains intact for locale detection and routing.
- Login/auth pages and other public routes are excluded from redirect-loop behavior.
- The quick task ends with a written summary capturing implementation details and checks.
</success_criteria>

<output>
After completion, create `/Users/mqcbook/Documents/github/my-source/PAPERY/.planning/quick/260423-qhm-implement-missing-auth-guard-in-frontend/260423-qhm-SUMMARY.md`
</output>
