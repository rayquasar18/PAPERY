'use client';

import { TrendingUp, TrendingDown } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

/**
 * SectionCards -- Dashboard stats cards adapted from shadcn dashboard-01.
 *
 * Displays four metric cards: Total Projects, Documents, AI Queries, Storage.
 * Uses @container queries from the parent layout for responsive grid.
 * Shows placeholder data ("0", "--") until real data is wired.
 * All labels use i18n translations from the Dashboard namespace.
 */
export function SectionCards() {
  const t = useTranslations('Dashboard');

  return (
    <div className="grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4 dark:*:data-[slot=card]:bg-card">
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>{t('stats.totalProjects')}</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            0
          </CardTitle>
          <CardAction>
            <Badge variant="outline">
              <TrendingUp />
              --
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            {t('stats.noData')}
          </div>
          <div className="text-muted-foreground">
            {t('stats.fromLastMonth', { count: 0 })}
          </div>
        </CardFooter>
      </Card>

      <Card className="@container/card">
        <CardHeader>
          <CardDescription>{t('stats.totalDocuments')}</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            0
          </CardTitle>
          <CardAction>
            <Badge variant="outline">
              <TrendingUp />
              --
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            {t('stats.noData')}
          </div>
          <div className="text-muted-foreground">
            {t('stats.fromLastMonth', { count: 0 })}
          </div>
        </CardFooter>
      </Card>

      <Card className="@container/card">
        <CardHeader>
          <CardDescription>{t('stats.aiQueries')}</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            0
          </CardTitle>
          <CardAction>
            <Badge variant="outline">
              <TrendingDown />
              --
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            {t('stats.noData')}
          </div>
          <div className="text-muted-foreground">
            {t('stats.fromLastMonth', { count: 0 })}
          </div>
        </CardFooter>
      </Card>

      <Card className="@container/card">
        <CardHeader>
          <CardDescription>{t('stats.storageUsed')}</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            0 MB
          </CardTitle>
          <CardAction>
            <Badge variant="outline">
              <TrendingUp />
              --
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            {t('stats.noData')}
          </div>
          <div className="text-muted-foreground">
            {t('stats.fromLastMonth', { count: 0 })}
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
