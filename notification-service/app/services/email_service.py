"""
Email notification service using Resend.

Sends notification emails for network events and anomalies.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..models import (
    NetworkEvent,
    NotificationType,
    NotificationPriority,
    NotificationRecord,
    NotificationChannel,
)

logger = logging.getLogger(__name__)

# Resend configuration
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Cartographer <notifications@cartographer.app>")
APPLICATION_URL = os.environ.get("APPLICATION_URL", "http://localhost:5173")

# Lazy load resend module
_resend = None


def _get_resend():
    """Lazy load resend module"""
    global _resend
    if _resend is None:
        try:
            import resend
            if RESEND_API_KEY:
                resend.api_key = RESEND_API_KEY
            _resend = resend
        except ImportError:
            logger.warning("Resend module not installed")
            return None
    return _resend


def is_email_configured() -> bool:
    """Check if email sending is configured"""
    return bool(RESEND_API_KEY)


def _get_priority_color(priority: NotificationPriority) -> str:
    """Get color for priority level"""
    colors = {
        NotificationPriority.LOW: "#64748b",  # slate
        NotificationPriority.MEDIUM: "#f59e0b",  # amber
        NotificationPriority.HIGH: "#f97316",  # orange
        NotificationPriority.CRITICAL: "#ef4444",  # red
    }
    return colors.get(priority, "#64748b")


def _get_notification_icon(event_type: NotificationType) -> str:
    """Get emoji icon for notification type"""
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
    }
    return icons.get(event_type, "📢")


def _build_notification_email_html(event: NetworkEvent) -> str:
    """Build HTML email content for a network event notification"""
    icon = _get_notification_icon(event.event_type)
    priority_color = _get_priority_color(event.priority)
    
    # Build device info section if available
    device_info_html = ""
    if event.device_ip or event.device_name:
        device_info_html = f"""
        <div style="background-color: #f8fafc; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <h3 style="margin: 0 0 12px; color: #334155; font-size: 14px; font-weight: 600;">Device Information</h3>
            <table style="width: 100%; border-collapse: collapse;">
                {"<tr><td style='padding: 4px 0; color: #64748b; font-size: 13px;'>Name:</td><td style='padding: 4px 0; color: #0f172a; font-size: 13px;'>" + (event.device_name or 'Unknown') + "</td></tr>" if event.device_name else ""}
                {"<tr><td style='padding: 4px 0; color: #64748b; font-size: 13px;'>IP Address:</td><td style='padding: 4px 0; color: #0f172a; font-size: 13px;'>" + event.device_ip + "</td></tr>" if event.device_ip else ""}
                {"<tr><td style='padding: 4px 0; color: #64748b; font-size: 13px;'>Hostname:</td><td style='padding: 4px 0; color: #0f172a; font-size: 13px;'>" + event.device_hostname + "</td></tr>" if event.device_hostname else ""}
                {"<tr><td style='padding: 4px 0; color: #64748b; font-size: 13px;'>Previous State:</td><td style='padding: 4px 0; color: #0f172a; font-size: 13px;'>" + event.previous_state + "</td></tr>" if event.previous_state else ""}
                {"<tr><td style='padding: 4px 0; color: #64748b; font-size: 13px;'>Current State:</td><td style='padding: 4px 0; color: #0f172a; font-size: 13px;'>" + event.current_state + "</td></tr>" if event.current_state else ""}
            </table>
        </div>
        """
    
    # Build anomaly info if present
    anomaly_info_html = ""
    if event.anomaly_score is not None:
        anomaly_percent = int(event.anomaly_score * 100)
        anomaly_info_html = f"""
        <div style="background-color: #fef3c7; padding: 12px 16px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #f59e0b;">
            <p style="margin: 0; color: #92400e; font-size: 13px;">
                <strong>Anomaly Score:</strong> {anomaly_percent}% - This event was detected by our ML-based anomaly detection system.
            </p>
        </div>
        """
    
    # Build additional details if present
    details_html = ""
    if event.details:
        details_rows = ""
        for key, value in event.details.items():
            display_key = key.replace("_", " ").title()
            details_rows += f"<tr><td style='padding: 4px 0; color: #64748b; font-size: 13px;'>{display_key}:</td><td style='padding: 4px 0; color: #0f172a; font-size: 13px;'>{value}</td></tr>"
        
        details_html = f"""
        <div style="background-color: #f8fafc; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <h3 style="margin: 0 0 12px; color: #334155; font-size: 14px; font-weight: 600;">Additional Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                {details_rows}
            </table>
        </div>
        """
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{event.title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f1f5f9;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f1f5f9;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 24px 40px; background: linear-gradient(135deg, #0891b2 0%, #0e7490 100%); border-radius: 12px 12px 0 0;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 600;">🗺️ Cartographer Alert</h1>
                                    </td>
                                    <td style="text-align: right;">
                                        <span style="display: inline-block; padding: 4px 12px; background-color: {priority_color}; color: #ffffff; font-size: 11px; font-weight: 600; border-radius: 12px; text-transform: uppercase;">
                                            {event.priority.value}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 32px 40px;">
                            <h2 style="margin: 0 0 16px; color: #0f172a; font-size: 18px; font-weight: 600;">
                                {icon} {event.title}
                            </h2>
                            <p style="margin: 0 0 24px; color: #475569; font-size: 15px; line-height: 1.6;">
                                {event.message}
                            </p>
                            
                            {device_info_html}
                            {anomaly_info_html}
                            {details_html}
                            
                            <!-- Timestamp -->
                            <p style="margin: 24px 0 0; color: #94a3b8; font-size: 12px;">
                                Event detected at {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
                            </p>
                            
                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="padding: 24px 0 0;">
                                        <a href="{APPLICATION_URL}" style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #0891b2 0%, #0e7490 100%); color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 600; border-radius: 8px;">
                                            View Network Map
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 40px; background-color: #f8fafc; border-radius: 0 0 12px 12px; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; color: #94a3b8; font-size: 12px; text-align: center;">
                                Cartographer Network Monitoring<br>
                                <a href="{APPLICATION_URL}/settings/notifications" style="color: #0891b2;">Manage notification preferences</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    return html_content


def _build_notification_email_text(event: NetworkEvent) -> str:
    """Build plain text email content for a network event notification"""
    icon = _get_notification_icon(event.event_type)
    
    text_content = f"""
{icon} Cartographer Alert: {event.title}
{'=' * 50}

Priority: {event.priority.value.upper()}

{event.message}
"""
    
    if event.device_ip or event.device_name:
        text_content += f"""
Device Information:
-------------------
"""
        if event.device_name:
            text_content += f"Name: {event.device_name}\n"
        if event.device_ip:
            text_content += f"IP Address: {event.device_ip}\n"
        if event.device_hostname:
            text_content += f"Hostname: {event.device_hostname}\n"
        if event.previous_state:
            text_content += f"Previous State: {event.previous_state}\n"
        if event.current_state:
            text_content += f"Current State: {event.current_state}\n"
    
    if event.anomaly_score is not None:
        anomaly_percent = int(event.anomaly_score * 100)
        text_content += f"""
Anomaly Detection:
------------------
Anomaly Score: {anomaly_percent}%
This event was flagged by our ML-based anomaly detection system.
"""
    
    if event.details:
        text_content += """
Additional Details:
-------------------
"""
        for key, value in event.details.items():
            display_key = key.replace("_", " ").title()
            text_content += f"{display_key}: {value}\n"
    
    text_content += f"""
---
Event detected at {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

View your network map: {APPLICATION_URL}
Manage notifications: {APPLICATION_URL}/settings/notifications

---
Cartographer Network Monitoring
"""
    return text_content


async def send_notification_email(
    to_email: str,
    event: NetworkEvent,
    notification_id: str,
) -> NotificationRecord:
    """
    Send a notification email for a network event.
    
    Returns a NotificationRecord with the result.
    """
    record = NotificationRecord(
        notification_id=notification_id,
        event_id=event.event_id,
        network_id=event.network_id,
        channel=NotificationChannel.EMAIL,
        title=event.title,
        message=event.message,
        priority=event.priority,
        success=False,
    )
    
    if not is_email_configured():
        record.error_message = "Email not configured - RESEND_API_KEY not set"
        logger.warning(f"✗ Email not configured - RESEND_API_KEY not set. Cannot send notification to {to_email}")
        return record
    
    resend = _get_resend()
    if not resend:
        record.error_message = "Resend module not available"
        logger.error(f"✗ Resend module not available. Cannot send notification to {to_email}")
        return record
    
    try:
        icon = _get_notification_icon(event.event_type)
        subject = f"{icon} {event.title}"
        
        if event.priority == NotificationPriority.CRITICAL:
            subject = f"🚨 CRITICAL: {event.title}"
        elif event.priority == NotificationPriority.HIGH:
            subject = f"⚠️ {event.title}"
        
        html_content = _build_notification_email_html(event)
        text_content = _build_notification_email_text(event)
        
        params = {
            "from": EMAIL_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }
        
        logger.info(f"Attempting to send email via Resend to {to_email} with subject: {subject}")
        result = resend.Emails.send(params)
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        
        if email_id:
            record.success = True
            logger.info(f"✓ Notification email sent successfully to {to_email} (Resend ID: {email_id}) - {event.title}")
        else:
            record.error_message = "Resend API returned no email ID"
            logger.error(f"✗ Resend API returned no email ID for notification to {to_email}")
        
    except Exception as e:
        record.error_message = str(e)
        logger.error(f"✗ Exception while sending notification email to {to_email}: {e}", exc_info=True)
    
    return record


async def send_test_email(to_email: str) -> Dict[str, Any]:
    """Send a test notification email"""
    test_event = NetworkEvent(
        event_id="test-event",
        event_type=NotificationType.SYSTEM_STATUS,
        priority=NotificationPriority.LOW,
        title="Test Notification",
        message="This is a test notification from Cartographer. If you received this email, your notification settings are working correctly!",
        details={
            "test": True,
            "sent_at": datetime.utcnow().isoformat(),
        }
    )
    
    record = await send_notification_email(to_email, test_event, "test-notification")
    
    return {
        "success": record.success,
        "error": record.error_message,
    }

