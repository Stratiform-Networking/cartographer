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


class TestAgentSyncHelpers:
    """Tests for agent sync helper functions"""

    def test_initialize_layout_data_with_existing_data(self):
        """Should return existing layout data unchanged"""
        from app.routers.networks import _initialize_layout_data

        existing = {"version": 5, "root": {"id": "existing"}}
        result = _initialize_layout_data("Test Network", existing)

        assert result == existing
        assert result["version"] == 5

    def test_initialize_layout_data_creates_new_structure(self):
        """Should create new layout data when none exists"""
        from app.routers.networks import _initialize_layout_data

        result = _initialize_layout_data("Test Network", None)

        assert result["version"] == 1
        assert "timestamp" in result
        assert "positions" in result
        assert result["root"]["id"] == "root"
        assert result["root"]["name"] == "Test Network"
        assert result["root"]["role"] == "gateway/router"
        assert result["root"]["children"] == []

    def test_ensure_root_node_with_existing_root(self):
        """Should return existing root node with children"""
        from app.routers.networks import _ensure_root_node

        layout_data = {"root": {"id": "router-1", "name": "My Router", "children": ["child1"]}}
        root = _ensure_root_node(layout_data, "Test Network")

        assert root["id"] == "router-1"
        assert root["name"] == "My Router"
        assert root["children"] == ["child1"]

    def test_ensure_root_node_creates_missing_root(self):
        """Should create root node if missing"""
        from app.routers.networks import _ensure_root_node

        layout_data = {}
        root = _ensure_root_node(layout_data, "Test Network")

        assert root["id"] == "root"
        assert root["name"] == "Test Network"
        assert root["role"] == "gateway/router"
        assert root["children"] == []
        assert layout_data["root"] == root

    def test_ensure_root_node_adds_missing_children(self):
        """Should add children list if missing"""
        from app.routers.networks import _ensure_root_node

        layout_data = {"root": {"id": "root", "name": "Router"}}
        root = _ensure_root_node(layout_data, "Test Network")

        assert "children" in root
        assert root["children"] == []

    def test_build_nodes_by_ip_single_level(self):
        """Should index nodes by IP address"""
        from app.routers.networks import _build_nodes_by_ip

        root = {
            "id": "root",
            "ip": "192.168.1.1",
            "children": [
                {"id": "node1", "ip": "192.168.1.10", "children": []},
                {"id": "node2", "ip": "192.168.1.20", "children": []},
            ],
        }

        nodes_by_ip = _build_nodes_by_ip(root)

        assert len(nodes_by_ip) == 3
        assert nodes_by_ip["192.168.1.1"]["id"] == "root"
        assert nodes_by_ip["192.168.1.10"]["id"] == "node1"
        assert nodes_by_ip["192.168.1.20"]["id"] == "node2"

    def test_build_nodes_by_ip_nested(self):
        """Should recursively index nested nodes"""
        from app.routers.networks import _build_nodes_by_ip

        root = {
            "id": "root",
            "ip": "192.168.1.1",
            "children": [
                {
                    "id": "switch",
                    "ip": "192.168.1.5",
                    "children": [
                        {"id": "pc1", "ip": "192.168.1.100", "children": []},
                        {"id": "pc2", "ip": "192.168.1.101", "children": []},
                    ],
                }
            ],
        }

        nodes_by_ip = _build_nodes_by_ip(root)

        assert len(nodes_by_ip) == 4
        assert nodes_by_ip["192.168.1.100"]["id"] == "pc1"
        assert nodes_by_ip["192.168.1.101"]["id"] == "pc2"

    def test_build_nodes_by_ip_ignores_nodes_without_ip(self):
        """Should skip nodes without IP addresses"""
        from app.routers.networks import _build_nodes_by_ip

        root = {
            "id": "root",
            "name": "Router",
            "children": [
                {"id": "node1", "ip": "192.168.1.10", "children": []},
                {"id": "node2", "name": "No IP", "children": []},
            ],
        }

        nodes_by_ip = _build_nodes_by_ip(root)

        assert len(nodes_by_ip) == 1
        assert "192.168.1.10" in nodes_by_ip
        assert nodes_by_ip["192.168.1.10"]["id"] == "node1"

    def test_update_existing_device_with_all_fields(self):
        """Should update existing device with new data"""
        from datetime import datetime

        from app.routers.networks import _update_existing_device
        from app.schemas.agent_sync import SyncDevice

        existing_node = {
            "id": "node-1",
            "ip": "192.168.1.10",
            "hostname": None,
            "mac": None,
            "updatedAt": "2024-01-01T00:00:00Z",
        }

        device = SyncDevice(
            ip="192.168.1.10",
            hostname="test-pc",
            mac="AA:BB:CC:DD:EE:FF",
            response_time_ms=12.5,
        )

        now = "2024-12-01T12:00:00Z"
        _update_existing_device(existing_node, device, now)

        assert existing_node["hostname"] == "test-pc"
        assert existing_node["mac"] == "AA:BB:CC:DD:EE:FF"
        assert existing_node["updatedAt"] == now
        assert existing_node["lastSeenAt"] == now
        assert existing_node["lastResponseMs"] == 12.5

    def test_update_existing_device_preserves_existing_hostname(self):
        """Should not overwrite existing hostname"""
        from app.routers.networks import _update_existing_device
        from app.schemas.agent_sync import SyncDevice

        existing_node = {
            "id": "node-1",
            "ip": "192.168.1.10",
            "hostname": "original-name",
            "mac": None,
        }

        device = SyncDevice(ip="192.168.1.10", hostname="new-name")
        now = "2024-12-01T12:00:00Z"

        _update_existing_device(existing_node, device, now)

        assert existing_node["hostname"] == "original-name"

    def test_update_existing_device_preserves_existing_mac(self):
        """Should not overwrite existing MAC address"""
        from app.routers.networks import _update_existing_device
        from app.schemas.agent_sync import SyncDevice

        existing_node = {
            "id": "node-1",
            "ip": "192.168.1.10",
            "hostname": None,
            "mac": "AA:BB:CC:DD:EE:FF",
        }

        device = SyncDevice(ip="192.168.1.10", mac="11:22:33:44:55:66")
        now = "2024-12-01T12:00:00Z"

        _update_existing_device(existing_node, device, now)

        assert existing_node["mac"] == "AA:BB:CC:DD:EE:FF"

    def test_update_existing_device_without_response_time(self):
        """Should handle missing response time"""
        from app.routers.networks import _update_existing_device
        from app.schemas.agent_sync import SyncDevice

        existing_node = {
            "id": "node-1",
            "ip": "192.168.1.10",
            "lastResponseMs": 5.0,
        }

        device = SyncDevice(ip="192.168.1.10", response_time_ms=None)
        now = "2024-12-01T12:00:00Z"

        _update_existing_device(existing_node, device, now)

        # Should not update lastResponseMs if response_time_ms is None
        assert "lastResponseMs" not in existing_node or existing_node.get("lastResponseMs") == 5.0

    def test_create_new_device_node_with_all_fields(self):
        """Should create complete device node"""
        from app.routers.networks import _create_new_device_node
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(
            ip="192.168.1.50",
            hostname="new-device",
            mac="AA:BB:CC:DD:EE:FF",
            response_time_ms=8.5,
            is_gateway=False,
        )

        now = "2024-12-01T12:00:00Z"
        node = _create_new_device_node(device, "root-id", now)

        assert node["name"] == "new-device"
        assert node["ip"] == "192.168.1.50"
        assert node["hostname"] == "new-device"
        assert node["mac"] == "AA:BB:CC:DD:EE:FF"
        assert node["role"] == "client"
        assert node["parentId"] == "root-id"
        assert node["createdAt"] == now
        assert node["updatedAt"] == now
        assert node["lastSeenAt"] == now
        assert node["monitoringEnabled"] is True
        assert node["children"] == []
        assert node["lastResponseMs"] == 8.5
        assert "id" in node

    def test_create_new_device_node_gateway(self):
        """Should create gateway device with correct role"""
        from app.routers.networks import _create_new_device_node
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.1", hostname="gateway", is_gateway=True)

        now = "2024-12-01T12:00:00Z"
        node = _create_new_device_node(device, "root-id", now)

        assert node["role"] == "gateway/router"

    def test_create_new_device_node_without_hostname(self):
        """Should use IP as name when hostname missing"""
        from app.routers.networks import _create_new_device_node
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.100", hostname=None)

        now = "2024-12-01T12:00:00Z"
        node = _create_new_device_node(device, "root-id", now)

        assert node["name"] == "192.168.1.100"

    def test_create_new_device_node_without_response_time(self):
        """Should not include lastResponseMs if no response time"""
        from app.routers.networks import _create_new_device_node
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.100", response_time_ms=None)

        now = "2024-12-01T12:00:00Z"
        node = _create_new_device_node(device, "root-id", now)

        assert "lastResponseMs" not in node

    def test_create_new_device_node_unique_ids(self):
        """Should generate unique IDs for different devices"""
        from app.routers.networks import _create_new_device_node
        from app.schemas.agent_sync import SyncDevice

        device1 = SyncDevice(ip="192.168.1.10")
        device2 = SyncDevice(ip="192.168.1.20")

        now = "2024-12-01T12:00:00Z"
        node1 = _create_new_device_node(device1, "root-id", now)
        node2 = _create_new_device_node(device2, "root-id", now)

        assert node1["id"] != node2["id"]


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
        from app.services.network_service import get_network_member_user_ids

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_network_member_user_ids("nonexistent", mock_db)

        assert exc_info.value.status_code == 404

    async def test_returns_owner_and_members(self, mock_db, sample_network):
        """Should return all user IDs with access"""
        from app.services.network_service import get_network_member_user_ids

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
        from app.services.network_service import get_network_member_user_ids

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

    async def test_create_network_success(self, owner_user, mock_db, mock_cache):
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

        response = await create_network(network_data, owner_user, mock_db, mock_cache)

        assert response.name == "New Network"
        assert response.description == "A new test network"
        assert response.is_owner is True
        mock_db.add.assert_called_once()


class TestListNetworks:
    """Tests for list_networks endpoint"""

    async def test_list_networks_as_service(
        self, service_user, mock_db, sample_network, mock_cache
    ):
        """Service user should see all networks"""
        from app.routers.networks import list_networks

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_network]
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await list_networks(service_user, mock_db, mock_cache)

        assert len(response) == 1
        assert response[0].is_owner is False
        assert response[0].permission == PermissionRole.EDITOR

    async def test_list_networks_as_metrics_service(
        self, metrics_service_user, mock_db, sample_network, mock_cache
    ):
        """Metrics service user should see all networks"""
        from app.routers.networks import list_networks

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_network]
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await list_networks(metrics_service_user, mock_db, mock_cache)

        assert len(response) == 1
        assert response[0].is_owner is False

    async def test_list_networks_as_owner(self, owner_user, mock_db, sample_network, mock_cache):
        """Regular user should see owned networks"""
        from app.routers.networks import list_networks

        # Mock for owned networks
        owned_result = MagicMock()
        owned_result.scalars.return_value.all.return_value = [sample_network]

        # Mock for shared networks (empty)
        shared_result = MagicMock()
        shared_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[owned_result, shared_result])

        response = await list_networks(owner_user, mock_db, mock_cache)

        assert len(response) == 1
        assert response[0].is_owner is True

    async def test_list_networks_with_shared(self, admin_user, mock_db, sample_network, mock_cache):
        """User should see shared networks"""
        from app.routers.networks import list_networks

        # Mock for owned networks (empty)
        owned_result = MagicMock()
        owned_result.scalars.return_value.all.return_value = []

        # Mock for shared networks - returns tuple (network, role)
        shared_result = MagicMock()
        shared_result.all.return_value = [(sample_network, PermissionRole.EDITOR)]

        mock_db.execute = AsyncMock(side_effect=[owned_result, shared_result])

        response = await list_networks(admin_user, mock_db, mock_cache)

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

    async def test_update_network_name(self, owner_user, mock_db, sample_network, mock_cache):
        """Should update network name"""
        from app.routers.networks import update_network
        from app.schemas import NetworkUpdate

        update_data = NetworkUpdate(name="Updated Name")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        response = await update_network("network-123", update_data, owner_user, mock_db, mock_cache)

        assert sample_network.name == "Updated Name"

    async def test_update_network_description(
        self, owner_user, mock_db, sample_network, mock_cache
    ):
        """Should update network description"""
        from app.routers.networks import update_network
        from app.schemas import NetworkUpdate

        update_data = NetworkUpdate(description="New description")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        response = await update_network("network-123", update_data, owner_user, mock_db, mock_cache)

        assert sample_network.description == "New description"

    async def test_update_network_partial(self, owner_user, mock_db, sample_network, mock_cache):
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

        response = await update_network("network-123", update_data, owner_user, mock_db, mock_cache)

        # Name should not change
        assert sample_network.name == original_name
        assert sample_network.description == "Only desc"


class TestDeleteNetwork:
    """Tests for delete_network endpoint"""

    async def test_delete_network_success(self, owner_user, mock_db, sample_network, mock_cache):
        """Owner should be able to delete network"""
        from app.routers.networks import delete_network

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        # Should not raise
        await delete_network("network-123", owner_user, mock_db, mock_cache)

        mock_db.delete.assert_called_once()

    async def test_delete_network_not_owner(self, admin_user, mock_db, sample_network, mock_cache):
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
            await delete_network("network-123", admin_user, mock_db, mock_cache)

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

    async def test_create_permission_success(self, owner_user, mock_db, sample_network, mock_cache):
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

        response = await create_permission(
            "network-123", perm_data, owner_user, mock_db, mock_cache
        )

        assert response.user_id == "new-user-123"
        assert response.role == PermissionRole.VIEWER

    async def test_create_permission_already_exists(
        self, owner_user, mock_db, sample_network, mock_cache
    ):
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
            await create_permission("network-123", perm_data, owner_user, mock_db, mock_cache)

        assert exc_info.value.status_code == 409
        assert "already has access" in exc_info.value.detail.lower()

    async def test_create_permission_self(self, owner_user, mock_db, sample_network, mock_cache):
        """Should not allow sharing with self"""
        from app.routers.networks import create_permission
        from app.schemas import PermissionCreate

        perm_data = PermissionCreate(user_id="owner-123", role=PermissionRole.VIEWER)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_network
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await create_permission("network-123", perm_data, owner_user, mock_db, mock_cache)

        assert exc_info.value.status_code == 400
        assert "yourself" in exc_info.value.detail.lower()

    async def test_create_permission_not_owner(
        self, admin_user, mock_db, sample_network, mock_cache
    ):
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
            await create_permission("network-123", perm_data, admin_user, mock_db, mock_cache)

        assert exc_info.value.status_code == 403


class TestDeletePermission:
    """Tests for delete_permission endpoint"""

    async def test_delete_permission_success(self, owner_user, mock_db, sample_network, mock_cache):
        """Owner should be able to delete permission"""
        from app.routers.networks import delete_permission

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_perm = MagicMock(spec=NetworkPermission)
        mock_perm.user_id = "user-to-remove"
        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = mock_perm

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        await delete_permission("network-123", "user-to-remove", owner_user, mock_db, mock_cache)

        mock_db.delete.assert_called_once()

    async def test_delete_permission_not_found(
        self, owner_user, mock_db, sample_network, mock_cache
    ):
        """Should return 404 if permission not found"""
        from app.routers.networks import delete_permission

        mock_network_result = MagicMock()
        mock_network_result.scalar_one_or_none.return_value = sample_network

        mock_perm_result = MagicMock()
        mock_perm_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_network_result, mock_perm_result])

        with pytest.raises(HTTPException) as exc_info:
            await delete_permission("network-123", "nonexistent", owner_user, mock_db, mock_cache)

        assert exc_info.value.status_code == 404

    async def test_delete_permission_not_owner(
        self, admin_user, mock_db, sample_network, mock_cache
    ):
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
            await delete_permission(
                "network-123", "user-to-remove", admin_user, mock_db, mock_cache
            )

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


# ==================== Device Classification Tests ====================


class TestDeviceClassification:
    """Tests for device role classification based on hostname patterns"""

    def test_classify_gateway_by_is_gateway_flag(self):
        """Device with is_gateway=True should be classified as gateway/router"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.1", hostname="some-device", is_gateway=True)
        role = _classify_device_role(device)

        assert role == "gateway/router"

    def test_classify_gateway_by_hostname_routerboard(self):
        """Device with 'routerboard' in hostname should be gateway/router"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.1", hostname="routerboard.lan")
        role = _classify_device_role(device)

        assert role == "gateway/router"

    def test_classify_switch_by_hostname(self):
        """Device with switch-related hostname should be switch/ap"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        test_cases = [
            ("tl-sg108e.lan", "switch/ap"),
            ("unifi-switch.local", "switch/ap"),
            ("cisco-2960.lan", "switch/ap"),
            ("netgear-gs108.lan", "switch/ap"),
        ]

        for hostname, expected_role in test_cases:
            device = SyncDevice(ip="192.168.1.10", hostname=hostname)
            role = _classify_device_role(device)
            assert role == expected_role, f"Expected {expected_role} for {hostname}, got {role}"

    def test_classify_firewall_by_hostname(self):
        """Device with firewall-related hostname should be firewall"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        test_cases = [
            "firewalla.lan",
            "pfsense.local",
            "opnsense.lan",
        ]

        for hostname in test_cases:
            device = SyncDevice(ip="192.168.1.10", hostname=hostname)
            role = _classify_device_role(device)
            assert role == "firewall", f"Expected firewall for {hostname}, got {role}"

    def test_classify_nas_by_hostname(self):
        """Device with NAS-related hostname should be nas"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        test_cases = [
            "synology-nas.lan",
            "qnap-ts.local",
            "ugreen-nas.lan",
            "mynas.local",
        ]

        for hostname in test_cases:
            device = SyncDevice(ip="192.168.1.10", hostname=hostname)
            role = _classify_device_role(device)
            assert role == "nas", f"Expected nas for {hostname}, got {role}"

    def test_classify_server_by_hostname(self):
        """Device with server-related hostname should be server"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        test_cases = [
            "ubuntu-server.lan",
            "debian-vm.local",
            "proxmox.lan",
        ]

        for hostname in test_cases:
            device = SyncDevice(ip="192.168.1.10", hostname=hostname)
            role = _classify_device_role(device)
            assert role == "server", f"Expected server for {hostname}, got {role}"

    def test_classify_service_by_hostname(self):
        """Device with service-related hostname should be service"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        test_cases = [
            "jellyfin.lan",
            "plex.local",
            "grafana.lan",
            "home-assistant.local",
            "pihole.lan",
        ]

        for hostname in test_cases:
            device = SyncDevice(ip="192.168.1.10", hostname=hostname)
            role = _classify_device_role(device)
            assert role == "service", f"Expected service for {hostname}, got {role}"

    def test_classify_client_by_default(self):
        """Device without recognized hostname should be client"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.100", hostname="johns-iphone.lan")
        role = _classify_device_role(device)

        assert role == "client"

    def test_classify_client_without_hostname(self):
        """Device without hostname should be client"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.100", hostname=None)
        role = _classify_device_role(device)

        assert role == "client"

    def test_classify_case_insensitive(self):
        """Classification should be case-insensitive"""
        from app.routers.networks import _classify_device_role
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.10", hostname="SYNOLOGY-NAS.LAN")
        role = _classify_device_role(device)

        assert role == "nas"


class TestGroupAssignment:
    """Tests for assigning devices to groups based on role"""

    def test_get_group_for_gateway(self):
        """Non-primary routers should go to Infrastructure group"""
        from app.routers.networks import _get_group_for_role

        # Gateway/router devices that aren't the primary gateway go to Infrastructure
        group = _get_group_for_role("gateway/router")
        assert group == "Infrastructure"

    def test_get_group_for_infrastructure(self):
        """Switches and firewalls should go to Infrastructure"""
        from app.routers.networks import _get_group_for_role

        assert _get_group_for_role("switch/ap") == "Infrastructure"
        assert _get_group_for_role("firewall") == "Infrastructure"

    def test_get_group_for_servers(self):
        """Servers, NAS, and services should go to Servers"""
        from app.routers.networks import _get_group_for_role

        assert _get_group_for_role("server") == "Servers"
        assert _get_group_for_role("nas") == "Servers"
        assert _get_group_for_role("service") == "Servers"

    def test_get_group_for_clients(self):
        """Clients should go to Clients group"""
        from app.routers.networks import _get_group_for_role

        assert _get_group_for_role("client") == "Clients"
        assert _get_group_for_role("unknown") == "Clients"


class TestEnsureGroupsExist:
    """Tests for ensuring group nodes exist in layout"""

    def test_creates_all_groups_when_none_exist(self):
        """Should create Infrastructure, Servers, and Clients groups"""
        from app.routers.networks import _ensure_groups_exist

        root = {"id": "root", "children": []}
        groups = _ensure_groups_exist(root)

        assert "Infrastructure" in groups
        assert "Servers" in groups
        assert "Clients" in groups
        assert len(root["children"]) == 3

    def test_preserves_existing_groups(self):
        """Should not duplicate existing group nodes"""
        from app.routers.networks import _ensure_groups_exist

        existing_group = {
            "id": "group:infrastructure",
            "name": "Infrastructure",
            "role": "group",
            "children": [{"id": "switch-1"}],
        }
        root = {"id": "root", "children": [existing_group]}
        groups = _ensure_groups_exist(root)

        assert groups["Infrastructure"] == existing_group
        assert len(groups["Infrastructure"]["children"]) == 1

    def test_creates_missing_groups_only(self):
        """Should only create groups that don't exist"""
        from app.routers.networks import _ensure_groups_exist

        existing_group = {
            "id": "group:servers",
            "name": "Servers",
            "role": "group",
            "children": [],
        }
        root = {"id": "root", "children": [existing_group]}
        groups = _ensure_groups_exist(root)

        # Should have 3 groups now
        assert len(groups) == 3
        assert groups["Servers"] == existing_group


class TestFindDeviceInGroups:
    """Tests for finding devices within groups"""

    def test_finds_device_by_ip(self):
        """Should find device in any group by IP"""
        from app.routers.networks import _find_device_in_groups

        device = {"id": "device-1", "ip": "192.168.1.50"}
        groups = {
            "Infrastructure": {"children": []},
            "Servers": {"children": [device]},
            "Clients": {"children": []},
        }

        found = _find_device_in_groups(groups, "192.168.1.50")
        assert found == device

    def test_returns_none_when_not_found(self):
        """Should return None when device not in any group"""
        from app.routers.networks import _find_device_in_groups

        groups = {
            "Infrastructure": {"children": []},
            "Servers": {"children": [{"id": "other", "ip": "192.168.1.10"}]},
            "Clients": {"children": []},
        }

        found = _find_device_in_groups(groups, "192.168.1.50")
        assert found is None


class TestUpdateRootWithGateway:
    """Tests for updating root node with gateway device"""

    def test_updates_placeholder_root(self):
        """Should update root when it has no IP (placeholder)"""
        from app.routers.networks import _update_root_with_gateway
        from app.schemas.agent_sync import SyncDevice

        root = {"id": "root", "name": "Test Network", "role": "gateway/router"}
        gateway = SyncDevice(
            ip="192.168.1.1",
            hostname="router.lan",
            mac="AA:BB:CC:DD:EE:FF",
            response_time_ms=1.5,
        )

        result = _update_root_with_gateway(root, gateway, "2024-01-01T00:00:00Z")

        assert result is True
        assert root["ip"] == "192.168.1.1"
        assert root["hostname"] == "router.lan"
        assert root["mac"] == "AA:BB:CC:DD:EE:FF"
        assert root["name"] == "192.168.1.1 (router.lan)"
        assert root["lastResponseMs"] == 1.5

    def test_updates_matching_gateway_ip(self):
        """Should update root when it matches gateway IP"""
        from app.routers.networks import _update_root_with_gateway
        from app.schemas.agent_sync import SyncDevice

        root = {"id": "root", "ip": "192.168.1.1", "name": "Old Name"}
        gateway = SyncDevice(ip="192.168.1.1", hostname="new-name.lan")

        result = _update_root_with_gateway(root, gateway, "2024-01-01T00:00:00Z")

        assert result is True
        assert root["name"] == "192.168.1.1 (new-name.lan)"

    def test_skips_different_gateway_ip(self):
        """Should not update root when it has different IP"""
        from app.routers.networks import _update_root_with_gateway
        from app.schemas.agent_sync import SyncDevice

        root = {"id": "root", "ip": "192.168.1.1", "name": "Original"}
        gateway = SyncDevice(ip="192.168.1.254", hostname="new-gateway.lan")

        result = _update_root_with_gateway(root, gateway, "2024-01-01T00:00:00Z")

        assert result is False
        assert root["name"] == "Original"

    def test_handles_no_hostname(self):
        """Should use IP as name when hostname is None"""
        from app.routers.networks import _update_root_with_gateway
        from app.schemas.agent_sync import SyncDevice

        root = {"id": "root"}
        gateway = SyncDevice(ip="192.168.1.1", hostname=None)

        _update_root_with_gateway(root, gateway, "2024-01-01T00:00:00Z")

        assert root["name"] == "192.168.1.1"


class TestBuildNodesbyIPWithGroups:
    """Tests for building IP index including grouped devices"""

    def test_includes_root_ip(self):
        """Should include root node if it has IP"""
        from app.routers.networks import _build_nodes_by_ip_with_groups

        root = {"id": "root", "ip": "192.168.1.1", "children": []}
        groups = {"Clients": {"children": []}}

        nodes = _build_nodes_by_ip_with_groups(root, groups)

        assert "192.168.1.1" in nodes
        assert nodes["192.168.1.1"]["id"] == "root"

    def test_includes_grouped_devices(self):
        """Should include devices from all groups"""
        from app.routers.networks import _build_nodes_by_ip_with_groups

        device1 = {"id": "d1", "ip": "192.168.1.10"}
        device2 = {"id": "d2", "ip": "192.168.1.20"}
        root = {"id": "root", "children": []}
        groups = {
            "Infrastructure": {"children": [device1]},
            "Clients": {"children": [device2]},
        }

        nodes = _build_nodes_by_ip_with_groups(root, groups)

        assert "192.168.1.10" in nodes
        assert "192.168.1.20" in nodes

    def test_includes_legacy_flat_devices(self):
        """Should include devices directly under root (legacy)"""
        from app.routers.networks import _build_nodes_by_ip_with_groups

        legacy_device = {"id": "legacy", "ip": "192.168.1.50", "role": "client"}
        root = {"id": "root", "children": [legacy_device]}
        groups = {"Clients": {"children": []}}

        nodes = _build_nodes_by_ip_with_groups(root, groups)

        assert "192.168.1.50" in nodes


class TestMigrateLegacyDevices:
    """Tests for migrating flat devices into groups"""

    def test_migrates_client_to_clients_group(self):
        """Should move client devices to Clients group"""
        from app.routers.networks import _migrate_legacy_devices

        device = {"id": "d1", "ip": "192.168.1.50", "role": "client"}
        root = {"id": "root", "ip": "192.168.1.1", "children": [device]}
        groups = {
            "Infrastructure": {"id": "group:infrastructure", "children": []},
            "Servers": {"id": "group:servers", "children": []},
            "Clients": {"id": "group:clients", "children": []},
        }

        _migrate_legacy_devices(root, groups)

        assert device in groups["Clients"]["children"]
        assert device not in root["children"]

    def test_preserves_group_nodes(self):
        """Should not migrate group nodes"""
        from app.routers.networks import _migrate_legacy_devices

        group_node = {"id": "group:clients", "role": "group", "children": []}
        root = {"id": "root", "children": [group_node]}
        groups = {"Clients": {"id": "group:clients", "children": []}}

        _migrate_legacy_devices(root, groups)

        assert group_node in root["children"]

    def test_skips_root_ip_device(self):
        """Should not migrate device with same IP as root"""
        from app.routers.networks import _migrate_legacy_devices

        device = {"id": "d1", "ip": "192.168.1.1", "role": "gateway/router"}
        root = {"id": "root", "ip": "192.168.1.1", "children": [device]}
        groups = {"Clients": {"id": "group:clients", "children": []}}

        _migrate_legacy_devices(root, groups)

        # Device should not be in any group
        assert device not in groups["Clients"]["children"]


class TestProcessDeviceSync:
    """Tests for processing individual devices during sync"""

    def test_skips_gateway_device(self):
        """Should skip device matching gateway IP"""
        from app.routers.networks import _process_device_sync
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.1")
        groups = {"Clients": {"id": "group:clients", "children": []}}
        nodes_by_ip = {}

        added, updated = _process_device_sync(
            device, "192.168.1.1", groups, nodes_by_ip, "2024-01-01T00:00:00Z"
        )

        assert added == 0
        assert updated == 0

    def test_updates_existing_device(self):
        """Should update device if already exists"""
        from app.routers.networks import _process_device_sync
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.50", hostname="updated.lan")
        existing = {"id": "d1", "ip": "192.168.1.50", "role": "client"}
        groups = {"Clients": {"id": "group:clients", "children": []}}
        nodes_by_ip = {"192.168.1.50": existing}

        added, updated = _process_device_sync(
            device, None, groups, nodes_by_ip, "2024-01-01T00:00:00Z"
        )

        assert added == 0
        assert updated == 1

    def test_creates_new_device(self):
        """Should create new device if not exists"""
        from app.routers.networks import _process_device_sync
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.50")
        groups = {"Clients": {"id": "group:clients", "children": []}}
        nodes_by_ip = {}

        added, updated = _process_device_sync(
            device, None, groups, nodes_by_ip, "2024-01-01T00:00:00Z"
        )

        assert added == 1
        assert updated == 0
        assert len(groups["Clients"]["children"]) == 1

    def test_upgrades_client_role(self):
        """Should upgrade role from client to more specific role"""
        from app.routers.networks import _process_device_sync
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(ip="192.168.1.50", hostname="synology-nas.lan")
        existing = {"id": "d1", "ip": "192.168.1.50", "role": "client"}
        groups = {
            "Servers": {"id": "group:servers", "children": []},
            "Clients": {"id": "group:clients", "children": []},
        }
        nodes_by_ip = {"192.168.1.50": existing}

        _process_device_sync(device, None, groups, nodes_by_ip, "2024-01-01T00:00:00Z")

        assert existing["role"] == "nas"
