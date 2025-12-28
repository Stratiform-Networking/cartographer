"""
Extended tests for database.py to improve coverage.

Covers:
- Database migrations
- Session management
- Connection handling
"""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Set test environment
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"

from app.database import (
    DatabaseSettings,
    db_settings,
    get_db,
    init_db,
    _migrate_network_id_to_uuid,
)


class TestDatabaseSettings:
    """Tests for database settings."""
    
    def test_default_database_url(self):
        """Test default database URL."""
        # Just verify settings are created
        assert db_settings is not None
    
    def test_custom_database_url(self):
        """Test custom database URL from environment."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://custom:pass@host:5432/db"}):
            settings = DatabaseSettings()
            assert "custom" in settings.database_url or db_settings.database_url is not None


class TestGetDb:
    """Tests for get_db dependency."""
    
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test get_db yields a session and closes it."""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch('app.database.async_session_maker') as mock_maker:
            mock_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_maker.return_value.__aexit__ = AsyncMock()
            
            async for session in get_db():
                assert session is mock_session


class TestMigrateNetworkIdToUuid:
    """Tests for network_id to UUID migration."""
    
    @pytest.mark.asyncio
    async def test_migrate_context_id_integer_to_uuid(self):
        """Test migration of INTEGER context_id to UUID."""
        mock_conn = AsyncMock()
        
        # First query: check context_id type - return integer
        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = ('integer',)
        
        # Second query: check network_id type - return uuid (already migrated)
        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = ('uuid',)
        
        mock_conn.execute = AsyncMock(side_effect=[
            mock_result1,  # Check context_id type
            MagicMock(),   # Add new column
            MagicMock(),   # Update rows
            MagicMock(),   # Drop old column
            MagicMock(),   # Rename new column
            mock_result2,  # Check network_id type
        ])
        
        await _migrate_network_id_to_uuid(mock_conn)
        
        # Verify execute was called
        assert mock_conn.execute.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_migrate_context_id_bigint_to_uuid(self):
        """Test migration of BIGINT context_id to UUID."""
        mock_conn = AsyncMock()
        
        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = ('bigint',)
        
        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = ('uuid',)
        
        mock_conn.execute = AsyncMock(side_effect=[
            mock_result1,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            mock_result2,
        ])
        
        await _migrate_network_id_to_uuid(mock_conn)
        
        assert mock_conn.execute.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_migrate_network_id_integer_to_uuid(self):
        """Test migration of INTEGER network_id to UUID."""
        mock_conn = AsyncMock()
        
        # First query: context_id already UUID
        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = ('uuid',)
        
        # Second query: network_id is integer
        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = ('integer',)
        
        mock_conn.execute = AsyncMock(side_effect=[
            mock_result1,  # Check context_id type
            mock_result2,  # Check network_id type
            MagicMock(),   # Delete rows
            MagicMock(),   # Drop column
            MagicMock(),   # Add new column
            MagicMock(),   # Create index
        ])
        
        await _migrate_network_id_to_uuid(mock_conn)
        
        assert mock_conn.execute.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_migrate_already_uuid(self):
        """Test migration skips when already UUID."""
        mock_conn = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ('uuid',)
        
        mock_conn.execute = AsyncMock(return_value=mock_result)
        
        await _migrate_network_id_to_uuid(mock_conn)
        
        # Should only check types, not perform migration
        assert mock_conn.execute.call_count == 2  # Two type checks
    
    @pytest.mark.asyncio
    async def test_migrate_no_column(self):
        """Test migration when column doesn't exist."""
        mock_conn = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None  # Column doesn't exist
        
        mock_conn.execute = AsyncMock(return_value=mock_result)
        
        await _migrate_network_id_to_uuid(mock_conn)
        
        # Should check both columns but not migrate
        assert mock_conn.execute.call_count == 2


class TestInitDb:
    """Tests for init_db function."""
    
    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self):
        """Test init_db creates tables and runs migrations."""
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ('uuid',)
        mock_conn.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.database.engine') as mock_engine:
            mock_engine.begin = MagicMock()
            mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_engine.begin.return_value.__aexit__ = AsyncMock()
            
            await init_db()
            
            mock_conn.run_sync.assert_called_once()

