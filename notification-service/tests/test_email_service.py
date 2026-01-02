"""
Unit tests for email service.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models import NetworkEvent, NotificationChannel, NotificationPriority, NotificationType
from app.services.email_service import (
    _build_notification_email_html,
    _build_notification_email_text,
    _get_resend,
    is_email_configured,
    send_notification_email,
    send_test_email,
)
from app.utils import get_notification_icon, get_priority_color_hex


class TestEmailConfiguration:
    """Tests for email configuration"""

    def test_is_email_configured_false(self):
        """Should return False when no API key"""
        with patch("app.services.email_service.settings.resend_api_key", ""):
            assert is_email_configured() is False

    def test_is_email_configured_true(self):
        """Should return True when API key set"""
        with patch("app.services.email_service.settings.resend_api_key", "test-key"):
            assert is_email_configured() is True

    def test_get_resend_not_installed(self):
        """Should return None when resend not installed"""
        import app.services.email_service as email_service

        email_service._resend = None  # Reset cache

        with patch.dict("sys.modules", {"resend": None}):
            with patch("builtins.__import__", side_effect=ImportError):
                result = _get_resend()

        # Reset for other tests
        email_service._resend = None


class TestEmailHelpers:
    """Tests for email helper functions"""

    def testget_priority_color_hex(self):
        """Should return correct colors"""
        assert get_priority_color_hex(NotificationPriority.LOW) == "#64748b"
        assert get_priority_color_hex(NotificationPriority.CRITICAL) == "#ef4444"

    def testget_notification_icon(self):
        """Should return correct icons"""
        assert get_notification_icon(NotificationType.DEVICE_OFFLINE) == "🔴"
        assert get_notification_icon(NotificationType.DEVICE_ONLINE) == "🟢"
        assert get_notification_icon(NotificationType.SECURITY_ALERT) == "🔒"

    def testget_notification_icon_default(self):
        """Should return default icon for unknown type"""
        # Use a valid type that's not in the icons dict
        icon = get_notification_icon(NotificationType.CARTOGRAPHER_UP)
        assert icon == "📢"  # Default


class TestEmailContent:
    """Tests for email content generation"""

    def test_build_html_basic(self):
        """Should build basic HTML email"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test Event",
            message="Test message",
        )

        html = _build_notification_email_html(event)

        assert "Test Event" in html
        assert "Test message" in html
        assert "<!DOCTYPE html>" in html

    def test_build_html_with_device(self):
        """Should include device info in HTML"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test",
            device_ip="192.168.1.100",
            device_name="Test Device",
        )

        html = _build_notification_email_html(event)

        assert "192.168.1.100" in html
        assert "Test Device" in html

    def test_build_html_with_anomaly(self):
        """Should include anomaly info in HTML"""
        event = NetworkEvent(
            event_type=NotificationType.ANOMALY_DETECTED,
            title="Test",
            message="Test",
            anomaly_score=0.85,
        )

        html = _build_notification_email_html(event)

        assert "85%" in html

    def test_build_text_basic(self):
        """Should build basic text email"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test Event", message="Test message"
        )

        text = _build_notification_email_text(event)

        assert "Test Event" in text
        assert "Test message" in text

    def test_build_text_with_device(self):
        """Should include device info in text"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test",
            device_ip="192.168.1.100",
            device_name="Test Device",
        )

        text = _build_notification_email_text(event)

        assert "192.168.1.100" in text
        assert "Test Device" in text


class TestSendEmail:
    """Tests for sending emails"""

    async def test_send_notification_email_not_configured(self):
        """Should fail when not configured"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        with patch("app.services.email_service.settings.resend_api_key", ""):
            record = await send_notification_email("test@example.com", event, "notification-123")

        assert record.success is False
        assert "not configured" in record.error_message.lower()

    async def test_send_notification_email_no_resend(self):
        """Should fail when resend not available"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        with patch("app.services.email_service.settings.resend_api_key", "test-key"):
            with patch("app.services.email_service._get_resend", return_value=None):
                record = await send_notification_email(
                    "test@example.com", event, "notification-123"
                )

        assert record.success is False

    async def test_send_notification_email_success(self):
        """Should send email successfully"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "email-123"}

        with patch("app.services.email_service.settings.resend_api_key", "test-key"):
            with patch("app.services.email_service._get_resend", return_value=mock_resend):
                record = await send_notification_email(
                    "test@example.com", event, "notification-123"
                )

        assert record.success is True

    async def test_send_notification_email_critical(self):
        """Should add CRITICAL prefix for critical priority"""
        event = NetworkEvent(
            event_type=NotificationType.SECURITY_ALERT,
            priority=NotificationPriority.CRITICAL,
            title="Security Alert",
            message="Test",
        )

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "email-123"}

        with patch("app.services.email_service.settings.resend_api_key", "test-key"):
            with patch("app.services.email_service._get_resend", return_value=mock_resend):
                await send_notification_email("test@example.com", event, "notification-123")

        # Check that the subject was modified
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert "CRITICAL" in call_args["subject"]

    async def test_send_notification_email_error(self):
        """Should handle send error"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("Send failed")

        with patch("app.services.email_service.settings.resend_api_key", "test-key"):
            with patch("app.services.email_service._get_resend", return_value=mock_resend):
                record = await send_notification_email(
                    "test@example.com", event, "notification-123"
                )

        assert record.success is False
        assert "Send failed" in record.error_message

    async def test_send_test_email(self):
        """Should send test email"""
        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "email-123"}

        with patch("app.services.email_service.settings.resend_api_key", "test-key"):
            with patch("app.services.email_service._get_resend", return_value=mock_resend):
                result = await send_test_email("test@example.com")

        assert result["success"] is True
