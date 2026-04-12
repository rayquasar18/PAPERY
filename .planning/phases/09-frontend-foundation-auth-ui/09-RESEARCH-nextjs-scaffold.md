# Phase 9 Research: Next.js 16 + React 19 Scaffold

**Researched:** 2026-04-12
**Scope:** Next.js 16 features, React 19 integration, TypeScript strict, pnpm, folder structure
**Relevant decisions:** D-23, D-24
**Requirement:** FRONT-01 — Next.js 16 + React 19 App Router setup with TypeScript strict mode

---

## 1. Key Findings

1. **Next.js 16.2** is the latest stable (March 2026). Released Oct 2025 as v16.0. Key changes: Turbopack is default bundler, Cache Components, `proxy.ts` replaces `middleware.ts`, React Compiler support.
2. **React 19.2** is bundled with Next.js 16 — includes View Transitions, `useEffectEvent()`, and Activity (background rendering with `display: none`).
3. **`proxy.ts` replaces `middleware.ts`** — This is a CRITICAL breaking change. The function export name is `proxy` (not `middleware`). Confirmed by Next.js 16 blog and reference project.
4. **Turbopack is now the default** — No need to opt-in. `next build --webpack` to opt out. File system caching for dev is experimental.
5. **Parallel routes require `default.js`** — All parallel route slots now require explicit `default.js` files; builds fail without them.
6. **Reference project** (open-notebook) successfully uses Next.js 16.1.5 + React 19.2.3 with pnpm — validates our stack choices.

## 2. Next.js 16 Breaking Changes from 15

| Change | Impact | Action |
|--------|--------|--------|
| `proxy.ts` replaces `middleware.ts` | HIGH — auth + i18n middleware must use new file | Use `src/proxy.ts` with `export function proxy()` |
| Turbopack default bundler | LOW — better perf, same API | No action needed, automatic |
| `revalidateTag()` requires cacheLife profile | MEDIUM — affects caching | Use `revalidateTag('key', 'max')` |
| `images.minimumCacheTTL` → 4h default | LOW | No action for new project |
| `images.qualities` → [75] default | LOW | No action for new project |
| Parallel routes need `default.js` | MEDIUM — affects route groups | Add `default.tsx` to each parallel slot |
| ESLint defaults to Flat Config | MEDIUM | Use `eslint.config.mjs` format |
| Border-color default → `currentColor` (Tailwind v4) | MEDIUM | Always specify border color explicitly |
| Prefetch cache rewrite | LOW — internal change | No action |
| Dev + build separate output dirs | LOW — enables concurrent execution | Beneficial for DX |

## 3. React 19.2 Features

| Feature | Use Case in PAPERY |
|---------|-------------------|
| **Server Components** (stable) | Default for all pages/layouts — zero JS shipped for static content |
| **Client Components** (`'use client'`) | Interactive components: forms, theme toggle, sidebar state |
| **Server Actions** (`'use server'`) | Form submissions, data mutations (optional — we use REST API) |
| **`use()` hook** | Read promises/context in render — useful for async data |
| **View Transitions** (19.2) | Smooth page transitions in navigation — FUTURE USE |
| **`useEffectEvent()`** (19.2) | Extract non-reactive logic from Effects |
| **Activity** (19.2) | Background rendering for tab/panel preloading — FUTURE USE |
| **React Compiler** | Auto-memoization — enable via `reactCompiler: true` in next.config |

## 4. TypeScript Configuration

```jsonc
// tsconfig.json — strict mode for Next.js 16
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,                    // D-23: strict mode
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]               // Required for shadcn/ui
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

## 5. pnpm Setup

```ini
# .npmrc for Next.js 16 + pnpm
shamefully-hoist=true
strict-peer-dependencies=false
```

- `shamefully-hoist=true` — Required for Next.js and many React ecosystem packages that expect flat node_modules
- Reference project uses pnpm with these settings confirmed working

Scaffold command:
```bash
pnpm create next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-pnpm
```

## 6. Recommended Folder Structure

```
frontend/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── [locale]/                 # i18n locale segment
│   │   │   ├── (auth)/               # Auth route group (no layout chrome)
│   │   │   │   ├── login/page.tsx
│   │   │   │   ├── register/page.tsx
│   │   │   │   ├── verify-email/page.tsx
│   │   │   │   ├── forgot-password/page.tsx
│   │   │   │   ├── reset-password/page.tsx
│   │   │   │   └── layout.tsx        # Auth layout (split-screen branding)
│   │   │   ├── (dashboard)/          # Protected route group
│   │   │   │   ├── dashboard/page.tsx
│   │   │   │   ├── projects/page.tsx
│   │   │   │   ├── settings/page.tsx
│   │   │   │   ├── layout.tsx        # Dashboard layout (sidebar + topbar)
│   │   │   │   └── default.tsx       # Required for parallel routes
│   │   │   ├── layout.tsx            # Root locale layout (providers)
│   │   │   └── page.tsx              # Redirect to /dashboard
│   │   ├── layout.tsx                # Root layout (html, body, fonts)
│   │   ├── not-found.tsx
│   │   └── global-error.tsx
│   ├── components/
│   │   ├── ui/                       # shadcn/ui components
│   │   ├── layout/                   # AppSidebar, TopBar, ChatPanel
│   │   ├── auth/                     # LoginForm, RegisterForm, etc.
│   │   └── providers/                # ThemeProvider, QueryProvider, etc.
│   ├── lib/
│   │   ├── api/                      # Axios client, API modules
│   │   ├── hooks/                    # Custom React hooks
│   │   ├── stores/                   # Zustand stores
│   │   ├── types/                    # TypeScript type definitions
│   │   ├── schemas/                  # Zod validation schemas
│   │   └── utils.ts                  # cn() helper, utility functions
│   ├── i18n/                         # next-intl config
│   │   ├── routing.ts
│   │   ├── request.ts
│   │   └── navigation.ts
│   ├── locale/                       # Translation JSON files
│   │   ├── en.json
│   │   └── vi.json
│   └── proxy.ts                      # Next.js 16 proxy (replaces middleware)
├── public/                           # Static assets
├── next.config.ts
├── tailwind.config.ts                # If needed beyond CSS-first
├── postcss.config.mjs
├── tsconfig.json
├── .npmrc
├── .env.local
├── .env.example
└── package.json
```

## 7. Scaffold Steps

1. `pnpm create next-app@latest frontend` — with TypeScript, Tailwind, ESLint, App Router, src-dir
2. Configure `.npmrc` with `shamefully-hoist=true`
3. Update `tsconfig.json` with strict mode settings
4. Create `next.config.ts` with reactCompiler and cacheComponents
5. Set up `src/proxy.ts` (replaces middleware.ts)
6. Configure PostCSS for Tailwind v4
7. Install shadcn/ui via `pnpm dlx shadcn@latest init`
8. Set up folder structure as above

## 8. next.config.ts Recommended

```typescript
import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  reactCompiler: true,
  // cacheComponents: true,  // Enable when ready
  images: {
    remotePatterns: [
      // Add backend MinIO URLs
    ],
  },
};

export default withNextIntl(nextConfig);
```

## 9. Risks & Considerations

1. **proxy.ts is new in Next.js 16** — Composing i18n + auth in single proxy file needs careful design
2. **Turbopack compatibility** — Some older packages may have issues; fallback to webpack available
3. **React Compiler** — Still relatively new; may cause unexpected re-render behavior. Can disable per-component.
4. **Tailwind v4 CSS-first config** — No more `tailwind.config.js` by default; may need `@config` directive for complex setups

## 10. Recommended Package Versions (from reference + latest)

```json
{
  "next": "^16.2.0",
  "react": "^19.2.0",
  "react-dom": "^19.2.0",
  "typescript": "^5.7.0",
  "tailwindcss": "^4.2.0",
  "@tailwindcss/postcss": "^4.2.0",
  "eslint": "^9.0.0",
  "eslint-config-next": "^16.2.0"
}
```

---

## RESEARCH COMPLETE

*Phase: 09-frontend-foundation-auth-ui*
*Research scope: Next.js 16 + React 19 Scaffold*
*Researched: 2026-04-12*
