/**
 * Application configuration
 *
 * API_BASE is derived from Vite's BASE_URL, which is set via VITE_BASE_PATH at build time.
 * - Self-hosted: "/" → API calls go to /api/...
 * - Cloud deployment: "/app/" → API calls go to /app/api/...
 */

// Get base URL, remove trailing slash for consistent path joining
export const API_BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '');

/**
 * Build a full API URL from a path
 * @param path API path (e.g., "/api/auth/login")
 * @returns Full URL with correct base (e.g., "/app/api/auth/login" in cloud)
 */
export function apiUrl(path: string): string {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${normalizedPath}`;
}
