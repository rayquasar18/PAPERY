import { z } from 'zod';

export const projectSchema = z.object({
  uuid: z.string().uuid(),
  owner_id: z.number().int(),
  name: z.string(),
  description: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
  relationship_type: z.enum(['owned', 'shared']).optional(),
});

export const projectsListSchema = z.object({
  items: z.array(projectSchema),
  page: z.number().int(),
  per_page: z.number().int(),
  total: z.number().int(),
});

export const projectCreateSchema = z.object({
  name: z.string().trim().min(1).max(160),
  description: z.string().trim().max(1000).nullable().optional(),
});

export const projectUpdateSchema = projectCreateSchema.partial();

export const projectInviteSchema = z.object({
  token: z.string(),
  expires_at: z.string(),
  role: z.enum(['owner', 'editor', 'viewer']),
});

export type Project = z.infer<typeof projectSchema>;
export type ProjectsList = z.infer<typeof projectsListSchema>;
export type ProjectCreateInput = z.infer<typeof projectCreateSchema>;
export type ProjectUpdateInput = z.infer<typeof projectUpdateSchema>;
