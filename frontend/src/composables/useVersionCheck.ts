/**
 * Version check composable
 *
 * Manages version checking and update notifications.
 */

import { ref, computed, readonly, onMounted, onUnmounted } from 'vue';
import * as notificationsApi from '../api/notifications';
import { extractErrorMessage } from '../api/client';
import type { VersionType, VersionPreferences, VersionInfo } from '../types/version';

// Re-export types for backwards compatibility
export type { VersionType, VersionPreferences, VersionInfo } from '../types/version';

const VERSION_PREFS_KEY = 'cartographer_version_prefs';
const GITHUB_REPO = 'DevArtech/cartographer';
const GITHUB_COMMITS_API = `https://api.github.com/repos/${GITHUB_REPO}/commits/main`;
const GITHUB_CONTENTS_API = `https://api.github.com/repos/${GITHUB_REPO}/contents/VERSION`;
const CHANGELOG_URL = `https://github.com/${GITHUB_REPO}/blob/main/CHANGELOG.md`;
const CHECK_INTERVAL = 1000 * 60 * 60; // Check every hour

// Current app version (injected at build time via vite.config.ts)
const CURRENT_VERSION = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.1.1';

// Reactive state
const latestVersion = ref<string | null>(null);
const isChecking = ref(false);
const lastError = ref<string | null>(null);
const preferences = ref<VersionPreferences>({
  enabledTypes: ['major', 'minor'], // Default: major and minor only
  dismissed: [],
  lastChecked: 0,
});

let checkInterval: ReturnType<typeof setInterval> | null = null;

// Parse version string into components
function parseVersion(version: string): { major: number; minor: number; patch: number } | null {
  const match = version.trim().match(/^v?(\d+)\.(\d+)\.(\d+)/);
  if (!match) return null;
  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10),
  };
}

// Compare two versions and determine the type of update
function compareVersions(
  current: string,
  latest: string
): { hasUpdate: boolean; type: VersionType | null } {
  const currentParsed = parseVersion(current);
  const latestParsed = parseVersion(latest);

  if (!currentParsed || !latestParsed) {
    return { hasUpdate: false, type: null };
  }

  if (latestParsed.major > currentParsed.major) {
    return { hasUpdate: true, type: 'major' };
  }
  if (latestParsed.major === currentParsed.major && latestParsed.minor > currentParsed.minor) {
    return { hasUpdate: true, type: 'minor' };
  }
  if (
    latestParsed.major === currentParsed.major &&
    latestParsed.minor === currentParsed.minor &&
    latestParsed.patch > currentParsed.patch
  ) {
    return { hasUpdate: true, type: 'patch' };
  }

  return { hasUpdate: false, type: null };
}

// Load preferences from localStorage
function loadPreferences(): void {
  try {
    const stored = localStorage.getItem(VERSION_PREFS_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as Partial<VersionPreferences>;
      preferences.value = {
        enabledTypes: parsed.enabledTypes ?? ['major', 'minor'],
        dismissed: parsed.dismissed ?? [],
        lastChecked: parsed.lastChecked ?? 0,
      };
    }
  } catch (e) {
    console.warn('[VersionCheck] Failed to load preferences:', e);
  }
}

// Save preferences to localStorage
function savePreferences(): void {
  try {
    localStorage.setItem(VERSION_PREFS_KEY, JSON.stringify(preferences.value));
  } catch (e) {
    console.warn('[VersionCheck] Failed to save preferences:', e);
  }
}

// Fetch latest version from GitHub API
async function checkForUpdates(): Promise<void> {
  if (isChecking.value) return;

  isChecking.value = true;
  lastError.value = null;

  try {
    // Step 1: Get the latest commit SHA on main branch
    const commitResponse = await fetch(GITHUB_COMMITS_API, {
      cache: 'no-store',
      headers: {
        Accept: 'application/vnd.github.v3+json',
      },
    });

    if (!commitResponse.ok) {
      throw new Error(`Failed to fetch latest commit: HTTP ${commitResponse.status}`);
    }

    const commitData = await commitResponse.json();
    const latestSha = commitData.sha;

    console.log('[VersionCheck] Latest commit SHA:', latestSha.substring(0, 7));

    // Step 2: Fetch VERSION file at this specific SHA
    const versionResponse = await fetch(`${GITHUB_CONTENTS_API}?ref=${latestSha}`, {
      cache: 'no-store',
      headers: {
        Accept: 'application/vnd.github.v3+json',
      },
    });

    if (!versionResponse.ok) {
      throw new Error(`Failed to fetch VERSION file: HTTP ${versionResponse.status}`);
    }

    const versionData = await versionResponse.json();

    // GitHub API returns base64 encoded content
    const versionText = atob(versionData.content).trim();
    latestVersion.value = versionText;
    preferences.value.lastChecked = Date.now();
    savePreferences();

    console.log(
      '[VersionCheck] Latest version:',
      latestVersion.value,
      `(from commit ${latestSha.substring(0, 7)})`
    );
  } catch (e: unknown) {
    lastError.value = e instanceof Error ? e.message : 'Failed to check for updates';
    console.warn('[VersionCheck] Failed to fetch version:', e);
  } finally {
    isChecking.value = false;
  }
}

// Computed: version info
const versionInfo = computed<VersionInfo>(() => {
  const latest = latestVersion.value;
  if (!latest) {
    return {
      current: CURRENT_VERSION,
      latest: CURRENT_VERSION,
      updateAvailable: false,
      updateType: null,
    };
  }

  const comparison = compareVersions(CURRENT_VERSION, latest);
  return {
    current: CURRENT_VERSION,
    latest,
    updateAvailable: comparison.hasUpdate,
    updateType: comparison.type,
  };
});

// Computed: should show banner
const shouldShowBanner = computed<boolean>(() => {
  const info = versionInfo.value;

  // No update available
  if (!info.updateAvailable || !info.updateType) {
    return false;
  }

  // Check if this version type is enabled
  if (!preferences.value.enabledTypes.includes(info.updateType)) {
    return false;
  }

  // Check if this version was dismissed
  if (preferences.value.dismissed.includes(info.latest)) {
    return false;
  }

  return true;
});

// Dismiss the current update notification
function dismissUpdate(): void {
  const latest = latestVersion.value;
  if (latest && !preferences.value.dismissed.includes(latest)) {
    preferences.value.dismissed.push(latest);
    savePreferences();
  }
}

// Update enabled notification types
function setEnabledTypes(types: VersionType[]): void {
  preferences.value.enabledTypes = types;
  savePreferences();
}

// Toggle a specific version type
function toggleVersionType(type: VersionType): void {
  const index = preferences.value.enabledTypes.indexOf(type);
  if (index === -1) {
    preferences.value.enabledTypes.push(type);
  } else {
    preferences.value.enabledTypes.splice(index, 1);
  }
  savePreferences();
}

// Check if a version type is enabled
function isTypeEnabled(type: VersionType): boolean {
  return preferences.value.enabledTypes.includes(type);
}

// Clear dismissed versions
function clearDismissed(): void {
  preferences.value.dismissed = [];
  savePreferences();
}

// Undismiss a specific version
function undismissVersion(version: string): void {
  const index = preferences.value.dismissed.indexOf(version);
  if (index !== -1) {
    preferences.value.dismissed.splice(index, 1);
    savePreferences();
  }
}

// Force show banner for current update
function forceShowBanner(): void {
  const latest = latestVersion.value;
  if (latest) {
    undismissVersion(latest);
  }
}

// Trigger backend notification for version update
async function triggerBackendNotification(): Promise<{
  success: boolean;
  users_notified?: number;
  error?: string;
}> {
  try {
    const result = await notificationsApi.triggerVersionNotification();
    console.log('[VersionCheck] Backend notification triggered:', result);
    return result;
  } catch (e: unknown) {
    const errorMessage = extractErrorMessage(e);
    console.error('[VersionCheck] Failed to trigger backend notification:', errorMessage);
    return { success: false, error: errorMessage };
  }
}

// Start periodic version checks
function startPeriodicChecks(): void {
  if (checkInterval) return;

  // Check immediately if it's been a while since last check
  const timeSinceLastCheck = Date.now() - preferences.value.lastChecked;
  if (timeSinceLastCheck > CHECK_INTERVAL) {
    checkForUpdates();
  }

  // Set up periodic checks
  checkInterval = setInterval(() => {
    checkForUpdates();
  }, CHECK_INTERVAL);
}

// Stop periodic version checks
function stopPeriodicChecks(): void {
  if (checkInterval) {
    clearInterval(checkInterval);
    checkInterval = null;
  }
}

// Get user-friendly update type label
function getUpdateTypeLabel(type: VersionType | null): string {
  switch (type) {
    case 'major':
      return 'Major Update';
    case 'minor':
      return 'New Features';
    case 'patch':
      return 'Bug Fixes';
    default:
      return 'Update';
  }
}

// Get update type description
function getUpdateTypeDescription(type: VersionType | null): string {
  switch (type) {
    case 'major':
      return 'This is a major release with significant changes';
    case 'minor':
      return 'New features and improvements are available';
    case 'patch':
      return 'Bug fixes and minor improvements';
    default:
      return 'A new version is available';
  }
}

// Main composable export
export function useVersionCheck() {
  // Initialize on first use
  loadPreferences();

  // Set up lifecycle hooks when used in a component
  onMounted(() => {
    startPeriodicChecks();
  });

  onUnmounted(() => {
    stopPeriodicChecks();
  });

  return {
    // State (readonly)
    latestVersion: readonly(latestVersion),
    isChecking: readonly(isChecking),
    lastError: readonly(lastError),
    preferences: readonly(preferences),

    // Computed
    versionInfo,
    shouldShowBanner,

    // Constants
    CHANGELOG_URL,
    CURRENT_VERSION,

    // Actions
    checkForUpdates,
    dismissUpdate,
    setEnabledTypes,
    toggleVersionType,
    isTypeEnabled,
    clearDismissed,
    undismissVersion,
    forceShowBanner,
    triggerBackendNotification,
    startPeriodicChecks,
    stopPeriodicChecks,

    // Helpers
    getUpdateTypeLabel,
    getUpdateTypeDescription,
  };
}
