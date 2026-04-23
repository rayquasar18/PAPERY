import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { routing } from '@/lib/i18n/routing';

const intlMiddleware = createMiddleware(routing);
const PROTECTED_ROUTE_ROOTS = ['/dashboard', '/projects', '/settings'] as const;
const AUTH_ROUTE_ROOTS = [
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
  '/verify-email',
] as const;
type AppLocale = (typeof routing.locales)[number];

function normalizePathname(pathname: string): string {
  if (!pathname || pathname === '/') {
    return '/';
  }

  return pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
}

function stripLocalePrefix(pathname: string): {
  localeFromPath: AppLocale | null;
  normalizedPathname: string;
} {
  const normalized = normalizePathname(pathname);
  const segments = normalized.split('/').filter(Boolean);
  const maybeLocale = segments[0] as AppLocale | undefined;

  if (maybeLocale && routing.locales.includes(maybeLocale)) {
    const restPath = `/${segments.slice(1).join('/')}`;

    return {
      localeFromPath: maybeLocale,
      normalizedPathname: normalizePathname(restPath),
    };
  }

  return {
    localeFromPath: null,
    normalizedPathname: normalized,
  };
}

function resolveLocale(request: NextRequest, localeFromPath: AppLocale | null): AppLocale {
  if (localeFromPath) {
    return localeFromPath;
  }

  const localeCookieConfig = routing.localeCookie;

  if (localeCookieConfig && typeof localeCookieConfig !== 'boolean') {
    const localeFromCookie = request.cookies.get(localeCookieConfig.name)?.value;

    if (localeFromCookie && routing.locales.includes(localeFromCookie as AppLocale)) {
      return localeFromCookie as AppLocale;
    }
  }

  return routing.defaultLocale;
}

function matchesRouteRoot(pathname: string, routeRoot: string): boolean {
  return pathname === routeRoot || pathname.startsWith(`${routeRoot}/`);
}

function isProtectedPath(pathname: string): boolean {
  return PROTECTED_ROUTE_ROOTS.some((routeRoot) => matchesRouteRoot(pathname, routeRoot));
}

function isAuthPath(pathname: string): boolean {
  return AUTH_ROUTE_ROOTS.some((routeRoot) => matchesRouteRoot(pathname, routeRoot));
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname, search } = request.nextUrl;

  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  const { localeFromPath, normalizedPathname } = stripLocalePrefix(pathname);

  if (isAuthPath(normalizedPathname) && request.nextUrl.searchParams.has('redirect')) {
    return intlMiddleware(request) as NextResponse;
  }

  const hasAccessToken = Boolean(request.cookies.get('access_token')?.value);

  if (isProtectedPath(normalizedPathname) && !hasAccessToken) {
    const locale = resolveLocale(request, localeFromPath);
    const loginUrl = request.nextUrl.clone();

    loginUrl.pathname = `/${locale}/login`;
    loginUrl.search = '';
    loginUrl.searchParams.set('redirect', `${pathname}${search}`);

    return NextResponse.redirect(loginUrl);
  }

  return intlMiddleware(request) as NextResponse;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
