import { setRequestLocale, getTranslations } from 'next-intl/server';
import { hasLocale } from 'next-intl';
import {
  FolderKanban,
  FileText,
  Bot,
  HardDrive,
  FolderPlus,
  Upload,
  MessageSquare,
  Activity,
  Inbox,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { routing } from '@/lib/i18n/routing';

type Props = {
  params: Promise<{ locale: string }>;
};

/**
 * DashboardPage — Main dashboard overview page.
 *
 * Displays stats cards, recent projects, recent activity, and quick actions.
 * Currently shows placeholder data; real data will be wired in future phases.
 */
export default async function DashboardPage({ params }: Props) {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale)
    ? rawLocale
    : routing.defaultLocale;
  setRequestLocale(locale as 'en' | 'vi');

  const t = await getTranslations({ locale, namespace: 'Dashboard' });

  const statsCards = [
    {
      title: t('stats.totalProjects'),
      value: '0',
      subtitle: t('stats.noData'),
      icon: FolderKanban,
    },
    {
      title: t('stats.totalDocuments'),
      value: '0',
      subtitle: t('stats.noData'),
      icon: FileText,
    },
    {
      title: t('stats.aiQueries'),
      value: '0',
      subtitle: t('stats.noData'),
      icon: Bot,
    },
    {
      title: t('stats.storageUsed'),
      value: '0 MB',
      subtitle: t('stats.noData'),
      icon: HardDrive,
    },
  ];

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {t('title')}
        </h1>
        <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statsCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardDescription className="text-sm font-medium">
                  {stat.title}
                </CardDescription>
                <Icon className="size-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">{stat.subtitle}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Main content: Recent Projects + Recent Activity */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Recent Projects */}
        <Card>
          <CardHeader>
            <CardTitle>{t('recentProjects.title')}</CardTitle>
            <CardDescription>{t('recentProjects.emptyBody')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex min-h-40 flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-6">
              <div className="flex size-12 items-center justify-center rounded-full bg-muted">
                <Inbox className="size-6 text-muted-foreground" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-muted-foreground">
                  {t('recentProjects.emptyTitle')}
                </p>
                <p className="mt-1 text-xs text-muted-foreground/70">
                  {t('recentProjects.emptyBody')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>{t('recentActivity.title')}</CardTitle>
            <CardDescription>{t('recentActivity.emptyBody')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex min-h-40 flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-6">
              <div className="flex size-12 items-center justify-center rounded-full bg-muted">
                <Activity className="size-6 text-muted-foreground" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-muted-foreground">
                  {t('recentActivity.emptyTitle')}
                </p>
                <p className="mt-1 text-xs text-muted-foreground/70">
                  {t('recentActivity.emptyBody')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>{t('quickActions.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" className="gap-2">
              <FolderPlus className="size-4" />
              {t('quickActions.newProject')}
            </Button>
            <Button variant="outline" className="gap-2">
              <Upload className="size-4" />
              {t('quickActions.uploadDocument')}
            </Button>
            <Button variant="outline" className="gap-2">
              <MessageSquare className="size-4" />
              {t('quickActions.startChat')}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
