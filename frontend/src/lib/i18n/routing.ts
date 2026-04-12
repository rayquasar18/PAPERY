import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'vi'],
  defaultLocale: 'en',
  localePrefix: 'always',
  localeCookie: {
    name: 'NEXT_LOCALE',
    maxAge: 60 * 60 * 24 * 365, // 1 year persistence
  },
});
