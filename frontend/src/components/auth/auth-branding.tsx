'use client';

import { useTranslations } from 'next-intl';

/**
 * Left-side branding panel for auth pages.
 * Displays PAPERY logo, tagline, and a subtle monochrome background.
 * Hidden on mobile — visible from md breakpoint up.
 */
export function AuthBranding() {
  const t = useTranslations('Auth.branding');

  return (
    <div className="relative hidden overflow-hidden border-r border-border bg-background text-foreground md:flex md:w-2/5 md:flex-col md:items-center md:justify-center p-12 lg:w-1/2">
      {/* Subtle monochrome layer */}
      <div aria-hidden="true" className="absolute inset-0 bg-secondary/40" />

      {/* Content — above the decorative layer */}
      <div className="relative z-10 flex flex-col items-center text-center max-w-md gap-6">
        {/* PAPERY logo — text-based for v1 */}
        <div className="flex items-center gap-2" style={{ height: '48px' }}>
          <span className="text-4xl font-medium tracking-tight select-none">
            PAPERY
          </span>
        </div>

        {/* Tagline — display size (30px), semibold */}
        <h1
          className="font-medium leading-tight font-display"
          style={{ fontSize: '1.875rem', lineHeight: '1.2' }}
        >
          {t('tagline')}
        </h1>

        {/* Subtitle — body size (14px), 70% opacity */}
        <p className="leading-relaxed text-muted-foreground" style={{ fontSize: '0.875rem' }}>
          {t('subtitle')}
        </p>
      </div>
    </div>
  );
}
