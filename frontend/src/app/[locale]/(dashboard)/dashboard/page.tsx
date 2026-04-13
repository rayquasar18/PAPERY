import { setRequestLocale } from 'next-intl/server';
import { hasLocale } from 'next-intl';
import { SectionCards } from '@/components/layout/section-cards';
import { ChartAreaInteractive } from '@/components/layout/chart-area-interactive';
import { routing } from '@/lib/i18n/routing';

type Props = {
  params: Promise<{ locale: string }>;
};

/**
 * DashboardPage -- Main dashboard overview page.
 *
 * Adapted from shadcn dashboard-01 layout structure:
 * - SectionCards (4 metric cards with @container responsive grid)
 * - ChartAreaInteractive (interactive area chart)
 *
 * Currently shows placeholder data; real data will be wired in future phases.
 */
export default async function DashboardPage({ params }: Props) {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale)
    ? rawLocale
    : routing.defaultLocale;
  setRequestLocale(locale as 'en' | 'vi');

  return (
    <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
      <SectionCards />
      <div className="px-4 lg:px-6">
        <ChartAreaInteractive />
      </div>
    </div>
  );
}
