/**
 * Dark Mode composable
 *
 * Manages dark mode state with localStorage persistence for immediate load
 * and server sync for cross-device preferences.
 */

import { ref, readonly, watch } from 'vue';
import { useAuth } from './useAuth';
import client from '../api/client';

const STORAGE_KEY = 'cartographer_darkMode';
const SYNC_DEBOUNCE_MS = 1000;

// Shared reactive state (singleton pattern)
const isDark = ref(false);
const isInitialized = ref(false);

// Debounce timer for server sync
let syncTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * Initialize dark mode from localStorage immediately (before any async calls).
 * This ensures the correct theme is applied on first paint.
 */
function initFromLocalStorage(): void {
  if (isInitialized.value) return;

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'true') {
      isDark.value = true;
      document.documentElement.classList.add('dark');
    } else if (stored === 'false') {
      isDark.value = false;
      document.documentElement.classList.remove('dark');
    } else {
      // No stored preference - use system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      isDark.value = prefersDark;
      if (prefersDark) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
  } catch (e) {
    console.warn('[DarkMode] Failed to read from localStorage:', e);
  }

  isInitialized.value = true;
}

/**
 * Apply dark mode state to DOM and localStorage.
 */
function applyDarkMode(dark: boolean): void {
  isDark.value = dark;

  if (dark) {
    document.documentElement.classList.add('dark');
    localStorage.setItem(STORAGE_KEY, 'true');
  } else {
    document.documentElement.classList.remove('dark');
    localStorage.setItem(STORAGE_KEY, 'false');
  }
}

/**
 * Toggle dark mode.
 */
function toggleDarkMode(): void {
  applyDarkMode(!isDark.value);
}

/**
 * Set dark mode explicitly.
 */
function setDarkMode(dark: boolean): void {
  applyDarkMode(dark);
}

/**
 * Sync preferences to server (debounced).
 */
async function syncToServer(): Promise<void> {
  // Cancel any pending sync
  if (syncTimer) {
    clearTimeout(syncTimer);
  }

  syncTimer = setTimeout(async () => {
    try {
      await client.patch('/api/auth/me/preferences', {
        dark_mode: isDark.value,
      });
      console.log('[DarkMode] Synced to server:', isDark.value);
    } catch (e) {
      // Don't fail loudly - localStorage is the primary store
      console.warn('[DarkMode] Failed to sync to server:', e);
    }
  }, SYNC_DEBOUNCE_MS);
}

/**
 * Fetch preferences from server and apply.
 * Call this after authentication to sync cross-device preferences.
 */
async function syncFromServer(): Promise<void> {
  try {
    const response = await client.get<{ dark_mode?: boolean }>('/api/auth/me/preferences');
    const serverDarkMode = response.data?.dark_mode;

    if (typeof serverDarkMode === 'boolean') {
      // Server has a preference - apply it
      applyDarkMode(serverDarkMode);
      console.log('[DarkMode] Synced from server:', serverDarkMode);
    }
    // If server has no preference, keep localStorage/system default
  } catch (e) {
    // Don't fail loudly - localStorage is the primary store
    console.warn('[DarkMode] Failed to sync from server:', e);
  }
}

export function useDarkMode() {
  // Initialize immediately on first use
  if (!isInitialized.value) {
    initFromLocalStorage();
  }

  const { isAuthenticated } = useAuth();

  // Watch for toggle and sync to server when authenticated
  watch(isDark, (newValue, oldValue) => {
    if (oldValue !== undefined && isAuthenticated.value) {
      syncToServer();
    }
  });

  return {
    // State (readonly)
    isDark: readonly(isDark),
    isInitialized: readonly(isInitialized),

    // Actions
    toggleDarkMode,
    setDarkMode,
    syncFromServer,
    syncToServer,

    // Manual init (for app entry point)
    initFromLocalStorage,
  };
}
