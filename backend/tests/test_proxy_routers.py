"""
Comprehensive tests for all proxy routers.
Tests endpoint routing, authentication, and request forwarding.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.dependencies.auth import AuthenticatedUser, UserRole

# ==================== Fixtures ====================


@pytest.fixture
def owner_user():
    return AuthenticatedUser(user_id="owner-123", username="owner", role=UserRole.OWNER)


@pytest.fixture
def readwrite_user():
    return AuthenticatedUser(user_id="rw-123", username="admin", role=UserRole.ADMIN)


@pytest.fixture
def readonly_user():
    return AuthenticatedUser(user_id="ro-123", username="member", role=UserRole.MEMBER)


def create_mock_response(content=None, status_code=200):
    """Create a mock JSONResponse"""
    if content is None:
        content = {"success": True}
    return JSONResponse(content=content, status_code=status_code)


# ==================== Health Proxy Tests ====================


class TestHealthProxyRouter:
    """Tests for health proxy router endpoints"""

    @pytest.fixture(autouse=True)
    def mock_http_pool(self):
        """Mock http_pool for health proxy tests"""
        with patch("app.services.proxy_service.http_pool") as mock:
            mock.request = AsyncMock(return_value=create_mock_response())
            yield mock

    async def test_proxy_request_forwards_correctly(self, mock_http_pool):
        """proxy_health_request should forward to health service"""
        from app.services.proxy_service import proxy_health_request

        await proxy_health_request("GET", "/check/192.168.1.1", params={"include_ports": True})

        mock_http_pool.request.assert_called_once_with(
            service_name="health",
            method="GET",
            path="/api/health/check/192.168.1.1",
            params={"include_ports": True},
            json_body=None,
            headers=None,
            timeout=30.0,
        )

    async def test_check_device_requires_auth(self, mock_http_pool, owner_user):
        """check_device endpoint should work with authenticated user"""
        from app.routers.health_proxy import check_device

        result = await check_device(
            ip="192.168.1.1", include_ports=True, include_dns=False, user=owner_user
        )

        assert mock_http_pool.request.called

    async def test_check_batch_with_body(self, mock_http_pool, owner_user):
        """check_batch should forward request body"""
        from app.routers.health_proxy import check_batch

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"ips": ["192.168.1.1", "192.168.1.2"]})

        await check_batch(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["json_body"] == {"ips": ["192.168.1.1", "192.168.1.2"]}

    async def test_get_cached_ip(self, mock_http_pool, owner_user):
        """get_cached should forward IP parameter"""
        from app.routers.health_proxy import get_cached

        await get_cached(ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/cached/192.168.1.1" in call_kwargs["path"]

    async def test_get_all_cached(self, mock_http_pool, owner_user, mock_cache):
        """get_all_cached should request all cached metrics"""
        from app.routers.health_proxy import get_all_cached

        await get_all_cached(user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["path"].endswith("/cached")

    async def test_clear_cache_requires_write(self, mock_http_pool, readwrite_user):
        """clear_cache should work with write access"""
        from app.routers.health_proxy import clear_cache

        await clear_cache(user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_ping_with_count(self, mock_http_pool, owner_user):
        """ping should forward count parameter"""
        from app.routers.health_proxy import ping

        await ping(ip="192.168.1.1", count=5, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["count"] == 5

    async def test_scan_ports(self, mock_http_pool, owner_user):
        """scan_ports should forward IP"""
        from app.routers.health_proxy import scan_ports

        await scan_ports(ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/ports/192.168.1.1" in call_kwargs["path"]

    async def test_check_dns(self, mock_http_pool, owner_user):
        """check_dns should forward IP"""
        from app.routers.health_proxy import check_dns

        await check_dns(ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/dns/192.168.1.1" in call_kwargs["path"]

    async def test_register_devices(self, mock_http_pool, readwrite_user):
        """register_devices should forward body with write access"""
        from app.routers.health_proxy import register_devices

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"ips": ["192.168.1.1"], "network_id": 1})

        await register_devices(request=mock_request, user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert "/monitoring/devices" in call_kwargs["path"]

    async def test_get_monitored_devices(self, mock_http_pool, owner_user):
        """get_monitored_devices should work"""
        from app.routers.health_proxy import get_monitored_devices

        await get_monitored_devices(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "GET"

    async def test_clear_monitored_devices(self, mock_http_pool, readwrite_user):
        """clear_monitored_devices should use DELETE"""
        from app.routers.health_proxy import clear_monitored_devices

        await clear_monitored_devices(user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_get_monitoring_config(self, mock_http_pool, owner_user):
        """get_monitoring_config should work"""
        from app.routers.health_proxy import get_monitoring_config

        await get_monitoring_config(user=owner_user)

        assert mock_http_pool.request.called

    async def test_set_monitoring_config(self, mock_http_pool, readwrite_user):
        """set_monitoring_config should forward body"""
        from app.routers.health_proxy import set_monitoring_config

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"interval": 60})

        await set_monitoring_config(request=mock_request, user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["json_body"] == {"interval": 60}

    async def test_get_monitoring_status(self, mock_http_pool, owner_user, mock_cache):
        """get_monitoring_status should work"""
        from app.routers.health_proxy import get_monitoring_status

        await get_monitoring_status(user=owner_user, cache=mock_cache)

        assert mock_http_pool.request.called

    async def test_start_monitoring(self, mock_http_pool, readwrite_user):
        """start_monitoring should POST"""
        from app.routers.health_proxy import start_monitoring

        await start_monitoring(user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert "/monitoring/start" in call_kwargs["path"]

    async def test_stop_monitoring(self, mock_http_pool, readwrite_user):
        """stop_monitoring should POST"""
        from app.routers.health_proxy import stop_monitoring

        await stop_monitoring(user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert "/monitoring/stop" in call_kwargs["path"]

    async def test_trigger_check(self, mock_http_pool, readwrite_user):
        """trigger_check should POST to check-now"""
        from app.routers.health_proxy import trigger_check

        await trigger_check(user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/monitoring/check-now" in call_kwargs["path"]

    async def test_get_all_gateway_test_ips(self, mock_http_pool, owner_user):
        """get_all_gateway_test_ips should work"""
        from app.routers.health_proxy import get_all_gateway_test_ips

        await get_all_gateway_test_ips(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/gateway/test-ips/all" in call_kwargs["path"]

    async def test_set_gateway_test_ips(self, mock_http_pool, readwrite_user):
        """set_gateway_test_ips should forward body"""
        from app.routers.health_proxy import set_gateway_test_ips

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"test_ips": ["8.8.8.8"]})

        await set_gateway_test_ips(
            gateway_ip="192.168.1.1", request=mock_request, user=readwrite_user
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/gateway/192.168.1.1/test-ips" in call_kwargs["path"]

    async def test_get_gateway_test_ips(self, mock_http_pool, owner_user):
        """get_gateway_test_ips should work"""
        from app.routers.health_proxy import get_gateway_test_ips

        await get_gateway_test_ips(gateway_ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/gateway/192.168.1.1/test-ips" in call_kwargs["path"]

    async def test_remove_gateway_test_ips(self, mock_http_pool, readwrite_user):
        """remove_gateway_test_ips should DELETE"""
        from app.routers.health_proxy import remove_gateway_test_ips

        await remove_gateway_test_ips(gateway_ip="192.168.1.1", user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_check_gateway_test_ips(self, mock_http_pool, owner_user):
        """check_gateway_test_ips should GET"""
        from app.routers.health_proxy import check_gateway_test_ips

        await check_gateway_test_ips(gateway_ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/test-ips/check" in call_kwargs["path"]

    async def test_get_cached_test_ip_metrics(self, mock_http_pool, owner_user):
        """get_cached_test_ip_metrics should GET"""
        from app.routers.health_proxy import get_cached_test_ip_metrics

        await get_cached_test_ip_metrics(gateway_ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/test-ips/cached" in call_kwargs["path"]

    async def test_run_speed_test(self, mock_http_pool, readwrite_user):
        """run_speed_test should POST with extended timeout"""
        from app.routers.health_proxy import run_speed_test

        await run_speed_test(user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["timeout"] == 120.0

    async def test_get_all_speed_tests(self, mock_http_pool, owner_user):
        """get_all_speed_tests should GET"""
        from app.routers.health_proxy import get_all_speed_tests

        await get_all_speed_tests(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/speedtest/all" in call_kwargs["path"]

    async def test_get_gateway_speed_test(self, mock_http_pool, owner_user):
        """get_gateway_speed_test should GET with gateway IP"""
        from app.routers.health_proxy import get_gateway_speed_test

        await get_gateway_speed_test(gateway_ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/gateway/192.168.1.1/speedtest" in call_kwargs["path"]

    async def test_run_gateway_speed_test(self, mock_http_pool, readwrite_user):
        """run_gateway_speed_test should POST with extended timeout"""
        from app.routers.health_proxy import run_gateway_speed_test

        await run_gateway_speed_test(gateway_ip="192.168.1.1", user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["timeout"] == 120.0


# ==================== Auth Proxy Tests ====================


class TestAuthProxyRouter:
    """Tests for auth proxy router endpoints"""

    @pytest.fixture(autouse=True)
    def mock_http_pool(self):
        """Mock http_pool for auth proxy tests"""
        with patch("app.services.proxy_service.http_pool") as mock:
            mock.request = AsyncMock(return_value=create_mock_response())
            yield mock

    async def test_proxy_request_forwards_auth_header(self, mock_http_pool):
        """proxy_auth_request should forward Authorization header"""
        from app.services.proxy_service import proxy_auth_request

        mock_request = MagicMock()
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value="Bearer test-token")

        await proxy_auth_request("POST", "/verify", mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "Authorization" in call_kwargs["headers"]

    async def test_get_setup_status(self, mock_http_pool):
        """get_setup_status should work without auth"""
        from app.routers.auth_proxy import get_setup_status

        mock_request = MagicMock()
        mock_request.headers = {}

        await get_setup_status(request=mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/setup/status" in call_kwargs["path"]

    async def test_setup_owner(self, mock_http_pool):
        """setup_owner should forward body"""
        from app.routers.auth_proxy import setup_owner

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.json = AsyncMock(return_value={"username": "admin", "password": "secret"})

        await setup_owner(request=mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["json_body"] == {"username": "admin", "password": "secret"}

    async def test_login(self, mock_http_pool):
        """login should forward credentials"""
        from app.routers.auth_proxy import login

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.json = AsyncMock(return_value={"username": "user", "password": "pass"})

        await login(request=mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert "/login" in call_kwargs["path"]

    async def test_logout(self, mock_http_pool, owner_user):
        """logout should POST (requires auth)"""
        from app.routers.auth_proxy import logout

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await logout(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/logout" in call_kwargs["path"]

    async def test_get_session(self, mock_http_pool, owner_user, mock_cache):
        """get_session should GET (requires auth)"""
        from app.routers.auth_proxy import get_session

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await get_session(request=mock_request, user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "GET"
        assert "/session" in call_kwargs["path"]

    async def test_verify_token(self, mock_http_pool):
        """verify_token should POST"""
        from app.routers.auth_proxy import verify_token

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await verify_token(request=mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/verify" in call_kwargs["path"]

    async def test_list_users(self, mock_http_pool, owner_user):
        """list_users should GET (requires auth)"""
        from app.routers.auth_proxy import list_users

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await list_users(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/users" in call_kwargs["path"]

    async def test_create_user(self, mock_http_pool, owner_user):
        """create_user should POST with body (requires owner)"""
        from app.routers.auth_proxy import create_user

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}
        mock_request.json = AsyncMock(return_value={"username": "newuser", "role": "readonly"})

        await create_user(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"

    async def test_get_user(self, mock_http_pool, owner_user):
        """get_user should GET by ID (requires auth)"""
        from app.routers.auth_proxy import get_user

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await get_user(user_id="user-123", request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/users/user-123" in call_kwargs["path"]

    async def test_update_user(self, mock_http_pool, owner_user):
        """update_user should PATCH (requires auth)"""
        from app.routers.auth_proxy import update_user

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}
        mock_request.json = AsyncMock(return_value={"role": "readwrite"})

        await update_user(user_id="user-123", request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "PATCH"

    async def test_delete_user(self, mock_http_pool, owner_user):
        """delete_user should DELETE (requires owner)"""
        from app.routers.auth_proxy import delete_user

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await delete_user(user_id="user-123", request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_get_current_profile(self, mock_http_pool, owner_user):
        """get_current_profile should GET /me (requires auth)"""
        from app.routers.auth_proxy import get_current_profile

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await get_current_profile(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/me" in call_kwargs["path"]

    async def test_update_current_profile(self, mock_http_pool, owner_user):
        """update_current_profile should PATCH /me (requires auth)"""
        from app.routers.auth_proxy import update_current_profile

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}
        mock_request.json = AsyncMock(return_value={"display_name": "New Name"})

        await update_current_profile(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "PATCH"

    async def test_change_password(self, mock_http_pool, owner_user):
        """change_password should POST (requires auth)"""
        from app.routers.auth_proxy import change_password

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}
        mock_request.json = AsyncMock(return_value={"old_password": "old", "new_password": "new"})

        await change_password(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/change-password" in call_kwargs["path"]

    async def test_list_invites(self, mock_http_pool, owner_user):
        """list_invites should GET (requires owner)"""
        from app.routers.auth_proxy import list_invites

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await list_invites(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/invites" in call_kwargs["path"]

    async def test_create_invite(self, mock_http_pool, owner_user):
        """create_invite should POST (requires owner)"""
        from app.routers.auth_proxy import create_invite

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}
        mock_request.json = AsyncMock(return_value={"email": "test@example.com"})

        await create_invite(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"

    async def test_get_invite(self, mock_http_pool, owner_user):
        """get_invite should GET by ID (requires owner)"""
        from app.routers.auth_proxy import get_invite

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await get_invite(invite_id="inv-123", request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/invites/inv-123" in call_kwargs["path"]

    async def test_revoke_invite(self, mock_http_pool, owner_user):
        """revoke_invite should DELETE (requires owner)"""
        from app.routers.auth_proxy import revoke_invite

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await revoke_invite(invite_id="inv-123", request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_resend_invite(self, mock_http_pool, owner_user):
        """resend_invite should POST (requires owner)"""
        from app.routers.auth_proxy import resend_invite

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer token"}

        await resend_invite(invite_id="inv-123", request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/resend" in call_kwargs["path"]

    async def test_verify_invite_token(self, mock_http_pool):
        """verify_invite_token should GET"""
        from app.routers.auth_proxy import verify_invite_token

        mock_request = MagicMock()
        mock_request.headers = {}

        await verify_invite_token(token="invite-token", request=mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/invite/verify/invite-token" in call_kwargs["path"]

    async def test_accept_invite(self, mock_http_pool):
        """accept_invite should POST"""
        from app.routers.auth_proxy import accept_invite

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.json = AsyncMock(return_value={"token": "invite-token", "password": "newpass"})

        await accept_invite(request=mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/invite/accept" in call_kwargs["path"]


# ==================== Metrics Proxy Tests ====================


class TestMetricsProxyRouter:
    """Tests for metrics proxy router endpoints"""

    @pytest.fixture(autouse=True)
    def mock_http_pool(self):
        """Mock http_pool for metrics proxy tests"""
        with patch("app.services.proxy_service.http_pool") as mock:
            mock.request = AsyncMock(return_value=create_mock_response())
            yield mock

    async def test_proxy_request_forwards_correctly(self, mock_http_pool):
        """proxy_metrics_request should forward to metrics service"""
        from app.services.proxy_service import proxy_metrics_request

        await proxy_metrics_request("GET", "/snapshot")

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["service_name"] == "metrics"
        assert "/api/metrics/snapshot" in call_kwargs["path"]

    async def test_get_snapshot(self, mock_http_pool, owner_user):
        """get_snapshot should GET"""
        from app.routers.metrics_proxy import get_snapshot

        await get_snapshot(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/snapshot" in call_kwargs["path"]

    async def test_get_snapshot_with_network_id(self, mock_http_pool, owner_user):
        """get_snapshot should pass network_id param"""
        from app.routers.metrics_proxy import get_snapshot

        await get_snapshot(network_id="net-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "net-123"

    async def test_generate_snapshot(self, mock_http_pool, readwrite_user):
        """generate_snapshot should POST"""
        from app.routers.metrics_proxy import generate_snapshot

        await generate_snapshot(user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert "/generate" in call_kwargs["path"]

    async def test_generate_snapshot_with_network_id(self, mock_http_pool, readwrite_user):
        """generate_snapshot should pass network_id param"""
        from app.routers.metrics_proxy import generate_snapshot

        await generate_snapshot(network_id="net-456", user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "net-456"

    async def test_publish_snapshot(self, mock_http_pool, readwrite_user):
        """publish_snapshot should POST"""
        from app.routers.metrics_proxy import publish_snapshot

        await publish_snapshot(user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/publish" in call_kwargs["path"]

    async def test_publish_snapshot_with_network_id(self, mock_http_pool, readwrite_user):
        """publish_snapshot should pass network_id param"""
        from app.routers.metrics_proxy import publish_snapshot

        await publish_snapshot(network_id="net-789", user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "net-789"

    async def test_get_cached_snapshot(self, mock_http_pool, owner_user):
        """get_cached_snapshot should GET"""
        from app.routers.metrics_proxy import get_cached_snapshot

        await get_cached_snapshot(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/cached" in call_kwargs["path"]

    async def test_get_config(self, mock_http_pool, owner_user, mock_cache):
        """get_config should GET"""
        from app.routers.metrics_proxy import get_config

        await get_config(user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/config" in call_kwargs["path"]

    async def test_update_config(self, mock_http_pool, readwrite_user):
        """update_config should POST with body"""
        from app.routers.metrics_proxy import update_config

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"refresh_interval": 30})

        await update_config(request=mock_request, user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["json_body"] == {"refresh_interval": 30}

    async def test_get_summary(self, mock_http_pool, owner_user, mock_cache):
        """get_summary should GET"""
        from app.routers.metrics_proxy import get_summary

        await get_summary(user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/summary" in call_kwargs["path"]

    async def test_get_summary_with_network_id(self, mock_http_pool, owner_user, mock_cache):
        """get_summary should pass network_id param"""
        from app.routers.metrics_proxy import get_summary

        await get_summary(network_id="net-summary", user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "net-summary"

    async def test_get_node_metrics(self, mock_http_pool, owner_user):
        """get_node_metrics should GET by node ID"""
        from app.routers.metrics_proxy import get_node_metrics

        await get_node_metrics(node_id="node-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/nodes/node-123" in call_kwargs["path"]

    async def test_get_node_metrics_with_network_id(self, mock_http_pool, owner_user):
        """get_node_metrics should pass network_id param"""
        from app.routers.metrics_proxy import get_node_metrics

        await get_node_metrics(node_id="node-123", network_id="net-node", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "net-node"

    async def test_get_connections(self, mock_http_pool, owner_user):
        """get_connections should GET"""
        from app.routers.metrics_proxy import get_connections

        await get_connections(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/connections" in call_kwargs["path"]

    async def test_get_connections_with_network_id(self, mock_http_pool, owner_user):
        """get_connections should pass network_id param"""
        from app.routers.metrics_proxy import get_connections

        await get_connections(network_id="net-conn", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "net-conn"

    async def test_get_gateways(self, mock_http_pool, owner_user):
        """get_gateways should GET"""
        from app.routers.metrics_proxy import get_gateways

        await get_gateways(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/gateways" in call_kwargs["path"]

    async def test_get_gateways_with_network_id(self, mock_http_pool, owner_user):
        """get_gateways should pass network_id param"""
        from app.routers.metrics_proxy import get_gateways

        await get_gateways(network_id="net-gw", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "net-gw"

    async def test_debug_layout(self, mock_http_pool, owner_user):
        """debug_layout should GET"""
        from app.routers.metrics_proxy import debug_layout

        await debug_layout(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/debug/layout" in call_kwargs["path"]

    async def test_debug_layout_with_network_id(self, mock_http_pool, owner_user):
        """debug_layout should pass network_id param"""
        from app.routers.metrics_proxy import debug_layout

        await debug_layout(network_id="net-debug", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "net-debug"

    async def test_trigger_speed_test(self, mock_http_pool, readwrite_user):
        """trigger_speed_test should POST with extended timeout"""
        from app.routers.metrics_proxy import trigger_speed_test

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"server_id": "server-1"})

        await trigger_speed_test(request=mock_request, user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["timeout"] == 120.0

    async def test_get_redis_status(self, mock_http_pool, owner_user):
        """get_redis_status should GET"""
        from app.routers.metrics_proxy import get_redis_status

        await get_redis_status(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/redis/status" in call_kwargs["path"]

    async def test_reconnect_redis(self, mock_http_pool, readwrite_user):
        """reconnect_redis should POST"""
        from app.routers.metrics_proxy import reconnect_redis

        await reconnect_redis(user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/redis/reconnect" in call_kwargs["path"]

    # ==================== Usage Statistics Tests ====================

    async def test_record_usage(self, mock_http_pool):
        """record_usage should POST without auth"""
        from app.routers.metrics_proxy import record_usage

        mock_request = MagicMock()
        mock_request.json = AsyncMock(
            return_value={
                "endpoint": "/api/health/status",
                "method": "GET",
                "service": "health-service",
                "status_code": 200,
                "response_time_ms": 45.0,
            }
        )

        await record_usage(request=mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/usage/record" in call_kwargs["path"]
        assert call_kwargs["method"] == "POST"

    async def test_record_usage_batch(self, mock_http_pool):
        """record_usage_batch should POST without auth"""
        from app.routers.metrics_proxy import record_usage_batch

        mock_request = MagicMock()
        mock_request.json = AsyncMock(
            return_value={
                "records": [
                    {
                        "endpoint": "/api/test",
                        "method": "GET",
                        "service": "test",
                        "status_code": 200,
                        "response_time_ms": 10.0,
                    }
                ]
            }
        )

        await record_usage_batch(request=mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/usage/record/batch" in call_kwargs["path"]
        assert call_kwargs["method"] == "POST"

    async def test_get_usage_stats(self, mock_http_pool, owner_user, mock_cache):
        """get_usage_stats should GET with auth"""
        from app.routers.metrics_proxy import get_usage_stats

        await get_usage_stats(service=None, user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/usage/stats" in call_kwargs["path"]
        assert call_kwargs["method"] == "GET"

    async def test_get_usage_stats_filtered(self, mock_http_pool, owner_user, mock_cache):
        """get_usage_stats should filter by service"""
        from app.routers.metrics_proxy import get_usage_stats

        await get_usage_stats(service="health-service", user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["service"] == "health-service"

    async def test_reset_usage_stats(self, mock_http_pool, readwrite_user):
        """reset_usage_stats should DELETE with write access"""
        from app.routers.metrics_proxy import reset_usage_stats

        await reset_usage_stats(service=None, user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/usage/stats" in call_kwargs["path"]
        assert call_kwargs["method"] == "DELETE"

    async def test_reset_usage_stats_single_service(self, mock_http_pool, readwrite_user):
        """reset_usage_stats should filter by service"""
        from app.routers.metrics_proxy import reset_usage_stats

        await reset_usage_stats(service="health-service", user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["service"] == "health-service"


# ==================== Assistant Proxy Tests ====================


class TestAssistantProxyRouter:
    """Tests for assistant proxy router endpoints"""

    @pytest.fixture(autouse=True)
    def mock_http_pool(self):
        """Mock http_pool for assistant proxy tests"""
        with patch("app.services.proxy_service.http_pool") as mock:
            mock.request = AsyncMock(return_value=create_mock_response())
            yield mock

    async def test_proxy_request_forwards_correctly(self, mock_http_pool):
        """proxy_assistant_request should forward to assistant service"""
        from app.services.proxy_service import proxy_request

        await proxy_request("assistant", "GET", "/config")

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["service_name"] == "assistant"
        assert "/api/assistant/config" in call_kwargs["path"]

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object with headers"""
        request = MagicMock()
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="Bearer test-token")
        request.headers = mock_headers
        return request

    async def test_get_config(self, mock_http_pool, owner_user, mock_request, mock_cache):
        """get_config should GET"""
        from app.routers.assistant_proxy import get_config

        await get_config(request=mock_request, user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/config" in call_kwargs["path"]

    async def test_list_providers(self, mock_http_pool, owner_user, mock_request, mock_cache):
        """list_providers should GET"""
        from app.routers.assistant_proxy import list_providers

        await list_providers(request=mock_request, user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/providers" in call_kwargs["path"]

    async def test_list_models(self, mock_http_pool, owner_user, mock_request):
        """list_models should GET by provider"""
        from app.routers.assistant_proxy import list_models

        await list_models(request=mock_request, provider="openai", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/models/openai" in call_kwargs["path"]

    async def test_get_context(self, mock_http_pool, owner_user, mock_request):
        """get_context should GET"""
        from app.routers.assistant_proxy import get_context

        await get_context(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/context" in call_kwargs["path"]

    async def test_refresh_context(self, mock_http_pool, owner_user, mock_request):
        """refresh_context should POST"""
        from app.routers.assistant_proxy import refresh_context

        await refresh_context(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert "/context/refresh" in call_kwargs["path"]

    async def test_get_context_debug(self, mock_http_pool, owner_user, mock_request):
        """get_context_debug should GET"""
        from app.routers.assistant_proxy import get_context_debug

        await get_context_debug(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/context/debug" in call_kwargs["path"]

    async def test_get_context_raw(self, mock_http_pool, owner_user, mock_request):
        """get_context_raw should GET"""
        from app.routers.assistant_proxy import get_context_raw

        await get_context_raw(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/context/raw" in call_kwargs["path"]

    async def test_get_context_status(self, mock_http_pool, owner_user, mock_request):
        """get_context_status should GET"""
        from app.routers.assistant_proxy import get_context_status

        await get_context_status(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/context/status" in call_kwargs["path"]

    async def test_chat(self, mock_http_pool, owner_user):
        """chat should POST with extended timeout"""
        from app.routers.assistant_proxy import chat

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"message": "Hello"})

        await chat(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["timeout"] == 120.0

    async def test_chat_stream_returns_streaming_response(self, owner_user, mock_request):
        """chat_stream should return StreamingResponse"""
        from fastapi.responses import StreamingResponse

        from app.routers.assistant_proxy import chat_stream

        mock_request.json = AsyncMock(return_value={"message": "Hello"})

        async def mock_aiter_bytes():
            yield b'data: {"type": "chunk"}\n\n'

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.aiter_bytes = mock_aiter_bytes
            mock_response.aclose = AsyncMock()

            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            response = await chat_stream(request=mock_request, user=owner_user)

            assert isinstance(response, StreamingResponse)
            assert response.media_type == "text/event-stream"

    async def test_get_context_with_network_id(self, mock_http_pool, owner_user, mock_request):
        """get_context should pass network_id param"""
        from app.routers.assistant_proxy import get_context

        await get_context(request=mock_request, network_id="test-net-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "test-net-123"

    async def test_refresh_context_with_network_id(self, mock_http_pool, owner_user, mock_request):
        """refresh_context should pass network_id param"""
        from app.routers.assistant_proxy import refresh_context

        await refresh_context(request=mock_request, network_id="test-net-456", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "test-net-456"

    async def test_get_context_debug_with_network_id(
        self, mock_http_pool, owner_user, mock_request
    ):
        """get_context_debug should pass network_id param"""
        from app.routers.assistant_proxy import get_context_debug

        await get_context_debug(request=mock_request, network_id="test-net-789", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "test-net-789"

    async def test_get_context_raw_with_network_id(self, mock_http_pool, owner_user, mock_request):
        """get_context_raw should pass network_id param"""
        from app.routers.assistant_proxy import get_context_raw

        await get_context_raw(request=mock_request, network_id="test-net-abc", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["network_id"] == "test-net-abc"

    async def test_get_chat_limit(self, mock_http_pool, owner_user, mock_request):
        """get_chat_limit should GET"""
        from app.routers.assistant_proxy import get_chat_limit

        await get_chat_limit(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/chat/limit" in call_kwargs["path"]

    async def test_chat_stream_429_error(self, owner_user, mock_request):
        """chat_stream should raise 429 on rate limit"""
        from fastapi import HTTPException

        from app.routers.assistant_proxy import chat_stream

        mock_request.json = AsyncMock(return_value={"message": "Hello"})

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "3600"}
            mock_response.aread = AsyncMock(return_value=b'{"detail": "Rate limit exceeded"}')
            mock_response.aclose = AsyncMock()

            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await chat_stream(request=mock_request, user=owner_user)

            assert exc_info.value.status_code == 429

    async def test_chat_stream_401_error(self, owner_user, mock_request):
        """chat_stream should raise 401 on auth error"""
        from fastapi import HTTPException

        from app.routers.assistant_proxy import chat_stream

        mock_request.json = AsyncMock(return_value={"message": "Hello"})

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.aclose = AsyncMock()

            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await chat_stream(request=mock_request, user=owner_user)

            assert exc_info.value.status_code == 401

    async def test_chat_stream_400_error(self, owner_user, mock_request):
        """chat_stream should raise 400+ errors"""
        from fastapi import HTTPException

        from app.routers.assistant_proxy import chat_stream

        mock_request.json = AsyncMock(return_value={"message": "Hello"})

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.aread = AsyncMock(return_value=b'{"detail": "Bad request"}')
            mock_response.aclose = AsyncMock()

            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await chat_stream(request=mock_request, user=owner_user)

            assert exc_info.value.status_code == 400

    async def test_chat_stream_429_parse_error(self, owner_user, mock_request):
        """chat_stream should handle 429 with unparseable body"""
        from fastapi import HTTPException

        from app.routers.assistant_proxy import chat_stream

        mock_request.json = AsyncMock(return_value={"message": "Hello"})

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {}
            mock_response.aread = AsyncMock(return_value=b"invalid json")
            mock_response.aclose = AsyncMock()

            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await chat_stream(request=mock_request, user=owner_user)

            assert exc_info.value.status_code == 429
            assert "Daily chat limit exceeded" in exc_info.value.detail

    async def test_chat_stream_400_parse_error(self, owner_user, mock_request):
        """chat_stream should handle 400+ with unparseable body"""
        from fastapi import HTTPException

        from app.routers.assistant_proxy import chat_stream

        mock_request.json = AsyncMock(return_value={"message": "Hello"})

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.aread = AsyncMock(side_effect=Exception("Read error"))
            mock_response.aclose = AsyncMock()

            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await chat_stream(request=mock_request, user=owner_user)

            assert exc_info.value.status_code == 500

    async def test_chat_stream_generator_error_during_stream(self, owner_user, mock_request):
        """Stream generator should yield error on exception during iteration"""
        from app.routers.assistant_proxy import chat_stream

        mock_request.json = AsyncMock(return_value={"message": "Hello"})

        async def mock_aiter_bytes():
            yield b'data: {"type": "chunk"}\n\n'
            raise RuntimeError("Stream error")

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.aiter_bytes = mock_aiter_bytes
            mock_response.aclose = AsyncMock()

            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            response = await chat_stream(request=mock_request, user=owner_user)

            # Consume the generator to trigger the error
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)

            # Should have multiple chunks including error
            assert len(chunks) > 0
            all_data = b"".join(chunks)
            assert b"error" in all_data


# ==================== Notification Proxy Tests ====================


class TestNotificationProxyRouter:
    """Tests for notification proxy router endpoints"""

    @pytest.fixture(autouse=True)
    def mock_http_pool(self):
        """Mock http_pool for notification proxy tests"""
        with patch("app.services.proxy_service.http_pool") as mock:
            mock.request = AsyncMock(return_value=create_mock_response())
            yield mock

    async def test_proxy_request_forwards_correctly(self, mock_http_pool):
        """proxy_notification_request should forward to notification service"""
        from app.services.proxy_service import proxy_notification_request

        await proxy_notification_request("GET", "/preferences", headers={"X-User-Id": "user-123"})

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["service_name"] == "notification"
        assert "/api/notifications/preferences" in call_kwargs["path"]

    # ==================== Per-Network Preferences Tests ====================

    async def test_get_network_preferences(self, mock_http_pool, owner_user):
        """get_network_preferences should GET for specific network"""
        from app.routers.notification_proxy import get_network_preferences

        await get_network_preferences(network_id="net-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/networks/net-123/preferences" in call_kwargs["path"]
        assert call_kwargs["headers"]["X-User-Id"] == owner_user.user_id

    async def test_update_network_preferences(self, mock_http_pool, owner_user):
        """update_network_preferences should PUT with body"""
        from app.routers.notification_proxy import update_network_preferences

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"email_enabled": True})

        await update_network_preferences(
            network_id="net-123", request=mock_request, user=owner_user
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "PUT"
        assert "/networks/net-123/preferences" in call_kwargs["path"]

    async def test_delete_network_preferences(self, mock_http_pool, owner_user):
        """delete_network_preferences should DELETE"""
        from app.routers.notification_proxy import delete_network_preferences

        await delete_network_preferences(network_id="net-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"
        assert "/networks/net-123/preferences" in call_kwargs["path"]

    async def test_send_network_test_notification(self, mock_http_pool, owner_user):
        """send_network_test_notification should POST with body"""
        from app.routers.notification_proxy import send_network_test_notification

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"type": "test"})

        await send_network_test_notification(
            network_id="net-123", request=mock_request, user=owner_user
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert "/networks/net-123/test" in call_kwargs["path"]

    async def test_get_network_notification_history(self, mock_http_pool, owner_user):
        """get_network_notification_history should GET with pagination"""
        from app.routers.notification_proxy import get_network_notification_history

        await get_network_notification_history(
            network_id="net-123", page=2, per_page=25, user=owner_user
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/networks/net-123/history" in call_kwargs["path"]
        assert call_kwargs["params"]["page"] == 2
        assert call_kwargs["params"]["per_page"] == 25

    async def test_get_network_notification_stats(self, mock_http_pool, owner_user):
        """get_network_notification_stats should GET"""
        from app.routers.notification_proxy import get_network_notification_stats

        await get_network_notification_stats(network_id="net-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/networks/net-123/stats" in call_kwargs["path"]

    # ==================== Legacy Preferences Tests ====================

    async def test_get_preferences(self, mock_http_pool, owner_user, mock_cache):
        """get_preferences should GET with user header"""
        from app.routers.notification_proxy import get_preferences

        await get_preferences(user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["headers"]["X-User-Id"] == owner_user.user_id

    async def test_update_preferences(self, mock_http_pool, owner_user, mock_cache):
        """update_preferences should PUT with body"""
        from app.routers.notification_proxy import update_preferences

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"email_enabled": True})

        await update_preferences(request=mock_request, user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "PUT"

    async def test_delete_preferences(self, mock_http_pool, owner_user, mock_cache):
        """delete_preferences should DELETE"""
        from app.routers.notification_proxy import delete_preferences

        await delete_preferences(user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_get_service_status(self, mock_http_pool, owner_user, mock_cache):
        """get_service_status should GET"""
        from app.routers.notification_proxy import get_service_status

        await get_service_status(user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/status" in call_kwargs["path"]

    async def test_get_discord_info(self, mock_http_pool, owner_user):
        """get_discord_info should GET user's discord link status"""
        from app.routers.notification_proxy import get_discord_info

        await get_discord_info(context_type="global", network_id=None, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/discord" in call_kwargs["path"]
        assert owner_user.user_id in call_kwargs["path"]

    async def test_get_discord_guilds(self, mock_http_pool, owner_user):
        """get_discord_guilds should GET"""
        from app.routers.notification_proxy import get_discord_guilds

        await get_discord_guilds(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/discord/guilds" in call_kwargs["path"]

    async def test_get_discord_channels(self, mock_http_pool, owner_user):
        """get_discord_channels should GET by guild ID"""
        from app.routers.notification_proxy import get_discord_channels

        await get_discord_channels(guild_id="guild-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/discord/guilds/guild-123/channels" in call_kwargs["path"]

    async def test_get_discord_invite_url(self, mock_http_pool, owner_user):
        """get_discord_invite_url should GET"""
        from app.routers.notification_proxy import get_discord_invite_url

        await get_discord_invite_url(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/discord/invite-url" in call_kwargs["path"]

    async def test_send_test_notification(self, mock_http_pool, owner_user):
        """send_test_notification should POST"""
        from app.routers.notification_proxy import send_test_notification

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"channel": "email"})

        await send_test_notification(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/test" in call_kwargs["path"]

    async def test_get_notification_history(self, mock_http_pool, owner_user):
        """get_notification_history should GET with pagination"""
        from app.routers.notification_proxy import get_notification_history

        await get_notification_history(page=2, per_page=25, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["page"] == 2
        assert call_kwargs["params"]["per_page"] == 25

    async def test_get_notification_stats(self, mock_http_pool, owner_user):
        """get_notification_stats should GET"""
        from app.routers.notification_proxy import get_notification_stats

        await get_notification_stats(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/stats" in call_kwargs["path"]

    async def test_get_ml_model_status(self, mock_http_pool, owner_user):
        """get_ml_model_status should GET"""
        from app.routers.notification_proxy import get_ml_model_status

        await get_ml_model_status(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/ml/status" in call_kwargs["path"]

    async def test_get_device_baseline(self, mock_http_pool, owner_user):
        """get_device_baseline should GET by IP"""
        from app.routers.notification_proxy import get_device_baseline

        await get_device_baseline(device_ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/ml/baseline/192.168.1.1" in call_kwargs["path"]

    async def test_mark_false_positive(self, mock_http_pool, owner_user):
        """mark_false_positive should POST"""
        from app.routers.notification_proxy import mark_false_positive

        await mark_false_positive(event_id="event-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/ml/feedback/false-positive" in call_kwargs["path"]

    async def test_reset_device_baseline(self, mock_http_pool, owner_user):
        """reset_device_baseline should DELETE (owner only)"""
        from app.routers.notification_proxy import reset_device_baseline

        await reset_device_baseline(device_ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_reset_all_ml_data(self, mock_http_pool, owner_user):
        """reset_all_ml_data should DELETE (owner only)"""
        from app.routers.notification_proxy import reset_all_ml_data

        await reset_all_ml_data(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/ml/reset" in call_kwargs["path"]

    async def test_send_global_notification(self, mock_http_pool, owner_user):
        """send_global_notification should POST (owner only)"""
        from app.routers.notification_proxy import send_global_notification

        mock_request = MagicMock()
        mock_request.json = AsyncMock(
            return_value={"title": "Test", "message": "Test message", "network_id": 1}
        )

        mock_db = AsyncMock()
        # Mock the get_network_member_user_ids to return a list of users
        with patch(
            "app.routers.notification.broadcast.get_network_member_user_ids", new_callable=AsyncMock
        ) as mock_get_users:
            mock_get_users.return_value = ["user-1", "user-2"]
            await send_global_notification(request=mock_request, user=owner_user, db=mock_db)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/send-notification" in call_kwargs["path"]

    async def test_get_scheduled_broadcasts(self, mock_http_pool, owner_user):
        """get_scheduled_broadcasts should GET (owner only)"""
        from app.routers.notification_proxy import get_scheduled_broadcasts

        await get_scheduled_broadcasts(include_completed=True, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["include_completed"] is True

    async def test_create_scheduled_broadcast(self, mock_http_pool, owner_user):
        """create_scheduled_broadcast should POST (owner only)"""
        from app.routers.notification_proxy import create_scheduled_broadcast

        mock_request = MagicMock()
        mock_request.json = AsyncMock(
            return_value={
                "title": "Scheduled",
                "message": "Test",
                "scheduled_at": "2024-12-31T00:00:00Z",
            }
        )

        await create_scheduled_broadcast(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["headers"]["X-Username"] == owner_user.username

    async def test_get_scheduled_broadcast(self, mock_http_pool, owner_user):
        """get_scheduled_broadcast should GET by ID (owner only)"""
        from app.routers.notification_proxy import get_scheduled_broadcast

        await get_scheduled_broadcast(broadcast_id="bc-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/scheduled/bc-123" in call_kwargs["path"]

    async def test_cancel_scheduled_broadcast(self, mock_http_pool, owner_user):
        """cancel_scheduled_broadcast should POST (owner only)"""
        from app.routers.notification_proxy import cancel_scheduled_broadcast

        await cancel_scheduled_broadcast(broadcast_id="bc-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/cancel" in call_kwargs["path"]

    async def test_delete_scheduled_broadcast(self, mock_http_pool, owner_user):
        """delete_scheduled_broadcast should DELETE (owner only)"""
        from app.routers.notification_proxy import delete_scheduled_broadcast

        await delete_scheduled_broadcast(broadcast_id="bc-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_get_silenced_devices(self, mock_http_pool, owner_user):
        """get_silenced_devices should GET"""
        from app.routers.notification_proxy import get_silenced_devices

        await get_silenced_devices(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/silenced-devices" in call_kwargs["path"]

    async def test_set_silenced_devices(self, mock_http_pool, readwrite_user):
        """set_silenced_devices should POST (write access)"""
        from app.routers.notification_proxy import set_silenced_devices

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"device_ips": ["192.168.1.1"]})

        await set_silenced_devices(request=mock_request, user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"

    async def test_silence_device(self, mock_http_pool, readwrite_user):
        """silence_device should POST (write access)"""
        from app.routers.notification_proxy import silence_device

        await silence_device(device_ip="192.168.1.1", user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/silenced-devices/192.168.1.1" in call_kwargs["path"]

    async def test_unsilence_device(self, mock_http_pool, readwrite_user):
        """unsilence_device should DELETE (write access)"""
        from app.routers.notification_proxy import unsilence_device

        await unsilence_device(device_ip="192.168.1.1", user=readwrite_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_check_device_silenced(self, mock_http_pool, owner_user):
        """check_device_silenced should GET"""
        from app.routers.notification_proxy import check_device_silenced

        await check_device_silenced(device_ip="192.168.1.1", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "GET"

    async def test_process_health_check(self, mock_http_pool):
        """process_health_check internal endpoint should work"""
        from app.routers.notification_proxy import process_health_check

        await process_health_check(
            device_ip="192.168.1.1",
            success=True,
            latency_ms=25.5,
            packet_loss=0.0,
            device_name="router",
            previous_state="healthy",
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/process-health-check" in call_kwargs["path"]

    async def test_notify_service_up(self, mock_http_pool, owner_user):
        """notify_service_up should POST (owner only)"""
        from app.routers.notification_proxy import notify_service_up

        mock_request = MagicMock()
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value="application/json")
        mock_request.json = AsyncMock(return_value={"message": "Back online"})

        await notify_service_up(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/service-status/up" in call_kwargs["path"]

    async def test_notify_service_down(self, mock_http_pool, owner_user):
        """notify_service_down should POST (owner only)"""
        from app.routers.notification_proxy import notify_service_down

        mock_request = MagicMock()
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value="application/json")
        mock_request.json = AsyncMock(return_value={"message": "Maintenance"})

        await notify_service_down(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/service-status/down" in call_kwargs["path"]

    async def test_get_version_status(self, mock_http_pool, owner_user):
        """get_version_status should GET"""
        from app.routers.notification_proxy import get_version_status

        await get_version_status(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/version" in call_kwargs["path"]

    async def test_check_for_updates(self, mock_http_pool, owner_user):
        """check_for_updates should POST"""
        from app.routers.notification_proxy import check_for_updates

        await check_for_updates(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/version/check" in call_kwargs["path"]

    async def test_send_version_notification(self, mock_http_pool, owner_user):
        """send_version_notification should POST"""
        from app.routers.notification_proxy import send_version_notification

        await send_version_notification(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/version/notify" in call_kwargs["path"]

    # ==================== Additional Notification Proxy Tests ====================

    async def test_get_discord_info_simple(self, mock_http_pool, owner_user):
        """get_discord_info should GET discord bot info"""
        # Import from proxy_service
        from app.services.proxy_service import proxy_notification_request

        # Call the simple get_discord_info (not the one with context_type param)
        result = await proxy_notification_request("GET", "/discord/info")

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/discord/info" in call_kwargs["path"]

    async def test_get_global_preferences(self, mock_http_pool, owner_user, mock_cache):
        """get_global_preferences should GET"""
        from app.routers.notification_proxy import get_global_preferences

        await get_global_preferences(user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/global/preferences" in call_kwargs["path"]

    async def test_update_global_preferences(self, mock_http_pool, owner_user, mock_cache):
        """update_global_preferences should PUT with body"""
        from app.routers.notification_proxy import update_global_preferences

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"enabled": True})

        await update_global_preferences(request=mock_request, user=owner_user, cache=mock_cache)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "PUT"
        assert "/global/preferences" in call_kwargs["path"]

    async def test_update_scheduled_broadcast(self, mock_http_pool, owner_user):
        """update_scheduled_broadcast should PATCH"""
        from app.routers.notification_proxy import update_scheduled_broadcast

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"title": "Updated Title"})

        await update_scheduled_broadcast(
            broadcast_id="bc-123", request=mock_request, user=owner_user
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "PATCH"
        assert "/scheduled/bc-123" in call_kwargs["path"]

    async def test_mark_broadcast_seen(self, mock_http_pool, owner_user):
        """mark_broadcast_seen should POST"""
        from app.routers.notification_proxy import mark_broadcast_seen

        await mark_broadcast_seen(broadcast_id="bc-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/scheduled/bc-123/seen" in call_kwargs["path"]

    async def test_get_cartographer_status_subscription(self, mock_http_pool, owner_user):
        """get_cartographer_status_subscription should GET"""
        from app.routers.notification_proxy import get_cartographer_status_subscription

        await get_cartographer_status_subscription(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/cartographer-status/subscription" in call_kwargs["path"]

    async def test_create_cartographer_status_subscription(self, mock_http_pool, owner_user):
        """create_cartographer_status_subscription should POST"""
        from app.routers.notification_proxy import create_cartographer_status_subscription

        await create_cartographer_status_subscription(body={"enabled": True}, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/cartographer-status/subscription" in call_kwargs["path"]

    async def test_update_cartographer_status_subscription(self, mock_http_pool, owner_user):
        """update_cartographer_status_subscription should PUT"""
        from app.routers.notification_proxy import update_cartographer_status_subscription

        await update_cartographer_status_subscription(body={"enabled": False}, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "PUT"

    async def test_delete_cartographer_status_subscription(self, mock_http_pool, owner_user):
        """delete_cartographer_status_subscription should DELETE"""
        from app.routers.notification_proxy import delete_cartographer_status_subscription

        await delete_cartographer_status_subscription(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_test_global_discord(self, mock_http_pool, owner_user):
        """test_global_discord should POST"""
        from app.routers.notification_proxy import test_global_discord

        await test_global_discord(body={"test": True}, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert "/test/discord" in call_kwargs["path"]

    async def test_get_user_network_preferences(self, mock_http_pool, owner_user):
        """get_user_network_preferences should GET"""
        from app.routers.notification_proxy import get_user_network_preferences

        await get_user_network_preferences(network_id="net-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert f"/users/{owner_user.user_id}/networks/net-123/preferences" in call_kwargs["path"]

    async def test_update_user_network_preferences(self, mock_http_pool, owner_user):
        """update_user_network_preferences should PUT"""
        from app.routers.notification_proxy import update_user_network_preferences

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"email_enabled": True})

        await update_user_network_preferences(
            network_id="net-123", request=mock_request, user=owner_user
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "PUT"

    async def test_delete_user_network_preferences(self, mock_http_pool, owner_user):
        """delete_user_network_preferences should DELETE"""
        from app.routers.notification_proxy import delete_user_network_preferences

        await delete_user_network_preferences(network_id="net-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    async def test_get_user_global_preferences(self, mock_http_pool, owner_user):
        """get_user_global_preferences should GET"""
        from app.routers.notification_proxy import get_user_global_preferences

        await get_user_global_preferences(user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert f"/users/{owner_user.user_id}/global/preferences" in call_kwargs["path"]

    async def test_update_user_global_preferences(self, mock_http_pool, owner_user):
        """update_user_global_preferences should PUT"""
        from app.routers.notification_proxy import update_user_global_preferences

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"enabled": True})

        await update_user_global_preferences(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "PUT"

    async def test_test_user_network_notification(self, mock_http_pool, owner_user):
        """test_user_network_notification should POST"""
        from app.routers.notification_proxy import test_user_network_notification

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"type": "test"})

        await test_user_network_notification(
            network_id="net-123", request=mock_request, user=owner_user
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["method"] == "POST"

    async def test_test_user_global_notification(self, mock_http_pool, owner_user):
        """test_user_global_notification should POST"""
        from app.routers.notification_proxy import test_user_global_notification

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"type": "test"})

        await test_user_global_notification(request=mock_request, user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert f"/users/{owner_user.user_id}/global/test" in call_kwargs["path"]

    async def test_initiate_discord_oauth(self, mock_http_pool, owner_user):
        """initiate_discord_oauth should GET with params"""
        from app.routers.notification_proxy import initiate_discord_oauth

        await initiate_discord_oauth(context_type="network", network_id="net-123", user=owner_user)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert f"user_id={owner_user.user_id}" in call_kwargs["path"]
        assert "network_id=net-123" in call_kwargs["path"]

    async def test_get_user_discord_info_with_network(self, mock_http_pool, owner_user):
        """get_discord_info (user version) should GET with network_id"""
        # Import from proxy_service
        from app.services.proxy_service import proxy_notification_request

        # Call proxy_notification_request directly to test the path
        await proxy_notification_request(
            "GET",
            f"/users/{owner_user.user_id}/discord",
            params={"context_type": "network", "network_id": "net-123"},
            use_user_path=True,
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert f"/users/{owner_user.user_id}/discord" in call_kwargs["path"]

    async def test_send_network_notification_success(self, mock_http_pool, readwrite_user):
        """send_network_notification should POST with user_ids"""
        from app.routers.notification_proxy import send_network_notification

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"title": "Test", "message": "Hello"})
        mock_db = AsyncMock()

        with patch(
            "app.routers.notification.broadcast.get_network_member_user_ids", new_callable=AsyncMock
        ) as mock_get_members:
            mock_get_members.return_value = ["user-1", "user-2"]

            await send_network_notification(
                network_id="net-123", request=mock_request, user=readwrite_user, db=mock_db
            )

            call_kwargs = mock_http_pool.request.call_args[1]
            assert "user_ids" in call_kwargs["json_body"]

    async def test_send_network_notification_member_error(self, mock_http_pool, readwrite_user):
        """send_network_notification should raise on member lookup error"""
        from fastapi import HTTPException

        from app.routers.notification_proxy import send_network_notification

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"title": "Test"})
        mock_db = AsyncMock()

        with patch(
            "app.routers.notification.broadcast.get_network_member_user_ids", new_callable=AsyncMock
        ) as mock_get_members:
            mock_get_members.side_effect = Exception("Database error")

            with pytest.raises(HTTPException) as exc_info:
                await send_network_notification(
                    network_id="net-123", request=mock_request, user=readwrite_user, db=mock_db
                )

            assert exc_info.value.status_code == 500
