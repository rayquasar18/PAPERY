# Plan 09-05 — SUMMARY

**Plan:** 09-05  
**Title:** Auth Pages — Login, Register, Verify, Password Reset  
**Status:** COMPLETE  
**Build:** ✅ `pnpm build` passes — 18 pages generated successfully

---

## Tasks Completed

### 09-05-01: Auth split-screen layout with branding panel
**Commits:** `f401c1d`

- Created `frontend/src/components/auth/auth-branding.tsx`
  - Left panel with `bg-gradient-to-br from-indigo-600 to-blue-800`
  - Decorative dot grid at 10% opacity
  - PAPERY logo (text-based), display tagline (30px semibold), subtitle (14px, 70% opacity)
  - Hidden on mobile: `hidden md:flex`
- Created `frontend/src/app/[locale]/(auth)/layout.tsx`
  - Full-screen split: branding (50%) + form (50%) on desktop; 40%/60% on tablet; form-only on mobile
  - `setRequestLocale(locale)` with `hasLocale()` narrowing
- Added `Auth.branding` translation keys to `en.json` and `vi.json`

### 09-05-02: useAuth hook and OAuthButtons component
**Commits:** `979fec1`

- Created `frontend/src/lib/hooks/use-auth.ts`
  - `useQuery` for `authApi.me` with `QUERY_KEYS.user`
  - `loginMutation`, `registerMutation`, `logoutMutation` via `useMutation`
  - Redirect-back URL passed as arg to avoid `useSearchParams` at hook level
  - Returns: `{ user, isLoading, isAuthenticated, login, logout, register, isLoggingIn, isRegistering, isLoggingOut }`
- Created `frontend/src/components/auth/oauth-buttons.tsx`
  - "Or continue with" `Separator` divider
  - Google + GitHub buttons with inline SVG icons
  - Calls `authApi.googleLogin()` / `authApi.githubLogin()` on click

### 09-05-03: LoginForm and login page
**Commits:** `b7367ec`

- Created `frontend/src/components/auth/login-form.tsx`
  - `useForm<LoginInput>` with `zodResolver(loginSchema)`, `mode: 'onBlur'`
  - Email + password fields with visibility toggle
  - "Forgot password?" link, `OAuthButtons`, register footer link
  - `useSearchParams` wrapped in `Suspense` boundary
  - Loading spinner when `isLoggingIn`
- Created `frontend/src/app/[locale]/(auth)/login/page.tsx`
  - Server component, `generateMetadata` with translated title

### 09-05-04: RegisterForm with PasswordStrength and register page
**Commits:** `5d0bdae`

- Created `frontend/src/components/auth/password-strength.tsx`
  - Four levels: Weak (red/25%), Fair (orange/50%), Good (yellow/75%), Strong (green/100%)
  - Criteria: length + character category count + special char for Strong
  - Animated color bar + label with `aria-live="polite"`
- Created `frontend/src/components/auth/register-form.tsx`
  - `useForm<RegisterInput>` with `zodResolver(registerSchema)`, `mode: 'onBlur'`
  - Fields: displayName, email, password + PasswordStrength, confirmPassword, terms checkbox
  - `t.rich()` for terms notice rich text (next-intl pattern)
- Created `frontend/src/app/[locale]/(auth)/register/page.tsx`

### 09-05-05: Verify-email, forgot-password, reset-password pages
**Commits:** `a1ab7b7`

- Created `frontend/src/app/[locale]/(auth)/verify-email/page.tsx`
  - Auto-calls `authApi.verifyEmail(token)` when `?token=` in URL
  - Shows success/error result states
  - 60s resend cooldown timer with `authApi.resendVerification(email)`
  - `useSearchParams` wrapped in `Suspense`
- Created `frontend/src/components/auth/forgot-password-form.tsx`
  - `zodResolver(forgotPasswordSchema)`, inline success state after submission
- Created `frontend/src/app/[locale]/(auth)/forgot-password/page.tsx`
- Created `frontend/src/components/auth/reset-password-form.tsx`
  - Reads `?token=` from URL, includes `PasswordStrength`, redirects to login on success
  - `useSearchParams` wrapped in `Suspense`
- Created `frontend/src/app/[locale]/(auth)/reset-password/page.tsx`

---

## Build Fixes (pre-existing issues resolved)

The following issues existed in code from Plans 09-02/09-03/09-04 and were
fixed as part of getting `pnpm build` to pass:

- **Locale type narrowing:** All pages using `setRequestLocale(locale)` now
  narrow `locale: string` → `"en" | "vi"` via `hasLocale()` before passing to
  next-intl server functions.
- **react-resizable-panels v4 API:** `PanelGroup`/`PanelResizeHandle` renamed
  to `Group`/`Separator` in v4; `layout-client.tsx` updated to use shadcn
  `ResizablePanelGroup` wrapper which handles the v4 API correctly.
- **language-switcher.tsx:** `router.replace` locale param narrowed with
  `routing.locales.find()` before passing.
- **dashboard/page.tsx:** Added `hasLocale()` narrowing for `setRequestLocale`.

---

## Files Created

| File | Purpose |
|------|---------|
| `frontend/src/components/auth/auth-branding.tsx` | Gradient branding left panel |
| `frontend/src/app/[locale]/(auth)/layout.tsx` | Auth split-screen layout |
| `frontend/src/lib/hooks/use-auth.ts` | Central auth hook (TanStack Query) |
| `frontend/src/components/auth/oauth-buttons.tsx` | Google + GitHub OAuth buttons |
| `frontend/src/components/auth/login-form.tsx` | Login form (RHF + Zod) |
| `frontend/src/app/[locale]/(auth)/login/page.tsx` | Login page |
| `frontend/src/components/auth/password-strength.tsx` | Password strength indicator |
| `frontend/src/components/auth/register-form.tsx` | Register form (RHF + Zod) |
| `frontend/src/app/[locale]/(auth)/register/page.tsx` | Register page |
| `frontend/src/app/[locale]/(auth)/verify-email/page.tsx` | Email verification page |
| `frontend/src/components/auth/forgot-password-form.tsx` | Forgot password form |
| `frontend/src/app/[locale]/(auth)/forgot-password/page.tsx` | Forgot password page |
| `frontend/src/components/auth/reset-password-form.tsx` | Reset password form |
| `frontend/src/app/[locale]/(auth)/reset-password/page.tsx` | Reset password page |

---

## Must-Haves Verification

- [x] Auth split-screen layout (branding left, form right, responsive)
- [x] LoginForm with email/password, Zod validation on blur, OAuth buttons
- [x] RegisterForm with password strength indicator
- [x] Verify-email page with resend button (60s cooldown)
- [x] Forgot-password and reset-password forms
- [x] useAuth hook with login/logout/register mutations
- [x] All forms use React Hook Form + zodResolver
- [x] All text uses `useTranslations()` for i18n
- [x] `pnpm build` succeeds (18 pages generated)

---

*Completed: 2026-04-12*  
*Branch: feature/frontend-foundation-auth-ui*  
*Commits: f401c1d, 979fec1, b7367ec, 5d0bdae, a1ab7b7, f430799*
