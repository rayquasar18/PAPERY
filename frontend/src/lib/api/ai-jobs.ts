import apiClient from './client';
import {
  aiJobResponseSchema,
  aiJobSubmitSchema,
  type AIJobResponse,
  type AIJobSubmitInput,
} from '@/schemas/ai-job.schemas';

const TERMINAL_STATUSES = new Set(['succeeded', 'failed', 'timed_out']);

export const aiJobsApi = {
  submit: async (input: AIJobSubmitInput): Promise<AIJobResponse> => {
    const payload = aiJobSubmitSchema.parse(input);
    const response = await apiClient.post('/ai-jobs', payload);
    return aiJobResponseSchema.parse(response.data);
  },

  getStatus: async (jobId: string): Promise<AIJobResponse> => {
    const response = await apiClient.get(`/ai-jobs/${jobId}`);
    return aiJobResponseSchema.parse(response.data);
  },

  isTerminal(status: AIJobResponse['status']): boolean {
    return TERMINAL_STATUSES.has(status);
  },
};
