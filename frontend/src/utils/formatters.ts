/**
 * Date and time formatting utilities
 *
 * Centralized formatters to avoid duplication across components.
 */

/**
 * Format a timestamp as relative time (e.g., "5m ago", "2d ago")
 * Falls back to formatted date for older timestamps.
 *
 * @param dateInput - ISO string or Date object
 * @param options - Formatting options
 * @returns Formatted relative time string
 */
export function formatRelativeTime(
  dateInput: string | Date,
  options: {
    includeTime?: boolean;
    capitalizeJustNow?: boolean;
  } = {}
): string {
  const { includeTime = false, capitalizeJustNow = false } = options;

  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return capitalizeJustNow ? 'Just now' : 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  if (includeTime) {
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a timestamp for short display (just now, Xm ago, then time)
 * Used for compact displays like health check timestamps.
 *
 * @param dateInput - ISO string or Date object
 * @returns Formatted short time string
 */
export function formatShortTime(dateInput: string | Date): string {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

/**
 * Format a date with full date and time
 * Used for detailed displays like user management.
 *
 * @param dateInput - ISO string or Date object
 * @returns Formatted date/time string
 */
export function formatDateTime(dateInput: string | Date): string {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format a date as a friendly relative date (today, yesterday, X days ago)
 * Used for embed lists and similar displays.
 *
 * @param dateInput - ISO string or Date object
 * @param options - Formatting options
 * @returns Formatted relative date string
 */
export function formatRelativeDate(
  dateInput: string | Date,
  options: { includeYear?: boolean } = {}
): string {
  const { includeYear = true } = options;

  if (!dateInput) return '';

  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;

  const dateOptions: Intl.DateTimeFormatOptions = {
    month: 'short',
    day: 'numeric',
  };
  if (includeYear) {
    dateOptions.year = 'numeric';
  }

  return date.toLocaleDateString(undefined, dateOptions);
}

// Aliases for backward compatibility with existing code
export const formatTimestamp = (dateInput: string | Date) =>
  formatRelativeTime(dateInput, { includeTime: true, capitalizeJustNow: true });

export const formatDate = (dateInput: string | Date) => formatRelativeTime(dateInput);
