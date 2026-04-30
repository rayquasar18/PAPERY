import { ArrowRight, Clock3 } from 'lucide-react';
import { hasLocale } from 'next-intl';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { routing } from '@/lib/i18n/routing';

const recentJobs = [
  { id: 'job-1', status: 'pending', action: 'summarize', detail: 'Waiting in queue' },
  { id: 'job-2', status: 'running', action: 'extract', detail: 'Processing source pages' },
  { id: 'job-3', status: 'succeeded', action: 'translate', detail: 'Completed with citations' },
];

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

        <Card>
          <CardHeader>
            <CardTitle>AI jobs</CardTitle>
            <CardDescription>Polling-first status stream from backend async jobs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {recentJobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between rounded-[12px] border p-3">
                <div className="flex items-start gap-3">
                  <Clock3 className="mt-0.5 size-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{job.action}</p>
                    <p className="text-xs text-muted-foreground">{job.detail}</p>
                  </div>
                </div>
                <Badge variant={job.status === 'succeeded' ? 'default' : 'secondary'}>{job.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
