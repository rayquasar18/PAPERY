# Plan 09-01 Execution Summary

**Plan:** 09-01 — Next.js 16 Project Scaffold & Core Configuration
**Phase:** 09 — Frontend Foundation & Auth UI
**Status:** COMPLETE ✅
**Executed:** 2026-04-12
**Branch:** feature/frontend-foundation-auth-ui

---

## Tasks Completed

### Task 09-01-01: Scaffold Next.js 16 project with pnpm ✅

**Commits:** `5226c62`

**What was done:**
- Scaffolded `frontend/` with `pnpm create next-app@latest` using TypeScript, Tailwind, ESLint, App Router, src-dir, `@/*` import alias
- Installed Next.js 16.2.3, React 19.2.4, React DOM 19.2.4
- Created `frontend/.npmrc` with `shamefully-hoist=true` and `strict-peer-dependencies=false`
- Created `frontend/.env.example` and `frontend/.env.local` with `NEXT_PUBLIC_BACKEND_API_URL`, `NEXT_PUBLIC_API_VERSION`, `BACKEND_API_URL`, `API_VERSION`
- Updated `frontend/.gitignore` to add `!.env.example` exception so the example file is committed

**Acceptance criteria met:**
- ✅ `frontend/package.json` contains `"next": "16.2.3"`
- ✅ `frontend/tsconfig.json` contains `"strict": true`
- ✅ `frontend/tsconfig.json` contains `"@/*": ["./src/*"]`
- ✅ `frontend/.npmrc` contains `shamefully-hoist=true`
- ✅ `frontend/.env.example` contains `NEXT_PUBLIC_BACKEND_API_URL`

---

### Task 09-01-02: Configure Tailwind CSS v4 and PostCSS ✅

**Commits:** `0c3e7f8`

**What was done:**
- `postcss.config.mjs` already had `@tailwindcss/postcss` from scaffold (no changes needed)
- Rewrote `frontend/src/app/globals.css` with Tailwind v4 CSS-first config:
  - `@import "tailwindcss"` (v4 syntax — no `@tailwind base/components/utilities`)
  - `@import "tw-animate-css"` for shadcn/ui animation compatibility
  - Blue/Indigo professional color palette via CSS variables (HSL, both light and dark mode)
  - `@theme inline` block mapping CSS vars to Tailwind color tokens
  - `@custom-variant dark` for Tailwind v4 class-based dark mode
- Installed `tw-animate-css@1.4.0` as a dependency

**Acceptance criteria met:**
- ✅ `postcss.config.mjs` contains `@tailwindcss/postcss`
- ✅ `globals.css` contains `@import "tailwindcss"` and does NOT contain `@tailwind base`
- ✅ `globals.css` contains `@import "tw-animate-css"`
- ✅ `package.json` devDependencies contains `@tailwindcss/postcss`
- ✅ `package.json` dependencies contains `tw-animate-css`

---

### Task 09-01-03: Configure ESLint flat config and next.config.ts ✅

**Commits:** `8f3a1da`

**What was done:**
- `eslint.config.mjs` uses ESLint flat config format (Next.js 16 default — `defineConfig` + `globalIgnores`)
- Updated `next.config.ts` with `reactCompiler: true` and `images.remotePatterns` stub
- Installed `babel-plugin-react-compiler@1.0.0` (required by Next.js 16 for React Compiler)
- `pnpm lint` runs without config errors

**Acceptance criteria met:**
- ✅ `next.config.ts` contains `reactCompiler: true`
- ✅ `eslint.config.mjs` exists with flat config format
- ✅ `pnpm lint` completes without config errors

---

### Task 09-01-04: Initialize shadcn/ui and install base components ✅

**Commits:** `062e4b0`

**What was done:**
- Created `frontend/components.json` with new-york style, RSC, TSX, CSS variables, neutral base color, and correct path aliases
- Created `frontend/src/lib/utils.ts` with `cn()` helper using `clsx` + `tailwind-merge`
- Installed core shadcn/ui dependencies: `clsx@2.1.1`, `tailwind-merge@3.5.0`, `class-variance-authority@0.7.1`, `lucide-react@1.8.0`
- Installed shadcn/ui components via `pnpm dlx shadcn@latest add`: `button`, `input`, `label`, `card`, `separator`
  - Components installed at `frontend/src/components/ui/`

**Acceptance criteria met:**
- ✅ `components.json` exists and contains `"style": "new-york"`
- ✅ `src/lib/utils.ts` exists and contains `export function cn`
- ✅ `src/components/ui/button.tsx` exists
- ✅ `src/components/ui/input.tsx` exists
- ✅ `src/components/ui/card.tsx` exists
- ✅ `package.json` contains `clsx` in dependencies
- ✅ `package.json` contains `tailwind-merge` in dependencies

---

### Task 09-01-05: Create base folder structure and root layout ✅

**Commits:** `4ef09fb`

**What was done:**
- Created all required directories with `.gitkeep` files:
  - `src/components/layout/`, `src/components/auth/`, `src/components/providers/`
  - `src/lib/api/`, `src/lib/hooks/`, `src/lib/stores/`, `src/lib/types/`, `src/lib/schemas/`
  - `src/i18n/`, `src/locale/`
- Updated `src/app/layout.tsx` as root layout:
  - Inter font with `subsets: ['latin', 'vietnamese']`, `variable: '--font-sans'`, `display: 'swap'`
  - `suppressHydrationWarning` on `<html>` for next-themes compatibility
  - Metadata: title "PAPERY", description "AI-powered document intelligence platform"
- Created `src/app/not-found.tsx` — 404 page with link back home
- Created `src/app/global-error.tsx` — error boundary with `'use client'` directive, error logging, reset button

**Note:** Root layout includes `<html>` and `<body>` tags at this level. The `[locale]/layout.tsx` (Plan 09-02) will override the `lang` attribute via next-intl locale routing.

**Acceptance criteria met:**
- ✅ `src/app/layout.tsx` contains `Inter` font import from `next/font/google`
- ✅ `src/app/layout.tsx` contains `subsets: ['latin', 'vietnamese']`
- ✅ `src/app/layout.tsx` contains `variable: '--font-sans'`
- ✅ `src/app/not-found.tsx` exists
- ✅ `src/app/global-error.tsx` exists
- ✅ All required directories exist

---

## Build Verification

```
pnpm build → ✅ SUCCESS
▲ Next.js 16.2.3 (Turbopack)
✓ Compiled successfully in 1618ms
✓ TypeScript passed
✓ Generating static pages (4/4)
```

```
pnpm lint → ✅ No errors
```

---

## Must-Haves Status

- [x] Next.js 16 project exists at `frontend/` with `pnpm`
- [x] TypeScript strict mode enabled
- [x] Tailwind CSS v4 with `@import "tailwindcss"` syntax
- [x] shadcn/ui initialized with components.json
- [x] Inter font loaded with Vietnamese subset
- [x] Base folder structure created
- [x] `pnpm build` succeeds

---

## Files Created / Modified

| File | Action |
|------|--------|
| `frontend/package.json` | Created by scaffold, modified (tw-animate-css, shadcn deps, babel-plugin-react-compiler) |
| `frontend/tsconfig.json` | Created by scaffold (strict mode, bundler resolution, @/* already set) |
| `frontend/next.config.ts` | Modified (reactCompiler: true, images stub) |
| `frontend/postcss.config.mjs` | Created by scaffold (@tailwindcss/postcss already set) |
| `frontend/eslint.config.mjs` | Created by scaffold (ESLint flat config) |
| `frontend/.npmrc` | Created (shamefully-hoist=true) |
| `frontend/.env.local` | Created (gitignored, local dev values) |
| `frontend/.env.example` | Created (committed, placeholder values) |
| `frontend/.gitignore` | Modified (added !.env.example exception) |
| `frontend/components.json` | Created (shadcn/ui config) |
| `frontend/src/app/layout.tsx` | Modified (Inter font, PAPERY metadata, suppressHydrationWarning) |
| `frontend/src/app/globals.css` | Modified (Tailwind v4 imports, Blue/Indigo palette, @theme inline) |
| `frontend/src/app/not-found.tsx` | Created |
| `frontend/src/app/global-error.tsx` | Created |
| `frontend/src/lib/utils.ts` | Created (cn() helper) |
| `frontend/src/components/ui/button.tsx` | Created by shadcn |
| `frontend/src/components/ui/input.tsx` | Created by shadcn |
| `frontend/src/components/ui/label.tsx` | Created by shadcn |
| `frontend/src/components/ui/card.tsx` | Created by shadcn |
| `frontend/src/components/ui/separator.tsx` | Created by shadcn |
| `frontend/src/components/layout/.gitkeep` | Created |
| `frontend/src/components/auth/.gitkeep` | Created |
| `frontend/src/components/providers/.gitkeep` | Created |
| `frontend/src/lib/api/.gitkeep` | Created |
| `frontend/src/lib/hooks/.gitkeep` | Created |
| `frontend/src/lib/stores/.gitkeep` | Created |
| `frontend/src/lib/types/.gitkeep` | Created |
| `frontend/src/lib/schemas/.gitkeep` | Created |
| `frontend/src/i18n/.gitkeep` | Created |
| `frontend/src/locale/.gitkeep` | Created |

---

## Key Technical Notes

1. **Next.js 16.2.3 + React 19.2.4** — Latest stable versions, Turbopack is default bundler
2. **`babel-plugin-react-compiler` required** — Next.js 16 `reactCompiler: true` requires this Babel plugin; purely additive, no behavior change needed
3. **Tailwind v4 `@custom-variant dark`** — Used instead of v3 `darkMode: 'class'` config; Tailwind v4 handles this via CSS
4. **shadcn init skipped** — Created `components.json` manually to avoid interactive CLI prompts; components installed via `pnpm dlx shadcn@latest add` which works non-interactively
5. **Root layout has `<html>`/`<body>`** — Plan 09-02 will add `[locale]/layout.tsx` which Next.js App Router will treat as a nested layout; the `lang` attribute will need updating there via next-intl

---

*Executed by: Claude Opus 4.6*
*Plan: 09-01 | Phase: 09 | Wave: 1*
