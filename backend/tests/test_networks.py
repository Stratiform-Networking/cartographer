"""
Tests for the networks router.
Covers network CRUD, permissions, layout, and notification settings.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import AuthenticatedUser, UserRole
from app.models.network import (
    Network,
    NetworkNotificationSettings,
    NetworkPermission,
    PermissionRole,
)

# ==================== Fixtures ====================


@pytest.fixture
def owner_user():
    return AuthenticatedUser(user_id="owner-123", username="owner", role=UserRole.OWNER)


@pytest.fixture
def admin_user():
    return AuthenticatedUser(user_id="admin-456", username="admin", role=UserRole.ADMIN)


@pytest.fixture
def member_user():
    return AuthenticatedUser(user_id="member-789", username="member", role=UserRole.MEMBER)


@pytest.fixture
def service_user():
    """Service token user for internal operations"""
    return AuthenticatedUser(user_id="service", username="service", role=UserRole.ADMIN)


@pytest.fixture
def metrics_service_user():
    """Metrics service token user"""
    return AuthenticatedUser(user_id="metrics-service", username="metrics", role=UserRole.ADMIN)


@pytest.fixture
def mock_db():
    """Mock async database session"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def sample_network():
    """Create a sample network object"""
    network = MagicMock(spec=Network)
    network.id = "network-123"
    network.user_id = "owner-123"
    network.name = "Test Network"
    network.description = "A test network"
    network.agent_key = "test-agent-key"
    network.layout_data = {"root": {"id": "router"}}
    network.is_active = True
    network.created_at = datetime.now()
    network.updated_at = datetime.now()
    network.last_sync_at = None
    return network


# ==================== Helper Function Tests ====================


class TestGenerateAgentKey:
    """Tests for generate_agent_key"""

    def test_generate_agent_key_returns_hex_string(self):
        """Should return a 64-char hex string"""
        from app.routers.networks import generate_agent_key

        key = generate_agent_key()

        assert len(key) == 64
        # Should be valid hex
        int(key, 16)

    def test_generate_agent_key_unique(self):
        """Should generate unique keys"""
        from app.routers.networks import generate_agent_key

        keys = [generate_agent_key() for _ in range(10)]

        assert len(set(keys)) == 10


class TestGetNetworkWithAccess:
    """Tests for get_network_with_access helper"""

    async def test_network_not_found(self, owner_user, mock_db):
        """Should raise 404 when network doesn't exist"""
        from app.services.network_service import get_network_with_access

        # Mock execute to return no network
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_network_with_access("nonexistent", owner_user.user_id, mock_db)

        assert exc_info.value.status_code == 404

    async def test_owner_has_access(self, owner_user, mock_db, sample_network):
        """Owner should have full access"""
        from app.services.network_service import get_network_with_access

        # Mock execute to return the network
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)

        network, is_owner, permission = await get_network_with_access(
            "network-123", owner_user.user_id, mock_db
        )

        assert network == sample_network
        assert is_owner is True
        assert permission is None

    async def test_service_user_has_access(self, service_user, mock_db, sample_network):
        """Service token should have editor access to all networks"""
        from app.services.network_service import get_network_with_access

        # Mock execute to return the network
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)

        network, is_owner, permission = await get_network_with_access(
            "network-123", service_user.user_id, mock_db, is_service=True
        )

        assert network == sample_network
        assert is_owner is False
        assert permission == PermissionRole.EDITOR

    async def test_metrics_service_user_has_access(
        self, metrics_service_user, mock_db, sample_network
    ):
        """Metrics service token should have editor access to all networks"""
        from app.services.network_service import get_network_with_access

        # Mock execute to return the network
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)

        network, is_owner, permission = await get_network_with_access(
            "network-123", metrics_service_user.user_id, mock_db, is_service=True
        )

        assert network == sample_network
        assert is_owner is False
        assert permission == PermissionRole.EDITOR

    async def test_user_with_editor_permission(self, admin_user, mock_db, sample_network):
        """User with editor permission should have access"""
        from app.services.network_service import get_network_with_access

        # First call returns network, second returns permission
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_permission = MagicMock(spec=NetworkPermission)
        mock_permission.role = PermissionRole.EDITOR

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_permission

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        network, is_owner, permission = await get_network_with_access(
            "network-123", admin_user.user_id, mock_db
        )

        assert network == sample_network
        assert is_owner is False
        assert permission == PermissionRole.EDITOR

    async def test_user_with_viewer_permission(self, member_user, mock_db, sample_network):
        """User with viewer permission should have read access"""
        from app.routers.networks import get_network_with_access

        # First call returns network, second returns permission
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_permission = MagicMock(spec=NetworkPermission)
        mock_permission.role = PermissionRole.VIEWER

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_permission

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        network, is_owner, permission = await get_network_with_access(
            "network-123", member_user, mock_db
        )

        assert network == sample_network
        assert is_owner is False
        assert permission == PermissionRole.VIEWER

    async def test_no_permission_raises_404(self, admin_user, mock_db, sample_network):
        """User without permission should get 404"""
        from app.routers.networks import get_network_with_access

        # Network found, but no permission
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await get_network_with_access("network-123", admin_user, mock_db)

        assert exc_info.value.status_code == 404

    async def test_viewer_denied_write_access(self, member_user, mock_db, sample_network):
        """Viewer should be denied write access"""
        from app.routers.networks import get_network_with_access

        # Network found with viewer permission
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_permission = MagicMock(spec=NetworkPermission)
        mock_permission.role = PermissionRole.VIEWER

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_permission

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await get_network_with_access("network-123", member_user, mock_db, require_write=True)

        assert exc_info.value.status_code == 403
        assert "Write access required" in exc_info.value.detail


class TestGetNetworkMemberUserIds:
    """Tests for get_network_member_user_ids helper"""

    async def test_network_not_found(self, mock_db):
        """Should raise 404 when network doesn't exist"""
        from app.routers.networks import get_network_member_user_ids

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_network_member_user_ids("nonexistent", mock_db)

        assert exc_info.value.status_code == 404

    async def test_returns_owner_and_members(self, mock_db, sample_network):
        """Should return all user IDs with access"""
        from app.routers.networks import get_network_member_user_ids

        # First call returns network
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        # Second call returns permission user IDs
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["user-1", "user-2"]
        mock_perm_result = MagicMock()
        mock_perm_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        user_ids = await get_network_member_user_ids("network-123", mock_db)

        # Should include owner and permission users
        assert "owner-123" in user_ids
        assert "user-1" in user_ids
        assert "user-2" in user_ids

    async def test_returns_unique_user_ids(self, mock_db, sample_network):
        """Should return unique user IDs (no duplicates)"""
        from app.routers.networks import get_network_member_user_ids

        # First call returns network
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        # Second call returns permission user IDs (includes owner as duplicate)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["owner-123", "user-1"]
        mock_perm_result = MagicMock()
        mock_perm_result.scalars.return_value = mock_scalars

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        user_ids = await get_network_member_user_ids("network-123", mock_db)

        # Should be unique (no duplicates)
        assert len(user_ids) == len(set(user_ids))
        assert "owner-123" in user_ids
        assert "user-1" in user_ids


# ==================== Network CRUD Tests ====================


class TestCreateNetwork:
    """Tests for create_network endpoint"""

    async def test_create_network_success(self, owner_user, mock_db):
        """Should create a new network"""
        from app.routers.networks import create_network
        from app.schemas import NetworkCreate

        network_data = NetworkCreate(name="New Network", description="A new test network")

        # Mock add, commit, refresh
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        # Mock refresh to populate the network
        async def mock_refresh(network):
            network.id = "new-network-id"
            network.user_id = owner_user.user_id
            network.name = "New Network"
            network.description = "A new test network"
            network.is_active = True
            network.created_at = datetime.now()
            network.updated_at = datetime.now()
            network.layout_data = None
            network.last_sync_at = None
            network.agent_key = "test-key"

        mock_db.refresh = mock_refresh

        response = await create_network(network_data, owner_user, mock_db)

        assert response.name == "New Network"
        assert response.description == "A new test network"
        assert response.is_owner is True
        mock_db.add.assert_called_once()


class TestListNetworks:
    """Tests for list_networks endpoint"""

    async def test_list_networks_as_service(self, service_user, mock_db, sample_network):
        """Service user should see all networks"""
        from app.routers.networks import list_networks

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_network]
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await list_networks(service_user, mock_db)

        assert len(response) == 1
        assert response[0].is_owner is False
        assert response[0].permission == PermissionRole.EDITOR

    async def test_list_networks_as_metrics_service(
        self, metrics_service_user, mock_db, sample_network
    ):
        """Metrics service user should see all networks"""
        from app.routers.networks import list_networks

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_network]
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await list_networks(metrics_service_user, mock_db)

        assert len(response) == 1
        assert response[0].is_owner is False

    async def test_list_networks_as_owner(self, owner_user, mock_db, sample_network):
        """Regular user should see owned networks"""
        from app.routers.networks import list_networks

        # Mock for owned networks
        owned_result = MagicMock()
        owned_result.scalars.return_value.all.return_value = [sample_network]

        # Mock for shared networks (empty)
        shared_result = MagicMock()
        shared_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[owned_result, shared_result])

        response = await list_networks(owner_user, mock_db)

        assert len(response) == 1
        assert response[0].is_owner is True

    async def test_list_networks_with_shared(self, admin_user, mock_db, sample_network):
        """User should see shared networks"""
        from app.routers.networks import list_networks

        # Mock for owned networks (empty)
        owned_result = MagicMock()
        owned_result.scalars.return_value.all.return_value = []

        # Mock for shared networks - returns tuple (network, role)
        shared_result = MagicMock()
        shared_result.all.return_value = [(sample_network, PermissionRole.EDITOR)]

        mock_db.execute = AsyncMock(side_effect=[owned_result, shared_result])

        response = await list_networks(admin_user, mock_db)

        assert len(response) == 1
        assert response[0].is_owner is False
        assert response[0].permission == PermissionRole.EDITOR


class TestGetNetwork:
    """Tests for get_network endpoint"""

    async def test_get_network_success(self, owner_user, mock_db, sample_network):
        """Should return network details"""
        from app.routers.networks import get_network

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await get_network("network-123", owner_user, mock_db)

        assert response.id == sample_network.id
        assert response.is_owner is True


class TestUpdateNetwork:
    """Tests for update_network endpoint"""

    async def test_update_network_name(self, owner_user, mock_db, sample_network):
        """Should update network name"""
        from app.routers.networks import update_network
        from app.schemas import NetworkUpdate

        update_data = NetworkUpdate(name="Updated Name")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        response = await update_network("network-123", update_data, owner_user, mock_db)

        assert sample_network.name == "Updated Name"

    async def test_update_network_description(self, owner_user, mock_db, sample_network):
        """Should update network description"""
        from app.routers.networks import update_network
        from app.schemas import NetworkUpdate

        update_data = NetworkUpdate(description="New description")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        response = await update_network("network-123", update_data, owner_user, mock_db)

        assert sample_network.description == "New description"

    async def test_update_network_partial(self, owner_user, mock_db, sample_network):
        """Should only update provided fields"""
        from app.routers.networks import update_network
        from app.schemas import NetworkUpdate

        original_name = sample_network.name
        update_data = NetworkUpdate(description="Only desc")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        response = await update_network("network-123", update_data, owner_user, mock_db)

        # Name should not change
        assert sample_network.name == original_name
        assert sample_network.description == "Only desc"


class TestDeleteNetwork:
    """Tests for delete_network endpoint"""

    async def test_delete_network_success(self, owner_user, mock_db, sample_network):
        """Owner should be able to delete network"""
        from app.routers.networks import delete_network

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        # Should not raise
        await delete_network("network-123", owner_user, mock_db)

        mock_db.delete.assert_called_once()

    async def test_delete_network_not_owner(self, admin_user, mock_db, sample_network):
        """Non-owner should not be able to delete"""
        from app.routers.networks import delete_network

        # Set up admin user with editor permission
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_permission = MagicMock(spec=NetworkPermission)
        mock_permission.role = PermissionRole.EDITOR

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_permission

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await delete_network("network-123", admin_user, mock_db)

        assert exc_info.value.status_code == 403
        assert "owner" in exc_info.value.detail.lower()


# ==================== Layout Tests ====================


class TestGetNetworkLayout:
    """Tests for get_network_layout endpoint"""

    async def test_get_layout_success(self, owner_user, mock_db, sample_network):
        """Should return network layout"""
        from app.routers.networks import get_network_layout

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await get_network_layout("network-123", owner_user, mock_db)

        assert response.id == sample_network.id
        assert response.layout_data == sample_network.layout_data


class TestSaveNetworkLayout:
    """Tests for save_network_layout endpoint"""

    async def test_save_layout_success(self, owner_user, mock_db, sample_network):
        """Should save network layout"""
        from app.routers.networks import save_network_layout
        from app.schemas import NetworkLayoutSave

        layout_data = NetworkLayoutSave(layout_data={"root": {"id": "new-router"}})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        response = await save_network_layout("network-123", layout_data, owner_user, mock_db)

        assert sample_network.layout_data == {"root": {"id": "new-router"}}


# ==================== Permission Tests ====================


class TestListNetworkPermissions:
    """Tests for list_network_permissions endpoint"""

    async def test_list_permissions_success(self, owner_user, mock_db, sample_network):
        """Owner should see list of permissions"""
        from app.routers.networks import list_network_permissions

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        # Create mock permissions
        mock_perm1 = MagicMock(spec=NetworkPermission)
        mock_perm1.id = 1
        mock_perm1.network_id = "network-123"
        mock_perm1.user_id = "user-1"
        mock_perm1.role = PermissionRole.EDITOR
        mock_perm1.created_at = datetime.now()

        mock_perm_list_result = MagicMock()
        mock_perm_list_result.scalars.return_value.all.return_value = [mock_perm1]

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_list_result])

        response = await list_network_permissions("network-123", owner_user, mock_db)

        assert len(response) == 1
        assert response[0].user_id == "user-1"

    async def test_list_permissions_not_owner(self, admin_user, mock_db, sample_network):
        """Non-owner should not be able to list permissions"""
        from app.routers.networks import list_network_permissions

        # Set up with editor permission
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_permission = MagicMock(spec=NetworkPermission)
        mock_permission.role = PermissionRole.EDITOR

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_permission

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await list_network_permissions("network-123", admin_user, mock_db)

        assert exc_info.value.status_code == 403


class TestCreatePermission:
    """Tests for create_permission endpoint"""

    async def test_create_permission_success(self, owner_user, mock_db, sample_network):
        """Owner should create permission for another user"""
        from app.routers.networks import create_permission
        from app.schemas import PermissionCreate

        perm_data = PermissionCreate(user_id="new-user-123", role=PermissionRole.VIEWER)

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        # Existing check - no existing permission
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_existing_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        async def mock_refresh(perm):
            perm.id = 1
            perm.network_id = "network-123"
            perm.user_id = "new-user-123"
            perm.role = PermissionRole.VIEWER
            perm.created_at = datetime.now()

        mock_db.refresh = mock_refresh

        response = await create_permission("network-123", perm_data, owner_user, mock_db)

        assert response.user_id == "new-user-123"
        assert response.role == PermissionRole.VIEWER

    async def test_create_permission_already_exists(self, owner_user, mock_db, sample_network):
        """Should fail if user already has permission"""
        from app.routers.networks import create_permission
        from app.schemas import PermissionCreate

        perm_data = PermissionCreate(user_id="existing-user", role=PermissionRole.EDITOR)

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        # Existing check - permission already exists
        mock_existing_perm = MagicMock(spec=NetworkPermission)
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = mock_existing_perm

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_existing_result])

        with pytest.raises(HTTPException) as exc_info:
            await create_permission("network-123", perm_data, owner_user, mock_db)

        assert exc_info.value.status_code == 409
        assert "already has access" in exc_info.value.detail.lower()

    async def test_create_permission_self(self, owner_user, mock_db, sample_network):
        """Should not allow sharing with self"""
        from app.routers.networks import create_permission
        from app.schemas import PermissionCreate

        perm_data = PermissionCreate(user_id="owner-123", role=PermissionRole.VIEWER)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await create_permission("network-123", perm_data, owner_user, mock_db)

        assert exc_info.value.status_code == 400
        assert "yourself" in exc_info.value.detail.lower()

    async def test_create_permission_not_owner(self, admin_user, mock_db, sample_network):
        """Non-owner should not be able to share"""
        from app.routers.networks import create_permission
        from app.schemas import PermissionCreate

        perm_data = PermissionCreate(user_id="new-user", role=PermissionRole.VIEWER)

        # Set up with editor permission
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_permission = MagicMock(spec=NetworkPermission)
        mock_permission.role = PermissionRole.EDITOR

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_permission

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await create_permission("network-123", perm_data, admin_user, mock_db)

        assert exc_info.value.status_code == 403


class TestDeletePermission:
    """Tests for delete_permission endpoint"""

    async def test_delete_permission_success(self, owner_user, mock_db, sample_network):
        """Owner should be able to delete permission"""
        from app.routers.networks import delete_permission

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_perm = MagicMock(spec=NetworkPermission)
        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_perm

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        await delete_permission("network-123", "user-to-remove", owner_user, mock_db)

        mock_db.delete.assert_called_once()

    async def test_delete_permission_not_found(self, owner_user, mock_db, sample_network):
        """Should return 404 if permission not found"""
        from app.routers.networks import delete_permission

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await delete_permission("network-123", "nonexistent", owner_user, mock_db)

        assert exc_info.value.status_code == 404

    async def test_delete_permission_not_owner(self, admin_user, mock_db, sample_network):
        """Non-owner should not be able to remove access"""
        from app.routers.networks import delete_permission

        # Set up with editor permission
        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_permission = MagicMock(spec=NetworkPermission)
        mock_permission.role = PermissionRole.EDITOR

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_permission

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await delete_permission("network-123", "user-to-remove", admin_user, mock_db)

        assert exc_info.value.status_code == 403


# ==================== Notification Settings Tests ====================


class TestGetNetworkNotificationSettings:
    """Tests for get_network_notification_settings endpoint"""

    async def test_get_settings_success_existing(self, owner_user, mock_db, sample_network):
        """Owner should see notification settings"""
        from app.routers.networks import get_network_notification_settings

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        # Mock existing notification settings
        mock_settings = MagicMock(spec=NetworkNotificationSettings)
        mock_settings.id = 1
        mock_settings.network_id = "network-123"
        mock_settings.enabled = True
        mock_settings.email_enabled = True
        mock_settings.email_address = "test@example.com"
        mock_settings.discord_enabled = False
        mock_settings.discord_config = None
        mock_settings.preferences = {"device_offline": True}
        mock_settings.created_at = datetime.now()
        mock_settings.updated_at = datetime.now()

        mock_settings_result = MagicMock()
        mock_settings_result.scalar_one_or_none.return_value = mock_settings

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_settings_result])

        response = await get_network_notification_settings("network-123", owner_user, mock_db)

        assert response.enabled is True
        assert response.email_enabled is True

    async def test_get_settings_creates_default(self, owner_user, mock_db, sample_network):
        """Should create default settings if none exist"""
        from app.routers.networks import get_network_notification_settings

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        # No existing settings
        mock_settings_result = MagicMock()
        mock_settings_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_settings_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        async def mock_refresh(settings):
            settings.id = 1
            settings.network_id = "network-123"
            settings.enabled = True
            settings.email_enabled = False
            settings.email_address = None
            settings.discord_enabled = False
            settings.discord_config = None
            settings.preferences = None
            settings.created_at = datetime.now()
            settings.updated_at = datetime.now()

        mock_db.refresh = mock_refresh

        response = await get_network_notification_settings("network-123", owner_user, mock_db)

        assert response.enabled is True
        assert response.email_enabled is False
        mock_db.add.assert_called_once()

    async def test_get_settings_viewer_denied(self, member_user, mock_db, sample_network):
        """Viewers should not access notification settings"""
        from app.routers.networks import get_network_notification_settings

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_permission = MagicMock(spec=NetworkPermission)
        mock_permission.role = PermissionRole.VIEWER

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_permission

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await get_network_notification_settings("network-123", member_user, mock_db)

        assert exc_info.value.status_code == 403
        assert "viewer" in exc_info.value.detail.lower()


class TestUpdateNetworkNotificationSettings:
    """Tests for update_network_notification_settings endpoint"""

    async def test_update_settings_success(self, owner_user, mock_db, sample_network):
        """Owner should update notification settings"""
        from app.routers.networks import update_network_notification_settings
        from app.schemas import (
            DiscordConfigCreate,
            EmailConfigCreate,
            NetworkNotificationSettingsCreate,
            NotificationPreferencesCreate,
        )

        settings_data = NetworkNotificationSettingsCreate(
            enabled=True,
            email=EmailConfigCreate(enabled=True, email_address="new@example.com"),
            discord=DiscordConfigCreate(
                enabled=True,
                delivery_method="dm",
                discord_user_id="123456",
                guild_id=None,
                channel_id=None,
            ),
            preferences=NotificationPreferencesCreate(
                device_offline=True, device_online=False, speed_threshold=True
            ),
        )

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        # Mock existing settings
        mock_settings = MagicMock(spec=NetworkNotificationSettings)
        mock_settings.id = 1
        mock_settings.network_id = "network-123"
        mock_settings.enabled = False

        mock_settings_result = MagicMock()
        mock_settings_result.scalar_one_or_none.return_value = mock_settings

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_settings_result])
        mock_db.commit = AsyncMock()

        async def mock_refresh(settings):
            settings.id = 1
            settings.network_id = "network-123"
            settings.enabled = True
            settings.email_enabled = True
            settings.email_address = "new@example.com"
            settings.discord_enabled = True
            settings.discord_config = {"delivery_method": "dm", "discord_user_id": "123456"}
            settings.preferences = {"device_offline": True, "device_online": False}
            settings.created_at = datetime.now()
            settings.updated_at = datetime.now()

        mock_db.refresh = mock_refresh

        response = await update_network_notification_settings(
            "network-123", settings_data, owner_user, mock_db
        )

        assert response.enabled is True
        assert response.email_enabled is True

    async def test_update_settings_creates_new(self, owner_user, mock_db, sample_network):
        """Should create settings if none exist"""
        from app.routers.networks import update_network_notification_settings
        from app.schemas import NetworkNotificationSettingsCreate

        settings_data = NetworkNotificationSettingsCreate(enabled=True)

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        # No existing settings
        mock_settings_result = MagicMock()
        mock_settings_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_settings_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        async def mock_refresh(settings):
            settings.id = 1
            settings.network_id = "network-123"
            settings.enabled = True
            settings.email_enabled = False
            settings.email_address = None
            settings.discord_enabled = False
            settings.discord_config = None
            settings.preferences = None
            settings.created_at = datetime.now()
            settings.updated_at = datetime.now()

        mock_db.refresh = mock_refresh

        response = await update_network_notification_settings(
            "network-123", settings_data, owner_user, mock_db
        )

        assert response.enabled is True
        mock_db.add.assert_called_once()

    async def test_update_settings_viewer_denied(self, member_user, mock_db, sample_network):
        """Viewers should not modify notification settings"""
        from app.routers.networks import update_network_notification_settings
        from app.schemas import NetworkNotificationSettingsCreate

        settings_data = NetworkNotificationSettingsCreate(enabled=True)

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_permission = MagicMock(spec=NetworkPermission)
        mock_permission.role = PermissionRole.VIEWER

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_permission

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await update_network_notification_settings(
                "network-123", settings_data, member_user, mock_db
            )

        assert exc_info.value.status_code == 403
