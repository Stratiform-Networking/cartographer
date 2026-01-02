"""
Unit tests for the HTTP client pool with circuit breaker functionality.
"""

import asyncio
import time
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

# Import after setting env vars in conftest
from app.services.http_client import CircuitBreaker, CircuitState, HTTPClientPool, ServiceClient


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class"""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a fresh circuit breaker for each test"""
        return CircuitBreaker(failure_threshold=3, recovery_timeout=1.0, half_open_max_calls=1)

    async def test_initial_state_is_closed(self, circuit_breaker):
        """Circuit breaker should start in CLOSED state"""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    async def test_can_execute_when_closed(self, circuit_breaker):
        """Should allow requests when circuit is closed"""
        assert await circuit_breaker.can_execute() is True

    async def test_record_success_resets_failure_count(self, circuit_breaker):
        """Success should reset the failure count"""
        circuit_breaker.failure_count = 2
        await circuit_breaker.record_success()
        assert circuit_breaker.failure_count == 0

    async def test_record_failure_increments_count(self, circuit_breaker):
        """Failure should increment the failure count"""
        await circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 1

    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Circuit should open after reaching failure threshold"""
        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN
        assert await circuit_breaker.can_execute() is False

    async def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Circuit should transition to half-open after recovery timeout"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

        # Simulate time passing beyond recovery timeout
        circuit_breaker.last_failure_time = time.time() - 2.0

        # Should now allow one request (half-open)
        assert await circuit_breaker.can_execute() is True
        assert circuit_breaker.state == CircuitState.HALF_OPEN

    async def test_half_open_limits_calls(self, circuit_breaker):
        """Half-open state should limit concurrent test calls"""
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.half_open_calls = 0

        # First call should be allowed
        assert await circuit_breaker.can_execute() is True

        # Second call should be blocked
        assert await circuit_breaker.can_execute() is False

    async def test_success_in_half_open_closes_circuit(self, circuit_breaker):
        """Success during half-open should close the circuit"""
        circuit_breaker.state = CircuitState.HALF_OPEN

        await circuit_breaker.record_success()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    async def test_failure_in_half_open_reopens_circuit(self, circuit_breaker):
        """Failure during half-open should reopen the circuit"""
        circuit_breaker.state = CircuitState.HALF_OPEN

        await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN


class TestServiceClient:
    """Tests for the ServiceClient class"""

    @pytest.fixture
    def service_client(self):
        """Create a service client for testing"""
        return ServiceClient(name="test-service", base_url="http://localhost:9999")

    async def test_initialize_creates_client(self, service_client):
        """Initialize should create an httpx AsyncClient"""
        await service_client.initialize()

        assert service_client.client is not None
        assert isinstance(service_client.client, httpx.AsyncClient)

        # Cleanup
        await service_client.close()

    async def test_close_removes_client(self, service_client):
        """Close should remove the client reference"""
        await service_client.initialize()
        await service_client.close()

        assert service_client.client is None

    async def test_double_initialize_is_safe(self, service_client):
        """Calling initialize twice should be safe"""
        await service_client.initialize()
        first_client = service_client.client

        await service_client.initialize()
        second_client = service_client.client

        assert first_client is second_client

        # Cleanup
        await service_client.close()

    @patch.object(httpx.AsyncClient, "get")
    async def test_warm_up_success(self, mock_get, service_client):
        """Warm-up should return True on successful health check"""
        await service_client.initialize()

        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        service_client.client.get = AsyncMock(return_value=mock_response)

        result = await service_client.warm_up()
        assert result is True

        await service_client.close()

    async def test_warm_up_without_init(self, service_client):
        """Warm-up should initialize client if not already done"""
        assert service_client.client is None

        # Mock the get method after initialization
        with patch.object(ServiceClient, "initialize", new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = lambda: setattr(service_client, "client", MagicMock())
            service_client.client = MagicMock()
            service_client.client.get = AsyncMock(return_value=MagicMock(status_code=200))

            result = await service_client.warm_up()
            assert result is True


class TestHTTPClientPool:
    """Tests for the HTTPClientPool class"""

    @pytest.fixture
    def client_pool(self):
        """Create a fresh client pool for each test"""
        return HTTPClientPool()

    def test_register_service(self, client_pool):
        """Should register a service and return ServiceClient"""
        service = client_pool.register_service("my-service", "http://localhost:8080")

        assert service is not None
        assert service.name == "my-service"
        assert service.base_url == "http://localhost:8080"

    def test_register_same_service_returns_existing(self, client_pool):
        """Registering same service twice returns the same instance"""
        service1 = client_pool.register_service("my-service", "http://localhost:8080")
        service2 = client_pool.register_service("my-service", "http://localhost:9090")

        assert service1 is service2
        # Original URL is preserved
        assert service1.base_url == "http://localhost:8080"

    def test_get_service(self, client_pool):
        """Should retrieve registered service"""
        client_pool.register_service("my-service", "http://localhost:8080")

        service = client_pool.get_service("my-service")
        assert service is not None
        assert service.name == "my-service"

    def test_get_unknown_service_returns_none(self, client_pool):
        """Getting unknown service should return None"""
        service = client_pool.get_service("unknown")
        assert service is None

    async def test_initialize_all(self, client_pool):
        """Should initialize all registered services"""
        client_pool.register_service("service1", "http://localhost:8001")
        client_pool.register_service("service2", "http://localhost:8002")

        await client_pool.initialize_all()

        assert client_pool._initialized is True

        # Verify clients were created
        for service in client_pool._services.values():
            assert service.client is not None

        # Cleanup
        await client_pool.close_all()

    async def test_double_initialize_is_idempotent(self, client_pool):
        """Calling initialize_all twice should be safe"""
        client_pool.register_service("service1", "http://localhost:8001")

        await client_pool.initialize_all()
        await client_pool.initialize_all()

        assert client_pool._initialized is True

        # Cleanup
        await client_pool.close_all()

    async def test_close_all(self, client_pool):
        """Should close all clients and reset initialized flag"""
        client_pool.register_service("service1", "http://localhost:8001")
        await client_pool.initialize_all()

        await client_pool.close_all()

        assert client_pool._initialized is False
        for service in client_pool._services.values():
            assert service.client is None

    async def test_request_unknown_service_raises(self, client_pool):
        """Request to unknown service should raise HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            await client_pool.request("unknown", "GET", "/test")

        assert exc_info.value.status_code == 500
        assert "Unknown service" in exc_info.value.detail

    async def test_request_with_circuit_open(self, client_pool):
        """Request should fail fast when circuit is open"""
        service = client_pool.register_service("test", "http://localhost:8001")
        service.circuit_breaker.state = CircuitState.OPEN
        service.circuit_breaker.last_failure_time = time.time()  # Recent failure

        with pytest.raises(HTTPException) as exc_info:
            await client_pool.request("test", "GET", "/test")

        assert exc_info.value.status_code == 503
        assert "circuit open" in exc_info.value.detail

    async def test_request_records_success(self, client_pool):
        """Successful request should reset circuit breaker failure count"""
        service = client_pool.register_service("test", "http://localhost:8001")
        await service.initialize()

        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        service.client.request = AsyncMock(return_value=mock_response)

        # Set some failures first
        service.circuit_breaker.failure_count = 2

        await client_pool.request("test", "GET", "/test")

        assert service.circuit_breaker.failure_count == 0

        await service.close()

    async def test_request_connect_error_records_failure(self, client_pool):
        """Connection error should record failure and raise 503"""
        service = client_pool.register_service("test", "http://localhost:8001")
        await service.initialize()

        # Mock a connection error
        service.client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(HTTPException) as exc_info:
            await client_pool.request("test", "GET", "/test")

        assert exc_info.value.status_code == 503
        assert service.circuit_breaker.failure_count == 1

        await service.close()

    async def test_request_timeout_records_failure(self, client_pool):
        """Timeout should record failure and raise 504"""
        service = client_pool.register_service("test", "http://localhost:8001")
        await service.initialize()

        # Mock a timeout error
        service.client.request = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

        with pytest.raises(HTTPException) as exc_info:
            await client_pool.request("test", "GET", "/test")

        assert exc_info.value.status_code == 504
        assert service.circuit_breaker.failure_count == 1

        await service.close()

    async def test_request_with_body_and_params(self, client_pool):
        """Request should properly pass body and query params"""
        service = client_pool.register_service("test", "http://localhost:8001")
        await service.initialize()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        service.client.request = AsyncMock(return_value=mock_response)

        await client_pool.request(
            "test",
            "POST",
            "/api/data",
            params={"filter": "active"},
            json_body={"name": "test"},
            headers={"X-Custom": "header"},
        )

        # Verify the request was made with correct arguments
        service.client.request.assert_called_once()
        call_kwargs = service.client.request.call_args

        assert call_kwargs[0] == ("POST", "/api/data")
        assert call_kwargs[1]["params"] == {"filter": "active"}
        assert call_kwargs[1]["json"] == {"name": "test"}
        assert "X-Custom" in call_kwargs[1]["headers"]

        await service.close()


class TestWarmUpAll:
    """Tests for the warm_up_all functionality"""

    async def test_warm_up_all_parallel(self):
        """Warm-up should run in parallel for all services"""
        pool = HTTPClientPool()

        # Register multiple services
        for i in range(3):
            pool.register_service(f"service{i}", f"http://localhost:800{i}")

        await pool.initialize_all()

        # Mock warm-up to track timing
        warm_up_calls = []

        async def mock_warm_up(service):
            warm_up_calls.append(time.time())
            await asyncio.sleep(0.1)  # Simulate network delay
            return True

        for service in pool._services.values():
            service.warm_up = lambda s=service: mock_warm_up(s)

        start = time.time()
        results = await pool.warm_up_all()
        elapsed = time.time() - start

        # All services should have been warmed up
        assert len(results) == 3

        # If run in parallel, total time should be ~0.1s not ~0.3s
        assert elapsed < 0.25, "Warm-up should run in parallel"

        await pool.close_all()
