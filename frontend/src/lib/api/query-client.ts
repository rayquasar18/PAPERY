import { QueryClient } from '@tanstack/react-query';

/**
 * Factory function that creates a new QueryClient with project-wide defaults.
 * Use this for both browser singletons and per-request server instances (SSR).
 */
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,       // 5 minutes — avoid redundant refetches
        gcTime: 10 * 60 * 1000,          // 10 minutes — keep inactive cache longer
        retry: 2,
        refetchOnWindowFocus: false,     // Avoid jarring refetches on tab switch
      },
      mutations: {
        retry: 1,
      },
    },
  });
}

/**
 * Centralized query key registry.
 * All useQuery/useMutation calls MUST reference keys from here
 * to ensure consistent cache invalidation.
 */
export const QUERY_KEYS = {
  user: ['user'] as const,
  projects: ['projects'] as const,
  project: (id: string) => ['projects', id] as const,
  chatSessions: (projectId: string) => ['chat-sessions', projectId] as const,
  chatMessages: (sessionId: string) => ['chat-messages', sessionId] as const,
} as const;
