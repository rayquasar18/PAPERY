# Phase 9 Research: Internationalization (next-intl)

**Researched:** 2026-04-11
**Scope:** next-intl App Router integration, locale routing, translation file structure, middleware
**Relevant decisions:** D-18, D-19, D-20, D-21, D-22, D-31
**Requirement:** FRONT-02 — Internationalization from day one via next-intl (EN + VI minimum)

---

## 1. Key Findings

1. **next-intl v4.9.1** (released 2026-04-10) is the latest stable version. Fully supports Next.js 15/16 App Router. ESM-only since v4.0.
2. **Next.js 16 renamed `middleware.ts` to `proxy.ts`** — next-intl docs confirm this: the middleware file must be `src/proxy.ts` for Next.js 16+.
3. **Mandatory locale prefix (`always` mode)** is the default and matches our D-19 decision perfectly. All URLs will be `/en/...` and `/vi/...`.
4. **Server Components are first-class citizens** — translations stay on the server by default, zero client-side bundle impact. Only interactive components need `NextIntlClientProvider`.
5. **Type-safe translations** via `AppConfig` module augmentation — provides autocomplete and compile-time key validation with ~0.6s overhead.
6. **Locale auto-detection** from `Accept-Language` header is built into the middleware (D-20). Uses `@formatjs/intl-localematcher` with "best fit" algorithm.
7. **Cookie-based persistence** — middleware stores locale preference in `NEXT_LOCALE` session cookie automatically.
8. **Message precompilation** (v4.8.0+) — experimental feature that reduces bundle size and speeds up runtime formatting.

---

## 2. next-intl Version & Compatibility

### Current Version
- **v4.9.1** (April 10, 2026)
- Major version: **4.x** (stable since late 2024)

### Recent Notable Releases
| Version | Date | Highlight |
|---------|------|-----------|
| v4.9.1 | 2026-04-10 | Bug fix: middleware pathname validation |
| v4.9.0 | 2026-04-01 | `transitionTypes` on `Link` component |
| v4.8.4 | 2026-03-31 | Removed TypeScript peer dependency |
| v4.8.0 | 2026-01-28 | **Ahead-of-time message compilation** |

### Breaking Changes from v3 → v4
- **ESM-only** — CommonJS no longer supported (except `next-intl/plugin`)
- **React 17+** minimum peer dependency
- **TypeScript 5+** minimum
- **`NextIntlClientProvider`** must wrap all Client Components using next-intl
- **`AppConfig` interface** replaces old global type augmentation pattern
- **ICU arguments strictly typed** (opt-in)
- **Session cookies** by default (expire when browser closes)
- **`localeCookie: false`** replaces deprecated `localeDetection: false`

### Next.js 16 Compatibility
- ✅ Fully compatible
- `proxy.ts` replaces `middleware.ts` (Next.js 16 rename)
- `params` is now a `Promise` — must `await params` in layouts/pages

---

## 3. App Router Integration

### Required Directory Structure
```
frontend/
├── src/
│   ├── app/
│   │   └── [locale]/           # Dynamic locale segment
│   │       ├── layout.tsx      # Root locale layout
│   │       ├── page.tsx        # Home page
│   │       ├── (auth)/         # Auth route group
│   │       │   ├── login/
│   │       │   ├── register/
│   │       │   └── ...
│   │       └── (dashboard)/    # Dashboard route group
│   │           └── ...
│   ├── i18n/
│   │   ├── routing.ts          # Locale routing config
│   │   ├── navigation.ts       # Localized navigation APIs
│   │   └── request.ts          # Server-side request config
│   ├── locale/                  # Translation files (per D-22)
│   │   ├── en.json
│   │   └── vi.json
│   └── proxy.ts                # Middleware (Next.js 16 naming)
├── next.config.ts              # Plugin setup
└── tsconfig.json               # TypeScript config
```

### Plugin Setup (`next.config.ts`)
```typescript
import { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const nextConfig: NextConfig = {};

const withNextIntl = createNextIntlPlugin({
  requestConfig: './src/i18n/request.ts'
});

export default withNextIntl(nextConfig);
```

### Routing Config (`src/i18n/routing.ts`)
```typescript
import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'vi'],
  defaultLocale: 'en',
  localePrefix: 'always'  // D-19: mandatory prefix
});
```

### Request Config (`src/i18n/request.ts`)
```typescript
import { getRequestConfig } from 'next-intl/server';
import { hasLocale } from 'next-intl';
import { routing } from './routing';

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../locale/${locale}.json`)).default
  };
});
```

### Navigation APIs (`src/i18n/navigation.ts`)
```typescript
import { createNavigation } from 'next-intl/navigation';
import { routing } from './routing';

export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
```

### Root Locale Layout (`src/app/[locale]/layout.tsx`)
```typescript
import { NextIntlClientProvider, hasLocale } from 'next-intl';
import { notFound } from 'next/navigation';
import { routing } from '@/i18n/routing';
import { setRequestLocale } from 'next-intl/server';

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

---

## 4. Locale Routing

### Mandatory Prefix Strategy (D-19)

With `localePrefix: 'always'` (default):
- `/en/dashboard` → English dashboard
- `/vi/dashboard` → Vietnamese dashboard
- `/dashboard` → Redirected to `/en/dashboard` (based on detection)
- `/` → Redirected to `/en` or `/vi` (based on detection)

### Locale Detection Priority (middleware)
1. **Locale prefix in URL** (highest priority) — `/vi/about` → Vietnamese
2. **`NEXT_LOCALE` cookie** — Previously stored user preference
3. **`Accept-Language` header** — Browser language setting (D-20)
4. **`defaultLocale` fallback** — English (D-18)

### Redirect Behavior
- First visit with no cookie → Accept-Language detection → redirect to matched locale
- User switches locale → cookie updated → subsequent visits use cookie
- Direct URL with locale prefix → always honored, cookie updated

### Matcher Configuration
```typescript
// In proxy.ts
export const config = {
  matcher: '/((?!api|trpc|_next|_vercel|.*\\..*).*)'
};
```
This excludes: API routes, Next.js internals, Vercel internals, and static files.

---

## 5. Translation Files

### File Structure (per D-22)
Location: `src/locale/en.json` and `src/locale/vi.json`

### Recommended JSON Structure for PAPERY
```json
// src/locale/en.json
{
  "Common": {
    "appName": "PAPERY",
    "loading": "Loading...",
    "error": "An error occurred",
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete",
    "confirm": "Confirm",
    "back": "Back",
    "next": "Next",
    "submit": "Submit"
  },
  "Navigation": {
    "dashboard": "Dashboard",
    "projects": "Projects",
    "settings": "Settings"
  },
  "Auth": {
    "login": {
      "title": "Welcome back",
      "subtitle": "Sign in to your account",
      "emailLabel": "Email address",
      "emailPlaceholder": "Enter your email",
      "passwordLabel": "Password",
      "passwordPlaceholder": "Enter your password",
      "submitButton": "Sign in",
      "forgotPassword": "Forgot your password?",
      "noAccount": "Don't have an account?",
      "signUpLink": "Sign up",
      "orContinueWith": "Or continue with",
      "googleButton": "Continue with Google",
      "githubButton": "Continue with GitHub"
    },
    "register": {
      "title": "Create an account",
      "subtitle": "Get started with PAPERY",
      "nameLabel": "Full name",
      "namePlaceholder": "Enter your name",
      "emailLabel": "Email address",
      "emailPlaceholder": "Enter your email",
      "passwordLabel": "Password",
      "passwordPlaceholder": "Create a password",
      "confirmPasswordLabel": "Confirm password",
      "confirmPasswordPlaceholder": "Confirm your password",
      "submitButton": "Create account",
      "hasAccount": "Already have an account?",
      "signInLink": "Sign in",
      "termsNotice": "By creating an account, you agree to our <terms>Terms of Service</terms> and <privacy>Privacy Policy</privacy>."
    },
    "verification": {
      "title": "Check your email",
      "subtitle": "We sent a verification link to {email}",
      "resendButton": "Resend email",
      "resendSuccess": "Verification email sent",
      "backToLogin": "Back to sign in"
    },
    "forgotPassword": {
      "title": "Reset your password",
      "subtitle": "Enter your email to receive a reset link",
      "emailLabel": "Email address",
      "emailPlaceholder": "Enter your email",
      "submitButton": "Send reset link",
      "backToLogin": "Back to sign in",
      "successTitle": "Check your email",
      "successMessage": "We sent a password reset link to {email}"
    },
    "resetPassword": {
      "title": "Set new password",
      "subtitle": "Enter your new password below",
      "passwordLabel": "New password",
      "passwordPlaceholder": "Enter new password",
      "confirmPasswordLabel": "Confirm new password",
      "confirmPasswordPlaceholder": "Confirm new password",
      "submitButton": "Reset password",
      "successTitle": "Password reset successful",
      "successMessage": "You can now sign in with your new password"
    },
    "errors": {
      "invalidEmail": "Please enter a valid email address",
      "passwordTooShort": "Password must be at least 8 characters",
      "passwordMismatch": "Passwords do not match",
      "invalidCredentials": "Invalid email or password",
      "emailAlreadyExists": "An account with this email already exists",
      "emailNotVerified": "Please verify your email before signing in",
      "serverError": "Something went wrong. Please try again.",
      "networkError": "Unable to connect. Check your internet connection.",
      "tokenExpired": "Your session has expired. Please sign in again.",
      "resetLinkExpired": "This reset link has expired. Please request a new one."
    }
  },
  "Theme": {
    "light": "Light",
    "dark": "Dark",
    "system": "System"
  },
  "Language": {
    "en": "English",
    "vi": "Tiếng Việt",
    "switchLabel": "Language"
  },
  "Metadata": {
    "title": "PAPERY — Document Intelligence Platform",
    "description": "AI-powered document intelligence for research, Q&A, and collaboration"
  }
}
```

### Namespacing Strategy
- **Top-level keys = namespaces** — `Common`, `Auth`, `Navigation`, etc.
- **Feature-scoped grouping** — auth translations under `Auth`, dashboard under `Dashboard`
- **Dot notation access** within namespaces — `t('login.title')` when using `useTranslations('Auth')`
- **Namespace keys cannot contain `.`** — dots are reserved for nesting

### ICU Message Format Support
- **Interpolation:** `"subtitle": "We sent a verification link to {email}"`
- **Pluralization:** `"message": "You have {count, plural, =0 {no items} one {# item} other {# items}}"`
- **Rich text tags:** `"termsNotice": "...agree to our <terms>Terms</terms> and <privacy>Privacy</privacy>."`

---

## 6. Usage Patterns

### Server Components (Preferred — Zero Client Bundle)

```typescript
// Async Server Component
import { getTranslations } from 'next-intl/server';

export default async function LoginPage() {
  const t = await getTranslations('Auth.login');

  return (
    <div>
      <h1>{t('title')}</h1>
      <p>{t('subtitle')}</p>
    </div>
  );
}
```

### Client Components (Interactive)

```typescript
'use client';

import { useTranslations } from 'next-intl';

export function LoginForm() {
  const t = useTranslations('Auth.login');

  return (
    <form>
      <label>{t('emailLabel')}</label>
      <input placeholder={t('emailPlaceholder')} />
      <button type="submit">{t('submitButton')}</button>
    </form>
  );
}
```

### Metadata (SEO)

```typescript
import { getTranslations } from 'next-intl/server';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Metadata' });

  return {
    title: t('title'),
    description: t('description')
  };
}
```

### Static Rendering

For static rendering (SSG), call `setRequestLocale(locale)` in every layout and page **before** any next-intl function:

```typescript
import { setRequestLocale } from 'next-intl/server';
import { useTranslations } from 'next-intl';
import { use } from 'react';

export default function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = use(params);
  setRequestLocale(locale);

  const t = useTranslations('Auth.login');
  return <h1>{t('title')}</h1>;
}
```

### Rich Text with React Components

```typescript
const t = useTranslations('Auth.register');

// For: "By creating an account, you agree to our <terms>Terms</terms>..."
t.rich('termsNotice', {
  terms: (chunks) => <a href="/terms">{chunks}</a>,
  privacy: (chunks) => <a href="/privacy">{chunks}</a>
});
```

### Key Existence Check

```typescript
const t = useTranslations('Auth');
if (t.has('login.title')) {
  // Key exists
}
```

### Server-Side APIs Summary
| API | Context | Returns |
|-----|---------|---------|
| `getTranslations(namespace?)` | Async Server Components, Metadata, Route Handlers | `t()` function |
| `getMessages()` | Async Server Components | Raw message object |
| `getLocale()` | Async Server Components | Current locale string |
| `getNow()` | Async Server Components | Current timestamp |
| `getTimeZone()` | Async Server Components | Timezone string |
| `getFormatter()` | Async Server Components | Formatting utilities |
| `setRequestLocale(locale)` | Layouts/Pages (before other calls) | void (enables static rendering) |

---

## 7. Language Switcher

### Implementation Approach

Use `useRouter` and `usePathname` from `@/i18n/navigation` for client-side locale switching:

```typescript
'use client';

import { useLocale } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/navigation';
import { routing } from '@/i18n/routing';

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  function onLocaleChange(nextLocale: string) {
    router.replace(pathname, { locale: nextLocale });
  }

  return (
    <select value={locale} onChange={(e) => onLocaleChange(e.target.value)}>
      {routing.locales.map((loc) => (
        <option key={loc} value={loc}>
          {loc === 'en' ? 'English' : 'Tiếng Việt'}
        </option>
      ))}
    </select>
  );
}
```

### How It Works (No Full Page Reload)
1. `useRouter().replace()` updates the cookie on the **client side** before navigating
2. Next.js performs a **client-side navigation** to the new locale path
3. The middleware sees the updated cookie for subsequent requests
4. Result: seamless locale switch without full page reload

### Link-based Switching Alternative
```typescript
import { Link } from '@/i18n/navigation';

// Note: Link with locale prop disables prefetching to avoid
// prematurely overwriting the locale cookie
<Link href="/" locale="vi">Tiếng Việt</Link>
```

---

## 8. Type Safety

### Module Augmentation (`src/i18n/global.d.ts`)
```typescript
import { routing } from '@/i18n/routing';
import en from '../locale/en.json';

declare module 'next-intl' {
  interface AppConfig {
    Locale: (typeof routing.locales)[number]; // 'en' | 'vi'
    Messages: typeof en;
  }
}
```

### Benefits
- **Autocomplete** — IDE suggests valid translation keys
- **Compile-time validation** — TypeScript errors for invalid keys
- **Argument enforcement** — If message has `{email}`, TypeScript requires `t('key', { email })` 
- **Namespace scoping** — `useTranslations('Auth')` only allows keys within `Auth`

### tsconfig.json Addition
```json
{
  "compilerOptions": {
    "allowArbitraryExtensions": true
  }
}
```

### Optional: Auto-generated Type Declarations
```typescript
// next.config.ts
const withNextIntl = createNextIntlPlugin({
  requestConfig: './src/i18n/request.ts',
  experimental: {
    createMessagesDeclaration: './src/locale/en.json'
  }
});
```
This generates `src/locale/en.d.json.ts` automatically. Add `*.d.json.ts` to `.gitignore`.

### Performance Impact
- ~0.6 seconds added to type checking on a 340-message project
- Negligible for our initial EN + VI setup

---

## 9. Risks & Considerations

### Known Issues
1. **`proxy.ts` naming** — Next.js 16 specific; if team needs to support Next.js 15 locally, both names may be needed. Stick with `proxy.ts` since project targets Next.js 16 (D-23).
2. **`t.raw()` not supported with precompiled messages** — Avoid `t.raw()` if using message precompilation.
3. **Middleware composition** — next-intl middleware must be composed with auth middleware in a single `proxy.ts`. Auth checks should wrap the i18n middleware call.

### Performance Considerations
- **Server Components**: Translations stay on server — zero client bundle impact
- **Client Components**: Only namespaced messages are sent to client via `NextIntlClientProvider`
- **Message precompilation** (experimental): Reduces bundle size, speeds up formatting
- **Static rendering**: Use `setRequestLocale()` + `generateStaticParams()` for SSG pages

### Bundle Size
- next-intl is lightweight (~15-20KB gzipped for client runtime)
- Server Component translations have zero client cost
- Only Client Components contribute to bundle

### Middleware Composition Pattern (i18n + Auth)
```typescript
// src/proxy.ts
import createIntlMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';
import { NextRequest, NextResponse } from 'next/server';

const handleI18nRouting = createIntlMiddleware(routing);

export default async function proxy(request: NextRequest) {
  // Step 1: i18n routing (locale detection + redirect)
  const response = handleI18nRouting(request);

  // Step 2: Auth checks (after i18n resolves locale)
  // Read auth cookie, check protected routes, redirect if needed
  // ... auth logic here ...

  return response;
}

export const config = {
  matcher: '/((?!api|trpc|_next|_vercel|.*\\..*).*)'
};
```

### Translation Sync Risk
- Keeping `en.json` and `vi.json` in sync is manual
- Consider: lint script to detect missing keys between locales
- next-intl's `onError` callback can catch missing translations at runtime

---

## 10. Recommended Configuration

### Complete File List for i18n Setup

| File | Purpose |
|------|---------|
| `next.config.ts` | Plugin registration with `createNextIntlPlugin` |
| `src/proxy.ts` | Middleware for locale detection + routing |
| `src/i18n/routing.ts` | Locale list, default locale, prefix strategy |
| `src/i18n/request.ts` | Server-side config: locale resolution + message loading |
| `src/i18n/navigation.ts` | Localized `Link`, `useRouter`, `usePathname`, `redirect` |
| `src/i18n/global.d.ts` | TypeScript module augmentation for type-safe translations |
| `src/locale/en.json` | English translations |
| `src/locale/vi.json` | Vietnamese translations |
| `src/app/[locale]/layout.tsx` | Root locale layout with `NextIntlClientProvider` |

### Package to Install
```bash
pnpm add next-intl
```
No additional packages needed — `@formatjs/intl-localematcher` is bundled.

### Routing Config Decisions Mapped
| Decision | Config | Value |
|----------|--------|-------|
| D-18: Default locale EN | `defaultLocale` | `'en'` |
| D-19: Mandatory prefix | `localePrefix` | `'always'` |
| D-20: Auto-detect | `localeDetection` | `true` (default) |
| D-21: EN + VI | `locales` | `['en', 'vi']` |
| D-22: JSON in src/locale/ | `i18n/request.ts` | Dynamic import from `../locale/${locale}.json` |

### Cookie Configuration
- **Name:** `NEXT_LOCALE` (default)
- **Type:** Session cookie (expires on browser close — v4 default)
- **SameSite:** `lax`
- To persist across sessions: set `localeCookie: { maxAge: 60 * 60 * 24 * 365 }` (1 year)

### Recommendation: Persist Cookie
Since users explicitly choosing a language should have it remembered, override the default session cookie:

```typescript
// src/i18n/routing.ts
export const routing = defineRouting({
  locales: ['en', 'vi'],
  defaultLocale: 'en',
  localePrefix: 'always',
  localeCookie: {
    name: 'NEXT_LOCALE',
    maxAge: 60 * 60 * 24 * 365 // 1 year persistence
  }
});
```

---

*Research completed: 2026-04-11*
*Sources: next-intl.dev official docs (v4.9.x), GitHub releases*
