"""
Email notification service using Resend.

Sends notification emails for network events and anomalies.
"""

import logging
from datetime import datetime

from ..config import settings
from ..models import (
    NetworkEvent,
    NotificationChannel,
    NotificationPriority,
    NotificationRecord,
    NotificationType,
)
from ..utils import get_notification_icon, get_priority_color_hex

logger = logging.getLogger(__name__)

# Lazy load resend module
_resend = None


def _get_resend():
    """Lazy load resend module"""
    global _resend
    if _resend is None:
        try:
            import resend

            if settings.resend_api_key:
                resend.api_key = settings.resend_api_key
            _resend = resend
        except ImportError:
            logger.warning("Resend module not installed")
            return None
    return _resend


def is_email_configured() -> bool:
    """Check if email sending is configured"""
    return settings.is_email_configured


def _build_notification_email_html(event: NetworkEvent) -> str:
    """Build HTML email content for a network event notification"""
    icon = get_notification_icon(event.event_type)
    priority_color = get_priority_color_hex(event.priority)

    # Build device info section if available
    device_info_html = ""
    if event.device_ip or event.device_name:
        device_info_html = f"""
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; margin: 20px 0; border: 1px solid #e2e8f0;">
            <h3 style="margin: 0 0 16px; color: #0f172a; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Device Information</h3>
            <table style="width: 100%; border-collapse: collapse;">
                {"<tr><td style='padding: 6px 0; color: #64748b; font-size: 14px; width: 140px;'>Name</td><td style='padding: 6px 0; color: #0f172a; font-size: 14px; font-weight: 500;'>" + (event.device_name or 'Unknown') + "</td></tr>" if event.device_name else ""}
                {"<tr><td style='padding: 6px 0; color: #64748b; font-size: 14px;'>IP Address</td><td style='padding: 6px 0; color: #0f172a; font-size: 14px; font-weight: 500;'>" + event.device_ip + "</td></tr>" if event.device_ip else ""}
                {"<tr><td style='padding: 6px 0; color: #64748b; font-size: 14px;'>Hostname</td><td style='padding: 6px 0; color: #0f172a; font-size: 14px; font-weight: 500;'>" + event.device_hostname + "</td></tr>" if event.device_hostname else ""}
                {"<tr><td style='padding: 6px 0; color: #64748b; font-size: 14px;'>Previous State</td><td style='padding: 6px 0; color: #0f172a; font-size: 14px; font-weight: 500;'>" + event.previous_state + "</td></tr>" if event.previous_state else ""}
                {"<tr><td style='padding: 6px 0; color: #64748b; font-size: 14px;'>Current State</td><td style='padding: 6px 0; color: #0f172a; font-size: 14px; font-weight: 500;'>" + event.current_state + "</td></tr>" if event.current_state else ""}
            </table>
        </div>
        """

    # Build anomaly info if present
    anomaly_info_html = ""
    if event.anomaly_score is not None:
        anomaly_percent = int(event.anomaly_score * 100)
        anomaly_info_html = f"""
        <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(249, 115, 22, 0.1) 100%); padding: 16px 20px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #f59e0b;">
            <p style="margin: 0; color: #92400e; font-size: 14px; line-height: 1.5;">
                <strong style="font-weight: 600;">Anomaly Score: {anomaly_percent}%</strong><br>
                <span style="font-size: 13px; opacity: 0.9;">This event was detected by our ML-based anomaly detection system.</span>
            </p>
        </div>
        """

    # Build additional details if present
    details_html = ""
    if event.details:
        details_rows = ""
        for key, value in event.details.items():
            display_key = key.replace("_", " ").title()
            details_rows += f"<tr><td style='padding: 6px 0; color: #64748b; font-size: 14px; width: 140px;'>{display_key}</td><td style='padding: 6px 0; color: #0f172a; font-size: 14px; font-weight: 500;'>{value}</td></tr>"

        details_html = f"""
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; margin: 20px 0; border: 1px solid #e2e8f0;">
            <h3 style="margin: 0 0 16px; color: #0f172a; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Additional Details</h3>
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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #0f172a;">
        <tr>
            <td style="padding: 48px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 580px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 40px; background: linear-gradient(135deg, #0fb685 0%, #0994ae 100%); border-radius: 16px 16px 0 0;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td style="vertical-align: middle; padding-right: 12px;">
                                                    <div style="width: 40px; height: 40px; background: rgba(255, 255, 255, 0.2); border-radius: 10px; text-align: center; line-height: 40px; font-size: 20px;">🗺️</div>
                                                </td>
                                                <td style="vertical-align: middle;">
                                                    <h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: -0.3px;">Cartographer</h1>
                                                    <p style="margin: 2px 0 0; color: rgba(255, 255, 255, 0.85); font-size: 13px; font-weight: 500;">Network Alert</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td style="text-align: right; vertical-align: middle;">
                                        <span style="display: inline-block; padding: 6px 14px; background-color: {priority_color}; color: #ffffff; font-size: 11px; font-weight: 600; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);">
                                            {event.priority.value}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 36px 40px;">
                            <h2 style="margin: 0 0 12px; color: #0f172a; font-size: 20px; font-weight: 600; letter-spacing: -0.3px;">
                                {icon} {event.title}
                            </h2>
                            <p style="margin: 0 0 24px; color: #475569; font-size: 15px; line-height: 1.7;">
                                {event.message}
                            </p>

                            {device_info_html}
                            {anomaly_info_html}
                            {details_html}

                            <!-- Timestamp -->
                            <p style="margin: 24px 0 0; color: #94a3b8; font-size: 13px;">
                                Event detected at {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
                            </p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="padding: 28px 0 0;">
                                        <a href="{settings.application_url + ('/network/' + event.network_id if event.network_id else '')}" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #06b6d4 0%, #2563eb 100%); color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 600; border-radius: 10px; box-shadow: 0 4px 14px rgba(6, 182, 212, 0.35);">
                                            {'Open Network Map' if event.network_id else 'Open Cartographer'} →
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 40px 28px; background-color: #f8fafc; border-radius: 0 0 16px 16px; border-top: 1px solid #e2e8f0;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center;">
                                        <p style="margin: 0 0 8px; color: #64748b; font-size: 13px; font-weight: 500;">
                                            Cartographer Network Monitoring
                                        </p>
                                        <p style="margin: 0;">
                                            <a href="{settings.application_url}/settings/notifications" style="color: #0994ae; font-size: 12px; text-decoration: none; font-weight: 500;">Manage notification preferences</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>

                <!-- Bottom branding -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 580px; margin: 24px auto 0;">
                    <tr>
                        <td style="text-align: center;">
                            <p style="margin: 0; color: #475569; font-size: 12px;">
                                Powered by <span style="color: #0fb685; font-weight: 600;">Cartographer</span>
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
    icon = get_notification_icon(event.event_type)

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

    # Build network-specific URL if network_id is present
    network_url = settings.application_url
    if event.network_id:
        network_url = f"{settings.application_url}/network/{event.network_id}"

    text_content += f"""
---
Event detected at {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

{'Open network map' if event.network_id else 'Open Cartographer'}: {network_url}
Manage notifications: {settings.application_url}/settings/notifications

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
        logger.warning(
            f"✗ Email not configured - RESEND_API_KEY not set. Cannot send notification to {to_email}"
        )
        return record

    resend = _get_resend()
    if not resend:
        record.error_message = "Resend module not available"
        logger.error(f"✗ Resend module not available. Cannot send notification to {to_email}")
        return record

    try:
        icon = get_notification_icon(event.event_type)
        subject = f"{icon} {event.title}"

        if event.priority == NotificationPriority.CRITICAL:
            subject = f"🚨 CRITICAL: {event.title}"
        elif event.priority == NotificationPriority.HIGH:
            subject = f"⚠️ {event.title}"

        html_content = _build_notification_email_html(event)
        text_content = _build_notification_email_text(event)

        params = {
            "from": settings.email_from,
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
            logger.info(
                f"✓ Notification email sent successfully to {to_email} (Resend ID: {email_id}) - {event.title}"
            )
        else:
            record.error_message = "Resend API returned no email ID"
            logger.error(f"✗ Resend API returned no email ID for notification to {to_email}")

    except Exception as e:
        record.error_message = str(e)
        logger.error(
            f"✗ Exception while sending notification email to {to_email}: {e}", exc_info=True
        )

    return record


async def send_test_email(to_email: str) -> dict[str, any]:
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
        },
    )

    record = await send_notification_email(to_email, test_event, "test-notification")

    return {
        "success": record.success,
        "error": record.error_message,
    }
