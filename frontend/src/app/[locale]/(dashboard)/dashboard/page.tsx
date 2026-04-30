import { ArrowRight } from 'lucide-react';
import { hasLocale } from 'next-intl';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AIJobRunner } from '@/components/dashboard/ai-job-runner';
import { routing } from '@/lib/i18n/routing';

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function DashboardPage({ params }: Props) {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: 'Dashboard' });

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('title')}</h1>
        <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>{t('recentProjects.title')}</CardTitle>
            <CardDescription>{t('recentProjects.emptyBody')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline">
              {t('recentProjects.viewAll')}
              <ArrowRight className="size-4" />
            </Button>
          </CardContent>
        </Card>

        <AIJobRunner />
      </div>
    </div>
  );
}
