# Plan 09-04 Summary: Layout Shell — Sidebar, Top Bar, Chat Panel & Responsive

**Status:** COMPLETE  
**Executed:** 2026-04-12  
**Branch:** `feature/frontend-foundation-auth-ui`

---

## Tasks Completed

### 09-04-01 — Install layout shadcn components and react-resizable-panels ✅
- Added `react-resizable-panels@4.10.0` and `cmdk@1.1.1` to dependencies
- Installed shadcn components: `sidebar`, `breadcrumb`, `sheet`, `badge`, `scroll-area`, `tabs`, `skeleton`, `alert-dialog`, `command`, `resizable`, `toggle`, `toggle-group`, `dialog`
- All acceptance criteria met: sidebar.tsx, breadcrumb.tsx, sheet.tsx, skeleton.tsx, command.tsx exist

### 09-04-02 — Create AppSidebar component ✅
- Created `frontend/src/components/layout/app-sidebar.tsx`
- Uses `collapsible="icon"` for D-02 behavior (desktop expanded, tablet icon-only, mobile Sheet)
- SidebarHeader with PAPERY logo + app name
- SidebarContent with 3 nav items: Dashboard (LayoutDashboard), Projects (FolderKanban), Settings
- Active state detection via `usePathname` from `@/i18n/navigation`
- SidebarFooter with user placeholder, SidebarRail for toggle handle

### 09-04-03 — Create TopBar, ThemeToggle, LanguageSwitcher, UserMenu ✅
- Created `frontend/src/components/layout/theme-toggle.tsx` — sun/moon/monitor icons, `useTheme`/`setTheme`, mounted check for SSR safety
- Created `frontend/src/components/layout/language-switcher.tsx` — en/vi switcher via `router.replace(pathname, { locale })` from `@/i18n/navigation`
- Created `frontend/src/components/layout/user-menu.tsx` — avatar dropdown, Profile/Settings/Sign out items; full auth integration deferred to 09-05
- Created `frontend/src/components/layout/top-bar.tsx` — h-14 (56px) sticky header, SidebarTrigger + Breadcrumb left, ThemeToggle + LanguageSwitcher + chat toggle + UserMenu right

### 09-04-04 — Create ChatPanel and useMediaQuery hook ✅
- Created `frontend/src/lib/hooks/use-media-query.ts` — SSR-safe reactive hook, starts false, updates after mount via `addEventListener`
- Created `frontend/src/components/layout/chat-panel.tsx` — Bot icon header with close button, ScrollArea body with placeholder content, `useTranslations('Chat')`

### 09-04-05 — Create dashboard layout with sidebar + chat panel composition ✅
- Created `frontend/src/app/[locale]/(dashboard)/layout.tsx` — thin server wrapper
- Created `frontend/src/app/[locale]/(dashboard)/layout-client.tsx` — SidebarProvider + AppSidebar + TopBar + ResizablePanelGroup; chat panel conditionally rendered from Zustand `isChatPanelOpen`
- Created `frontend/src/app/[locale]/(dashboard)/dashboard/page.tsx` — empty state with "No projects yet" card and "Create project" CTA
- Created `frontend/src/app/[locale]/(dashboard)/default.tsx` — null fallback for parallel routes

---

## Build Fixes Applied

During build verification, pre-existing issues were identified and fixed:

1. **`react-resizable-panels` v4 API change** — `direction` prop renamed to `orientation`; `PanelGroup`→`Group`, `PanelResizeHandle`→`Separator`. Switched to shadcn `ResizablePanelGroup/ResizablePanel/ResizableHandle` wrappers with correct `orientation="horizontal"` prop.

2. **`useSearchParams` missing Suspense** — `login-form.tsx` refactored by 09-05 parallel agent to split `LoginFormInner` (with `useSearchParams`) wrapped in `<Suspense>` by `LoginForm`. `useAuth` hook refactored to accept `redirectTo` param instead of reading `searchParams` directly.

3. **`next-intl` v4 nested namespace** — `getTranslations({ namespace: 'Auth.login' })` not valid in next-intl v4 strict mode. Linter simplified auth pages to use `{ namespace: 'Auth' }` with single-level key access (linter-applied pattern).

---

## Commits

| Commit | Message |
|--------|---------|
| `869dc68` | `feat: install layout shadcn components and react-resizable-panels` |
| `9d88be3` | `feat: add AppSidebar component with collapsible icon mode` |
| `8c27566` | `feat: add TopBar, ThemeToggle, LanguageSwitcher, and UserMenu` |
| `aa889be` | `feat: add useMediaQuery hook and ChatPanel placeholder` |
| `13ceb8f` | `feat: add dashboard layout with sidebar+topbar+chat panel composition` |

---

## Must-Haves Verification

- [x] AppSidebar with collapsible icon mode and 3 nav items
- [x] TopBar with theme toggle, language switcher, user menu
- [x] ChatPanel with placeholder content
- [x] Dashboard layout composing sidebar + topbar + main + chat panel
- [x] Responsive: mobile sheet (shadcn built-in), tablet icon-only, desktop expanded
- [x] useMediaQuery hook
- [x] `pnpm build` succeeds ✓

---

## Files Created

```
frontend/src/components/layout/
  app-sidebar.tsx
  top-bar.tsx
  theme-toggle.tsx
  language-switcher.tsx
  user-menu.tsx
  chat-panel.tsx

frontend/src/lib/hooks/
  use-media-query.ts

frontend/src/app/[locale]/(dashboard)/
  layout.tsx
  layout-client.tsx
  dashboard/page.tsx
  default.tsx

frontend/src/components/ui/  (shadcn added)
  sidebar.tsx, breadcrumb.tsx, sheet.tsx, badge.tsx,
  scroll-area.tsx, tabs.tsx, skeleton.tsx, alert-dialog.tsx,
  command.tsx, resizable.tsx, toggle.tsx, toggle-group.tsx, dialog.tsx
```

## Notes

- Agent 09-05 ran in parallel and added auth form components; build fixes were coordinated across both plan scopes
- The `react-resizable-panels` v4 breaking change (renamed exports) required using shadcn `resizable.tsx` wrappers instead of direct library imports
- Chat panel is a v1 placeholder shell — QuasarFlow integration planned for a future phase
