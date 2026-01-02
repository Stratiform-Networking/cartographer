/**
 * Notification settings composable
 *
 * Manages notification preferences and orchestrates notification API calls.
 * For network owner/admin configuration of notification settings.
 */

import { ref } from 'vue';
import * as notificationsApi from '../api/notifications';
import { extractErrorMessage } from '../api/client';

// Re-export types for backwards compatibility
export type {
  NotificationPreferences,
  NotificationServiceStatus,
  DiscordBotInfo,
  DiscordGuild,
  DiscordChannel,
  TestNotificationResult,
  NotificationStats,
  NotificationType,
  NotificationPriority,
  ScheduledBroadcast,
  ScheduledBroadcastUpdate,
  ScheduledBroadcastResponse,
  GlobalUserPreferences,
  GlobalUserPreferencesUpdate,
  EmailConfig,
  DiscordConfig,
  ScheduledBroadcastStatus,
  NotificationTypePriorityOverrides,
} from '../types/notifications';

// Re-export UI constants for backwards compatibility
export { NOTIFICATION_TYPE_INFO, PRIORITY_INFO } from '../constants/notifications';

export function useNotifications(networkId?: string) {
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const currentNetworkId = ref<string | undefined>(networkId);

  // Set the network ID for subsequent calls
  function setNetworkId(id: string) {
    currentNetworkId.value = id;
  }

  // Get notification preferences for a network
  async function getPreferences(netId?: number) {
    const id = netId ?? currentNetworkId.value;
    if (!id) throw new Error('Network ID is required');

    isLoading.value = true;
    error.value = null;
    try {
      return await notificationsApi.getNetworkPreferences(id);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw new Error(error.value);
    } finally {
      isLoading.value = false;
    }
  }

  // Update notification preferences for a network
  async function updatePreferences(
    update: Partial<import('../types/notifications').NotificationPreferences>,
    netId?: number
  ) {
    const id = netId ?? currentNetworkId.value;
    if (!id) throw new Error('Network ID is required');

    error.value = null;
    try {
      return await notificationsApi.updateNetworkPreferences(id, update);
    } catch (e) {
      error.value = extractErrorMessage(e);
      throw new Error(error.value);
    }
  }

  // Get service status
  async function getServiceStatus() {
    return await notificationsApi.getServiceStatus();
  }

  // Get Discord bot info
  async function getDiscordBotInfo() {
    return await notificationsApi.getDiscordBotInfo();
  }

  // Get Discord guilds
  async function getDiscordGuilds() {
    return await notificationsApi.getDiscordGuilds();
  }

  // Get Discord channels for a guild
  async function getDiscordChannels(guildId: string) {
    return await notificationsApi.getDiscordChannels(guildId);
  }

  // Get Discord invite URL
  async function getDiscordInviteUrl() {
    return await notificationsApi.getDiscordInviteUrl();
  }

  // Send test notification for a network
  async function sendTestNotification(
    channel: 'email' | 'discord',
    message?: string,
    netId?: number
  ) {
    const id = netId ?? currentNetworkId.value;
    if (!id) throw new Error('Network ID is required');

    return await notificationsApi.sendTestNotification(id, channel, message);
  }

  // Get notification stats for a network
  async function getStats(netId?: number) {
    const id = netId ?? currentNetworkId.value;
    if (!id) throw new Error('Network ID is required');

    return await notificationsApi.getNotificationStats(id);
  }

  // Send broadcast notification (owner only, network-scoped)
  async function sendBroadcastNotification(
    networkIdParam: string,
    title: string,
    message: string,
    eventType: import('../types/notifications').NotificationType = 'scheduled_maintenance',
    priority: import('../types/notifications').NotificationPriority = 'medium'
  ) {
    return await notificationsApi.sendBroadcastNotification(
      networkIdParam,
      title,
      message,
      eventType,
      priority
    );
  }

  // Get scheduled broadcasts (owner only)
  async function getScheduledBroadcasts(includeCompleted = false) {
    return await notificationsApi.getScheduledBroadcasts(includeCompleted);
  }

  // Schedule a broadcast (owner only, network-scoped)
  async function scheduleBroadcast(
    networkIdParam: string,
    title: string,
    message: string,
    scheduledAt: Date,
    eventType: import('../types/notifications').NotificationType = 'scheduled_maintenance',
    priority: import('../types/notifications').NotificationPriority = 'medium',
    timezone?: string
  ) {
    return await notificationsApi.scheduleBroadcast(
      networkIdParam,
      title,
      message,
      scheduledAt,
      eventType,
      priority,
      timezone
    );
  }

  // Update a scheduled broadcast (owner only, only pending broadcasts)
  async function updateScheduledBroadcast(
    broadcastId: string,
    update: import('../types/notifications').ScheduledBroadcastUpdate
  ) {
    return await notificationsApi.updateScheduledBroadcast(broadcastId, update);
  }

  // Cancel a scheduled broadcast (owner only)
  async function cancelScheduledBroadcast(broadcastId: string) {
    await notificationsApi.cancelScheduledBroadcast(broadcastId);
  }

  // Delete a scheduled broadcast (owner only)
  async function deleteScheduledBroadcast(broadcastId: string) {
    await notificationsApi.deleteScheduledBroadcast(broadcastId);
  }

  // ==================== Silenced Devices ====================

  async function getSilencedDevices() {
    return await notificationsApi.getSilencedDevices();
  }

  async function setSilencedDevices(deviceIps: string[]) {
    await notificationsApi.setSilencedDevices(deviceIps);
  }

  async function silenceDevice(deviceIp: string) {
    await notificationsApi.silenceDevice(deviceIp);
  }

  async function unsilenceDevice(deviceIp: string) {
    await notificationsApi.unsilenceDevice(deviceIp);
  }

  async function isDeviceSilenced(deviceIp: string) {
    return await notificationsApi.isDeviceSilenced(deviceIp);
  }

  // Get global notification preferences (Cartographer Up/Down)
  async function getGlobalPreferences() {
    return await notificationsApi.getGlobalPreferences();
  }

  // Update global notification preferences (Cartographer Up/Down)
  async function updateGlobalPreferences(
    update: import('../types/notifications').GlobalUserPreferencesUpdate
  ) {
    return await notificationsApi.updateGlobalPreferences(update);
  }

  return {
    isLoading,
    error,
    currentNetworkId,
    setNetworkId,
    getPreferences,
    updatePreferences,
    getServiceStatus,
    getDiscordBotInfo,
    getDiscordGuilds,
    getDiscordChannels,
    getDiscordInviteUrl,
    sendTestNotification,
    getStats,
    sendBroadcastNotification,
    getScheduledBroadcasts,
    scheduleBroadcast,
    updateScheduledBroadcast,
    cancelScheduledBroadcast,
    deleteScheduledBroadcast,
    getSilencedDevices,
    setSilencedDevices,
    silenceDevice,
    unsilenceDevice,
    isDeviceSilenced,
    getGlobalPreferences,
    updateGlobalPreferences,
  };
}
