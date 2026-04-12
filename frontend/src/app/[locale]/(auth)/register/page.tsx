import type { Metadata } from 'next';
import { setRequestLocale, getTranslations } from 'next-intl/server';
import { hasLocale } from 'next-intl';
import { RegisterForm } from '@/components/auth/register-form';
import { routing } from '@/lib/i18n/routing';

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  const t = await getTranslations({ locale, namespace: 'Auth' });
  return {
    title: `${t('register.title')} — PAPERY`,
  };
}

/**
 * Register page — server component wrapper.
 * Declares locale for static rendering, renders client RegisterForm.
 */
export default async function RegisterPage({ params }: Props) {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  setRequestLocale(locale);

  return <RegisterForm />;
}
