import type { Metadata } from 'next';
import { setRequestLocale, getTranslations } from 'next-intl/server';
import { ForgotPasswordForm } from '@/components/auth/forgot-password-form';

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Auth.forgotPassword' });
  return {
    title: `${t('title')} — PAPERY`,
  };
}

/**
 * Forgot password page — server component wrapper.
 */
export default async function ForgotPasswordPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <ForgotPasswordForm />;
}
