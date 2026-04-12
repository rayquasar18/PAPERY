import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { NextIntlClientProvider, hasLocale } from 'next-intl';
import { setRequestLocale, getTranslations } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { Toaster } from '@/components/ui/sonner';
import { ThemeProvider } from '@/components/providers/theme-provider';
import { QueryProvider } from '@/components/providers/query-provider';
import { routing } from '@/lib/i18n/routing';
import '../globals.css';

// Inter font with Vietnamese subset support (D-15, D-21)
const inter = Inter({
  subsets: ['latin', 'vietnamese'],
  variable: '--font-sans',
  display: 'swap',
});

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale: rawLocale } = await params;
  // Narrow to typed locale for type-safe getTranslations call
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  const t = await getTranslations({ locale, namespace: 'Metadata' });

  return {
    title: t('title'),
    description: t('description'),
  };
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;

  // Validate locale against supported list; 404 if unknown
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  // Enable static rendering by declaring the locale for this request
  setRequestLocale(locale);

  return (
    <html lang={locale} className={inter.variable} suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <QueryProvider>
          <ThemeProvider>
            <NextIntlClientProvider>
              {children}
              <Toaster richColors position="top-right" />
            </NextIntlClientProvider>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
