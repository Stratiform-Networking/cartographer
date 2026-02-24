/**
 * Notification UI constants
 *
 * Labels, icons, and display information for notification types.
 * These are UI concerns and should not be in composables or types.
 */

import type { NotificationType, NotificationPriority } from '../types/notifications';

export interface NotificationTypeInfo {
  label: string;
  icon: string;
  description: string;
  defaultPriority: NotificationPriority;
}

export const NOTIFICATION_TYPE_INFO: Record<NotificationType, NotificationTypeInfo> = {
  device_offline: {
    label: 'Device Offline',
    icon: '🔴',
    description: 'When a device stops responding',
    defaultPriority: 'high',
  },
  device_online: {
    label: 'Device Online',
    icon: '🟢',
    description: 'When a device comes back online',
    defaultPriority: 'low',
  },
  device_degraded: {
    label: 'Device Degraded',
    icon: '🟡',
    description: 'When a device has degraded performance',
    defaultPriority: 'medium',
  },
  anomaly_detected: {
    label: 'Anomaly Detected',
    icon: '⚠️',
    description: 'ML-detected unusual behavior',
    defaultPriority: 'high',
  },
  high_latency: {
    label: 'High Latency',
    icon: '🐌',
    description: 'Unusual latency spikes',
    defaultPriority: 'medium',
  },
  packet_loss: {
    label: 'Packet Loss',
    icon: '📉',
    description: 'Significant packet loss',
    defaultPriority: 'medium',
  },
  isp_issue: {
    label: 'ISP Issue',
    icon: '🌐',
    description: 'Internet connectivity problems',
    defaultPriority: 'high',
  },
  security_alert: {
    label: 'Security Alert',
    icon: '🔒',
    description: 'Security-related notifications',
    defaultPriority: 'critical',
  },
  scheduled_maintenance: {
    label: 'Maintenance',
    icon: '🔧',
    description: 'Planned maintenance notices',
    defaultPriority: 'low',
  },
  system_status: {
    label: 'System Status',
    icon: 'ℹ️',
    description: 'General system updates',
    defaultPriority: 'low',
  },
  cartographer_down: {
    label: 'Cartographer Down',
    icon: '🚨',
    description: 'When Cartographer service goes offline',
    defaultPriority: 'critical',
  },
  cartographer_up: {
    label: 'Cartographer Up',
    icon: '✅',
    description: 'When Cartographer service comes back online',
    defaultPriority: 'medium',
  },
  mass_outage: {
    label: 'Mass Outage',
    icon: '💥',
    description: 'Multiple devices offline',
    defaultPriority: 'critical',
  },
  mass_recovery: {
    label: 'Mass Recovery',
    icon: '🔄',
    description: 'Multiple devices back online',
    defaultPriority: 'medium',
  },
  device_added: {
    label: 'Device Added',
    icon: '➕',
    description: 'When a new discovered device is added to the network',
    defaultPriority: 'high',
  },
  device_removed: {
    label: 'Device Removed',
    icon: '➖',
    description: 'When a device is manually removed from the network map',
    defaultPriority: 'high',
  },
};

export interface PriorityInfo {
  label: string;
  color: string;
}

export const PRIORITY_INFO: Record<NotificationPriority, PriorityInfo> = {
  low: { label: 'Low', color: 'emerald' },
  medium: { label: 'Medium', color: 'amber' },
  high: { label: 'High', color: 'orange' },
  critical: { label: 'Critical', color: 'red' },
};
