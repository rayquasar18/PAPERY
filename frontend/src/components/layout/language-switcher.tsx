'use client';

import { Globe } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter } from '@/lib/i18n/navigation';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { routing } from '@/lib/i18n/routing';

// Supported locales with display names (D-21)
const LOCALE_LABELS: Record<string, string> = {
  en: 'English',
  vi: 'Tiếng Việt',
};

/**
 * LanguageSwitcher — Locale selector dropdown.
 *
 * Switches between supported locales (en, vi) while preserving the
 * current pathname. Uses next-intl navigation for type-safe routing (D-21).
 */
export function LanguageSwitcher() {
  const t = useTranslations('Language');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const handleLocaleChange = (nextLocale: string) => {
    // Narrow to typed locale before passing to next-intl router
    const typedLocale = routing.locales.find((l) => l === nextLocale);
    if (typedLocale) router.replace(pathname, { locale: typedLocale });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 h-9 px-2"
          aria-label={t('switchLabel')}
        >
          <Globe className="size-4" />
          <span className="text-sm font-medium uppercase">{locale}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {routing.locales.map((l) => (
          <DropdownMenuItem
            key={l}
            onClick={() => handleLocaleChange(l)}
            className={l === locale ? 'font-medium' : ''}
          >
            {LOCALE_LABELS[l] ?? l}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
