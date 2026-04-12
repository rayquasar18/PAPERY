# Phase 9 Research: HTTP Client & Authentication

**Researched:** 2026-04-12
**Scope:** Axios configuration, JWT cookie auth, auto-refresh, Next.js proxy for route protection, auth pages
**Relevant decisions:** D-08 to D-13, D-26
**Requirements:** FRONT-08, FRONT-10

---

## 1. Key Findings

1. **Backend auth uses HttpOnly cookies exclusively** — access_token (30min) and refresh_token (7days) are set as HttpOnly cookies. Tokens are NEVER in response bodies. Frontend does NOT handle JWT directly.
2. **Next.js 16 uses `proxy.ts`** (not middleware.ts) — route protection, auth checks, and i18n must all be composed in `src/proxy.ts`.
3. **Axios with `withCredentials: true`** is essential — ensures cookies are sent with cross-origin requests to backend API.
4. **Auto-refresh pattern in proxy.ts** — user's proposed approach is correct: check cookie presence in proxy, call backend `/auth/refresh` if access_token expired but refresh_token exists, set new cookies on response.
5. **Backend schemas are clear** — `AuthResponse { user: UserPublicRead, message: string }`, error format `{ error_code, message, details, request_id }`.
6. **Reference project** uses Axios with interceptors but localStorage tokens (not cookies). PAPERY uses HttpOnly cookies — different approach needed.

## 2. Axios Configuration

```typescript
// src/lib/api/client.ts
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/${API_VERSION}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // CRITICAL: send HttpOnly cookies
});

// Request interceptor — FormData handling
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']; // Let browser set boundary
  }
  return config;
});

// Response interceptor — auto-refresh on 401
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: AxiosError | null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve();
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue requests while refreshing
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => apiClient(originalRequest));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await apiClient.post('/auth/refresh');
        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as AxiosError);
        // Redirect to login — refresh failed
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

**Note:** `_retry` is a custom property. Extend AxiosRequestConfig:
```typescript
// src/lib/types/axios.d.ts
import 'axios';
declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}
```

## 3. Cookie-Based JWT with Next.js 16

### How It Works
- Backend sets `access_token` and `refresh_token` as HttpOnly cookies
- Cookies are SameSite=Lax, Secure=true in production
- Frontend Axios sends cookies automatically via `withCredentials: true`
- Frontend JavaScript CANNOT read HttpOnly cookies — no token in JS memory
- SSR: Next.js proxy can read cookies from incoming request (server-side)

### Server-Side Cookie Reading (in proxy.ts)
```typescript
// src/proxy.ts
export function proxy(request: NextRequest) {
  const accessToken = request.cookies.get('access_token')?.value;
  const refreshToken = request.cookies.get('refresh_token')?.value;
  // ...
}
```

### Client-Side
- No cookie reading needed — Axios sends them automatically
- Auth state determined by: calling `/auth/me` endpoint on mount, caching result in TanStack Query

## 4. proxy.ts — Auth + i18n Composition

**User's proposed pattern** is solid but needs refinement for PAPERY's cookie names and i18n composition:

```typescript
// src/proxy.ts
import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { routing } from '@/i18n/routing';

// i18n middleware
const intlMiddleware = createMiddleware(routing);

// Public paths that don't require auth
const PUBLIC_PATHS = ['/login', '/register', '/verify-email', '/forgot-password', '/reset-password'];

function isPublicPath(pathname: string): boolean {
  // Strip locale prefix: /en/login → /login
  const pathWithoutLocale = pathname.replace(/^\/(en|vi)/, '') || '/';
  return PUBLIC_PATHS.some(p => pathWithoutLocale.startsWith(p));
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Skip for static/API routes
  if (pathname.startsWith('/_next') || pathname.startsWith('/api') || pathname.includes('.')) {
    return NextResponse.next();
  }

  const accessToken = request.cookies.get('access_token')?.value;
  const refreshToken = request.cookies.get('refresh_token')?.value;

  // CASE 1: Protected route, no tokens → redirect to login
  if (!accessToken && !refreshToken && !isPublicPath(pathname)) {
    const loginUrl = new URL('/en/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);  // D-11: redirect-back pattern
    return NextResponse.redirect(loginUrl);
  }

  // CASE 2: Access token expired, refresh token exists → refresh
  if (!accessToken && refreshToken && !isPublicPath(pathname)) {
    try {
      const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Cookie': `refresh_token=${refreshToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        // Extract Set-Cookie headers from backend response
        const setCookieHeaders = response.headers.getSetCookie();
        const nextResponse = intlMiddleware(request); // Apply i18n
        
        // Forward new cookies from backend
        for (const cookie of setCookieHeaders) {
          nextResponse.headers.append('Set-Cookie', cookie);
        }
        return nextResponse;
      } else {
        // Refresh failed → clear cookies, redirect to login
        const loginUrl = new URL('/en/login', request.url);
        const nextResponse = NextResponse.redirect(loginUrl);
        nextResponse.cookies.delete('access_token');
        nextResponse.cookies.delete('refresh_token');
        return nextResponse;
      }
    } catch {
      // Network error → let through, client-side will handle
      return intlMiddleware(request);
    }
  }

  // CASE 3: Auth user visiting login/register → redirect to dashboard
  if (accessToken && isPublicPath(pathname)) {
    return NextResponse.redirect(new URL('/en/dashboard', request.url));
  }

  // CASE 4: Normal request → apply i18n middleware
  return intlMiddleware(request);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
```

### Key Design Decisions
1. **proxy.ts handles BOTH auth AND i18n** — single entry point, no composition conflicts
2. **Refresh happens server-side** — user never sees 401, seamless experience
3. **redirect-back pattern (D-11)** — original URL stored in `?redirect=` query param
4. **Authenticated users redirected away from auth pages** — standard SaaS pattern

## 5. Error Normalization

```typescript
// src/lib/api/error.ts
import { type AxiosError } from 'axios';

export interface ApiError {
  errorCode: string;
  message: string;
  details: Record<string, unknown> | null;
  requestId: string | null;
  statusCode: number;
}

export function normalizeError(error: unknown): ApiError {
  if (isAxiosError(error) && error.response?.data) {
    const data = error.response.data as Record<string, unknown>;
    return {
      errorCode: (data.error_code as string) || 'UNKNOWN_ERROR',
      message: (data.message as string) || 'An unexpected error occurred',
      details: (data.details as Record<string, unknown>) || null,
      requestId: (data.request_id as string) || null,
      statusCode: error.response.status,
    };
  }

  return {
    errorCode: 'NETWORK_ERROR',
    message: error instanceof Error ? error.message : 'Network error',
    details: null,
    requestId: null,
    statusCode: 0,
  };
}

function isAxiosError(error: unknown): error is AxiosError {
  return (error as AxiosError)?.isAxiosError === true;
}
```

## 6. Auth API Client

```typescript
// src/lib/api/auth.ts
import apiClient from './client';
import type { z } from 'zod';
import type { loginSchema, registerSchema } from '@/lib/schemas/auth';

export interface UserPublicRead {
  uuid: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  is_verified: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface AuthResponse {
  user: UserPublicRead;
  message: string;
}

export interface MessageResponse {
  message: string;
}

export const authApi = {
  register: async (data: z.infer<typeof registerSchema>) => {
    const response = await apiClient.post<AuthResponse>('/auth/register', {
      email: data.email,
      password: data.password,
    });
    return response.data;
  },

  login: async (data: z.infer<typeof loginSchema>) => {
    const response = await apiClient.post<AuthResponse>('/auth/login', data);
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post<MessageResponse>('/auth/logout');
    return response.data;
  },

  refresh: async () => {
    const response = await apiClient.post<AuthResponse>('/auth/refresh');
    return response.data;
  },

  me: async () => {
    const response = await apiClient.get<UserPublicRead>('/auth/me');
    return response.data;
  },

  verifyEmail: async (token: string) => {
    const response = await apiClient.post<MessageResponse>('/auth/verify-email', { token });
    return response.data;
  },

  resendVerification: async (email: string) => {
    const response = await apiClient.post<MessageResponse>('/auth/resend-verification', { email });
    return response.data;
  },

  forgotPassword: async (email: string) => {
    const response = await apiClient.post<MessageResponse>('/auth/forgot-password', { email });
    return response.data;
  },

  resetPassword: async (token: string, newPassword: string) => {
    const response = await apiClient.post<MessageResponse>('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    return response.data;
  },

  // OAuth — redirect-based
  googleLogin: () => {
    window.location.href = `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/api/v1/auth/google`;
  },

  githubLogin: () => {
    window.location.href = `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/api/v1/auth/github`;
  },
};
```

## 7. Auth Pages Structure

| Page | Route | Purpose |
|------|-------|---------|
| Login | `/[locale]/login` | Email/password + OAuth buttons |
| Register | `/[locale]/register` | Email/password signup |
| Verify Email | `/[locale]/verify-email?token=xxx` | Email verification callback |
| Forgot Password | `/[locale]/forgot-password` | Request password reset email |
| Reset Password | `/[locale]/reset-password?token=xxx` | Set new password |

### Auth Layout (D-08)
Split-screen: branding left (60%), form right (40%). Mobile: form only (100%).

```
┌─────────────────────────────┬──────────────────┐
│                             │                  │
│  PAPERY                     │  Login Form      │
│  Tagline                    │  Email: [      ] │
│  Illustration/gradient      │  Password: [   ] │
│                             │  [Login]         │
│                             │  ─── or ───      │
│                             │  [Google] [GitHub]│
│                             │                  │
└─────────────────────────────┴──────────────────┘
```

## 8. OAuth Flow (Frontend Side)

1. User clicks "Login with Google/GitHub" button
2. Frontend redirects to backend OAuth endpoint: `GET /api/v1/auth/google`
3. Backend redirects to Google/GitHub OAuth consent page
4. User authorizes → callback to backend: `GET /api/v1/auth/google/callback`
5. Backend creates/links user, sets HttpOnly cookies, redirects to frontend dashboard
6. Frontend loads with cookies already set — no token handling needed

**Key:** OAuth is entirely backend-driven. Frontend just redirects.

## 9. useAuth Hook

```typescript
// src/lib/hooks/use-auth.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/lib/api/auth';
import { QUERY_KEYS } from '@/lib/api/query-client';
import { useRouter } from '@/i18n/navigation';
import { toast } from 'sonner';

export function useAuth() {
  const queryClient = useQueryClient();
  const router = useRouter();

  const { data: user, isLoading, error } = useQuery({
    queryKey: QUERY_KEYS.user,
    queryFn: authApi.me,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: (data) => {
      queryClient.setQueryData(QUERY_KEYS.user, data.user);
      toast.success(data.message);
      router.push('/dashboard');
    },
  });

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
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
    isLoggingIn: loginMutation.isPending,
  };
}
```

## 10. Risks & Considerations

1. **CORS configuration** — Backend `CORS_ORIGINS` must include frontend origin. `withCredentials: true` requires explicit origin (not `*`).
2. **SameSite=Lax cookies** — Won't be sent on cross-site POST requests. Backend and frontend should be same-site in production (or use SameSite=None + Secure).
3. **SSR auth state** — proxy.ts only checks cookie presence, not token validity. Invalid/expired access tokens pass through — client-side handles 401.
4. **Proxy refresh timing** — If backend is slow to respond, proxy request may timeout. Set reasonable timeout (5s).
5. **Cookie names must match** — Backend uses `access_token` and `refresh_token` — frontend proxy must use exact same names.
6. **Hydration mismatch** — Auth-dependent UI should be client components or use `useEffect` to avoid SSR/client mismatch.

## 11. Required Packages

```json
{
  "axios": "^1.13.0"
}
```

No additional auth packages needed — auth is entirely cookie-based via backend.

---

## RESEARCH COMPLETE

*Phase: 09-frontend-foundation-auth-ui*
*Research scope: HTTP Client & Authentication*
*Researched: 2026-04-12*
