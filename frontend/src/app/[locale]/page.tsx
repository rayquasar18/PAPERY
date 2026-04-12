import { redirect } from '@/i18n/navigation';

type Props = {
  params: Promise<{ locale: string }>;
};

// Root locale page redirects to /[locale]/dashboard
export default async function LocalePage({ params }: Props) {
  const { locale } = await params;
  redirect({ href: '/dashboard', locale });
}
