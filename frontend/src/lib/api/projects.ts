import apiClient from './client';
import {
  projectCreateSchema,
  projectInviteSchema,
  projectSchema,
  projectsListSchema,
  projectUpdateSchema,
  type ProjectCreateInput,
  type ProjectUpdateInput,
} from '@/schemas/project.schemas';

export const projectsApi = {
  list: async (params: { search?: string; page?: number; per_page?: number } = {}) => {
    const response = await apiClient.get('/projects', {
      params: {
        search: params.search || undefined,
        page: params.page ?? 1,
        per_page: params.per_page ?? 20,
      },
    });
    return projectsListSchema.parse(response.data);
  },

  create: async (input: ProjectCreateInput) => {
    const payload = projectCreateSchema.parse(input);
    const response = await apiClient.post('/projects', payload);
    return projectSchema.parse(response.data);
  },

  update: async (projectUuid: string, input: ProjectUpdateInput) => {
    const payload = projectUpdateSchema.parse(input);
    const response = await apiClient.patch(`/projects/${projectUuid}`, payload);
    return projectSchema.parse(response.data);
  },

  remove: async (projectUuid: string) => {
    await apiClient.delete(`/projects/${projectUuid}`);
  },

  createInvite: async (projectUuid: string, payload: { role: 'owner' | 'editor' | 'viewer'; invitee_email: string | null }) => {
    const response = await apiClient.post(`/projects/${projectUuid}/invites`, payload);
    return projectInviteSchema.parse(response.data);
  },
};
