/**
 * Tests for utils/formatters.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  formatRelativeTime,
  formatShortTime,
  formatDateTime,
  formatRelativeDate,
  formatTimestamp,
  formatDate,
} from '../../utils/formatters';

describe('formatters', () => {
  // Use a fixed date for consistent testing
  const NOW = new Date('2024-06-15T12:00:00Z');

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('formatRelativeTime', () => {
    it('returns "just now" for times less than 1 minute ago', () => {
      const date = new Date(NOW.getTime() - 30 * 1000); // 30 seconds ago
      expect(formatRelativeTime(date)).toBe('just now');
    });

    it('returns "Just now" when capitalizeJustNow is true', () => {
      const date = new Date(NOW.getTime() - 30 * 1000);
      expect(formatRelativeTime(date, { capitalizeJustNow: true })).toBe('Just now');
    });

    it('returns minutes ago for times less than 1 hour', () => {
      const date = new Date(NOW.getTime() - 5 * 60 * 1000); // 5 minutes ago
      expect(formatRelativeTime(date)).toBe('5m ago');
    });

    it('returns hours ago for times less than 24 hours', () => {
      const date = new Date(NOW.getTime() - 3 * 60 * 60 * 1000); // 3 hours ago
      expect(formatRelativeTime(date)).toBe('3h ago');
    });

    it('returns days ago for times less than 7 days', () => {
      const date = new Date(NOW.getTime() - 4 * 24 * 60 * 60 * 1000); // 4 days ago
      expect(formatRelativeTime(date)).toBe('4d ago');
    });

    it('returns formatted date for times more than 7 days ago', () => {
      const date = new Date('2024-06-01T10:30:00Z'); // 14 days ago
      const result = formatRelativeTime(date);
      expect(result).toContain('Jun');
      expect(result).toContain('1');
    });

    it('includes time when includeTime is true for old dates', () => {
      const date = new Date('2024-06-01T10:30:00Z');
      const result = formatRelativeTime(date, { includeTime: true });
      expect(result).toContain('Jun');
      expect(result).toContain('1');
    });

    it('accepts ISO string input', () => {
      const isoString = new Date(NOW.getTime() - 10 * 60 * 1000).toISOString();
      expect(formatRelativeTime(isoString)).toBe('10m ago');
    });
  });

  describe('formatShortTime', () => {
    it('returns "just now" for times less than 1 minute ago', () => {
      const date = new Date(NOW.getTime() - 30 * 1000);
      expect(formatShortTime(date)).toBe('just now');
    });

    it('returns minutes ago for times less than 1 hour', () => {
      const date = new Date(NOW.getTime() - 15 * 60 * 1000);
      expect(formatShortTime(date)).toBe('15m ago');
    });

    it('returns formatted time for times more than 1 hour ago', () => {
      const date = new Date(NOW.getTime() - 2 * 60 * 60 * 1000);
      const result = formatShortTime(date);
      // Should contain time format (e.g., "10:00" or "10:00 AM")
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });
  });

  describe('formatDateTime', () => {
    it('returns formatted date and time', () => {
      const date = new Date('2024-06-15T14:30:00Z');
      const result = formatDateTime(date);
      expect(result).toContain('Jun');
      expect(result).toContain('15');
    });

    it('accepts ISO string input', () => {
      const isoString = '2024-06-15T14:30:00Z';
      const result = formatDateTime(isoString);
      expect(result).toContain('Jun');
    });
  });

  describe('formatRelativeDate', () => {
    it('returns "today" for today', () => {
      const date = new Date(NOW.getTime() - 1000);
      expect(formatRelativeDate(date)).toBe('today');
    });

    it('returns "yesterday" for yesterday', () => {
      const date = new Date(NOW.getTime() - 24 * 60 * 60 * 1000);
      expect(formatRelativeDate(date)).toBe('yesterday');
    });

    it('returns "X days ago" for less than 7 days', () => {
      const date = new Date(NOW.getTime() - 5 * 24 * 60 * 60 * 1000);
      expect(formatRelativeDate(date)).toBe('5 days ago');
    });

    it('returns formatted date for more than 7 days ago', () => {
      const date = new Date('2024-06-01T10:00:00Z');
      const result = formatRelativeDate(date);
      expect(result).toContain('Jun');
      expect(result).toContain('1');
    });

    it('returns empty string for falsy input', () => {
      expect(formatRelativeDate('')).toBe('');
    });

    it('respects includeYear option', () => {
      const date = new Date('2023-06-01T10:00:00Z');
      const withYear = formatRelativeDate(date, { includeYear: true });
      const withoutYear = formatRelativeDate(date, { includeYear: false });
      expect(withYear).toContain('2023');
      expect(withoutYear).not.toContain('2023');
    });
  });

  describe('formatTimestamp (alias)', () => {
    it('calls formatRelativeTime with correct options', () => {
      const date = new Date(NOW.getTime() - 30 * 1000);
      expect(formatTimestamp(date)).toBe('Just now');
    });
  });

  describe('formatDate (alias)', () => {
    it('calls formatRelativeTime', () => {
      const date = new Date(NOW.getTime() - 5 * 60 * 1000);
      expect(formatDate(date)).toBe('5m ago');
    });
  });
});
