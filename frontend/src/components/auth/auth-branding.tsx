'use client';

import { useTranslations } from 'next-intl';

/**
 * Left-side branding panel for auth pages.
 * Displays PAPERY logo, tagline, and a decorative gradient background.
 * Hidden on mobile — visible from md breakpoint up.
 */
export function AuthBranding() {
  const t = useTranslations('Auth.branding');

  return (
    <div className="relative hidden md:flex md:w-2/5 lg:w-1/2 flex-col items-center justify-center bg-gradient-to-br from-indigo-600 to-blue-800 p-12 text-white overflow-hidden">
      {/* Decorative dot grid pattern at 10% opacity */}
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage:
            'radial-gradient(circle, white 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* Content — above the decorative layer */}
      <div className="relative z-10 flex flex-col items-center text-center max-w-md gap-6">
        {/* PAPERY logo — text-based for v1 */}
        <div className="flex items-center gap-2" style={{ height: '48px' }}>
          <span className="text-4xl font-bold tracking-tight select-none">
            PAPERY
          </span>
        </div>

        {/* Tagline — display size (30px), semibold */}
        <h1
          className="font-semibold leading-tight"
          style={{ fontSize: '1.875rem', lineHeight: '1.2' }}
        >
          {t('tagline')}
        </h1>

        {/* Subtitle — body size (14px), 70% opacity */}
        <p
          className="leading-relaxed"
          style={{ fontSize: '0.875rem', color: 'rgba(255,255,255,0.70)' }}
        >
          {t('subtitle')}
        </p>
      </div>
    </div>
  );
}
