import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  reactCompiler: true,
  images: {
    remotePatterns: [
      // MinIO/S3 backend URLs will be added here when configured
    ],
  },
};

export default withNextIntl(nextConfig);
