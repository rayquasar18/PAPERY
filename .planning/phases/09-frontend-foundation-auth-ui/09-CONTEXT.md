# Phase 9: Frontend Foundation & Auth UI - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up the complete frontend infrastructure and authentication UI for PAPERY. This phase delivers:
1. Next.js 16 + React 19 project scaffold with TypeScript strict mode
2. Full layout shell (hybrid sidebar + top bar + resizable chat panel + split-view main content)
3. Component library (shadcn/ui) and design system (Blue/Indigo theme, Inter font, dark/light/system)
4. i18n infrastructure (next-intl, EN + VI, locale-prefixed routing)
5. HTTP client (Axios), server state (TanStack Query v5), client state (Zustand v5), form handling (React Hook Form + Zod v4)
6. Authentication UI pages (login, register, email verification, password reset) consuming backend API from Phase 3
7. Auth middleware (cookie-based JWT, auto-refresh on 401, route protection)

This phase does NOT include: dashboard content, admin UI, project management UI, document features, or AI chat functionality. Those belong to Phase 10+.

</domain>

<decisions>
## Implementation Decisions

### Layout & Navigation
- **D-01:** Hybrid layout — collapsible sidebar (left) + top bar (right). Sidebar contains project tree + navigation items. Top bar contains breadcrumb, global search, theme toggle, and user menu.
- **D-02:** Sidebar is collapsible — toggles between full-width (with labels) and icon-only mode. User controls via toggle button.
- **D-03:** Responsive auto-collapse: sidebar expanded on desktop, icon-only on tablet, hidden on mobile.
- **D-04:** Mobile navigation: sidebar fully hidden, open/close via icon in header. Follow shadcn/ui dashboard-01 pattern (`npx shadcn@latest add dashboard-01` for reference). NO hamburger menu icon.
- **D-05:** Chat panel positioned on the right side, resizable (drag to adjust width). Panel can be opened/closed. This is the AI chatbot interaction area.
- **D-06:** Main content area supports split view — user can open multiple files/tabs and split into 2 or 3 panes for side-by-side comparison. Tabs can be documents (uploaded, editing, viewing, or any file the user wants to display).
- **D-07:** Sidebar items for v1: Dashboard (home), Projects, Settings. Additional items (Docs, Chat) will be added in future phases.

### Auth Pages & UX Flow
- **D-08:** Auth pages use split-screen layout — left side for PAPERY branding/image/tagline, right side for the form. Responsive: on mobile, branding section hides, form takes full width.
- **D-09:** OAuth buttons (Google, GitHub) placed below the email/password form, separated by a divider with "or" text.
- **D-10:** Form validation errors displayed inline below each field in red. Real-time validation on blur (React Hook Form + Zod resolver).
- **D-11:** After successful login, redirect to Dashboard (project list page). If user had a previous URL before being redirected to login, return to that URL (redirect-back pattern).
- **D-12:** Auth flow: Register → email verification notice → (verify link) → Login → Dashboard. Unverified users see a notice prompting email verification.
- **D-13:** Password reset: Request page → email sent notice → reset form (from email link) → success → redirect to login.

### Theme & Design Foundation
- **D-14:** Color palette: Blue/Indigo professional tone. Primary color in the indigo/blue range. Clean, modern, suitable for document intelligence platform.
- **D-15:** Typography: Inter font family. Loaded via `next/font/google` for optimal performance.
- **D-16:** Dark/Light/System theme toggle placed in the top bar (header). Three options: Light, Dark, System. Preference persisted in localStorage + cookie (for SSR consistency). Use `next-themes` library.
- **D-17:** Design tokens managed via Tailwind CSS + shadcn/ui CSS variables. Consistent spacing, border radius, shadow system from shadcn/ui defaults.

### i18n & Routing Strategy
- **D-18:** Default locale: English (en).
- **D-19:** URL structure: mandatory locale prefix — `/en/dashboard`, `/vi/login`, etc. All routes have locale prefix.
- **D-20:** Auto-detect browser locale on first visit via `Accept-Language` header. Redirect to matching supported locale. User can override via language switcher.
- **D-21:** Supported locales for v1: English (en) and Vietnamese (vi). Language switcher in UI (likely in user menu or footer).
- **D-22:** Translation files: JSON format in `src/locale/en.json`, `src/locale/vi.json`. Use `next-intl` with App Router integration.

### Tech Stack & Libraries
- **D-23:** Framework: Next.js 16 (latest) + React 19. App Router (not Pages Router). TypeScript strict mode enabled.
- **D-24:** Package manager: pnpm.
- **D-25:** Styling: Tailwind CSS v4 + shadcn/ui (Radix UI primitives). Lucide Icons for all iconography.
- **D-26:** HTTP client: Axios v1.x. Centralized instance with interceptors for Bearer token injection (from cookies), error normalization, and auto-refresh on 401.
- **D-27:** Server state: TanStack Query v5 (React Query). Caching, background refetch, optimistic mutations, devtools.
- **D-28:** Client state: Zustand v5. Max 3-5 stores (UI preferences, sidebar state, theme). Minimal, TypeScript-first.
- **D-29:** Validation: Zod v4 for runtime validation of API responses and form inputs.
- **D-30:** Form handling: React Hook Form + @hookform/resolvers (Zod resolver). Uncontrolled form approach for performance.
- **D-31:** i18n: next-intl with App Router integration.
- **D-32:** Theme: next-themes for SSR-compatible dark/light/system mode.
- **D-33:** Toasts: sonner for notification toasts (success, error, info).
- **D-34:** URL state: nuqs for type-safe URL search params management.
- **D-35:** Date utility: date-fns v4 for date formatting, relative time, timezone handling.
- **D-36:** Animation: Tailwind CSS transitions/animations only. No additional animation library for v1.
- **D-37:** All downstream agents (researcher, planner, executor) MUST use model Opus 4.6.

### Claude's Discretion
- Component file structure within `src/` (feature-scoped vs type-scoped) — Claude decides based on Next.js 16 best practices
- Exact Tailwind color values for the Blue/Indigo palette — Claude picks appropriate shades
- shadcn/ui component list to install initially — Claude decides based on auth UI needs
- Exact breakpoint values for responsive design — follow Tailwind defaults
- Zustand store structure (which stores, what goes where) — Claude decides based on phase needs
- Split-view implementation approach (tabs component, resizable panels library) — Claude researches and decides

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/codebase/ARCHITECTURE.md` — Overall system architecture, frontend layers detail
- `.planning/codebase/STRUCTURE.md` — Target directory structure for frontend/
- `.planning/codebase/CONVENTIONS.md` — Code style: kebab-case files, PascalCase components, TypeScript types required
- `.planning/codebase/STACK.md` — Confirmed tech stack decisions

### Project Context
- `.planning/PROJECT.md` — Project overview, constraints, key decisions
- `.planning/REQUIREMENTS.md` — FRONT-01 through FRONT-11 requirements with acceptance criteria
- `.planning/ROADMAP.md` — Phase 9 description, success criteria, dependency graph

### Backend API (Phase 3 — auth endpoints to consume)
- `.planning/phases/03-authentication-core-flows/03-CONTEXT.md` — Auth system decisions (JWT, cookies, token rotation)
- `backend/src/app/api/v1/auth.py` — Auth API endpoints (register, login, logout, refresh, verify)
- `backend/src/app/schemas/` — API request/response schemas

### Design Reference
- shadcn/ui dashboard-01 block — Reference for layout shell and mobile navigation pattern (`npx shadcn@latest add dashboard-01`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No frontend code exists yet — this is a greenfield frontend setup
- Backend auth API endpoints are ready (Phase 3 complete): POST /auth/register, POST /auth/login, POST /auth/logout, POST /auth/refresh, POST /auth/verify

### Established Patterns
- Backend uses dual ID (int internal + UUID public) — frontend must use UUID for all API calls
- Backend auth uses HttpOnly cookies for JWT — frontend does NOT handle tokens in JavaScript, cookies are automatic
- Error response format: `{ error_code, message, details, request_id }` — frontend HTTP client should normalize this
- API base: `/api/v1/` with versioning

### Integration Points
- Backend API at `BACKEND_API_URL` environment variable
- Auth cookies: `access_token` and `refresh_token` as HttpOnly cookies
- CORS: backend allows origins from `CORS_ORIGINS` env var — frontend origin must be in this list
- Next.js middleware for auth: check cookie presence, redirect to login if absent

</code_context>

<specifics>
## Specific Ideas

- **Mobile sidebar:** Reference shadcn/ui dashboard-01 block for the open/close pattern — NOT a hamburger menu, use a clean icon toggle in the header
- **Split view in main content:** User specifically wants to open multiple files side-by-side (2-3 panes) for comparison — similar to VS Code split editor or Google Docs tab splitting. This includes uploaded files, files being edited, or any viewable content
- **Chat panel:** Resizable right panel (drag handle), can be opened/closed. This will house the AI chatbot (QuasarFlow integration in v2). For v1, the panel shell and resize logic should be built, with placeholder content
- **Auth page branding:** Left side of split-screen auth should show PAPERY logo, tagline, and potentially a decorative illustration or gradient

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-frontend-foundation-auth-ui*
*Context gathered: 2026-04-11*
