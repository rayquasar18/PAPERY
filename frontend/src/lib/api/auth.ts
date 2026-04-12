import apiClient from './client';
import type { z } from 'zod';
import type { loginSchema, registerSchema } from '@/schemas/auth';
import type { AuthResponse, MessageResponse, UserPublicRead } from '@/types/api';

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Typed wrappers around every auth-related backend endpoint.
 * All requests use the shared apiClient which handles cookie injection,
 * 401 auto-refresh, and error normalization via interceptors.
 */
export const authApi = {
  /** Register a new account. Sends verification email on success. */
  register: async (data: z.infer<typeof registerSchema>) => {
    const response = await apiClient.post<AuthResponse>('/auth/register', {
      email: data.email,
      password: data.password,
      display_name: data.displayName,
    });
    return response.data;
  },

  /** Authenticate with email + password. Sets HttpOnly cookies on success. */
  login: async (data: z.infer<typeof loginSchema>) => {
    const response = await apiClient.post<AuthResponse>('/auth/login', data);
    return response.data;
  },

  /** Invalidate current tokens and clear auth cookies. */
  logout: async () => {
    const response = await apiClient.post<MessageResponse>('/auth/logout');
    return response.data;
  },

  /** Rotate access token using the refresh token cookie. */
  refresh: async () => {
    const response = await apiClient.post<AuthResponse>('/auth/refresh');
    return response.data;
  },

  /** Fetch the currently authenticated user's profile. */
  me: async () => {
    const response = await apiClient.get<UserPublicRead>('/auth/me');
    return response.data;
  },

  /** Verify an email address via the token sent in the verification email. */
  verifyEmail: async (token: string) => {
    const response = await apiClient.post<MessageResponse>('/auth/verify-email', {
      token,
    });
    return response.data;
  },

  /** Resend the verification email to the given address. */
  resendVerification: async (email: string) => {
    const response = await apiClient.post<MessageResponse>(
      '/auth/resend-verification',
      { email }
    );
    return response.data;
  },

  /** Request a password-reset email for the given address. */
  forgotPassword: async (email: string) => {
    const response = await apiClient.post<MessageResponse>(
      '/auth/forgot-password',
      { email }
    );
    return response.data;
  },

  /** Complete password reset using the token from the reset email. */
  resetPassword: async (token: string, newPassword: string) => {
    const response = await apiClient.post<MessageResponse>(
      '/auth/reset-password',
      { token, new_password: newPassword }
    );
    return response.data;
  },

  /**
   * Initiate Google OAuth flow.
   * Redirects the browser to the backend OAuth endpoint — no API call.
   */
  googleLogin: () => {
    window.location.href = `${BACKEND_URL}/api/${API_VERSION}/auth/google`;
  },

  /**
   * Initiate GitHub OAuth flow.
   * Redirects the browser to the backend OAuth endpoint — no API call.
   */
  githubLogin: () => {
    window.location.href = `${BACKEND_URL}/api/${API_VERSION}/auth/github`;
  },
};
