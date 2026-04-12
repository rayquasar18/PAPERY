import type { Metadata } from 'next';
import { setRequestLocale, getTranslations } from 'next-intl/server';
import { LoginForm } from '@/components/auth/login-form';

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Auth.login' });
  return {
    title: `${t('title')} — PAPERY`,
  };
}

/**
 * Login page — server component wrapper.
 * Declares locale for static rendering, renders client LoginForm.
 */
export default async function LoginPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <LoginForm />;
}
