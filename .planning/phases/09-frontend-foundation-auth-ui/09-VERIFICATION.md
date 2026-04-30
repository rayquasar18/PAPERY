---
phase: 09-frontend-foundation-auth-ui
verified: 2026-04-12T00:00:00Z
status: gaps_found
score: 4/5 success criteria verified
overrides_applied: 0
gaps:
  - truth: "Protected routes redirect unauthenticated users to login; proxy.ts implements auth guard"
    status: failed
    reason: "proxy.ts only handles i18n routing. The auth guard (redirecting unauthenticated users from protected routes like /dashboard to /login) was planned for Plan 09-05 (noted in proxy.ts comment: 'Auth guard logic will be added in Plan 09-05') but was not implemented. Plan 09-05 PLAN describes FRONT-08 as 'route protection preparation' and the tasks focus on auth UI pages, not the proxy auth guard. The comment in proxy.ts still says auth guard is coming — it never arrived."
    artifacts:
      - path: "frontend/src/proxy.ts"
        issue: "No auth guard logic. Only i18n middleware applied. Comment still says 'Auth guard logic will be added in Plan 09-05' — which shipped without it."
    missing:
      - "In proxy.ts: add logic to check for valid auth cookie (access_token) on protected routes (/dashboard, /projects, /settings) and redirect unauthenticated users to /{locale}/login with ?redirect= parameter"
      - "Optionally: add server-side auth check in dashboard layout.tsx as an additional layer"
human_verification:
  - test: "Auth flow end-to-end with running backend"
    expected: "Register form submits to /api/v1/auth/register, receives verification email notice, login form submits to /api/v1/auth/login, JWT cookies set, redirect to /en/dashboard occurs"
    why_human: "Requires backend to be running on localhost:8000. Cannot verify API integration programmatically without a live server."
  - test: "Locale switching"
    expected: "Clicking 'Tiếng Việt' in LanguageSwitcher changes all visible UI text to Vietnamese without a full page reload"
    why_human: "Requires browser interaction to verify locale cookie is set and text changes without reload."
  - test: "Theme toggle persistence"
    expected: "Selecting Dark mode persists after page reload; system preference is respected on first visit"
    why_human: "Requires browser storage and reload testing."
  - test: "Sidebar responsive behavior"
    expected: "On mobile (<768px) sidebar shows as a Sheet overlay; on tablet (768-1024px) shows icon-only; on desktop (>1024px) shows expanded with labels"
    why_human: "Requires browser viewport testing."
---

# Phase 9: Frontend Foundation & Auth UI — Verification Report

**Phase Goal:** Set up the complete frontend infrastructure — Next.js App Router, i18n, theming, state management, HTTP client, component library, and authentication UI (login, register, password flows).
**Verified:** 2026-04-12
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Next.js app boots with App Router, TypeScript strict mode, and locale-based routing (`/en/...`, `/vi/...`) working end-to-end | VERIFIED | `package.json` has `"next": "16.2.3"`, `tsconfig.json` has `"strict": true`, `routing.ts` defines `locales: ['en', 'vi']` with `localePrefix: 'always'`, `[locale]/layout.tsx` validates locale and returns 404 for unknown |
| 2 | All UI text uses `t()` function from next-intl; switching locale changes all visible text | VERIFIED | Every component (login-form, register-form, app-sidebar, top-bar, theme-toggle, language-switcher, chat-panel, auth-branding, dashboard/page) uses `useTranslations()`. Both `en.json` and `vi.json` exist with identical top-level keys. Language switcher calls `router.replace(pathname, { locale })` from `@/i18n/navigation`. |
| 3 | Dark/light/system theme toggle works and persists user preference across sessions | VERIFIED | `theme-provider.tsx` wraps with `NextThemesProvider` with `attribute="class"`, `defaultTheme="system"`, `enableSystem`, `storageKey="papery-theme"`. `theme-toggle.tsx` calls `setTheme` with light/dark/system. `globals.css` has `.dark` selector with OKLCH tokens. |
| 4 | Auth flow works end-to-end: register form -> API call -> email verification notice -> login form -> JWT cookies set -> redirect to dashboard | VERIFIED (code path) / ? NEEDS HUMAN (runtime) | `register-form.tsx` → `useAuth().register` → `authApi.register()` → POST `/auth/register` → `router.push('/verify-email')`. `login-form.tsx` → `useAuth().login` → `authApi.login()` → POST `/auth/login` → `router.push('/dashboard')`. Cookie handling is `withCredentials: true`. Full end-to-end requires running backend. |
| 5 | Protected routes redirect unauthenticated users to login; 401 responses trigger automatic token refresh before retry | PARTIAL FAIL | **401 auto-refresh: VERIFIED** — `client.ts` has full isRefreshing queue pattern that calls `/auth/refresh` on 401, replays original request, falls back to `window.location.href='/login'`. **Route protection: MISSING** — `proxy.ts` contains only i18n middleware. No auth cookie check, no redirect to login for unauthenticated access to `/dashboard`, `/projects`, `/settings`. |

**Score:** 4/5 success criteria verified (1 partial fail — route protection absent from proxy.ts)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/package.json` | Next.js 16 + deps | VERIFIED | next@16.2.3, react@19.2.4, all required deps present |
| `frontend/tsconfig.json` | strict mode, paths | VERIFIED | `"strict": true`, `"@/*": ["./src/*"]`, `moduleResolution: "bundler"` |
| `frontend/next.config.ts` | reactCompiler, next-intl plugin | VERIFIED | `reactCompiler: true`, `createNextIntlPlugin` wrapping |
| `frontend/components.json` | shadcn/ui config | VERIFIED | `"style": "new-york"`, RSC, TSX, CSS variables |
| `frontend/src/app/globals.css` | Tailwind v4, OKLCH tokens | VERIFIED | `@import "tailwindcss"`, `@import "tw-animate-css"`, `--primary: oklch(0.488 0.195 264)`, `.dark` block, `@theme inline` |
| `frontend/src/app/layout.tsx` | Inter font root layout | VERIFIED | Inter with `subsets: ['latin', 'vietnamese']`, `variable: '--font-sans'` |
| `frontend/src/app/[locale]/layout.tsx` | Provider stack, locale validation | VERIFIED | QueryProvider → ThemeProvider → NextIntlClientProvider, `suppressHydrationWarning`, `generateStaticParams`, `setRequestLocale` |
| `frontend/src/i18n/routing.ts` | locales, defaultLocale, prefix | VERIFIED | `locales: ['en', 'vi']`, `defaultLocale: 'en'`, `localePrefix: 'always'` |
| `frontend/src/i18n/request.ts` | getRequestConfig | VERIFIED | Dynamic message loading per locale |
| `frontend/src/i18n/navigation.ts` | createNavigation | VERIFIED | Exports Link, redirect, usePathname, useRouter, getPathname |
| `frontend/src/i18n/global.d.ts` | AppConfig interface | VERIFIED | `interface AppConfig { Locale: ...; Messages: typeof en }` |
| `frontend/src/locale/en.json` | All namespaces | VERIFIED | Common, Navigation, Auth (all sub-keys), Theme, Language, Metadata, Dashboard, Chat, Toast |
| `frontend/src/locale/vi.json` | Vietnamese translations | VERIFIED | Identical structure with Vietnamese text (e.g. "Đăng nhập", "Bảng điều khiển") |
| `frontend/src/proxy.ts` | i18n middleware, auth guard | PARTIAL | i18n middleware: VERIFIED. Auth guard: MISSING |
| `frontend/src/components/providers/theme-provider.tsx` | next-themes wrapper | VERIFIED | `attribute="class"`, `storageKey="papery-theme"`, `enableSystem` |
| `frontend/src/components/providers/query-provider.tsx` | QueryClientProvider | VERIFIED | `makeQueryClient`, `ReactQueryDevtools`, client-only (`'use client'`) |
| `frontend/src/lib/api/client.ts` | Axios with 401 auto-refresh | VERIFIED | `withCredentials: true`, `_retry` flag, `isRefreshing` queue, `/auth/refresh` call |
| `frontend/src/lib/api/error.ts` | ApiError + normalizeError | VERIFIED | `interface ApiError`, `normalizeError()` mapping snake_case to camelCase |
| `frontend/src/lib/api/auth.ts` | authApi with all endpoints | VERIFIED | 11 typed methods: register, login, logout, refresh, me, verifyEmail, resendVerification, forgotPassword, resetPassword, googleLogin, githubLogin |
| `frontend/src/lib/api/query-client.ts` | makeQueryClient + QUERY_KEYS | VERIFIED | staleTime 5min, gcTime 10min, retry 2; QUERY_KEYS registry |
| `frontend/src/lib/schemas/auth.ts` | Zod v4 auth schemas | VERIFIED | loginSchema, registerSchema, forgotPasswordSchema, resetPasswordSchema; all exported types |
| `frontend/src/lib/stores/sidebar-store.ts` | useSidebarStore with persist | VERIFIED | isExpanded, isChatPanelOpen, chatPanelWidth; persisted to `papery-sidebar` |
| `frontend/src/lib/stores/ui-store.ts` | useUIStore with persist | VERIFIED | splitMode; persisted to `papery-ui` |
| `frontend/src/lib/hooks/use-auth.ts` | useAuth hook | VERIFIED | useQuery(authApi.me), loginMutation, registerMutation, logoutMutation; full return type |
| `frontend/src/lib/hooks/use-media-query.ts` | useMediaQuery | VERIFIED | SSR-safe, window.matchMedia, addEventListener |
| `frontend/src/lib/types/api.ts` | UserPublicRead, AuthResponse, MessageResponse | VERIFIED | All interfaces present |
| `frontend/src/lib/types/axios.d.ts` | _retry extension | VERIFIED | `InternalAxiosRequestConfig._retry?: boolean` |
| `frontend/src/components/layout/app-sidebar.tsx` | Sidebar with collapsible icon | VERIFIED | `collapsible="icon"`, SidebarHeader, SidebarContent, SidebarRail, Link from @/i18n/navigation, LayoutDashboard + FolderKanban icons |
| `frontend/src/components/layout/top-bar.tsx` | TopBar 56px sticky | VERIFIED | `h-14`, SidebarTrigger, ThemeToggle, LanguageSwitcher, UserMenu |
| `frontend/src/components/layout/theme-toggle.tsx` | useTheme, setTheme, mounted check | VERIFIED | `useTheme`, `setTheme`, `useEffect` for mounted |
| `frontend/src/components/layout/language-switcher.tsx` | Locale switcher | VERIFIED | `useLocale`, `router.replace(pathname, { locale })` with type narrowing |
| `frontend/src/components/layout/user-menu.tsx` | User menu dropdown | VERIFIED | Avatar dropdown with Profile/Settings/Sign out items |
| `frontend/src/components/layout/chat-panel.tsx` | Chat panel placeholder | VERIFIED | Uses `useTranslations('Chat')`, ScrollArea, header with close button |
| `frontend/src/app/[locale]/(dashboard)/layout.tsx` | Dashboard layout | VERIFIED | Thin server wrapper delegating to layout-client.tsx |
| `frontend/src/app/[locale]/(dashboard)/layout-client.tsx` | SidebarProvider + panels | VERIFIED | SidebarProvider, AppSidebar, TopBar, ResizablePanelGroup, conditional ChatPanel |
| `frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx` | Dashboard empty state | VERIFIED | Empty state with "No projects yet" card, Create project CTA |
| `frontend/src/app/[locale]/(dashboard)/default.tsx` | Parallel route fallback | VERIFIED | Returns null |
| `frontend/src/app/[locale]/(auth)/layout.tsx` | Auth split-screen layout | VERIFIED | AuthBranding + form area, setRequestLocale, hasLocale narrowing |
| `frontend/src/components/auth/auth-branding.tsx` | Gradient branding panel | VERIFIED | `from-indigo-600 to-blue-800`, `hidden md:flex`, decorative dot grid |
| `frontend/src/components/auth/login-form.tsx` | Login form RHF + Zod | VERIFIED | zodResolver(loginSchema), mode:'onBlur', FormField, useTranslations, type="password" toggle, Suspense boundary |
| `frontend/src/components/auth/register-form.tsx` | Register form with strength | VERIFIED | zodResolver(registerSchema), displayName, confirmPassword, PasswordStrength embedded |
| `frontend/src/components/auth/password-strength.tsx` | 4-level strength indicator | VERIFIED | weak/fair/good/strong levels, animated color bar, aria-live="polite" |
| `frontend/src/components/auth/oauth-buttons.tsx` | Google + GitHub OAuth | VERIFIED | Separator, googleLogin/githubLogin calls, inline SVG icons |
| `frontend/src/components/auth/forgot-password-form.tsx` | Forgot password form | VERIFIED | zodResolver(forgotPasswordSchema), success state toggle |
| `frontend/src/components/auth/reset-password-form.tsx` | Reset password form | VERIFIED | zodResolver(resetPasswordSchema), PasswordStrength, reads ?token=, Suspense |
| `frontend/src/app/[locale]/(auth)/login/page.tsx` | Login page | VERIFIED | Server component, generateMetadata, LoginForm |
| `frontend/src/app/[locale]/(auth)/register/page.tsx` | Register page | VERIFIED | Exists, renders RegisterForm |
| `frontend/src/app/[locale]/(auth)/verify-email/page.tsx` | Verify email page | VERIFIED | Auto-calls authApi.verifyEmail(token), 60s resend cooldown, Suspense |
| `frontend/src/app/[locale]/(auth)/forgot-password/page.tsx` | Forgot password page | VERIFIED | Exists |
| `frontend/src/app/[locale]/(auth)/reset-password/page.tsx` | Reset password page | VERIFIED | Exists |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `login-form.tsx` | `authApi.login` | `useAuth().login` → `authApi.login()` | WIRED | loginMutation.mutateAsync called on form submit |
| `register-form.tsx` | `authApi.register` | `useAuth().register` → `authApi.register()` | WIRED | registerMutation.mutateAsync called on form submit |
| `authApi` | `/api/v1/auth/login` | `apiClient.post('/auth/login')` | WIRED | apiClient has `baseURL: ${BACKEND_URL}/api/${VERSION}` |
| `apiClient` | `401 → /auth/refresh` | Response interceptor queue pattern | WIRED | isRefreshing + failedQueue + processQueue pattern |
| `ThemeProvider` | localStorage | `storageKey="papery-theme"` in NextThemesProvider | WIRED | Cookie + localStorage for SSR compatibility |
| `locale routing` | `[locale]/layout.tsx` | next-intl plugin in next.config.ts | WIRED | `createNextIntlPlugin('./src/i18n/request.ts')` |
| `proxy.ts` | auth guard | proxy logic | NOT WIRED | Only i18n middleware applied; no auth guard for protected routes |
| `useSidebarStore` | chat panel toggle | `isChatPanelOpen` in layout-client.tsx | WIRED | Conditional render of ResizablePanel |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `login-form.tsx` | `isLoggingIn` | `useAuth().isLoggingIn` → `loginMutation.isPending` | Yes (TanStack Query mutation state) | FLOWING |
| `use-auth.ts` | `user` | `useQuery(authApi.me)` → `GET /auth/me` | Yes (real API call, cookie-based) | FLOWING |
| `app-sidebar.tsx` | `pathname` (active state) | `usePathname()` from `@/i18n/navigation` | Yes (Next.js router) | FLOWING |
| `language-switcher.tsx` | `locale` | `useLocale()` from next-intl | Yes (next-intl request context) | FLOWING |
| `theme-toggle.tsx` | `theme` | `useTheme()` from next-themes | Yes (localStorage + cookie) | FLOWING |
| `chat-panel.tsx` | n/a | Placeholder — no dynamic data | No (intentional v1 placeholder) | STATIC (expected) |

---

### Behavioral Spot-Checks

| Behavior | Check | Result | Status |
|----------|-------|--------|--------|
| Build compiles successfully | `.next/BUILD_ID` exists | BUILD_ID file present | PASS |
| All auth endpoints wired in authApi | `grep '/auth/login'` in auth.ts | Found at line 28 | PASS |
| proxy.ts is valid Next.js 16 file convention | `proxy.md` in Next.js 16 docs confirms `proxy.ts` replaces `middleware.ts` | Confirmed | PASS |
| Zod v4 installed | `package.json` has `"zod": "^4.3.6"` | Found | PASS |
| Zustand stores persist | grep `persist` in sidebar-store.ts + ui-store.ts | Found in both | PASS |
| Auth guard in proxy.ts | grep for redirect/auth logic in proxy.ts | NOT FOUND | FAIL |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FRONT-01 | 09-01 | Next.js 16 + React 19 App Router, TypeScript strict | SATISFIED | next@16.2.3, react@19.2.4, `"strict": true`, App Router structure |
| FRONT-02 | 09-02 | next-intl EN + VI locale-prefixed routing | SATISFIED | routing.ts, en.json + vi.json, [locale] routing, createNavigation |
| FRONT-03 | 09-02 | Dark/light/system theme with persistence | SATISFIED | ThemeProvider, storageKey="papery-theme", .dark CSS tokens |
| FRONT-04 | 09-04 | Responsive layout (mobile/tablet/desktop) via Tailwind | SATISFIED | AppSidebar with `collapsible="icon"`, auth layout `hidden md:flex`, AuthBranding `md:w-2/5 lg:w-1/2` |
| FRONT-05 | 09-03 | TanStack Query v5 | SATISFIED | @tanstack/react-query@5.99.0, makeQueryClient, QUERY_KEYS, QueryProvider |
| FRONT-06 | 09-03 | Zustand v5 stores, max 3-5 | SATISFIED | zustand@5.0.12, sidebar-store + ui-store (2 stores), both persisted |
| FRONT-07 | 09-03 | Zod v4 runtime validation | SATISFIED | zod@4.3.6, loginSchema/registerSchema/forgotPasswordSchema/resetPasswordSchema |
| FRONT-08 | 09-05 | Auth middleware — cookie-based JWT, auto-refresh on 401, route protection | PARTIAL | **Cookie-based JWT**: withCredentials: true — SATISFIED. **Auto-refresh on 401**: isRefreshing queue in client.ts — SATISFIED. **Route protection**: MISSING — proxy.ts has no auth guard |
| FRONT-09 | 09-01/09-02/09-04 | shadcn/ui component library (Radix UI, accessible) | SATISFIED | components.json, button/input/form/card/sidebar/breadcrumb/sheet/dropdown-menu + 15 more components |
| FRONT-10 | 09-03 | HTTP client with typed calls, Bearer injection, error normalization | SATISFIED | Axios apiClient, withCredentials (cookie = Bearer), normalizeError(), typed authApi |
| FRONT-11 | 09-03/09-05 | React Hook Form + Zod resolver | SATISFIED | react-hook-form@7.72.1, @hookform/resolvers@5.2.2, zodResolver used in all 4 auth forms |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/layout/chat-panel.tsx` | 13 | Comment: "v1 placeholder: shows 'AI Assistant coming soon' message" | INFO | Expected — QuasarFlow integration planned for Phase 10/v2. Not a blocker. |
| `frontend/src/proxy.ts` | 11 | Comment: "Auth guard logic will be added in Plan 09-05" — Plan 09-05 shipped without it | BLOCKER | Protected routes are accessible to unauthenticated users. SC5 partially unmet. |

---

### Human Verification Required

#### 1. Auth Flow End-to-End (with Running Backend)

**Test:** Start backend (`docker compose up`), navigate to `/en/register`, fill form, submit. Then check verify-email notice. Then navigate to `/en/login`, submit. Check JWT cookies are set.
**Expected:** Register form shows verify-email page. Login form redirects to `/en/dashboard`. Browser shows `access_token` and `refresh_token` HttpOnly cookies.
**Why human:** Requires running backend on localhost:8000. Cannot test without live server.

#### 2. Locale Switching

**Test:** Visit `/en/dashboard`. Click language switcher. Select "Tiếng Việt". Observe all visible text changes.
**Expected:** All UI labels change to Vietnamese immediately. URL changes to `/vi/dashboard`. NEXT_LOCALE cookie is set.
**Why human:** Requires browser interaction to verify text change and cookie persistence.

#### 3. Theme Persistence

**Test:** Select "Dark" in ThemeToggle. Refresh page. Observe theme is preserved. Toggle to "System" and verify system preference is respected.
**Expected:** Dark mode persists after refresh. System preference (OS dark/light) is detected on first visit.
**Why human:** Requires browser storage access and reload testing.

#### 4. Sidebar Responsive Behavior

**Test:** Resize browser to mobile (<768px), tablet (768-1024px), desktop (>1024px) widths. Observe sidebar behavior.
**Expected:** Mobile: sidebar accessible via Sheet overlay. Tablet: icon-only sidebar. Desktop: expanded with labels.
**Why human:** Requires viewport testing in a browser.

---

### Gaps Summary

**1 gap blocking full goal achievement:**

**Route protection missing from proxy.ts (FRONT-08 partial, SC5 partial):**

The proxy.ts middleware handles i18n routing but does NOT protect routes. Unauthenticated users can access `/en/dashboard`, `/en/projects`, `/en/settings` without being redirected to login. The proxy.ts file even contains a comment from Plan 09-02 that says "Auth guard logic will be added in Plan 09-05" — but Plan 09-05 executed fully (all auth UI pages built) without adding this guard.

The **401 auto-refresh** component of FRONT-08 is fully implemented in `client.ts`. Only the **route protection** (proxy.ts auth guard) is absent.

To fix: Add auth guard logic to `proxy.ts` that:
1. Defines protected path prefixes (e.g., `/dashboard`, `/projects`, `/settings`)
2. Checks for the presence of an `access_token` cookie
3. Redirects to `/{locale}/login?redirect={pathname}` if the cookie is absent

**Context:** The 401 auto-refresh in `client.ts` means that once a user is on a page, expired tokens are handled correctly. But there is no gate preventing initial unauthenticated page access.

---

*Verified: 2026-04-12T00:00:00Z*
*Verifier: Claude (gsd-verifier)*
