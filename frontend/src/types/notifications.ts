/**
 * Notification types for the notification settings API
 */

// ==================== Core Types ====================

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
  | 'system_status'
  | 'cartographer_down'
  | 'cartographer_up';

export type NotificationPriority = 'low' | 'medium' | 'high' | 'critical';

export type NetworkNotificationType =
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

export type GlobalNotificationType = 'cartographer_up' | 'cartographer_down';

// Priority overrides for specific notification types (user customization)
export type NotificationTypePriorityOverrides = Partial<
  Record<NotificationType, NotificationPriority>
>;

// ==================== Config Types ====================

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

// ==================== Preferences Types ====================

export interface NotificationPreferences {
  network_id: string;
  network_name?: string;
  owner_user_id?: string;
  enabled: boolean;
  email: EmailConfig;
  discord: DiscordConfig;
  enabled_notification_types: NotificationType[];
  minimum_priority: NotificationPriority;
  notification_type_priorities?: NotificationTypePriorityOverrides;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  quiet_hours_bypass_priority?: NotificationPriority | null;
  timezone?: string;
  max_notifications_per_hour: number;
  created_at: string;
  updated_at: string;
}

export interface NetworkPreferences {
  user_id: string;
  network_id: string;
  email_enabled: boolean;
  discord_enabled: boolean;
  discord_user_id?: string;
  enabled_types: string[];
  type_priorities: Record<string, string>;
  minimum_priority: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  quiet_hours_timezone?: string;
  quiet_hours_bypass_priority?: string;
  created_at: string;
  updated_at: string;
}

export interface GlobalPreferences {
  user_id: string;
  email_enabled: boolean;
  discord_enabled: boolean;
  discord_user_id?: string;
  cartographer_up_enabled: boolean;
  cartographer_down_enabled: boolean;
  minimum_priority: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  quiet_hours_timezone?: string;
  quiet_hours_bypass_priority?: string;
  created_at: string;
  updated_at: string;
}

export interface GlobalUserPreferences {
  user_id: string;
  email_address?: string;
  cartographer_up_enabled: boolean;
  cartographer_down_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface GlobalUserPreferencesUpdate {
  email_address?: string;
  cartographer_up_enabled?: boolean;
  cartographer_down_enabled?: boolean;
}

// ==================== Service Status Types ====================

export interface NotificationServiceStatus {
  email_configured: boolean;
  discord_configured: boolean;
  discord_bot_connected: boolean;
  ml_model_status: {
    model_version: string;
    is_trained: boolean;
    is_online_learning: boolean;
    training_status: 'initializing' | 'online_learning';
    devices_tracked: number;
    anomalies_detected_total: number;
    anomalies_detected_24h: number;
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
  type: number; // Discord channel type: 0=text, 2=voice, etc.
}

export interface DiscordLinkInfo {
  linked: boolean;
  discord_id?: string;
  discord_username?: string;
  discord_avatar?: string;
}

// ==================== Stats Types ====================

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

// ==================== Scheduled Broadcast Types ====================

export type ScheduledBroadcastStatus = 'pending' | 'sent' | 'cancelled' | 'failed';

export interface ScheduledBroadcast {
  id: string;
  title: string;
  message: string;
  event_type: NotificationType;
  priority: NotificationPriority;
  network_id: string;
  scheduled_at: string;
  timezone?: string;
  created_at: string;
  created_by: string;
  status: ScheduledBroadcastStatus;
  sent_at?: string;
  users_notified: number;
  error_message?: string;
}

export interface ScheduledBroadcastUpdate {
  title?: string;
  message?: string;
  event_type?: NotificationType;
  priority?: NotificationPriority;
  scheduled_at?: string;
  timezone?: string;
}

export interface ScheduledBroadcastResponse {
  broadcasts: ScheduledBroadcast[];
  total_count: number;
}

// ==================== Anomaly Stats ====================

export interface AnomalyStats {
  devices_tracked: number;
  anomalies_detected_24h: number;
  is_trained: boolean;
  is_online_learning: boolean;
  training_status: 'initializing' | 'online_learning';
}

// ==================== Cartographer Status Types ====================

export interface CartographerStatusSubscription {
  subscribed: boolean;
  email_address?: string;
  email_enabled?: boolean;
  discord_enabled?: boolean;
  discord_user_id?: string;
  discord_guild_id?: string;
  discord_channel_id?: string;
  discord_delivery_method?: 'dm' | 'channel';
  cartographer_up_enabled?: boolean;
  cartographer_down_enabled?: boolean;
}
