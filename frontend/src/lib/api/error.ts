import { type AxiosError } from 'axios';

/**
 * Normalized error shape returned by all API calls.
 * Maps backend snake_case fields to camelCase.
 */
export interface ApiError {
  errorCode: string;
  message: string;
  details: Record<string, unknown> | null;
  requestId: string | null;
  statusCode: number;
}

function isAxiosError(error: unknown): error is AxiosError {
  return (error as AxiosError)?.isAxiosError === true;
}

/**
 * Normalizes any thrown value into a consistent ApiError shape.
 * Handles AxiosError with response data and network-level failures.
 */
export function normalizeError(error: unknown): ApiError {
  if (isAxiosError(error) && error.response?.data) {
    const data = error.response.data as Record<string, unknown>;
    return {
      errorCode: (data.error_code as string) || 'UNKNOWN_ERROR',
      message: (data.message as string) || 'An unexpected error occurred',
      details: (data.details as Record<string, unknown>) ?? null,
      requestId: (data.request_id as string) ?? null,
      statusCode: error.response.status,
    };
  }

  return {
    errorCode: 'NETWORK_ERROR',
    message: error instanceof Error ? error.message : 'Network error',
    details: null,
    requestId: null,
    statusCode: 0,
  };
}
