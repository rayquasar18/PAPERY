import { redirect } from '@/i18n/navigation';
import { hasLocale } from 'next-intl';
import { routing } from '@/i18n/routing';

type Props = {
  params: Promise<{ locale: string }>;
};

// Root locale page redirects to /[locale]/dashboard
export default async function LocalePage({ params }: Props) {
  const { locale: rawLocale } = await params;
  // Narrow to typed locale — fallback to default if unknown
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  redirect({ href: '/dashboard', locale });
}
