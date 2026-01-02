/**
 * Centralized HTTP client wrapper
 *
 * All HTTP requests go through this client which handles:
 * - Auth headers (attached automatically from stored token)
 * - Error handling with typed responses
 * - Request timeouts
 * - Response interceptors for 401 handling
 */

import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { API_BASE } from '../config';

const AUTH_STORAGE_KEY = 'cartographer_auth';
const REQUEST_TIMEOUT = 30000; // 30 seconds

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
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach auth token
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    try {
      const stored = localStorage.getItem(AUTH_STORAGE_KEY);
      if (stored) {
        const authState = JSON.parse(stored);
        if (authState.token && authState.expiresAt > Date.now()) {
          config.headers.Authorization = `Bearer ${authState.token}`;
        }
      }
    } catch {
      // Ignore storage errors
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
