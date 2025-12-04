/**
 * Composable for notification settings API
 */

import { ref } from 'vue';

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

  async function fetchApi<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = localStorage.getItem('auth_token');
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Request failed: ${response.status}`);
    }

    return response.json();
  }

  // Get notification preferences
  async function getPreferences(): Promise<NotificationPreferences> {
    isLoading.value = true;
    error.value = null;
    try {
      return await fetchApi<NotificationPreferences>('/preferences');
    } catch (e: any) {
      error.value = e.message;
      throw e;
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
      return await fetchApi<NotificationPreferences>('/preferences', {
        method: 'PUT',
        body: JSON.stringify(update),
      });
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  // Get service status
  async function getServiceStatus(): Promise<NotificationServiceStatus> {
    return fetchApi<NotificationServiceStatus>('/status');
  }

  // Get Discord bot info
  async function getDiscordBotInfo(): Promise<DiscordBotInfo> {
    return fetchApi<DiscordBotInfo>('/discord/info');
  }

  // Get Discord guilds
  async function getDiscordGuilds(): Promise<DiscordGuild[]> {
    const response = await fetchApi<{ guilds: DiscordGuild[] }>('/discord/guilds');
    return response.guilds;
  }

  // Get Discord channels for a guild
  async function getDiscordChannels(guildId: string): Promise<DiscordChannel[]> {
    const response = await fetchApi<{ channels: DiscordChannel[] }>(
      `/discord/guilds/${guildId}/channels`
    );
    return response.channels;
  }

  // Get Discord invite URL
  async function getDiscordInviteUrl(): Promise<string> {
    const response = await fetchApi<{ invite_url: string }>('/discord/invite-url');
    return response.invite_url;
  }

  // Send test notification
  async function sendTestNotification(
    channel: 'email' | 'discord',
    message?: string
  ): Promise<TestNotificationResult> {
    return fetchApi<TestNotificationResult>('/test', {
      method: 'POST',
      body: JSON.stringify({ channel, message }),
    });
  }

  // Get notification stats
  async function getStats(): Promise<NotificationStats> {
    return fetchApi<NotificationStats>('/stats');
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

