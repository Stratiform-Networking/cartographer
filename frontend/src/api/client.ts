/**
 * Centralized HTTP client wrapper
 *
 * All HTTP requests go through this client which handles:
 * - Cookie-based session auth (with credentials enabled)
 * - CSRF header injection for unsafe methods
 * - Error handling with typed responses
 * - Request timeouts
 * - Response interceptors for 401 handling
 */

import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { API_BASE } from '../config';

const REQUEST_TIMEOUT = 30000; // 30 seconds
const CSRF_COOKIE_NAME = 'cartographer_csrf';

function getCookieValue(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const prefix = `${name}=`;
  const cookie = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  if (!cookie) return null;
  return decodeURIComponent(cookie.slice(prefix.length));
}

function isUnsafeMethod(method?: string): boolean {
  if (!method) return false;
  const normalized = method.toUpperCase();
  return (
    normalized === 'POST' ||
    normalized === 'PUT' ||
    normalized === 'PATCH' ||
    normalized === 'DELETE'
  );
}

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

// Callbacks for auth state changes (set by useAuth composable)
let onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(callback: () => void): void {
  onUnauthorized = callback;
}

// Create axios instance with defaults
const client: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: REQUEST_TIMEOUT,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach CSRF token for unsafe cookie-authenticated requests
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    config.withCredentials = true;
    if (isUnsafeMethod(config.method)) {
      const csrfToken = getCookieValue(CSRF_COOKIE_NAME);
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 errors
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      const isAuthEndpoint =
        url.includes('/api/auth/login') ||
        url.includes('/api/auth/setup') ||
        url.includes('/api/auth/verify');

      if (!isAuthEndpoint && onUnauthorized) {
        console.warn('[API Client] Received 401, triggering unauthorized callback');
        onUnauthorized();
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Extract error message from axios error
 */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;
    return axiosError.response?.data?.detail || axiosError.message || 'Request failed';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Unknown error';
}

/**
 * Create an API error from axios error
 */
export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;
    return {
      status: axiosError.response?.status || 0,
      message: extractErrorMessage(error),
      detail: axiosError.response?.data?.detail,
    };
  }
  return {
    status: 0,
    message: error instanceof Error ? error.message : 'Unknown error',
  };
}

export { client };
export default client;
