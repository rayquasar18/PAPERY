import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

// Inter font with Vietnamese subset support (D-15, D-21)
const inter = Inter({
  subsets: ['latin', 'vietnamese'],
  variable: '--font-sans',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'PAPERY',
  description: 'AI-powered document intelligence platform',
};

// Root layout — html/body tags are in [locale]/layout.tsx (needs lang attribute from locale)
// This layout only sets up font variable and passes children through
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
