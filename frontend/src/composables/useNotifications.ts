/**
 * Composable for notification settings API
 */

import { ref } from 'vue';
import axios from 'axios';

// Types
export interface EmailConfig {
  enabled: boolean;
  email_address: string;
}

export interface DiscordChannelConfig {
  guild_id: string;
  channel_id: string;
  guild_name?: string;
  channel_name?: string;
}

export interface DiscordConfig {
  enabled: boolean;
  delivery_method: 'channel' | 'dm';
  discord_user_id?: string;
  channel_config?: DiscordChannelConfig;
}

export type NotificationType = 
  | 'device_offline'
  | 'device_online'
  | 'device_degraded'
  | 'anomaly_detected'
  | 'high_latency'
  | 'packet_loss'
  | 'isp_issue'
  | 'security_alert'
  | 'scheduled_maintenance'
  | 'system_status';

export type NotificationPriority = 'low' | 'medium' | 'high' | 'critical';

export interface NotificationPreferences {
  user_id: string;
  enabled: boolean;
  email: EmailConfig;
  discord: DiscordConfig;
  enabled_notification_types: NotificationType[];
  minimum_priority: NotificationPriority;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  max_notifications_per_hour: number;
  created_at: string;
  updated_at: string;
}

export interface NotificationServiceStatus {
  email_configured: boolean;
  discord_configured: boolean;
  discord_bot_connected: boolean;
  ml_model_status: {
    model_version: string;
    is_trained: boolean;
    devices_tracked: number;
    anomalies_detected_total: number;
  };
}

export interface DiscordBotInfo {
  bot_name: string;
  bot_id?: string;
  invite_url?: string;
  is_connected: boolean;
  connected_guilds: number;
}

export interface DiscordGuild {
  id: string;
  name: string;
  icon_url?: string;
  member_count?: number;
}

export interface DiscordChannel {
  id: string;
  name: string;
  type: string;
}

export interface NotificationStats {
  total_sent_24h: number;
  total_sent_7d: number;
  by_channel: Record<string, number>;
  by_type: Record<string, number>;
  success_rate: number;
  anomalies_detected_24h: number;
}

export interface TestNotificationResult {
  success: boolean;
  channel: string;
  message: string;
  error?: string;
}

const API_BASE = '/api/notifications';

export function useNotifications() {
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // Get notification preferences
  async function getPreferences(): Promise<NotificationPreferences> {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.get<NotificationPreferences>(`${API_BASE}/preferences`);
      return response.data;
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message;
      throw new Error(error.value || 'Failed to get preferences');
    } finally {
      isLoading.value = false;
    }
  }

  // Update notification preferences
  async function updatePreferences(
    update: Partial<NotificationPreferences>
  ): Promise<NotificationPreferences> {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.put<NotificationPreferences>(`${API_BASE}/preferences`, update);
      return response.data;
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message;
      throw new Error(error.value || 'Failed to update preferences');
    } finally {
      isLoading.value = false;
    }
  }

  // Get service status
  async function getServiceStatus(): Promise<NotificationServiceStatus> {
    const response = await axios.get<NotificationServiceStatus>(`${API_BASE}/status`);
    return response.data;
  }

  // Get Discord bot info
  async function getDiscordBotInfo(): Promise<DiscordBotInfo> {
    const response = await axios.get<DiscordBotInfo>(`${API_BASE}/discord/info`);
    return response.data;
  }

  // Get Discord guilds
  async function getDiscordGuilds(): Promise<DiscordGuild[]> {
    const response = await axios.get<{ guilds: DiscordGuild[] }>(`${API_BASE}/discord/guilds`);
    return response.data.guilds;
  }

  // Get Discord channels for a guild
  async function getDiscordChannels(guildId: string): Promise<DiscordChannel[]> {
    const response = await axios.get<{ channels: DiscordChannel[] }>(
      `${API_BASE}/discord/guilds/${guildId}/channels`
    );
    return response.data.channels;
  }

  // Get Discord invite URL
  async function getDiscordInviteUrl(): Promise<string> {
    const response = await axios.get<{ invite_url: string }>(`${API_BASE}/discord/invite-url`);
    return response.data.invite_url;
  }

  // Send test notification
  async function sendTestNotification(
    channel: 'email' | 'discord',
    message?: string
  ): Promise<TestNotificationResult> {
    const response = await axios.post<TestNotificationResult>(`${API_BASE}/test`, { channel, message });
    return response.data;
  }

  // Get notification stats
  async function getStats(): Promise<NotificationStats> {
    const response = await axios.get<NotificationStats>(`${API_BASE}/stats`);
    return response.data;
  }

  // Send broadcast notification (owner only)
  async function sendBroadcastNotification(
    title: string,
    message: string,
    eventType: NotificationType = 'scheduled_maintenance',
    priority: NotificationPriority = 'medium'
  ): Promise<{ success: boolean; users_notified: number }> {
    const response = await axios.post<{ success: boolean; users_notified: number }>(
      `${API_BASE}/broadcast`,
      {
        title,
        message,
        event_type: eventType,
        priority,
      }
    );
    return response.data;
  }

  return {
    isLoading,
    error,
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
  };
}

// Notification type labels and icons
export const NOTIFICATION_TYPE_INFO: Record<NotificationType, { label: string; icon: string; description: string }> = {
  device_offline: { 
    label: 'Device Offline', 
    icon: '🔴', 
    description: 'When a device stops responding' 
  },
  device_online: { 
    label: 'Device Online', 
    icon: '🟢', 
    description: 'When a device comes back online' 
  },
  device_degraded: { 
    label: 'Device Degraded', 
    icon: '🟡', 
    description: 'When a device has degraded performance' 
  },
  anomaly_detected: { 
    label: 'Anomaly Detected', 
    icon: '⚠️', 
    description: 'ML-detected unusual behavior' 
  },
  high_latency: { 
    label: 'High Latency', 
    icon: '🐌', 
    description: 'Unusual latency spikes' 
  },
  packet_loss: { 
    label: 'Packet Loss', 
    icon: '📉', 
    description: 'Significant packet loss' 
  },
  isp_issue: { 
    label: 'ISP Issue', 
    icon: '🌐', 
    description: 'Internet connectivity problems' 
  },
  security_alert: { 
    label: 'Security Alert', 
    icon: '🔒', 
    description: 'Security-related notifications' 
  },
  scheduled_maintenance: { 
    label: 'Maintenance', 
    icon: '🔧', 
    description: 'Planned maintenance notices' 
  },
  system_status: { 
    label: 'System Status', 
    icon: 'ℹ️', 
    description: 'General system updates' 
  },
};

export const PRIORITY_INFO: Record<NotificationPriority, { label: string; color: string }> = {
  low: { label: 'Low', color: 'slate' },
  medium: { label: 'Medium', color: 'amber' },
  high: { label: 'High', color: 'orange' },
  critical: { label: 'Critical', color: 'red' },
};

