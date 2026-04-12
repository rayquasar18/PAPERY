import { NextRequest, NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { routing } from '@/lib/i18n/routing';

// i18n middleware — handles locale detection, cookie persistence, and URL prefix
const intlMiddleware = createMiddleware(routing);

/**
 * Proxy function (Next.js 16 replacement for middleware.ts).
 * Currently handles i18n routing only.
 * Auth guard logic will be added in Plan 09-05.
 */
export async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname } = request.nextUrl;

  // Skip proxy for Next.js internals, API routes, and static files
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // Apply i18n middleware for all other routes
  return intlMiddleware(request) as NextResponse;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)',],
};
