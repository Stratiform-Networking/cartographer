/**
 * Notifications API module
 *
 * All notification settings and management API calls.
 */

import client from './client';
import type {
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
  NetworkPreferences,
  GlobalPreferences,
  DiscordLinkInfo,
  AnomalyStats,
  CartographerStatusSubscription,
} from '../types/notifications';

// Re-export types for backwards compatibility (consumers should import from types/ directly)
export type { CartographerStatusSubscription, DiscordChannel } from '../types/notifications';

const API_BASE = '/api/notifications';

// ==================== Network Preferences (Owner/Admin) ====================

export async function getNetworkPreferences(
  networkId: number | string
): Promise<NotificationPreferences> {
  const response = await client.get<NotificationPreferences>(
    `${API_BASE}/networks/${networkId}/preferences`
  );
  return response.data;
}

export async function updateNetworkPreferences(
  networkId: number | string,
  update: Partial<NotificationPreferences>
): Promise<NotificationPreferences> {
  const response = await client.put<NotificationPreferences>(
    `${API_BASE}/networks/${networkId}/preferences`,
    update
  );
  return response.data;
}

// ==================== Service Status ====================

export async function getServiceStatus(): Promise<NotificationServiceStatus> {
  const response = await client.get<NotificationServiceStatus>(`${API_BASE}/status`);
  return response.data;
}

// ==================== Discord ====================

export async function getDiscordBotInfo(): Promise<DiscordBotInfo> {
  const response = await client.get<DiscordBotInfo>(`${API_BASE}/discord/info`);
  return response.data;
}

export async function getDiscordGuilds(): Promise<DiscordGuild[]> {
  const response = await client.get<{ guilds: DiscordGuild[] }>(`${API_BASE}/discord/guilds`);
  return response.data.guilds;
}

export async function getDiscordChannels(guildId: string): Promise<DiscordChannel[]> {
  const response = await client.get<{ channels: DiscordChannel[] }>(
    `${API_BASE}/discord/guilds/${guildId}/channels`
  );
  return response.data.channels;
}

export async function getDiscordInviteUrl(): Promise<string> {
  const response = await client.get<{ invite_url: string }>(`${API_BASE}/discord/invite-url`);
  return response.data.invite_url;
}

// ==================== Test Notifications ====================

export async function sendTestNotification(
  networkId: number | string,
  channel: 'email' | 'discord',
  message?: string
): Promise<TestNotificationResult> {
  const response = await client.post<TestNotificationResult>(
    `${API_BASE}/networks/${networkId}/test`,
    {
      channel,
      message,
    }
  );
  return response.data;
}

// ==================== Stats ====================

export async function getNotificationStats(networkId: number | string): Promise<NotificationStats> {
  const response = await client.get<NotificationStats>(`${API_BASE}/networks/${networkId}/stats`);
  return response.data;
}

// ==================== Broadcasts ====================

export async function sendBroadcastNotification(
  networkId: string,
  title: string,
  message: string,
  eventType: NotificationType = 'scheduled_maintenance',
  priority: NotificationPriority = 'medium'
): Promise<{ success: boolean; users_notified: number }> {
  const response = await client.post<{ success: boolean; users_notified: number }>(
    `${API_BASE}/broadcast`,
    {
      network_id: networkId,
      title,
      message,
      event_type: eventType,
      priority,
    }
  );
  return response.data;
}

export async function getScheduledBroadcasts(
  includeCompleted = false
): Promise<ScheduledBroadcastResponse> {
  const response = await client.get<ScheduledBroadcastResponse>(`${API_BASE}/scheduled`, {
    params: { include_completed: includeCompleted },
  });
  return response.data;
}

export async function scheduleBroadcast(
  networkId: string,
  title: string,
  message: string,
  scheduledAt: Date,
  eventType: NotificationType = 'scheduled_maintenance',
  priority: NotificationPriority = 'medium',
  timezone?: string
): Promise<ScheduledBroadcast> {
  const response = await client.post<ScheduledBroadcast>(`${API_BASE}/scheduled`, {
    network_id: networkId,
    title,
    message,
    event_type: eventType,
    priority,
    scheduled_at: scheduledAt.toISOString(),
    timezone: timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
  });
  return response.data;
}

export async function updateScheduledBroadcast(
  broadcastId: string,
  update: ScheduledBroadcastUpdate
): Promise<ScheduledBroadcast> {
  const response = await client.patch<ScheduledBroadcast>(
    `${API_BASE}/scheduled/${broadcastId}`,
    update
  );
  return response.data;
}

export async function cancelScheduledBroadcast(broadcastId: string): Promise<void> {
  await client.post(`${API_BASE}/scheduled/${broadcastId}/cancel`);
}

export async function deleteScheduledBroadcast(broadcastId: string): Promise<void> {
  await client.delete(`${API_BASE}/scheduled/${broadcastId}`);
}

// ==================== Silenced Devices ====================

export async function getSilencedDevices(): Promise<string[]> {
  const response = await client.get<{ devices: string[] }>(`${API_BASE}/silenced-devices`);
  return response.data.devices;
}

export async function setSilencedDevices(deviceIps: string[]): Promise<void> {
  await client.post(`${API_BASE}/silenced-devices`, deviceIps);
}

export async function silenceDevice(deviceIp: string): Promise<void> {
  await client.post(`${API_BASE}/silenced-devices/${encodeURIComponent(deviceIp)}`);
}

export async function unsilenceDevice(deviceIp: string): Promise<void> {
  await client.delete(`${API_BASE}/silenced-devices/${encodeURIComponent(deviceIp)}`);
}

export async function isDeviceSilenced(deviceIp: string): Promise<boolean> {
  const response = await client.get<{ silenced: boolean }>(
    `${API_BASE}/silenced-devices/${encodeURIComponent(deviceIp)}`
  );
  return response.data.silenced;
}

// ==================== Global Preferences ====================

export async function getGlobalPreferences(): Promise<GlobalUserPreferences> {
  const response = await client.get<GlobalUserPreferences>(`${API_BASE}/global/preferences`);
  return response.data;
}

export async function updateGlobalPreferences(
  update: GlobalUserPreferencesUpdate
): Promise<GlobalUserPreferences> {
  const response = await client.put<GlobalUserPreferences>(
    `${API_BASE}/global/preferences`,
    update
  );
  return response.data;
}

// ==================== User-Specific Preferences ====================

export async function getUserNetworkPreferences(networkId: string): Promise<NetworkPreferences> {
  const response = await client.get<NetworkPreferences>(
    `${API_BASE}/users/me/networks/${networkId}/preferences`
  );
  return response.data;
}

export async function updateUserNetworkPreferences(
  networkId: string,
  update: Partial<NetworkPreferences>
): Promise<NetworkPreferences> {
  const response = await client.put<NetworkPreferences>(
    `${API_BASE}/users/me/networks/${networkId}/preferences`,
    update
  );
  return response.data;
}

export async function deleteUserNetworkPreferences(networkId: string): Promise<void> {
  await client.delete(`${API_BASE}/users/me/networks/${networkId}/preferences`);
}

export async function getUserGlobalPreferences(): Promise<GlobalPreferences> {
  const response = await client.get<GlobalPreferences>(`${API_BASE}/users/me/global/preferences`);
  return response.data;
}

export async function updateUserGlobalPreferences(
  update: Partial<GlobalPreferences>
): Promise<GlobalPreferences> {
  const response = await client.put<GlobalPreferences>(
    `${API_BASE}/users/me/global/preferences`,
    update
  );
  return response.data;
}

// ==================== User Test Notifications ====================

export async function testUserNetworkNotification(
  networkId: string,
  channel: 'email' | 'discord'
): Promise<{ success: boolean; message: string; error?: string }> {
  const response = await client.post(`${API_BASE}/users/me/networks/${networkId}/test`, {
    channel,
  });
  return response.data;
}

export async function testUserGlobalNotification(
  channel: 'email' | 'discord'
): Promise<{ success: boolean; message: string; error?: string }> {
  const response = await client.post(`${API_BASE}/users/me/global/test`, { channel });
  return response.data;
}

// ==================== Discord OAuth ====================

export async function initiateDiscordOAuth(
  contextType: 'network' | 'global' = 'global',
  networkId?: string
): Promise<{ authorization_url: string }> {
  const params: Record<string, string> = { context_type: contextType };
  if (contextType === 'network' && networkId !== undefined) {
    params.network_id = networkId;
  }
  const response = await client.get<{ authorization_url: string }>(
    `${API_BASE}/auth/discord/link`,
    {
      params,
    }
  );
  return response.data;
}

export async function getDiscordLink(
  contextType: 'network' | 'global' = 'global',
  networkId?: string
): Promise<DiscordLinkInfo> {
  const params: Record<string, string> = { context_type: contextType };
  if (contextType === 'network' && networkId !== undefined) {
    params.network_id = networkId;
  }
  const response = await client.get<DiscordLinkInfo>(`${API_BASE}/users/me/discord`, { params });
  return response.data;
}

export async function unlinkDiscord(
  contextType: 'network' | 'global' = 'global',
  networkId?: string
): Promise<void> {
  const params: Record<string, string> = { context_type: contextType };
  if (contextType === 'network' && networkId !== undefined) {
    params.network_id = networkId;
  }
  await client.delete(`${API_BASE}/users/me/discord/link`, { params });
}

// ==================== Anomaly Stats ====================

export async function getAnomalyStats(networkId: string): Promise<AnomalyStats> {
  const response = await client.get(`${API_BASE}/ml/status`, {
    params: { network_id: networkId },
  });
  return {
    devices_tracked: response.data.devices_tracked || 0,
    anomalies_detected_24h: response.data.anomalies_detected_24h || 0,
    is_trained: response.data.is_trained || false,
    is_online_learning: response.data.is_online_learning || false,
    training_status: response.data.training_status || 'initializing',
  };
}

// ==================== Version Notifications ====================

export async function triggerVersionNotification(): Promise<{
  success: boolean;
  users_notified?: number;
  error?: string;
}> {
  const response = await client.post('/api/notifications/version/notify');
  return response.data;
}

// ==================== Cartographer Status ====================

export async function getCartographerStatusSubscription(): Promise<CartographerStatusSubscription> {
  const response = await client.get(`${API_BASE}/cartographer-status/subscription`);
  return response.data;
}

export async function createCartographerStatusSubscription(data: {
  email_address?: string;
  cartographer_up_enabled?: boolean;
  cartographer_down_enabled?: boolean;
}): Promise<CartographerStatusSubscription> {
  const response = await client.post(`${API_BASE}/cartographer-status/subscription`, data);
  return response.data;
}

export async function updateCartographerStatusSubscription(
  data: Partial<{
    email_address: string;
    email_enabled: boolean;
    discord_enabled: boolean;
    discord_delivery_method: 'dm' | 'channel';
    discord_guild_id: string;
    discord_channel_id: string;
    cartographer_up_enabled: boolean;
    cartographer_down_enabled: boolean;
  }>
): Promise<CartographerStatusSubscription> {
  const response = await client.put(`${API_BASE}/cartographer-status/subscription`, data);
  return response.data;
}

export async function deleteCartographerStatusSubscription(): Promise<void> {
  await client.delete(`${API_BASE}/cartographer-status/subscription`);
}

export async function testCartographerStatusNotification(target: {
  channel_id?: string;
  user_id?: string;
}): Promise<void> {
  await client.post(`${API_BASE}/cartographer-status/test/discord`, target);
}

// ==================== Discord Channels ====================

export async function getDiscordGuildChannels(
  guildId: string
): Promise<{ channels: DiscordChannel[] }> {
  const response = await client.get(`${API_BASE}/discord/guilds/${guildId}/channels`);
  return response.data;
}

// ==================== Scheduled Broadcasts ====================

export async function markBroadcastAsSeen(
  broadcastId: string
): Promise<{ seen_at: string | null }> {
  const response = await client.post(`${API_BASE}/scheduled/${broadcastId}/seen`);
  return response.data;
}

// ==================== Send Network Notification ====================

export async function sendNetworkNotification(
  networkId: string,
  data: {
    title: string;
    message: string;
    type: string;
    priority: string;
    delivery_channels?: string[];
  }
): Promise<void> {
  await client.post(`${API_BASE}/networks/${networkId}/send`, data);
}

// ==================== User Profile ====================

export async function getUserProfile(): Promise<{ email?: string }> {
  const response = await client.get('/api/user/profile');
  return response.data;
}
