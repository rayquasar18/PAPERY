import type { Metadata } from 'next';
import { setRequestLocale, getTranslations } from 'next-intl/server';
import { RegisterForm } from '@/components/auth/register-form';

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Auth.register' });
  return {
    title: `${t('title')} — PAPERY`,
  };
}

/**
 * Register page — server component wrapper.
 * Declares locale for static rendering, renders client RegisterForm.
 */
export default async function RegisterPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <RegisterForm />;
}
