/**
 * User notifications composable
 *
 * Manages user-specific notification preferences.
 * For individual user configuration (not admin/owner settings).
 */

import { ref } from 'vue';
import * as notificationsApi from '../api/notifications';
import { extractErrorMessage } from '../api/client';

// Re-export types for backwards compatibility
export type {
  NetworkPreferences,
  GlobalPreferences,
  DiscordLinkInfo,
  NotificationPriority,
  NetworkNotificationType,
  GlobalNotificationType,
} from '../types/notifications';

export function useUserNotifications() {
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // Network preferences
  async function getNetworkPreferences(networkId: string) {
    isLoading.value = true;
    error.value = null;
    try {
      return await notificationsApi.getUserNetworkPreferences(networkId);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  async function updateNetworkPreferences(
    networkId: string,
    update: Partial<import('../types/notifications').NetworkPreferences>
  ) {
    error.value = null;
    try {
      return await notificationsApi.updateUserNetworkPreferences(networkId, update);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  async function deleteNetworkPreferences(networkId: string) {
    error.value = null;
    try {
      await notificationsApi.deleteUserNetworkPreferences(networkId);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  // Global preferences
  async function getGlobalPreferences() {
    isLoading.value = true;
    error.value = null;
    try {
      return await notificationsApi.getUserGlobalPreferences();
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  async function updateGlobalPreferences(
    update: Partial<import('../types/notifications').GlobalPreferences>
  ) {
    error.value = null;
    try {
      return await notificationsApi.updateUserGlobalPreferences(update);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  // Test notifications
  async function testNetworkNotification(networkId: string, channel: 'email' | 'discord') {
    error.value = null;
    try {
      return await notificationsApi.testUserNetworkNotification(networkId, channel);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  async function testGlobalNotification(channel: 'email' | 'discord') {
    error.value = null;
    try {
      return await notificationsApi.testUserGlobalNotification(channel);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  // Discord OAuth - Context-aware (per-network or global)
  async function initiateDiscordOAuth(
    contextType: 'network' | 'global' = 'global',
    networkId?: string
  ) {
    error.value = null;
    try {
      return await notificationsApi.initiateDiscordOAuth(contextType, networkId);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  async function getDiscordLink(contextType: 'network' | 'global' = 'global', networkId?: string) {
    error.value = null;
    try {
      return await notificationsApi.getDiscordLink(contextType, networkId);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  async function unlinkDiscord(contextType: 'network' | 'global' = 'global', networkId?: string) {
    error.value = null;
    try {
      await notificationsApi.unlinkDiscord(contextType, networkId);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  // Service status
  async function getServiceStatus() {
    try {
      return await notificationsApi.getServiceStatus();
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  // Anomaly stats (network only)
  async function getAnomalyStats(networkId: string) {
    try {
      return await notificationsApi.getAnomalyStats(networkId);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw e;
    }
  }

  return {
    isLoading,
    error,
    getNetworkPreferences,
    updateNetworkPreferences,
    deleteNetworkPreferences,
    getGlobalPreferences,
    updateGlobalPreferences,
    testNetworkNotification,
    testGlobalNotification,
    initiateDiscordOAuth,
    getDiscordLink,
    unlinkDiscord,
    getServiceStatus,
    getAnomalyStats,
  };
}
