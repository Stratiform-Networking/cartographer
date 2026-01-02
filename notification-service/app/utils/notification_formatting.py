"""
Shared notification formatting utilities.

Provides consistent icons and colors for notifications across all channels.
"""

from ..models import NotificationPriority, NotificationType


def get_priority_color_hex(priority: NotificationPriority) -> str:
    """
    Get hex color string for priority level.
    Used for email templates.
    """
    colors = {
        NotificationPriority.LOW: "#64748b",  # slate
        NotificationPriority.MEDIUM: "#f59e0b",  # amber
        NotificationPriority.HIGH: "#f97316",  # orange
        NotificationPriority.CRITICAL: "#ef4444",  # red
    }
    return colors.get(priority, "#64748b")


def get_priority_color_discord(priority: NotificationPriority) -> int:
    """
    Get Discord embed color (integer) for priority level.
    Used for Discord embed messages.
    """
    colors = {
        NotificationPriority.LOW: 0x64748B,  # slate
        NotificationPriority.MEDIUM: 0xF59E0B,  # amber
        NotificationPriority.HIGH: 0xF97316,  # orange
        NotificationPriority.CRITICAL: 0xEF4444,  # red
    }
    return colors.get(priority, 0x64748B)


def get_notification_icon(event_type: NotificationType) -> str:
    """
    Get emoji icon for notification type.
    Used across all notification channels.
    """
    icons = {
        NotificationType.DEVICE_OFFLINE: "🔴",
        NotificationType.DEVICE_ONLINE: "🟢",
        NotificationType.DEVICE_DEGRADED: "🟡",
        NotificationType.ANOMALY_DETECTED: "⚠️",
        NotificationType.HIGH_LATENCY: "🐌",
        NotificationType.PACKET_LOSS: "📉",
        NotificationType.ISP_ISSUE: "🌐",
        NotificationType.SECURITY_ALERT: "🔒",
        NotificationType.SCHEDULED_MAINTENANCE: "🔧",
        NotificationType.SYSTEM_STATUS: "ℹ️",
        NotificationType.CARTOGRAPHER_UP: "🟢",
        NotificationType.CARTOGRAPHER_DOWN: "🔴",
    }
    return icons.get(event_type, "📢")
