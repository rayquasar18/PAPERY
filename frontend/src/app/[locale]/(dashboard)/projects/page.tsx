import { hasLocale } from 'next-intl';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { ProjectsDashboard } from '@/components/dashboard/projects-dashboard';
import { routing } from '@/lib/i18n/routing';

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function ProjectsPage({ params }: Props) {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: 'Dashboard' });

  return (
    <ProjectsDashboard
      emptyTitle={t('emptyState.title')}
      emptyBody={t('emptyState.body')}
      emptyCta={t('emptyState.cta')}
    />
  );
}
