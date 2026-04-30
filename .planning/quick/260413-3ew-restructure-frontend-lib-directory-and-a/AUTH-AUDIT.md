# Auth Proxy Flow Audit

**Date:** 2026-04-13
**Scope:** frontend/src/lib/api/client.ts, auth.ts, hooks/use-auth.ts, proxy.ts, schemas/auth.ts, lib/api/error.ts
**Auditor:** GSD execute agent (quick-260413-3ew)

---

## Summary Table

| ID | Topic | Severity | Status | Action Required |
|----|-------|----------|--------|-----------------|
| A  | Token refresh race condition | INFO | OK | None |
| B  | Redirect loop risk | INFO | OK | None |
| C  | Login redirect path (locale-unaware) | LOW | NEEDS-FIX | Apply in Task 3 |
| D  | SSR safety | INFO | OK | None |
| E  | CORS / withCredentials requirement | LOW | DEFERRED | Document backend requirement |
| F  | Schema validation inconsistency | LOW | NEEDS-FIX | Future plan |
| G  | Fragile error casting in use-auth.ts | LOW | NEEDS-FIX | Future plan |
| H  | Proxy has no auth guard | MEDIUM | DEFERRED | By design; future plan |
| I  | Query cache cleared on logout | INFO | OK | None |
| J  | OAuth redirect SSR safety | INFO | OK | None |

---

## Detailed Findings

### A. Token Refresh Race Condition
**Severity:** INFO
**Status:** OK

The `failedQueue` pattern in `client.ts` correctly handles concurrent 401 failures. When multiple requests fail simultaneously:
1. The first request sets `isRefreshing = true` and triggers `/auth/refresh`.
2. All subsequent 401s are pushed to `failedQueue` as deferred promises.
3. On refresh success, `processQueue(null)` resolves all queued promises, each replaying via `apiClient(originalRequest)`.
4. Replayed requests use the new cookies automatically because `withCredentials: true` sends all current cookies — no manual token injection needed.

**Verdict:** Implementation is correct. The queue pattern prevents N simultaneous refresh calls.

---

### B. Redirect Loop Risk
**Severity:** INFO
**Status:** OK

The `_retry` flag is set (`originalRequest._retry = true`) *before* the refresh call at line 66. If `/auth/refresh` itself returns 401:
- The refresh error propagates to the `catch` block.
- The queued requests are rejected via `processQueue(refreshError)`.
- `isRefreshing` is reset to `false` in `finally`.
- The original request already has `_retry = true`, so it cannot re-enter the interceptor refresh path.

**Verdict:** No infinite loop risk. The guard is correctly placed.

---

### C. Login Redirect Path (Locale-Unaware)
**Severity:** LOW
**Status:** NEEDS-FIX

**File:** `frontend/src/lib/api/client.ts` line 78

**Issue:** On refresh failure, the code redirects to `/login` using `window.location.href = '/login'`. This hits the i18n middleware which redirects to `/en/login` or `/vi/login`, causing a visible double-redirect flash.

**Recommended fix:**
```typescript
const locale = window.location.pathname.split('/')[1] || 'en';
window.location.href = `/${locale}/login`;
```

**Note:** This is safe — `pathname.split('/')[1]` extracts the locale segment (e.g., `en`, `vi`) from the current URL. No user input injection risk since the value is used only as a URL path segment, not interpreted as code.

**Action:** Applied in Task 3 of this quick task.

---

### D. SSR Safety
**Severity:** INFO
**Status:** OK

Two SSR considerations:

1. **`window.location.href` guard:** The code correctly checks `typeof window !== 'undefined'` before accessing `window.location.href` (line 77). On the server, the redirect simply does not execute, which is the correct behavior since 401 auto-refresh on the server would be a no-op anyway.

2. **Axios instance at module scope:** `apiClient` is created at module scope with `axios.create(...)`. This is safe in Next.js because:
   - The instance itself has no side effects on creation.
   - Interceptors only fire when requests are made.
   - The `isRefreshing` and `failedQueue` module-level variables are shared within a single Node.js process; for SSR requests, cookie management is handled differently (server components use `cookies()` from `next/headers` directly).

**Verdict:** SSR safety is adequate for the current usage pattern.

---

### E. CORS / withCredentials Requirement
**Severity:** LOW
**Status:** DEFERRED

**Issue:** `withCredentials: true` is set on the Axios instance. For this to work cross-origin, the backend FastAPI CORS configuration MUST:
- Set `allow_credentials=True` in `CORSMiddleware`.
- List specific origins (e.g., `http://localhost:3000`, production URL) — **not** `allow_origins=["*"]` (wildcards are incompatible with `allow_credentials=True`).

**Current state:** The backend `configs/cors.py` controls this via `CORS_ORIGINS` env var. The restriction on wildcard origins is a browser security requirement (not a backend choice).

**Recommended action:** Add to deployment documentation / environment variable checklist:
```
CORS_ORIGINS=http://localhost:3000,https://app.papery.io
```

**Action:** No code change needed. Document in deployment guide when that phase arrives.

---

### F. Schema Validation Inconsistency
**Severity:** LOW
**Status:** NEEDS-FIX (future plan)

**File:** `frontend/src/schemas/auth.ts`

**Issue:** The `registerSchema` includes a comment about password complexity (uppercase, lowercase, number, special character) but the actual Zod validation only enforces `min(8)`. The `loginSchema` also only validates `min(8)`.

**Inconsistency:** If the backend enforces complexity rules (e.g., at least one uppercase, one number), the frontend will accept passwords that the backend rejects, resulting in a confusing user experience.

**Recommended fix:** Either:
1. Add a regex to `registerSchema` matching backend rules: `.regex(/^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)/, 'Requires uppercase, lowercase, and number')`.
2. Or confirm backend does NOT enforce complexity and remove the misleading comment.

**Action:** Deferred — requires backend schema audit to confirm exact rules. Track for Phase 4 (password management).

---

### G. Fragile Error Casting in use-auth.ts
**Severity:** LOW
**Status:** NEEDS-FIX (future plan)

**File:** `frontend/src/hooks/use-auth.ts` (lines 45–47, 61–63)

**Issue:** Error handling uses raw type casting:
```typescript
(err as { response?: { data?: { message?: string } } })?.response?.data?.message
```

This bypasses the existing `normalizeError()` function in `lib/api/error.ts` which already handles AxiosError normalization and provides a typed `ApiError` interface.

**Inconsistency:** Other parts of the codebase (e.g., `forgot-password-form.tsx`, `reset-password-form.tsx`) also use the same fragile cast pattern. If the backend error response shape changes, all these casting sites would need updating.

**Recommended fix:**
```typescript
import { normalizeError } from '@/lib/api/error';
// In onError:
const normalized = normalizeError(err);
toast.error(normalized.message);
```

**Action:** Deferred — low impact, good cleanup for a future refactor plan.

---

### H. Proxy Has No Auth Guard
**Severity:** MEDIUM
**Status:** DEFERRED (by design)

**File:** `frontend/src/proxy.ts`

**Issue:** The proxy currently only applies i18n middleware. There is no authentication guard — all routes (including `/dashboard`, `/settings`) are accessible without a valid session at the proxy level. The comment "Auth guard logic will be added in Plan 09-05" confirms this is intentional.

**Security implication:** A non-authenticated user navigating to `/en/dashboard` will:
1. Receive the dashboard HTML/JS (no server-side redirect).
2. The dashboard client components will call `authApi.me()` via `useAuth()`, which will return 401.
3. The 401 interceptor will attempt refresh, fail, then redirect to login.

This is a **client-side** auth gate, not a **server-side** one. The user briefly sees the dashboard shell before being redirected.

**Recommended fix:** Add a server-side auth check in the proxy using the access token cookie:
```typescript
// In proxy.ts — check token cookie for protected paths
const PROTECTED_PATHS = ['/dashboard', '/settings', '/projects'];
if (PROTECTED_PATHS.some(p => pathname.includes(p))) {
  const token = request.cookies.get('access_token');
  if (!token) {
    return NextResponse.redirect(new URL(`/${locale}/login`, request.url));
  }
}
```

**Action:** Deferred — tracked in the plan comment. Must be implemented before production deployment. Flag for Phase 9 completion or a dedicated security hardening plan.

---

### I. Query Cache Security on Logout
**Severity:** INFO
**Status:** OK

**File:** `frontend/src/hooks/use-auth.ts` lines 71–72

`queryClient.clear()` is called on both successful logout and on logout error. This correctly:
- Removes the cached user object (`QUERY_KEYS.user`).
- Clears any other cached data (projects, documents, etc.) that might contain user-specific content.
- Prevents stale data leaking if a different user logs in on the same browser tab.

The error path (`onError`) also clears the cache and redirects — this is correct defensive behavior since a failed logout call may still mean the user's tokens are invalidated server-side.

**Verdict:** Cache security on logout is handled correctly.

---

### J. OAuth Redirect SSR Safety
**Severity:** INFO
**Status:** OK

**File:** `frontend/src/lib/api/auth.ts` (googleLogin, githubLogin methods)

Both `googleLogin()` and `githubLogin()` use `window.location.href` to redirect to backend OAuth endpoints. These methods:
1. Are only called from `useAuth()` hook — a client-side hook.
2. `useAuth()` is only used in components marked `'use client'`.
3. The `OAuthButtons` component that calls these is also a client component.

Therefore, these methods will never be called during SSR. No SSR guard is needed here.

**Verdict:** OK for current usage. If these methods are ever exported and used outside client components, a `typeof window !== 'undefined'` guard should be added.

---

## Action Items Summary

| Priority | Action | File | When |
|----------|--------|------|------|
| 1 | Fix locale-unaware login redirect | `lib/api/client.ts:78` | Task 3 (this task) |
| 2 | Add auth guard to proxy.ts | `proxy.ts` | Future plan (post Phase 9) |
| 3 | Fix schema validation inconsistency | `schemas/auth.ts` | Phase 4 (password management) |
| 4 | Replace fragile error casts with normalizeError() | `hooks/use-auth.ts`, auth forms | Future refactor plan |
| 5 | Document CORS_ORIGINS requirement | Deployment docs | When deployment guide is written |
