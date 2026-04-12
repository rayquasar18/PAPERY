# Phase 9 Research: Frontend Foundation & Auth UI

**Researched:** 2026-04-12
**Status:** Complete
**Phase:** 09-frontend-foundation-auth-ui
**Requirements:** FRONT-01 through FRONT-11

---

## Research Summary

This research was conducted across 6 focused domains. Each has its own detailed file.

### Research Files

| File | Domain | Key Finding |
|------|--------|-------------|
| `09-RESEARCH-nextjs-scaffold.md` | Next.js 16 + React 19 | Turbopack default, `proxy.ts` replaces `middleware.ts`, React Compiler |
| `09-RESEARCH-i18n.md` | Internationalization | next-intl v4.9.1, mandatory locale prefix, type-safe translations |
| `09-RESEARCH-theme-design.md` | Theme & Design System | Tailwind v4.2 CSS-first, shadcn/ui + next-themes, Blue/Indigo palette |
| `09-RESEARCH-state-forms.md` | State & Forms | TanStack Query v5, Zustand v5, Zod v4 (6-15x faster), RHF v7 |
| `09-RESEARCH-http-auth.md` | HTTP Client & Auth | Axios + HttpOnly cookies, proxy.ts auth+i18n composition, auto-refresh |
| `09-RESEARCH-layout-ui.md` | Layout & UI | shadcn/ui Sidebar component, react-resizable-panels, mobile sheet |

---

## Critical Findings

### 1. Next.js 16 Breaking Changes
- **`proxy.ts` replaces `middleware.ts`** — Export function named `proxy`, not `middleware`
- **Turbopack is default bundler** — No opt-in needed
- **Parallel routes require `default.js`** — Builds fail without them
- **ESLint defaults to Flat Config** — Use `eslint.config.mjs`

### 2. Tailwind CSS v4 Breaking Changes
- Single `@import "tailwindcss"` replaces three `@tailwind` directives
- PostCSS plugin: `@tailwindcss/postcss` (new package)
- Important modifier: `flex!` not `!flex`
- Border default color → `currentColor` (must specify explicitly)
- Several renamed utilities: `shadow-sm→shadow-xs`, `rounded-sm→rounded-xs`
- `tw-animate-css` replaces `tailwindcss-animate`

### 3. Auth Architecture
- Backend uses HttpOnly cookies — frontend NEVER handles JWT in JavaScript
- Axios `withCredentials: true` sends cookies automatically
- `proxy.ts` handles both auth guard AND i18n routing in single file
- Auto-refresh: proxy.ts calls backend `/auth/refresh` server-side when access_token expired
- OAuth is backend-driven — frontend just redirects

### 4. Zod v4 Major Upgrade
- 6-15x faster parsing, 57% smaller bundle
- `z.email()` top-level validator (replaces `.email()` method)
- Built-in JSON Schema support
- `z.locales` API for i18n error messages

### 5. Component Library
- shadcn/ui has built-in Sidebar component with `icon` collapsible mode
- react-resizable-panels for split-view and chat panel
- next-themes with `attribute="class"` for Tailwind dark mode

---

## Recommended Package Versions

```json
{
  "dependencies": {
    "next": "^16.2.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "@tanstack/react-query": "^5.83.0",
    "@tanstack/react-query-devtools": "^5.83.0",
    "zustand": "^5.0.6",
    "zod": "^4.0.5",
    "react-hook-form": "^7.60.0",
    "@hookform/resolvers": "^5.1.1",
    "axios": "^1.13.0",
    "next-themes": "^0.4.6",
    "next-intl": "^4.9.1",
    "lucide-react": "^0.525.0",
    "sonner": "^2.0.6",
    "nuqs": "^2.4.0",
    "react-resizable-panels": "^2.1.0",
    "cmdk": "^1.1.1",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^3.3.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "tailwindcss": "^4.2.0",
    "@tailwindcss/postcss": "^4.2.0",
    "tw-animate-css": "^1.3.5",
    "eslint": "^9.0.0",
    "eslint-config-next": "^16.2.0",
    "vitest": "^3.0.0",
    "@testing-library/react": "^16.2.0"
  }
}
```

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Tailwind v4 breaking changes | HIGH | Follow upgrade guide strictly, use renamed utilities |
| proxy.ts i18n+auth composition | MEDIUM | Single composed function, test order carefully |
| SSR hydration mismatches | MEDIUM | Client-only state in useEffect, Zustand `skipHydration` |
| Zod v4 API changes | LOW | Use new `z.email()` syntax, update resolvers |
| React Compiler edge cases | LOW | Can disable per-component if issues arise |

---

## Validation Architecture

### Test Strategy
- **Unit tests:** Vitest + React Testing Library for components
- **Integration tests:** Form submission flows, auth hooks
- **Type checks:** TypeScript strict mode catches type errors at compile time
- **Lint:** ESLint flat config with next/recommended

### Verification Commands
```bash
pnpm build          # TypeScript + Next.js build (catches type errors)
pnpm lint           # ESLint
pnpm test           # Vitest
pnpm dev            # Dev server boots without errors
```

---

## RESEARCH COMPLETE

*Phase: 09-frontend-foundation-auth-ui*
*Research: 2026-04-12*
