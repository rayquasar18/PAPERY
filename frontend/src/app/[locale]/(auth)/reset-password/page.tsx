import type { Metadata } from 'next';
import { setRequestLocale, getTranslations } from 'next-intl/server';
import { ResetPasswordForm } from '@/components/auth/reset-password-form';

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Auth.resetPassword' });
  return {
    title: `${t('title')} — PAPERY`,
  };
}

/**
 * Reset password page — server component wrapper.
 * ResetPasswordForm reads ?token= from URL client-side.
 */
export default async function ResetPasswordPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <ResetPasswordForm />;
}
