/**
 * Tests for api/client.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios, { AxiosError } from 'axios';
import client, { extractErrorMessage, toApiError, setOnUnauthorized } from '../../api/client';

// Helper to create mock axios errors
function createAxiosError(
  status: number,
  detail?: string,
  message = 'Request failed'
): AxiosError<{ detail?: string }> {
  const error = new Error(message) as AxiosError<{ detail?: string }>;
  error.isAxiosError = true;
  error.response = {
    status,
    statusText: 'Error',
    headers: {},
    config: {} as AxiosError['config'],
    data: detail ? { detail } : {},
  } as AxiosError<{ detail?: string }>['response'];
  error.config = {} as AxiosError['config'];
  error.toJSON = () => ({});
  return error;
}

describe('api/client', () => {
  describe('extractErrorMessage', () => {
    it('extracts detail from axios error response', () => {
      const error = createAxiosError(404, 'User not found');
      expect(axios.isAxiosError(error)).toBe(true);
      expect(extractErrorMessage(error)).toBe('User not found');
    });

    it('falls back to axios message when no detail', () => {
      const error = createAxiosError(500, undefined, 'Network Error');
      expect(extractErrorMessage(error)).toBe('Network Error');
    });

    it('extracts message from standard Error', () => {
      const error = new Error('Something went wrong');
      expect(extractErrorMessage(error)).toBe('Something went wrong');
    });

    it('returns "Unknown error" for non-error values', () => {
      expect(extractErrorMessage('string error')).toBe('Unknown error');
      expect(extractErrorMessage(null)).toBe('Unknown error');
      expect(extractErrorMessage(undefined)).toBe('Unknown error');
    });
  });

  describe('toApiError', () => {
    it('creates ApiError from axios error', () => {
      const error = createAxiosError(404, 'Not found');
      const apiError = toApiError(error);
      expect(apiError.status).toBe(404);
      expect(apiError.message).toBe('Not found');
      expect(apiError.detail).toBe('Not found');
    });

    it('handles axios error without response', () => {
      const error = new Error('Network Error') as AxiosError;
      error.isAxiosError = true;
      error.config = {} as AxiosError['config'];
      error.toJSON = () => ({});

      const apiError = toApiError(error);
      expect(apiError.status).toBe(0);
      expect(apiError.message).toBe('Network Error');
    });

    it('creates ApiError from standard Error', () => {
      const error = new Error('Standard error');
      const apiError = toApiError(error);
      expect(apiError.status).toBe(0);
      expect(apiError.message).toBe('Standard error');
    });

    it('handles unknown error types', () => {
      const apiError = toApiError('string error');
      expect(apiError.status).toBe(0);
      expect(apiError.message).toBe('Unknown error');
    });
  });

  describe('setOnUnauthorized', () => {
    it('accepts a callback function', () => {
      const callback = vi.fn();
      // Should not throw
      expect(() => setOnUnauthorized(callback)).not.toThrow();
    });

    it('can be called multiple times to update callback', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();

      setOnUnauthorized(callback1);
      setOnUnauthorized(callback2);

      // Should not throw - just updates internal state
      expect(callback1).not.toHaveBeenCalled();
      expect(callback2).not.toHaveBeenCalled();
    });
  });

  describe('401 interceptor behavior', () => {
    function getResponseErrorHandler() {
      const handlers = (client.interceptors.response as any).handlers;
      return handlers[handlers.length - 1].rejected as (error: AxiosError) => Promise<never>;
    }

    it('does not trigger unauthorized callback for password reset endpoints', async () => {
      const callback = vi.fn();
      setOnUnauthorized(callback);

      const handler = getResponseErrorHandler();
      const error = createAxiosError(401, 'Unauthorized');
      error.config = { url: '/api/auth/password-reset/request' } as AxiosError['config'];

      await handler(error).catch(() => {});

      expect(callback).not.toHaveBeenCalled();
    });

    it('triggers unauthorized callback for protected non-auth endpoints', async () => {
      const callback = vi.fn();
      setOnUnauthorized(callback);

      const handler = getResponseErrorHandler();
      const error = createAxiosError(401, 'Unauthorized');
      error.config = { url: '/api/networks' } as AxiosError['config'];

      await handler(error).catch(() => {});

      expect(callback).toHaveBeenCalledTimes(1);
    });
  });
});
