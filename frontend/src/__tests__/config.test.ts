/**
 * Tests for config.ts
 */

import { describe, it, expect } from 'vitest';
import { apiUrl, API_BASE } from '../config';

describe('config', () => {
  describe('API_BASE', () => {
    it('is defined', () => {
      expect(API_BASE).toBeDefined();
      expect(typeof API_BASE).toBe('string');
    });

    it('does not have trailing slash', () => {
      expect(API_BASE.endsWith('/')).toBe(false);
    });
  });

  describe('apiUrl', () => {
    it('builds URL with path starting with slash', () => {
      const result = apiUrl('/api/auth/login');
      expect(result).toBe(`${API_BASE}/api/auth/login`);
    });

    it('normalizes path without leading slash', () => {
      const result = apiUrl('api/auth/login');
      expect(result).toBe(`${API_BASE}/api/auth/login`);
    });

    it('handles root path', () => {
      const result = apiUrl('/');
      expect(result).toBe(`${API_BASE}/`);
    });

    it('handles empty string', () => {
      const result = apiUrl('');
      expect(result).toBe(`${API_BASE}/`);
    });

    it('preserves query parameters', () => {
      const result = apiUrl('/api/search?q=test&limit=10');
      expect(result).toBe(`${API_BASE}/api/search?q=test&limit=10`);
    });

    it('handles paths with special characters', () => {
      const result = apiUrl('/api/networks/abc-123_def');
      expect(result).toBe(`${API_BASE}/api/networks/abc-123_def`);
    });
  });
});
