import { useTranslations } from 'next-intl';
import { setRequestLocale } from 'next-intl/server';
import { hasLocale } from 'next-intl';
import { FolderPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { routing } from '@/lib/i18n/routing';

type Props = {
  params: Promise<{ locale: string }>;
};

/**
 * DashboardPage — Main dashboard page showing the projects overview.
 *
 * v1 empty state: prompts first-time users to create their first project.
 * Project grid with real data will be implemented in Phase 10.
 */
export default async function DashboardPage({ params }: Props) {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  setRequestLocale(locale as 'en' | 'vi');

  return <DashboardContent />;
}

function DashboardContent() {
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const t = useTranslations('Dashboard');

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t('title')}</h1>
        <Button size="sm">
          <FolderPlus className="mr-2 size-4" />
          {t('emptyState.cta')}
        </Button>
      </div>

      {/* Empty state */}
      <Card className="flex flex-col items-center justify-center min-h-80 text-center">
        <CardHeader>
          <div className="flex size-16 items-center justify-center rounded-full bg-primary/10 mx-auto mb-2">
            <FolderPlus className="size-8 text-primary" />
          </div>
          <CardTitle className="text-lg">{t('emptyState.title')}</CardTitle>
          <CardDescription className="max-w-sm mx-auto">
            {t('emptyState.body')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button>
            <FolderPlus className="mr-2 size-4" />
            {t('emptyState.cta')}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
