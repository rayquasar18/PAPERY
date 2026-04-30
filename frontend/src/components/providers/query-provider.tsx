'use client';

import { useState } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { makeQueryClient } from '@/lib/api/query-client';
import type { ReactNode } from 'react';

interface QueryProviderProps {
  children: ReactNode;
}

/**
 * Wraps the application with TanStack Query's QueryClientProvider.
 * Creates a stable client instance per browser session.
 * ReactQueryDevtools is rendered in development only.
 */
export function QueryProvider({ children }: QueryProviderProps) {
  // useState ensures the QueryClient is not recreated on every render
  const [queryClient] = useState(() => makeQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
