import { cookies } from 'next/headers';
import type { UserPublicRead } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

export async function getSessionUser(): Promise<UserPublicRead | null> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('access_token')?.value;

  if (!accessToken) {
    return null;
  }

  const response = await fetch(`${API_BASE_URL}/api/${API_VERSION}/auth/me`, {
    headers: {
      cookie: cookieStore.toString(),
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as UserPublicRead;
}
