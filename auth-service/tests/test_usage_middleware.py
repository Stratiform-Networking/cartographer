"""
Unit tests for usage tracking middleware.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.usage_middleware import UsageRecord, UsageTrackingMiddleware


class TestUsageRecord:
    """Tests for UsageRecord class"""

    def test_init(self):
        """Should initialize record"""
        now = datetime.now()
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=15.5,
            timestamp=now,
        )

        assert record.endpoint == "/api/test"
        assert record.method == "GET"
        assert record.status_code == 200
        assert record.response_time_ms == 15.5
        assert record.timestamp == now

    def test_to_dict(self):
        """Should convert to dict"""
        now = datetime.now()
        record = UsageRecord(
            endpoint="/api/auth/login",
            method="POST",
            status_code=201,
            response_time_ms=25.0,
            timestamp=now,
        )

        result = record.to_dict()

        assert result["endpoint"] == "/api/auth/login"
        assert result["method"] == "POST"
        assert result["service"] == "auth-service"
        assert result["status_code"] == 201
        assert result["response_time_ms"] == 25.0
        assert "timestamp" in result


class TestUsageTrackingMiddleware:
    """Tests for UsageTrackingMiddleware"""

    def test_init(self):
        """Should initialize middleware"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        assert middleware.service_name == "auth-service"
        assert len(middleware._buffer) == 0
        assert middleware._client is None
        assert not middleware._running

    def test_init_with_custom_service_name(self):
        """Should accept custom service name"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app, service_name="test-service")

        assert middleware.service_name == "test-service"

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self):
        """Should create HTTP client"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        client = await middleware._get_client()

        assert client is not None
        assert middleware._client is not None

        # Cleanup
        await client.aclose()

    @pytest.mark.asyncio
    async def test_get_client_reuses_client(self):
        """Should reuse existing client"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        client1 = await middleware._get_client()
        client2 = await middleware._get_client()

        assert client1 is client2

        # Cleanup
        await client1.aclose()

    @pytest.mark.asyncio
    async def test_start_flush_task(self):
        """Should start flush task"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        await middleware._start_flush_task()

        assert middleware._running
        assert middleware._flush_task is not None

        # Cleanup
        middleware._running = False
        middleware._flush_task.cancel()
        try:
            await middleware._flush_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_flush_buffer_empty(self):
        """Should handle empty buffer"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        await middleware._flush_buffer()  # Should not raise

    @pytest.mark.asyncio
    async def test_flush_buffer_with_records(self):
        """Should send records to metrics service"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.now(),
        )
        middleware._buffer.append(record)

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False

        # Override _get_client to return our mock
        middleware._get_client = AsyncMock(return_value=mock_client)

        await middleware._flush_buffer()

        # Should have sent records
        mock_client.post.assert_called_once()
        assert len(middleware._buffer) == 0

    @pytest.mark.asyncio
    async def test_flush_buffer_failure_returns_records(self):
        """Should return records to buffer on failure"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.now(),
        )
        middleware._buffer.append(record)

        # Mock HTTP client with failure
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        middleware._client = mock_client

        await middleware._flush_buffer()

        # Should have returned records to buffer
        assert len(middleware._buffer) == 1

    @pytest.mark.asyncio
    async def test_flush_buffer_exception_returns_records(self):
        """Should return records to buffer on exception"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.now(),
        )
        middleware._buffer.append(record)

        # Mock HTTP client with exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection failed")
        middleware._client = mock_client

        await middleware._flush_buffer()

        # Should have returned records to buffer
        assert len(middleware._buffer) == 1

    @pytest.mark.asyncio
    async def test_dispatch_excluded_paths(self):
        """Should skip excluded paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/healthz"
        mock_request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200

        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response == mock_response
        assert len(middleware._buffer) == 0

    @pytest.mark.asyncio
    async def test_dispatch_docs_paths(self):
        """Should skip docs paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/docs/oauth2-redirect"
        mock_request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200

        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response == mock_response
        assert len(middleware._buffer) == 0

    @pytest.mark.asyncio
    async def test_dispatch_tracks_request(self):
        """Should track non-excluded requests"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/auth/login"
        mock_request.method = "POST"

        mock_response = MagicMock()
        mock_response.status_code = 200

        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response == mock_response
        assert len(middleware._buffer) == 1

        record = middleware._buffer[0]
        assert record.endpoint == "/api/auth/login"
        assert record.method == "POST"
        assert record.status_code == 200

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Should clean up on shutdown"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Start running
        middleware._running = True
        middleware._flush_task = asyncio.create_task(asyncio.sleep(10))

        # Create and set a mock client
        mock_client = AsyncMock()
        middleware._client = mock_client

        await middleware.shutdown()

        assert not middleware._running
        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_loop(self):
        """Should run flush loop"""
        from app.config import settings

        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        # Mock _flush_buffer
        flush_count = 0
        original_flush = middleware._flush_buffer

        async def mock_flush():
            nonlocal flush_count
            flush_count += 1
            if flush_count >= 2:
                middleware._running = False

        middleware._flush_buffer = mock_flush

        with patch.object(settings, "usage_batch_interval_seconds", 0.01):
            await middleware._flush_loop()

        assert flush_count >= 1


class TestIntegration:
    """Integration tests for middleware with FastAPI app"""

    def test_middleware_with_app(self):
        """Should work with FastAPI app"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.add_middleware(UsageTrackingMiddleware, service_name="test-service")

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        response = client.get("/test")

        assert response.status_code == 200
