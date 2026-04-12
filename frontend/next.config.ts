import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactCompiler: true,
  images: {
    remotePatterns: [
      // MinIO/S3 backend URLs will be added here when configured
    ],
  },
};

export default nextConfig;
