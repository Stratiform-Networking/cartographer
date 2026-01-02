"""
Extended tests for CartographerStatusService to improve coverage.

Covers:
- Subscription creation and update
- File persistence (save/load)
- Error handling
- Migration from global preferences
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Set test environment
os.environ["NOTIFICATION_DATA_DIR"] = "/tmp/test_cartographer_status"
os.environ["RESEND_API_KEY"] = ""
os.environ["DISCORD_BOT_TOKEN"] = ""


class TestCartographerStatusSubscription:
    """Tests for CartographerStatusSubscription model."""

    def test_subscription_from_dict(self):
        """Test creating subscription from dict."""
        from app.services.cartographer_status import CartographerStatusSubscription

        data = {
            "user_id": "test-user",
            "email_address": "test@example.com",
            "cartographer_up_enabled": True,
            "cartographer_down_enabled": True,
        }

        sub = CartographerStatusSubscription.from_dict(data)

        assert sub.user_id == "test-user"
        assert sub.email_address == "test@example.com"

    def test_subscription_to_dict(self):
        """Test converting subscription to dict."""
        from app.services.cartographer_status import CartographerStatusSubscription

        sub = CartographerStatusSubscription(
            user_id="test-user",
            email_address="test@example.com",
        )

        data = sub.to_dict()

        assert data["user_id"] == "test-user"
        assert data["email_address"] == "test@example.com"

    def test_subscription_from_dict_with_dates(self):
        """Test subscription from dict with datetime parsing."""
        from app.services.cartographer_status import CartographerStatusSubscription

        data = {
            "user_id": "test-user",
            "email_address": "test@example.com",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }

        sub = CartographerStatusSubscription.from_dict(data)

        assert sub.user_id == "test-user"
        assert isinstance(sub.created_at, datetime)


class TestCartographerStatusServicePersistence:
    """Tests for service file persistence."""

    def test_save_subscriptions_error(self):
        """Test error handling when saving subscriptions fails."""
        from app.services.cartographer_status import CartographerStatusService

        service = CartographerStatusService()
        service._subscriptions = {"user1": MagicMock()}

        with patch("builtins.open", side_effect=PermissionError("No permission")):
            # Should not raise, just log error
            service._save_subscriptions()

    def test_load_subscriptions_error(self):
        """Test error handling when loading subscriptions fails."""
        from app.services.cartographer_status import CartographerStatusService

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", side_effect=PermissionError("No permission")):
                service = CartographerStatusService()
                # Should not raise, just log error

    def test_load_subscriptions_invalid_json(self):
        """Test loading with invalid JSON."""
        from app.services.cartographer_status import CartographerStatusService

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="invalid json")):
                with patch("json.load", side_effect=json.JSONDecodeError("", "", 0)):
                    service = CartographerStatusService()

    def test_load_subscriptions_invalid_subscription(self):
        """Test loading with invalid subscription data."""
        from app.services.cartographer_status import CartographerStatusService

        invalid_data = {"user1": {"invalid": "data"}}  # Missing required fields

        # Test that invalid subscription data is handled gracefully in from_dict
        # The service should log a warning but not crash
        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(invalid_data))):
                with patch("json.load", return_value=invalid_data):
                    # Create service - should handle invalid data gracefully
                    service = CartographerStatusService()
                    # Invalid subscription should be skipped
                    assert "user1" not in service._subscriptions


class TestCartographerStatusServiceSubscriptions:
    """Tests for subscription management."""

    def test_create_new_subscription(self):
        """Test creating a new subscription."""
        from app.services.cartographer_status import CartographerStatusService

        service = CartographerStatusService()
        service._save_subscriptions = MagicMock()

        sub = service.create_or_update_subscription(
            user_id="new-user",
            email_address="new@example.com",
            cartographer_up_enabled=True,
            cartographer_down_enabled=False,
        )

        assert sub.user_id == "new-user"
        assert sub.email_address == "new@example.com"
        assert sub.cartographer_up_enabled is True
        assert sub.cartographer_down_enabled is False

    def test_update_existing_subscription(self):
        """Test updating an existing subscription."""
        from app.services.cartographer_status import (
            CartographerStatusService,
            CartographerStatusSubscription,
        )

        service = CartographerStatusService()
        service._save_subscriptions = MagicMock()

        # Create initial subscription
        service._subscriptions["existing-user"] = CartographerStatusSubscription(
            user_id="existing-user",
            email_address="old@example.com",
        )

        # Update it
        sub = service.create_or_update_subscription(
            user_id="existing-user",
            email_address="new@example.com",
            cartographer_up_enabled=True,
        )

        assert sub.email_address == "new@example.com"
        assert sub.cartographer_up_enabled is True

    def test_update_subscription_with_discord_fields(self):
        """Test updating subscription Discord fields."""
        from app.services.cartographer_status import (
            CartographerStatusService,
            CartographerStatusSubscription,
        )

        service = CartographerStatusService()
        service._save_subscriptions = MagicMock()

        # Create initial subscription
        service._subscriptions["user"] = CartographerStatusSubscription(
            user_id="user",
            email_address="user@example.com",
        )

        # Update with Discord fields
        sub = service.create_or_update_subscription(
            user_id="user",
            discord_enabled=True,
            discord_delivery_method="dm",
            discord_guild_id="123",
            discord_channel_id="456",
            discord_user_id="789",
            _discord_guild_id_provided=True,
            _discord_channel_id_provided=True,
            _discord_user_id_provided=True,
        )

        assert sub.discord_enabled is True
        assert sub.discord_guild_id == "123"
        assert sub.discord_channel_id == "456"
        assert sub.discord_user_id == "789"

    def test_update_subscription_with_quiet_hours(self):
        """Test updating subscription quiet hours."""
        from app.services.cartographer_status import (
            CartographerStatusService,
            CartographerStatusSubscription,
        )

        service = CartographerStatusService()
        service._save_subscriptions = MagicMock()

        # Create initial subscription
        service._subscriptions["user"] = CartographerStatusSubscription(
            user_id="user",
            email_address="user@example.com",
        )

        # Update with quiet hours
        sub = service.create_or_update_subscription(
            user_id="user",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
            quiet_hours_bypass_priority="critical",
            timezone="America/New_York",
            _bypass_priority_provided=True,
            _timezone_provided=True,
        )

        assert sub.quiet_hours_enabled is True
        assert sub.quiet_hours_start == "22:00"
        assert sub.quiet_hours_end == "08:00"
        assert sub.quiet_hours_bypass_priority == "critical"
        assert sub.timezone == "America/New_York"

    def test_update_subscription_priority_fields(self):
        """Test updating subscription priority fields."""
        from app.services.cartographer_status import (
            CartographerStatusService,
            CartographerStatusSubscription,
        )

        service = CartographerStatusService()
        service._save_subscriptions = MagicMock()

        # Create initial subscription
        service._subscriptions["user"] = CartographerStatusSubscription(
            user_id="user",
            email_address="user@example.com",
        )

        # Update priority fields
        sub = service.create_or_update_subscription(
            user_id="user",
            cartographer_up_priority="high",
            cartographer_down_priority="critical",
            minimum_priority="medium",
        )

        assert sub.cartographer_up_priority == "high"
        assert sub.cartographer_down_priority == "critical"
        assert sub.minimum_priority == "medium"

    def test_delete_subscription(self):
        """Test deleting a subscription."""
        from app.services.cartographer_status import (
            CartographerStatusService,
            CartographerStatusSubscription,
        )

        service = CartographerStatusService()
        service._save_subscriptions = MagicMock()

        # Create subscription
        service._subscriptions["user"] = CartographerStatusSubscription(
            user_id="user",
            email_address="user@example.com",
        )

        result = service.delete_subscription("user")

        assert result is True
        assert "user" not in service._subscriptions

    def test_delete_nonexistent_subscription(self):
        """Test deleting a nonexistent subscription."""
        from app.services.cartographer_status import CartographerStatusService

        service = CartographerStatusService()

        result = service.delete_subscription("nonexistent")

        assert result is False


class TestCartographerStatusServiceSubscribers:
    """Tests for subscriber retrieval."""

    def test_get_all_subscriptions(self):
        """Test getting all subscriptions."""
        from app.services.cartographer_status import (
            CartographerStatusService,
            CartographerStatusSubscription,
        )

        service = CartographerStatusService()
        service._subscriptions = {
            "user1": CartographerStatusSubscription(
                user_id="user1", email_address="u1@example.com"
            ),
            "user2": CartographerStatusSubscription(
                user_id="user2", email_address="u2@example.com"
            ),
        }

        subscriptions = service.get_all_subscriptions()

        assert len(subscriptions) == 2

    def test_get_subscribers_for_unknown_event(self):
        """Test getting subscribers for unknown event type."""
        from app.services.cartographer_status import CartographerStatusService

        service = CartographerStatusService()
        service._subscriptions = {"user": MagicMock()}

        subscribers = service.get_subscribers_for_event("unknown")

        assert len(subscribers) == 0
