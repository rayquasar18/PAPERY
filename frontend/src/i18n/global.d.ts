import { routing } from '@/i18n/routing';
import en from '../locale/en.json';

declare module 'next-intl' {
  interface AppConfig {
    Locale: (typeof routing.locales)[number]; // 'en' | 'vi'
    Messages: typeof en;
  }
}
