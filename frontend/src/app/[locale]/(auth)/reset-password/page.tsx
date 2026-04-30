import type { Metadata } from 'next';
import { setRequestLocale, getTranslations } from 'next-intl/server';
import { hasLocale } from 'next-intl';
import { ResetPasswordForm } from '@/components/auth/reset-password-form';
import { routing } from '@/lib/i18n/routing';

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  const t = await getTranslations({ locale, namespace: 'Auth' });
  return {
    title: `${t('resetPassword.title')} — PAPERY`,
  };
}

/**
 * Reset password page — server component wrapper.
 * ResetPasswordForm reads ?token= from URL client-side.
 */
export default async function ResetPasswordPage({ params }: Props) {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  setRequestLocale(locale);

  return <ResetPasswordForm />;
}
