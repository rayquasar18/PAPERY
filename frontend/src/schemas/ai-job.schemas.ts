import { z } from 'zod';

export const aiJobStatusSchema = z.enum([
  'pending',
  'running',
  'succeeded',
  'failed',
  'timed_out',
]);

export const aiJobSubmitSchema = z.object({
  action: z.string().min(1),
  prompt: z.string().min(1),
  document_ids: z.array(z.string().min(1)).default([]),
  metadata: z.record(z.string(), z.unknown()).default({}),
});

export const aiJobResponseSchema = z.object({
  job_id: z.string().uuid(),
  status: aiJobStatusSchema,
  action: z.string(),
  progress: z.number().int().min(0).max(100).default(0),
  attempt: z.number().int().min(1).default(1),
  max_attempts: z.number().int().min(1).default(3),
  result_payload: z.record(z.string(), z.unknown()).nullable().optional(),
  error_payload: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const aiJobErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
  }),
  request_id: z.string().nullable().optional(),
});

export type AIJobSubmitInput = z.infer<typeof aiJobSubmitSchema>;
export type AIJobResponse = z.infer<typeof aiJobResponseSchema>;
