"""
Unit tests for email_service module.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.services.email_service import _get_resend, is_email_configured, send_invitation_email


class TestIsEmailConfigured:
    """Tests for is_email_configured function"""

    def test_returns_false_when_no_api_key(self):
        """Should return False without API key"""
        with patch.object(settings, "resend_api_key", ""):
            result = is_email_configured()

            assert result is False

    def test_returns_true_with_api_key(self):
        """Should return True with API key"""
        with patch.object(settings, "resend_api_key", "test-key"):
            result = is_email_configured()

            assert result is True


class TestGetResend:
    """Tests for _get_resend lazy loader"""

    def test_lazy_loads_resend(self):
        """Should lazy load resend module"""
        from app.services import email_service

        email_service._resend = None  # Reset

        with patch.dict(os.environ, {"RESEND_API_KEY": "test-key"}):
            with patch("resend.api_key", ""):
                resend = _get_resend()

                # Should have loaded the module
                assert resend is not None

    def test_handles_import_error(self):
        """Should handle missing resend module gracefully"""
        from app.services import email_service

        email_service._resend = None  # Reset to force reimport

        # Mock the import statement to raise ImportError
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "resend":
                raise ImportError("No module named 'resend'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            result = _get_resend()
            assert result is None

    def test_sets_api_key_when_configured(self):
        """Should set API key when resend is imported successfully"""
        from app.services import email_service

        email_service._resend = None  # Reset

        # Create a mock resend module
        mock_resend_module = MagicMock()
        mock_resend_module.api_key = None

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "resend":
                return mock_resend_module
            return original_import(name, *args, **kwargs)

        with (
            patch.object(builtins, "__import__", side_effect=mock_import),
            patch.object(settings, "resend_api_key", "test-api-key"),
        ):
            result = _get_resend()

            assert result is mock_resend_module
            assert mock_resend_module.api_key == "test-api-key"

    def test_returns_cached_resend(self):
        """Should return cached resend module on subsequent calls"""
        from app.services import email_service

        mock_cached = MagicMock()
        email_service._resend = mock_cached

        result = _get_resend()

        assert result is mock_cached


class TestSendInvitationEmail:
    """Tests for send_invitation_email function"""

    def test_returns_none_when_not_configured(self):
        """Should return None when email not configured"""
        from app.services import email_service

        with patch.object(settings, "resend_api_key", ""):
            result = send_invitation_email(
                to_email="test@test.com",
                invite_token="token123",
                invited_by_name="Admin User",
                role="readonly",
            )

            assert result is None

    def test_sends_email_successfully(self):
        """Should send email and return ID"""
        from app.services import email_service

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "email-123"}

        with patch.object(settings, "resend_api_key", "test-key"):
            with patch.object(email_service, "_get_resend", return_value=mock_resend):
                result = send_invitation_email(
                    to_email="test@test.com",
                    invite_token="token123",
                    invited_by_name="Admin User",
                    role="readonly",
                )

                assert result == "email-123"
                mock_resend.Emails.send.assert_called_once()

    def test_handles_email_send_error(self):
        """Should return None on error"""
        from app.services import email_service

        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API Error")

        with patch.object(settings, "resend_api_key", "test-key"):
            with patch.object(email_service, "_get_resend", return_value=mock_resend):
                result = send_invitation_email(
                    to_email="test@test.com",
                    invite_token="token123",
                    invited_by_name="Admin User",
                    role="readonly",
                )

                assert result is None

    def test_handles_resend_not_available(self):
        """Should return None if resend module unavailable"""
        from app.services import email_service

        with patch.object(settings, "resend_api_key", "test-key"):
            with patch.object(email_service, "_get_resend", return_value=None):
                result = send_invitation_email(
                    to_email="test@test.com",
                    invite_token="token123",
                    invited_by_name="Admin User",
                    role="readonly",
                )

                assert result is None

    def test_builds_correct_invite_url(self):
        """Should build correct invite URL"""
        from app.services import email_service

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "email-123"}

        with (
            patch.object(settings, "resend_api_key", "test-key"),
            patch.object(settings, "application_url", "http://localhost:5173"),
        ):
            with patch.object(email_service, "_get_resend", return_value=mock_resend):
                send_invitation_email(
                    to_email="test@test.com",
                    invite_token="mytoken",
                    invited_by_name="Admin User",
                    role="readonly",
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "http://localhost:5173/accept-invite?token=mytoken" in call_args["html"]

    def test_uses_role_display_names(self):
        """Should use friendly role display names"""
        from app.services import email_service

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = {"id": "email-123"}

        with patch.object(settings, "resend_api_key", "test-key"):
            with patch.object(email_service, "_get_resend", return_value=mock_resend):
                send_invitation_email(
                    to_email="test@test.com",
                    invite_token="token",
                    invited_by_name="Admin",
                    role="admin",
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "Admin" in call_args["html"] or "Admin" in call_args["text"]

    def test_handles_result_object(self):
        """Should handle result as object with id attribute"""
        from app.services import email_service

        mock_result = MagicMock()
        mock_result.id = "email-456"

        mock_resend = MagicMock()
        mock_resend.Emails.send.return_value = mock_result

        with patch.object(settings, "resend_api_key", "test-key"):
            with patch.object(email_service, "_get_resend", return_value=mock_resend):
                result = send_invitation_email(
                    to_email="test@test.com",
                    invite_token="token",
                    invited_by_name="Admin",
                    role="readonly",
                )

                assert result == "email-456"
