import { z } from 'zod';

export const adminUserSchema = z.object({
  uuid: z.string().uuid(),
  email: z.string(),
  display_name: z.string().nullable(),
  avatar_url: z.string().nullable(),
  status: z.string(),
  is_verified: z.boolean(),
  is_superuser: z.boolean(),
  tier_slug: z.string().nullable(),
  tier_name: z.string().nullable(),
  stripe_customer_id: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
});

export const adminUserListSchema = z.object({
  items: z.array(adminUserSchema),
  total: z.number().int(),
  page: z.number().int(),
  per_page: z.number().int(),
  pages: z.number().int(),
});

export const tierSchema = z.object({
  uuid: z.string().uuid(),
  name: z.string(),
  slug: z.string(),
  description: z.string().nullable(),
  max_projects: z.number().int(),
  max_docs_per_project: z.number().int(),
  max_fixes_monthly: z.number().int(),
  max_file_size_mb: z.number().int(),
  allowed_models: z.array(z.string()),
  feature_flags: z.record(z.string(), z.boolean()),
  stripe_price_id: z.string().nullable().optional(),
});

export const rateLimitRuleSchema = z.object({
  uuid: z.string().uuid(),
  tier_id: z.number().int().nullable().optional(),
  tier_slug: z.string().nullable().optional(),
  tier_name: z.string().nullable().optional(),
  endpoint_pattern: z.string(),
  max_requests: z.number().int(),
  window_seconds: z.number().int(),
  description: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string().nullable().optional(),
});

export const systemSettingSchema = z.object({
  uuid: z.string().uuid(),
  key: z.string(),
  value: z.record(z.string(), z.unknown()),
  category: z.string(),
  description: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
});

export const groupedSettingsSchema = z.object({
  settings: z.record(z.string(), z.array(systemSettingSchema)),
});

export type AdminUser = z.infer<typeof adminUserSchema>;
export type AdminUserList = z.infer<typeof adminUserListSchema>;
export type Tier = z.infer<typeof tierSchema>;
export type RateLimitRule = z.infer<typeof rateLimitRuleSchema>;
export type GroupedSettings = z.infer<typeof groupedSettingsSchema>;
