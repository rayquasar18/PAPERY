# Phase 9 Research: State Management & Forms

**Researched:** 2026-04-12
**Scope:** TanStack Query v5, Zustand v5, React Hook Form, Zod v4, sonner, nuqs
**Relevant decisions:** D-27, D-28, D-29, D-30, D-33, D-34
**Requirements:** FRONT-05, FRONT-06, FRONT-07, FRONT-11

---

## 1. Key Findings

1. **TanStack Query v5.83+** — Latest stable. Fully supports React 19 + Next.js 16 App Router. Requires `QueryClientProvider` in a client component.
2. **Zustand v5.0.12** — Latest. Includes `unstable_ssrSafe` middleware for Next.js (v5.0.9+). Persist middleware improved. No major API breaks from v4 — mostly TypeScript refinements.
3. **Zod v4.0.5** — Major release with 6-15x faster parsing, 57% smaller bundle, first-party JSON Schema support, recursive types, `z.email()` top-level validators, and new `z.locales` for i18n error messages.
4. **React Hook Form v7.60** — Stable with Zod v4 support via `@hookform/resolvers@^5.1.1`. Uncontrolled form approach for performance.
5. **Reference project** uses exact same stack: `@tanstack/react-query@^5.83.0`, `zustand@^5.0.6`, `zod@^4.0.5`, `react-hook-form@^7.60.0`, `@hookform/resolvers@^5.1.1`, `sonner@^2.0.6` — all confirmed working together.

## 2. TanStack Query v5 Setup

### QueryClientProvider
```typescript
// src/lib/api/query-client.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,       // 5 minutes
      gcTime: 10 * 60 * 1000,         // 10 minutes (was cacheTime in v4)
      retry: 2,
      refetchOnWindowFocus: false,     // Avoid unnecessary refetches
    },
    mutations: {
      retry: 1,
    },
  },
});

// Centralized query keys
export const QUERY_KEYS = {
  user: ['user'] as const,
  projects: ['projects'] as const,
  project: (id: string) => ['projects', id] as const,
  chatSessions: (projectId: string) => ['chat-sessions', projectId] as const,
  chatMessages: (sessionId: string) => ['chat-messages', sessionId] as const,
} as const;
```

### Provider Setup
```typescript
// src/components/providers/query-provider.tsx
'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from '@/lib/api/query-client';
import type { ReactNode } from 'react';

export function QueryProvider({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

### Usage Pattern (hooks)
```typescript
// src/lib/hooks/use-user.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/api/query-client';
import { userApi } from '@/lib/api/user';

export function useUser() {
  return useQuery({
    queryKey: QUERY_KEYS.user,
    queryFn: userApi.getProfile,
    staleTime: 10 * 60 * 1000,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: userApi.updateProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.user });
    },
  });
}
```

### SSR with Next.js App Router
For SSR prefetching, use `HydrationBoundary` + `dehydrate`:
```typescript
// In server component
import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/api/query-client';

export default async function Page() {
  const queryClient = getQueryClient();
  await queryClient.prefetchQuery({ queryKey: QUERY_KEYS.user, queryFn: fetchUser });

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <UserProfile />
    </HydrationBoundary>
  );
}
```

## 3. Zustand v5

### Store Pattern
```typescript
// src/lib/stores/sidebar-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SidebarState {
  isExpanded: boolean;
  isChatPanelOpen: boolean;
  chatPanelWidth: number;
  toggleSidebar: () => void;
  toggleChatPanel: () => void;
  setChatPanelWidth: (width: number) => void;
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      isExpanded: true,
      isChatPanelOpen: false,
      chatPanelWidth: 400,
      toggleSidebar: () => set((s) => ({ isExpanded: !s.isExpanded })),
      toggleChatPanel: () => set((s) => ({ isChatPanelOpen: !s.isChatPanelOpen })),
      setChatPanelWidth: (width) => set({ chatPanelWidth: width }),
    }),
    { name: 'papery-sidebar' }
  )
);
```

### Recommended Stores (max 3-5 per D-28)
| Store | Purpose | Persist? |
|-------|---------|----------|
| `useSidebarStore` | Sidebar expand/collapse, chat panel state | Yes |
| `useUIStore` | Responsive state, active tab, split-view config | Yes |
| `useAuthStore` | User info cache, login state (supplements cookies) | Session only |

### v5 Changes from v4
- `create` API unchanged — smooth migration
- TypeScript: Better generic inference, no need for `StateCreator` wrapper
- `persist` middleware: Improved post-rehydration callback (v5.0.12)
- New: `unstable_ssrSafe` middleware for Next.js SSR safety (v5.0.9+)

## 4. Zod v4

### Key Changes from v3
| Feature | v3 | v4 |
|---------|-----|-----|
| Parsing speed | Baseline | 6-15x faster |
| Bundle size | 12.47kb | 5.36kb (57% smaller) |
| String formats | `.email()` method | `z.email()` top-level |
| Error customization | `message`, `invalid_type_error` | Unified `error` param |
| Recursive types | Manual workaround | Native `getter` syntax |
| JSON Schema | 3rd party | `z.toJSONSchema()` built-in |
| i18n errors | Manual | `z.locales` API |
| Refinements | ZodEffects wrapper | Inline, chainable |

### Usage
```typescript
import { z } from 'zod';

// Auth schemas
export const loginSchema = z.object({
  email: z.email({ error: 'Invalid email address' }),
  password: z.string().min(8, { error: 'Password must be at least 8 characters' }),
});

export const registerSchema = z.object({
  email: z.email(),
  password: z.string().min(8),
  confirmPassword: z.string(),
  displayName: z.string().min(2).max(50),
}).refine((data) => data.password === data.confirmPassword, {
  error: 'Passwords do not match',
  path: ['confirmPassword'],
});

// Type inference
export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
```

### i18n Error Messages (D-22 support)
```typescript
import { z } from 'zod';

// Zod v4 built-in i18n support
z.locales.set({
  invalid_type: 'Expected {expected}, received {received}',
  too_small: 'Must be at least {minimum} characters',
  // ... Vietnamese translations
});
```

## 5. React Hook Form + Zod Integration

```typescript
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { loginSchema, type LoginInput } from '@/lib/schemas/auth';

export function LoginForm() {
  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
    mode: 'onBlur',          // D-10: real-time validation on blur
  });

  const onSubmit = (data: LoginInput) => {
    // Call login mutation
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      {/* Use shadcn/ui Form components */}
    </form>
  );
}
```

### shadcn/ui Form Integration
shadcn/ui provides `<Form>`, `<FormField>`, `<FormItem>`, `<FormLabel>`, `<FormControl>`, `<FormMessage>` components that integrate directly with React Hook Form:
```bash
pnpm dlx shadcn@latest add form
```

## 6. sonner (Toasts)

```bash
pnpm add sonner
```

```typescript
// Place Toaster in root layout
import { Toaster } from 'sonner';

// In layout.tsx
<Toaster richColors position="top-right" />

// Usage anywhere
import { toast } from 'sonner';
toast.success('Login successful');
toast.error('Invalid credentials');
toast.info('Check your email for verification link');
```

Reference project uses `sonner@^2.0.6` — confirmed working.

## 7. nuqs (URL State)

```bash
pnpm add nuqs
```

```typescript
import { useQueryState, parseAsString, parseAsInteger } from 'nuqs';

// Type-safe URL params
export function ProjectList() {
  const [search, setSearch] = useQueryState('q', parseAsString.withDefault(''));
  const [page, setPage] = useQueryState('page', parseAsInteger.withDefault(1));
  // URL: /projects?q=search&page=2
}
```

**Next.js App Router integration:** nuqs supports both Server and Client Components. Use `createSearchParamsCache` for server-side parsing.

## 8. Risks & Considerations

1. **Zod v4 breaking changes** — `z.email()` top-level replaces `.email()` method (deprecated). Update imports.
2. **TanStack Query SSR** — Must use `HydrationBoundary` pattern for Server Component prefetching. `QueryClientProvider` must be in a `'use client'` boundary.
3. **Zustand hydration mismatch** — Persisted stores may cause SSR mismatch. Use `skipHydration` or `unstable_ssrSafe` middleware.
4. **React Hook Form v7 vs v8** — v7 is current stable. v8 is in development with native React 19 form actions support.
5. **Bundle size** — TanStack Query devtools should be lazy-loaded or removed in production.

## 9. Required Packages

```json
{
  "@tanstack/react-query": "^5.83.0",
  "@tanstack/react-query-devtools": "^5.83.0",
  "zustand": "^5.0.6",
  "zod": "^4.0.5",
  "react-hook-form": "^7.60.0",
  "@hookform/resolvers": "^5.1.1",
  "sonner": "^2.0.6",
  "nuqs": "^2.4.0"
}
```

---

## RESEARCH COMPLETE

*Phase: 09-frontend-foundation-auth-ui*
*Research scope: State Management & Forms*
*Researched: 2026-04-12*
