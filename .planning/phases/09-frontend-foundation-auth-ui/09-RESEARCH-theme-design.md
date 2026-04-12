# Phase 9 Research: Theme & Design System

**Researched:** 2026-04-12
**Scope:** next-themes, shadcn/ui, Tailwind CSS v4, design tokens, color palette, icons
**Relevant decisions:** D-14, D-15, D-16, D-17, D-25
**Requirements:** FRONT-03, FRONT-04, FRONT-09

---

## 1. Key Findings

1. **Tailwind CSS v4.2** is current — major overhaul from v3. CSS-first config (`@import "tailwindcss"`), new PostCSS plugin (`@tailwindcss/postcss`), no more `tailwind.config.js` by default.
2. **shadcn/ui** fully supports Tailwind v4 + Next.js 16. Init via `pnpm dlx shadcn@latest init`. Uses CSS variables for theming.
3. **next-themes v0.4.6** — works with Next.js 16 App Router. Must use `suppressHydrationWarning` on `<html>`. Attribute can be `class` (for Tailwind dark mode).
4. **Reference project** uses: `next-themes@^0.4.6`, `tailwindcss@^4`, `tw-animate-css@^1.3.5`, `lucide-react@^0.525.0` — all confirmed working together.
5. **Tailwind v4 breaking changes are significant** — renamed utilities (shadow-sm→shadow-xs, rounded-sm→rounded-xs), important modifier position changed (`!flex` → `flex!`), border-color defaults to currentColor.

## 2. next-themes Setup

```typescript
// src/components/providers/theme-provider.tsx
'use client';

import { ThemeProvider as NextThemesProvider } from 'next-themes';
import type { ReactNode } from 'react';

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"           // Tailwind uses class-based dark mode
      defaultTheme="system"       // D-16: system default
      enableSystem                // D-16: system preference detection
      disableTransitionOnChange   // Prevents flash during theme switch
      storageKey="papery-theme"   // localStorage key
    >
      {children}
    </NextThemesProvider>
  );
}
```

**Cookie persistence for SSR:** next-themes stores in localStorage by default. For SSR consistency, the theme script runs before React hydration to prevent FOUC. Cookie-based approach can be added by reading localStorage value and setting a cookie in proxy.ts.

**Usage:**
```typescript
import { useTheme } from 'next-themes';
const { theme, setTheme, resolvedTheme } = useTheme();
// resolvedTheme gives actual theme when theme === 'system'
```

**IMPORTANT:** `useTheme()` returns `undefined` during SSR — must check `mounted` state before rendering theme UI.

## 3. shadcn/ui Installation

```bash
# Initialize shadcn/ui
pnpm dlx shadcn@latest init

# Install components needed for auth UI
pnpm dlx shadcn@latest add button card input label form separator dropdown-menu avatar sheet dialog tabs tooltip badge scroll-area
```

**components.json** generated:
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/app/globals.css",
    "baseColor": "zinc",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/lib/hooks"
  }
}
```

**cn() utility** (auto-generated):
```typescript
// src/lib/utils.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

## 4. Tailwind CSS v4 — Key Changes from v3

### Config Approach
```css
/* src/app/globals.css — CSS-first config */
@import "tailwindcss";

/* Theme customization via CSS */
@theme {
  --color-primary: oklch(0.55 0.18 265);
  --color-primary-foreground: oklch(0.98 0.01 265);
  --font-sans: 'Inter', sans-serif;
}
```

### PostCSS Config
```javascript
// postcss.config.mjs
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
```

### Key Breaking Changes to Remember
| v3 | v4 | Notes |
|----|-----|-------|
| `@tailwind base/components/utilities` | `@import "tailwindcss"` | Single import |
| `shadow-sm` | `shadow-xs` | Renamed |
| `shadow` | `shadow-sm` | Renamed |
| `rounded-sm` | `rounded-xs` | Renamed |
| `ring` | `ring-3` | Width change |
| `!flex` | `flex!` | Important modifier position |
| `bg-[--var]` | `bg-(--var)` | CSS vars in arbitrary values |
| `outline-none` | `outline-hidden` | Renamed |
| `border` (auto gray-200) | `border` (auto currentColor) | Must specify color |
| `tailwind.config.js` | `@theme` in CSS | Config approach |

### JavaScript Config (if needed)
```css
/* Can still use JS config via @config directive */
@config "../../tailwind.config.js";
```

## 5. Blue/Indigo Color Palette

shadcn/ui uses CSS variables with HSL values. For Blue/Indigo professional theme (D-14):

```css
/* Light mode */
:root {
  --background: 0 0% 100%;
  --foreground: 222 47% 11%;
  --card: 0 0% 100%;
  --card-foreground: 222 47% 11%;
  --popover: 0 0% 100%;
  --popover-foreground: 222 47% 11%;
  --primary: 234 89% 56%;              /* Indigo-600 */
  --primary-foreground: 0 0% 100%;
  --secondary: 220 14% 96%;
  --secondary-foreground: 222 47% 11%;
  --muted: 220 14% 96%;
  --muted-foreground: 220 9% 46%;
  --accent: 220 14% 96%;
  --accent-foreground: 222 47% 11%;
  --destructive: 0 84% 60%;
  --destructive-foreground: 0 0% 100%;
  --border: 220 13% 91%;
  --input: 220 13% 91%;
  --ring: 234 89% 56%;                 /* Matches primary */
  --radius: 0.5rem;
  --chart-1: 234 89% 56%;
  --chart-2: 220 70% 50%;
  --chart-3: 197 37% 24%;
  --chart-4: 43 74% 66%;
  --chart-5: 27 87% 67%;
}

/* Dark mode */
.dark {
  --background: 222 47% 5%;
  --foreground: 210 40% 98%;
  --card: 222 47% 8%;
  --card-foreground: 210 40% 98%;
  --popover: 222 47% 8%;
  --popover-foreground: 210 40% 98%;
  --primary: 234 89% 63%;              /* Indigo-500 (brighter for dark) */
  --primary-foreground: 0 0% 100%;
  --secondary: 222 47% 14%;
  --secondary-foreground: 210 40% 98%;
  --muted: 222 47% 14%;
  --muted-foreground: 215 20% 65%;
  --accent: 222 47% 14%;
  --accent-foreground: 210 40% 98%;
  --destructive: 0 62% 50%;
  --destructive-foreground: 0 0% 100%;
  --border: 222 47% 16%;
  --input: 222 47% 16%;
  --ring: 234 89% 63%;
}
```

## 6. Typography (Inter)

```typescript
// src/app/layout.tsx
import { Inter } from 'next/font/google';

const inter = Inter({
  subsets: ['latin', 'vietnamese'],   // D-21: support Vietnamese
  variable: '--font-sans',
  display: 'swap',
});

// Apply to html: <html className={inter.variable}>
```

CSS integration:
```css
@theme {
  --font-sans: var(--font-sans), ui-sans-serif, system-ui, sans-serif;
}
```

## 7. Lucide Icons

```bash
pnpm add lucide-react
```

Usage:
```typescript
import { Sun, Moon, Monitor, Menu, X } from 'lucide-react';
// Tree-shakes automatically — only imported icons are bundled
```

Reference project uses `lucide-react@^0.525.0` — confirmed working with React 19.

## 8. Dark/Light Toggle Component

```typescript
'use client';

import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const { setTheme } = useTheme();

  useEffect(() => setMounted(true), []);
  if (!mounted) return <Button variant="ghost" size="icon" disabled />;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme('light')}>
          <Sun className="mr-2 h-4 w-4" /> Light
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('dark')}>
          <Moon className="mr-2 h-4 w-4" /> Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('system')}>
          <Monitor className="mr-2 h-4 w-4" /> System
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

## 9. Animations

Reference project uses `tw-animate-css@^1.3.5` for animation utilities with Tailwind v4. This provides CSS-based animations compatible with shadcn/ui.

```bash
pnpm add tw-animate-css
```

```css
/* globals.css */
@import "tailwindcss";
@import "tw-animate-css";
```

## 10. Risks & Considerations

1. **Tailwind v4 breaking changes** — All renamed utilities must be used correctly from start. `shadow-sm` → `shadow-xs`, etc.
2. **shadcn/ui version compatibility** — Ensure shadcn CLI generates v4-compatible CSS
3. **FOUC prevention** — next-themes script injection handles this, but complex with i18n locale routing
4. **CSS variable naming** — shadcn/ui expects specific variable names; customizing requires updating all component styles
5. **`tw-animate-css`** replaces the old `tailwindcss-animate` plugin for v4

## 11. Required Packages

```json
{
  "next-themes": "^0.4.6",
  "tailwindcss": "^4.2.0",
  "@tailwindcss/postcss": "^4.2.0",
  "tw-animate-css": "^1.3.5",
  "lucide-react": "^0.525.0",
  "class-variance-authority": "^0.7.1",
  "clsx": "^2.1.1",
  "tailwind-merge": "^3.3.0"
}
```

---

## RESEARCH COMPLETE

*Phase: 09-frontend-foundation-auth-ui*
*Research scope: Theme & Design System*
*Researched: 2026-04-12*
