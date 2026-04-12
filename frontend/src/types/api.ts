/**
 * Shared API response types matching the backend Pydantic schemas.
 * Uses camelCase on the frontend; backend returns snake_case which Axios maps directly.
 */

/** Public user profile — safe fields only, no password or internal data. */
export interface UserPublicRead {
  uuid: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  is_verified: boolean;
  is_superuser: boolean;
  created_at: string;
}

/** Standard auth endpoint response wrapping a user + confirmation message. */
export interface AuthResponse {
  user: UserPublicRead;
  message: string;
}

/** Generic message-only response for endpoints that return no data. */
export interface MessageResponse {
  message: string;
}

/** Paginated list wrapper used by collection endpoints. */
export interface PaginatedResponse<T> {
  data: T[];
  total_count: number;
  has_more: boolean;
  page: number;
  page_size: number;
}
