import { ShieldCheck } from 'lucide-react';
import { redirect } from '@/lib/i18n/navigation';
import { routing } from '@/lib/i18n/routing';
import { getSessionUser } from '@/lib/auth/get-session-user';

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export default async function AdminLayout({ children, params }: Props) {
  const { locale } = await params;
  const safeLocale = routing.locales.includes(locale as 'en' | 'vi') ? (locale as 'en' | 'vi') : routing.defaultLocale;
  const user = await getSessionUser();

  if (!user) {
    redirect({ href: '/login', locale: safeLocale });
  }

  const sessionUser = user!;

  if (!sessionUser.is_superuser) {
    redirect({ href: '/dashboard', locale: safeLocale });
  }

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6">
      <div className="flex items-center gap-3 rounded-[12px] border bg-card p-4">
        <ShieldCheck className="size-5 text-primary" />
        <div>
          <h1 className="text-lg font-semibold">Admin workspace</h1>
          <p className="text-sm text-muted-foreground">
            Shared route group for users, tiers, rate limits, and runtime settings.
          </p>
        </div>
      </div>
      {children}
    </div>
  );
}
