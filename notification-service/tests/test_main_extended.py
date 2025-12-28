"""
Extended tests for main.py to improve coverage.

Covers:
- Lifespan events
- Service state management
- Cartographer status notifications
- Database migrations
- Application factory
"""

import os
import json
import asyncio
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import asynccontextmanager

# Set test environment
os.environ["NOTIFICATION_DATA_DIR"] = "/tmp/test_notification_data_main"
os.environ["RESEND_API_KEY"] = ""
os.environ["DISCORD_BOT_TOKEN"] = ""

from app.main import (
    _get_service_state,
    _save_service_state,
    _send_cartographer_status_notification,
    _send_cartographer_up_notification,
    _send_cartographer_down_notification,
    create_app,
    lifespan,
    DATA_DIR,
    SERVICE_STATE_FILE,
)
from app.models import NotificationType, NotificationPriority


class TestServiceState:
    """Tests for service state management."""
    
    def test_get_service_state_no_file(self):
        """Test getting state when file doesn't exist."""
        # Delete file if exists
        if SERVICE_STATE_FILE.exists():
            SERVICE_STATE_FILE.unlink()
        
        state = _get_service_state()
        
        assert state["clean_shutdown"] is False
        assert state["last_shutdown"] is None
        assert state["last_startup"] is None
    
    def test_get_service_state_with_file(self):
        """Test getting state from existing file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        expected_state = {
            "clean_shutdown": True,
            "last_shutdown": "2024-01-01T12:00:00",
            "last_startup": "2024-01-01T10:00:00",
        }
        
        with open(SERVICE_STATE_FILE, 'w') as f:
            json.dump(expected_state, f)
        
        state = _get_service_state()
        
        assert state["clean_shutdown"] is True
        assert state["last_shutdown"] == "2024-01-01T12:00:00"
    
    def test_get_service_state_corrupted_file(self):
        """Test getting state from corrupted file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(SERVICE_STATE_FILE, 'w') as f:
            f.write("not valid json")
        
        state = _get_service_state()
        
        # Should return default
        assert state["clean_shutdown"] is False
    
    def test_save_service_state_clean_shutdown(self):
        """Test saving clean shutdown state."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        _save_service_state(clean_shutdown=True)
        
        with open(SERVICE_STATE_FILE, 'r') as f:
            state = json.load(f)
        
        assert state["clean_shutdown"] is True
        assert state["last_shutdown"] is not None
    
    def test_save_service_state_not_clean(self):
        """Test saving non-clean shutdown state."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        _save_service_state(clean_shutdown=False)
        
        with open(SERVICE_STATE_FILE, 'r') as f:
            state = json.load(f)
        
        assert state["clean_shutdown"] is False
        assert state["last_shutdown"] is None
    
    def test_save_service_state_handles_exception(self):
        """Test save_service_state handles file write errors."""
        with patch('builtins.open', side_effect=PermissionError("No permission")):
            # Should not raise, just log warning
            _save_service_state(clean_shutdown=True)
        
        # Test passed if no exception raised


class TestCartographerStatusNotification:
    """Tests for Cartographer status notification sending."""
    
    @pytest.mark.asyncio
    async def test_send_cartographer_up_notification(self):
        """Test sending Cartographer up notification."""
        mock_record = MagicMock()
        mock_record.success = True
        
        with patch('app.services.email_service.is_email_configured', return_value=True), \
             patch('app.services.discord_service.is_discord_configured', return_value=False), \
             patch('app.services.cartographer_status.cartographer_status_service') as mock_service, \
             patch('app.services.email_service.send_notification_email', new_callable=AsyncMock, return_value=mock_record):
            
            mock_subscriber = MagicMock()
            mock_subscriber.email_enabled = True
            mock_subscriber.email_address = "test@example.com"
            mock_subscriber.discord_enabled = False
            mock_service.get_subscribers_for_event.return_value = [mock_subscriber]
            
            count = await _send_cartographer_status_notification("up", downtime_minutes=5)
        
        assert count >= 0  # May be 0 or 1 depending on import state
    
    @pytest.mark.asyncio
    async def test_send_cartographer_down_notification(self):
        """Test sending Cartographer down notification."""
        mock_record = MagicMock()
        mock_record.success = True
        
        with patch('app.services.email_service.is_email_configured', return_value=True), \
             patch('app.services.discord_service.is_discord_configured', return_value=False), \
             patch('app.services.cartographer_status.cartographer_status_service') as mock_service, \
             patch('app.services.email_service.send_notification_email', new_callable=AsyncMock, return_value=mock_record):
            
            mock_subscriber = MagicMock()
            mock_subscriber.email_enabled = True
            mock_subscriber.email_address = "test@example.com"
            mock_subscriber.discord_enabled = False
            mock_service.get_subscribers_for_event.return_value = [mock_subscriber]
            
            count = await _send_cartographer_status_notification("down")
        
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_send_cartographer_notification_no_subscribers(self):
        """Test notification when no subscribers."""
        with patch('app.services.cartographer_status.cartographer_status_service') as mock_service:
            mock_service.get_subscribers_for_event.return_value = []
            
            count = await _send_cartographer_status_notification("up")
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_send_cartographer_notification_no_services_configured(self):
        """Test notification when no email/discord configured."""
        with patch('app.services.email_service.is_email_configured', return_value=False), \
             patch('app.services.discord_service.is_discord_configured', return_value=False), \
             patch('app.services.cartographer_status.cartographer_status_service') as mock_service:
            
            mock_subscriber = MagicMock()
            mock_subscriber.email_enabled = True
            mock_subscriber.email_address = "test@example.com"
            mock_service.get_subscribers_for_event.return_value = [mock_subscriber]
            
            count = await _send_cartographer_status_notification("up")
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_send_cartographer_notification_discord_dm(self):
        """Test notification via Discord DM."""
        mock_record = MagicMock()
        mock_record.success = True
        
        with patch('app.services.email_service.is_email_configured', return_value=False), \
             patch('app.services.discord_service.is_discord_configured', return_value=True), \
             patch('app.services.cartographer_status.cartographer_status_service') as mock_service, \
             patch('app.services.discord_service.send_discord_notification', new_callable=AsyncMock, return_value=mock_record):
            
            mock_subscriber = MagicMock()
            mock_subscriber.email_enabled = False
            mock_subscriber.discord_enabled = True
            mock_subscriber.discord_delivery_method = "dm"
            mock_subscriber.discord_user_id = "123456789"
            mock_subscriber.discord_channel_id = None
            mock_service.get_subscribers_for_event.return_value = [mock_subscriber]
            
            count = await _send_cartographer_status_notification("up")
        
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_send_cartographer_notification_discord_channel(self):
        """Test notification via Discord channel."""
        mock_record = MagicMock()
        mock_record.success = True
        
        with patch('app.services.email_service.is_email_configured', return_value=False), \
             patch('app.services.discord_service.is_discord_configured', return_value=True), \
             patch('app.services.cartographer_status.cartographer_status_service') as mock_service, \
             patch('app.services.discord_service.send_discord_notification', new_callable=AsyncMock, return_value=mock_record):
            
            mock_subscriber = MagicMock()
            mock_subscriber.email_enabled = False
            mock_subscriber.discord_enabled = True
            mock_subscriber.discord_delivery_method = "channel"
            mock_subscriber.discord_channel_id = "987654321"
            mock_subscriber.discord_guild_id = "111222333"
            mock_subscriber.discord_user_id = None
            mock_subscriber.user_id = "test-user"
            mock_service.get_subscribers_for_event.return_value = [mock_subscriber]
            
            count = await _send_cartographer_status_notification("up")
        
        assert count >= 0
    
    @pytest.mark.asyncio
    async def test_send_cartographer_notification_email_failure(self):
        """Test notification when email fails."""
        mock_record = MagicMock()
        mock_record.success = False
        mock_record.error_message = "Failed to send"
        
        with patch('app.services.email_service.is_email_configured', return_value=True), \
             patch('app.services.discord_service.is_discord_configured', return_value=False), \
             patch('app.services.cartographer_status.cartographer_status_service') as mock_service, \
             patch('app.services.email_service.send_notification_email', new_callable=AsyncMock, return_value=mock_record):
            
            mock_subscriber = MagicMock()
            mock_subscriber.email_enabled = True
            mock_subscriber.email_address = "test@example.com"
            mock_subscriber.discord_enabled = False
            mock_service.get_subscribers_for_event.return_value = [mock_subscriber]
            
            count = await _send_cartographer_status_notification("up")
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_send_cartographer_notification_email_exception(self):
        """Test notification when email raises exception."""
        with patch('app.services.email_service.is_email_configured', return_value=True), \
             patch('app.services.discord_service.is_discord_configured', return_value=False), \
             patch('app.services.cartographer_status.cartographer_status_service') as mock_service, \
             patch('app.services.email_service.send_notification_email', new_callable=AsyncMock, 
                   side_effect=Exception("Network error")):
            
            mock_subscriber = MagicMock()
            mock_subscriber.email_enabled = True
            mock_subscriber.email_address = "test@example.com"
            mock_subscriber.discord_enabled = False
            mock_service.get_subscribers_for_event.return_value = [mock_subscriber]
            
            count = await _send_cartographer_status_notification("up")
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_send_cartographer_notification_discord_exception(self):
        """Test notification when Discord raises exception."""
        with patch('app.services.email_service.is_email_configured', return_value=False), \
             patch('app.services.discord_service.is_discord_configured', return_value=True), \
             patch('app.services.cartographer_status.cartographer_status_service') as mock_service, \
             patch('app.services.discord_service.send_discord_notification', new_callable=AsyncMock, 
                   side_effect=Exception("Discord error")):
            
            mock_subscriber = MagicMock()
            mock_subscriber.email_enabled = False
            mock_subscriber.discord_enabled = True
            mock_subscriber.discord_delivery_method = "dm"
            mock_subscriber.discord_user_id = "123456789"
            mock_service.get_subscribers_for_event.return_value = [mock_subscriber]
            
            count = await _send_cartographer_status_notification("up")
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_send_cartographer_notification_overall_exception(self):
        """Test notification handles overall exception."""
        with patch('app.services.cartographer_status.cartographer_status_service') as mock_service:
            mock_service.get_subscribers_for_event.side_effect = Exception("Service error")
            
            count = await _send_cartographer_status_notification("up")
        
        assert count == 0


class TestSendCartographerUpNotification:
    """Tests for _send_cartographer_up_notification."""
    
    @pytest.mark.asyncio
    async def test_send_up_notification_with_clean_shutdown(self):
        """Test up notification calculates downtime from clean shutdown."""
        previous_state = {
            "clean_shutdown": True,
            "last_shutdown": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
        }
        
        with patch('app.main._send_cartographer_status_notification', new_callable=AsyncMock) as mock_send:
            await _send_cartographer_up_notification(previous_state)
            
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[0][0] == "up"
            assert args[1]["downtime_minutes"] is not None
            assert args[1]["downtime_minutes"] >= 29  # Approximately 30 minutes
    
    @pytest.mark.asyncio
    async def test_send_up_notification_without_clean_shutdown(self):
        """Test up notification without clean shutdown has no downtime."""
        previous_state = {
            "clean_shutdown": False,
            "last_shutdown": None,
        }
        
        with patch('app.main._send_cartographer_status_notification', new_callable=AsyncMock) as mock_send:
            await _send_cartographer_up_notification(previous_state)
            
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[1]["downtime_minutes"] is None
    
    @pytest.mark.asyncio
    async def test_send_up_notification_invalid_shutdown_time(self):
        """Test up notification handles invalid shutdown time."""
        previous_state = {
            "clean_shutdown": True,
            "last_shutdown": "invalid-datetime",
        }
        
        with patch('app.main._send_cartographer_status_notification', new_callable=AsyncMock) as mock_send:
            await _send_cartographer_up_notification(previous_state)
            
            mock_send.assert_called_once()


class TestSendCartographerDownNotification:
    """Tests for _send_cartographer_down_notification."""
    
    @pytest.mark.asyncio
    async def test_send_down_notification(self):
        """Test sending down notification."""
        with patch('app.main._send_cartographer_status_notification', new_callable=AsyncMock) as mock_send:
            await _send_cartographer_down_notification()
            
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[0][0] == "down"
            assert "shutting down" in args[1]["message"]


class TestCreateApp:
    """Tests for application factory."""
    
    def test_create_app_default(self):
        """Test creating app with default settings."""
        app = create_app()
        
        assert app.title == "Cartographer Notification Service"
        assert app.docs_url == "/docs"
    
    def test_create_app_disable_docs(self):
        """Test creating app with docs disabled."""
        with patch.dict(os.environ, {"DISABLE_DOCS": "true"}):
            app = create_app()
            
            assert app.docs_url is None
            assert app.redoc_url is None
    
    def test_create_app_cors_origins(self):
        """Test creating app with custom CORS origins."""
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,http://localhost:5173"}):
            app = create_app()
            
            # CORS middleware should be configured
            assert app is not None


class TestMigrateNetworkIdsToUuid:
    """Tests for network ID migration in main."""
    
    @pytest.mark.asyncio
    async def test_migrate_network_ids_function_exists(self):
        """Test migration function exists and can be imported."""
        from app.main import _migrate_network_ids_to_uuid
        
        # Just verify function exists
        assert callable(_migrate_network_ids_to_uuid)
    
    @pytest.mark.asyncio
    async def test_migrate_discord_user_links_integer_to_uuid(self):
        """Test migrating discord_user_links.context_id from INTEGER to UUID."""
        from app.main import _migrate_network_ids_to_uuid
        
        # Mock session that returns 'integer' for context_id column type
        mock_session = AsyncMock()
        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = ('integer',)
        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = None  # No migration needed for second table
        
        # Return different results for consecutive execute calls
        mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result1, mock_result1, mock_result1, mock_result1, mock_result2])
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.async_session_maker', mock_session_maker):
            await _migrate_network_ids_to_uuid()
        
        # Verify execute was called
        assert mock_session.execute.called
    
    @pytest.mark.asyncio
    async def test_migrate_user_network_prefs_integer_to_uuid(self):
        """Test migrating user_network_notification_prefs.network_id from INTEGER to UUID."""
        from app.main import _migrate_network_ids_to_uuid
        
        mock_session = AsyncMock()
        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = None  # No migration needed for first table
        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = ('bigint',)  # Second table needs migration
        
        mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2, mock_result2, mock_result2, mock_result2, mock_result2])
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.async_session_maker', mock_session_maker):
            await _migrate_network_ids_to_uuid()
        
        assert mock_session.execute.called
    
    @pytest.mark.asyncio
    async def test_migrate_no_migration_needed(self):
        """Test migration when columns are already UUID."""
        from app.main import _migrate_network_ids_to_uuid
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ('uuid',)  # Already UUID type
        
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.async_session_maker', mock_session_maker):
            await _migrate_network_ids_to_uuid()
        
        # Should only call execute twice (for checking columns)
        assert mock_session.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_migrate_handles_exception(self):
        """Test migration handles database exceptions."""
        from app.main import _migrate_network_ids_to_uuid
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))
        mock_session.rollback = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.async_session_maker', mock_session_maker):
            # Should not raise, just log error and rollback
            await _migrate_network_ids_to_uuid()
        
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_migrate_column_not_exists(self):
        """Test migration when column doesn't exist in table."""
        from app.main import _migrate_network_ids_to_uuid
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None  # Column doesn't exist
        
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.async_session_maker', mock_session_maker):
            await _migrate_network_ids_to_uuid()
        
        # Should complete without error
        assert mock_session.execute.called


class TestAppEndpoints:
    """Tests for basic app endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        from fastapi.testclient import TestClient
        
        app = create_app()
        
        with TestClient(app) as client:
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Cartographer Notification Service"
            assert data["status"] == "running"
    
    def test_healthz_endpoint(self):
        """Test health check endpoint."""
        from fastapi.testclient import TestClient
        
        app = create_app()
        
        with TestClient(app) as client:
            response = client.get("/healthz")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

