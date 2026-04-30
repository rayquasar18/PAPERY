import 'axios';

declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    /** Marks a request that has already been retried after a 401 response. */
    _retry?: boolean;
  }
}
