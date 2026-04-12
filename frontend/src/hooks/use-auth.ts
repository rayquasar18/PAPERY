'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { authApi } from '@/lib/api/auth';
import { QUERY_KEYS } from '@/lib/api/query-client';
import { useRouter } from '@/lib/i18n/navigation';

/**
 * Central auth hook — wraps TanStack Query for user state and auth mutations.
 * Uses HttpOnly cookie auth — no token handling in JS.
 *
 * Note: useSearchParams is intentionally NOT used here to avoid Suspense
 * boundary requirements at the hook level. Callers handle redirect-back
 * by passing the target URL directly to login().
 */
export function useAuth() {
  const queryClient = useQueryClient();
  const router = useRouter();

  // Current user — fetched once on mount, cached for 5min
  const {
    data: user,
    isLoading,
    error,
  } = useQuery({
    queryKey: QUERY_KEYS.user,
    queryFn: authApi.me,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  // Login mutation — sets user in cache, redirects to dashboard or redirect-back URL
  const loginMutation = useMutation({
    mutationFn: (args: { data: Parameters<typeof authApi.login>[0]; redirectTo?: string }) =>
      authApi.login(args.data),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(QUERY_KEYS.user, data.user);
      toast.success(data.message || 'Welcome back!');
      // D-11: redirect-back pattern — caller provides redirect URL
      const target = variables.redirectTo || '/dashboard';
      router.push(target as Parameters<typeof router.push>[0]);
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message ?? 'Sign in failed. Please try again.';
      toast.error(message);
    },
  });

  // Register mutation
  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: (data) => {
      queryClient.setQueryData(QUERY_KEYS.user, data.user);
      toast.success(data.message || 'Account created! Check your email to verify.');
      router.push('/verify-email');
    },
    onError: (err: unknown) => {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message ?? 'Registration failed. Please try again.';
      toast.error(message);
    },
  });

  // Logout mutation — clears all query cache, redirects to login
  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.clear();
      toast.info('You have been signed out.');
      router.push('/login');
    },
    onError: () => {
      // Force clear even on error — assume logged out
      queryClient.clear();
      router.push('/login');
    },
  });

  return {
    user,
    isLoading,
    isAuthenticated: !!user && !error,
    login: loginMutation.mutateAsync,
    logout: logoutMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
  };
}
