# Phase 9 Research: Layout & UI Architecture

**Researched:** 2026-04-12
**Scope:** Sidebar, split-view, resizable panels, responsive design, shadcn/ui dashboard patterns
**Relevant decisions:** D-01 to D-07
**Requirement:** FRONT-04 — Responsive layout

---

## 1. Key Findings

1. **shadcn/ui has a built-in Sidebar component** — `pnpm dlx shadcn@latest add sidebar`. Full composition API: SidebarProvider → Sidebar → Header/Content/Footer. Supports `icon` collapsible mode (D-02).
2. **react-resizable-panels** — The standard library for resizable panels. Used for split-view (D-06) and chat panel (D-05). Supports horizontal/vertical, min/max size, collapsible, drag handles.
3. **shadcn/ui dashboard-01 block** — Reference layout with sidebar, header, and mobile sheet navigation. Install via `pnpm dlx shadcn@latest add dashboard-01`.
4. **Mobile sidebar** — shadcn/ui Sidebar automatically renders as a `Sheet` (drawer overlay) on mobile via `useSidebar().isMobile`. No hamburger menu — uses `SidebarTrigger` icon button (D-04).
5. **Keyboard shortcut** — `cmd+b` / `ctrl+b` toggles sidebar — built into shadcn/ui SidebarProvider.

## 2. shadcn/ui Sidebar Architecture

### Component Hierarchy
```
<SidebarProvider defaultOpen={true}>
  <Sidebar collapsible="icon">          {/* D-02: icon-only mode */}
    <SidebarHeader>
      {/* Logo + app name */}
    </SidebarHeader>
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel>Navigation</SidebarGroupLabel>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild isActive={isActive}>
              <Link href="/dashboard">
                <LayoutDashboard />
                <span>Dashboard</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          {/* D-07: Dashboard, Projects, Settings */}
        </SidebarMenu>
      </SidebarGroup>
    </SidebarContent>
    <SidebarFooter>
      {/* User menu */}
    </SidebarFooter>
    <SidebarRail />
  </Sidebar>
  
  <main className="flex-1">
    <TopBar />
    <ContentArea />
  </main>
</SidebarProvider>
```

### Collapsible Modes
| Mode | Behavior | Use Case |
|------|----------|----------|
| `offcanvas` | Slides completely off screen | Mobile only |
| `icon` | Collapses to icon-only width | **D-02: Our choice** |
| `none` | Always expanded | N/A |

### CSS Variables
```css
:root {
  --sidebar-width: 16rem;              /* Expanded width */
  --sidebar-width-mobile: 18rem;       /* Mobile sheet width */
  --sidebar-width-icon: 3rem;          /* Icon-only width */
}
```

### useSidebar Hook
```typescript
const {
  state,           // "expanded" | "collapsed"
  open,            // boolean (desktop)
  setOpen,         // (open: boolean) => void
  openMobile,      // boolean (mobile sheet)
  setOpenMobile,   // (open: boolean) => void
  isMobile,        // boolean (responsive detection)
  toggleSidebar,   // () => void
} = useSidebar();
```

## 3. Top Bar / Header

```
┌──────────────────────────────────────────────────────────┐
│ [☰] Breadcrumb > Path          🔍 Search    🌙 👤 Menu  │
└──────────────────────────────────────────────────────────┘
```

Components needed:
- `SidebarTrigger` — Toggle button (replaces hamburger menu, D-04)
- `Breadcrumb` — shadcn/ui breadcrumb component
- Search — Command palette (`cmdk` library) or simple input
- `ThemeToggle` — Dark/light/system (from theme research)
- User menu — `DropdownMenu` with avatar

## 4. Split-View Main Content (D-06)

### react-resizable-panels Approach

```bash
pnpm add react-resizable-panels
```

```typescript
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

// VS Code-like split view for document comparison
function SplitView() {
  return (
    <PanelGroup direction="horizontal">
      <Panel defaultSize={50} minSize={20}>
        {/* Document 1 */}
      </Panel>
      <PanelResizeHandle className="w-1 bg-border hover:bg-primary transition-colors" />
      <Panel defaultSize={50} minSize={20}>
        {/* Document 2 */}
      </Panel>
    </PanelGroup>
  );
}
```

### Tab System
For managing multiple open documents:
```typescript
// Use shadcn/ui Tabs component
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

// Or custom tab bar with close buttons
interface OpenTab {
  id: string;
  title: string;
  type: 'document' | 'settings' | 'project';
}
```

### Split View State
```typescript
// Store in Zustand
interface UIState {
  splitMode: 'single' | 'split-2' | 'split-3';
  activePanels: string[];  // tab IDs in each panel
  setSplitMode: (mode: UIState['splitMode']) => void;
}
```

## 5. Chat Panel (D-05)

Right-side resizable panel, independent of main content split:

```typescript
function AppLayout({ children }: { children: React.ReactNode }) {
  const { isChatPanelOpen } = useSidebarStore();
  
  return (
    <PanelGroup direction="horizontal">
      <Panel defaultSize={isChatPanelOpen ? 70 : 100} minSize={40}>
        {/* Main content (may contain its own split view) */}
        {children}
      </Panel>
      
      {isChatPanelOpen && (
        <>
          <PanelResizeHandle className="w-1 bg-border" />
          <Panel defaultSize={30} minSize={20} maxSize={50} collapsible>
            <ChatPanel />
          </Panel>
        </>
      )}
    </PanelGroup>
  );
}
```

**Chat panel toggle button** — In TopBar or as a floating button:
```typescript
<Button variant="ghost" size="icon" onClick={toggleChatPanel}>
  <MessageSquare className="h-5 w-5" />
</Button>
```

## 6. Responsive Design (D-03)

### Breakpoints (Tailwind defaults)
| Breakpoint | Width | Sidebar Behavior |
|------------|-------|-----------------|
| `sm` | 640px | Hidden (mobile sheet) |
| `md` | 768px | Icon-only (collapsed) |
| `lg` | 1024px | Expanded |
| `xl` | 1280px | Expanded |
| `2xl` | 1536px | Expanded |

### Auto-Collapse Logic
shadcn/ui SidebarProvider handles mobile detection automatically. For tablet icon-only:

```typescript
// In root layout or SidebarProvider wrapper
'use client';
import { useMediaQuery } from '@/lib/hooks/use-media-query';

function AppSidebarProvider({ children }: { children: React.ReactNode }) {
  const isTablet = useMediaQuery('(min-width: 640px) and (max-width: 1023px)');
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  
  return (
    <SidebarProvider defaultOpen={isDesktop}>
      {children}
    </SidebarProvider>
  );
}
```

### useMediaQuery Hook
```typescript
// src/lib/hooks/use-media-query.ts
import { useState, useEffect } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);
    
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, [query]);

  return matches;
}
```

Reference project has same hook at `src/lib/hooks/use-media-query.ts`.

## 7. Mobile Navigation (D-04)

shadcn/ui Sidebar auto-renders as a `Sheet` on mobile:
- `SidebarTrigger` in header opens/closes the sheet
- No hamburger menu icon — uses clean icon toggle (per D-04)
- Sheet slides from left with overlay

```typescript
// Mobile sidebar trigger in header
<header className="flex items-center gap-2 p-4 border-b">
  <SidebarTrigger />  {/* Auto: panel-left-open / panel-left-close icons */}
  <Separator orientation="vertical" className="h-4" />
  <Breadcrumb />
</header>
```

## 8. Overall Layout Composition

```
┌──────────────────────────────────────────────────────────────┐
│ ┌──────────┬───────────────────────────────────────────────┐ │
│ │          │ TopBar: [☰] Breadcrumb    🔍  🌙  💬  👤    │ │
│ │          ├───────────────────────────────┬───────────────┤ │
│ │ Sidebar  │                               │              │ │
│ │          │     Main Content Area          │  Chat Panel  │ │
│ │ Dashboard│  ┌─────────┬──────────┐       │  (resizable) │ │
│ │ Projects │  │ Panel 1 │ Panel 2  │       │              │ │
│ │ Settings │  │ (doc)   │ (doc)    │       │              │ │
│ │          │  │         │          │       │              │ │
│ │          │  └─────────┴──────────┘       │              │ │
│ └──────────┴───────────────────────────────┴───────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Provider Nesting Order (root layout)
```
<html>
  <body>
    1. ThemeProvider (next-themes)
    2. QueryProvider (TanStack Query)
    3. NextIntlClientProvider (i18n - in locale layout)
    4. SidebarProvider (shadcn/ui - in dashboard layout)
    5. PanelGroup (react-resizable-panels - in dashboard layout)
    6. Toaster (sonner)
  </body>
</html>
```

## 9. shadcn/ui Components to Install

```bash
# Layout & Navigation
pnpm dlx shadcn@latest add sidebar breadcrumb separator sheet

# UI Components for auth & general use
pnpm dlx shadcn@latest add button card input label form
pnpm dlx shadcn@latest add dropdown-menu avatar tooltip badge
pnpm dlx shadcn@latest add dialog tabs scroll-area

# Additional
pnpm dlx shadcn@latest add command   # Command palette (cmdk)
```

## 10. Required Packages

```json
{
  "react-resizable-panels": "^2.1.0",
  "cmdk": "^1.1.1"
}
```

## 11. Risks & Considerations

1. **SSR layout shift** — Sidebar state must be consistent between server and client. Use cookie or default state.
2. **Panel size persistence** — react-resizable-panels supports `autoSaveId` prop for localStorage persistence.
3. **Nested PanelGroups** — Main content split-view inside the chat panel layout requires nested PanelGroups. Test performance.
4. **Accessibility** — shadcn/ui Sidebar has built-in `aria-*` attributes. PanelResizeHandle needs `role="separator"`.
5. **Mobile chat panel** — On mobile, chat panel should be a full-screen sheet, not a side panel.

---

## RESEARCH COMPLETE

*Phase: 09-frontend-foundation-auth-ui*
*Research scope: Layout & UI Architecture*
*Researched: 2026-04-12*
