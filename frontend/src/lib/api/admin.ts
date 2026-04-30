import apiClient from './client';
import {
  adminUserListSchema,
  adminUserSchema,
  groupedSettingsSchema,
  rateLimitRuleSchema,
  tierSchema,
} from '@/schemas/admin.schemas';

export const adminApi = {
  listUsers: async () => {
    const response = await apiClient.get('/admin/users');
    return adminUserListSchema.parse(response.data);
  },

  getUser: async (userUuid: string) => {
    const response = await apiClient.get(`/admin/users/${userUuid}`);
    return adminUserSchema.parse(response.data);
  },

  listTiers: async () => {
    const response = await apiClient.get('/tiers');
    return response.data.map((item: unknown) => tierSchema.parse(item));
  },

  listRateLimits: async () => {
    const response = await apiClient.get('/admin/rate-limits');
    return response.data.map((item: unknown) => rateLimitRuleSchema.parse(item));
  },

  listSettings: async () => {
    const response = await apiClient.get('/admin/settings');
    return groupedSettingsSchema.parse(response.data);
  },

  createTier: async (payload: Record<string, unknown>) => {
    const response = await apiClient.post('/admin/tiers', payload);
    return tierSchema.parse(response.data);
  },

  updateTier: async (tierUuid: string, payload: Record<string, unknown>) => {
    const response = await apiClient.patch(`/admin/tiers/${tierUuid}`, payload);
    return tierSchema.parse(response.data);
  },
};
