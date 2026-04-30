import type { ReactNode } from 'react';
import { setRequestLocale } from 'next-intl/server';
import { hasLocale } from 'next-intl';
import { AuthBranding } from '@/components/auth/auth-branding';
import { routing } from '@/lib/i18n/routing';

type Props = {
  children: ReactNode;
  params: Promise<{ locale: string }>;
};

/**
 * Auth route group layout — split-screen pattern (D-08).
 * Desktop: AuthBranding (50%) | Form area (50%)
 * Tablet:  AuthBranding (40%) | Form area (60%)
 * Mobile:  Form only, full width, centered
 */
export default async function AuthLayout({ children, params }: Props) {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  setRequestLocale(locale);

  return (
    <div className="flex min-h-screen">
      {/* Left — branding panel (hidden on mobile, 40% on tablet, 50% on desktop) */}
      <AuthBranding />

      {/* Right — form panel */}
      <main className="flex flex-1 md:w-3/5 lg:w-1/2 items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  );
}
