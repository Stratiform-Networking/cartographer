"""
Tests for Redis-backed caching service.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import RedisError

from app.services.cache_service import CacheService


@pytest.fixture
async def cache_service():
    """Create a cache service instance for testing."""
    service = CacheService()
    service._enabled = True
    service._connection_attempted = False
    yield service
    if service._client:
        await service.close()


@pytest.fixture
async def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.setex = AsyncMock()
    mock.delete = AsyncMock(return_value=1)
    mock.scan_iter = AsyncMock(return_value=iter([]))
    return mock


class TestCacheService:
    """Test the CacheService class."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Complex async mock - tested via integration tests")
    async def test_initialize_success(self, cache_service):
        """Test successful Redis initialization."""
        # This test is complex to mock due to async context
        # Real initialization tested in integration tests
        pass

    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self, cache_service):
        """Test graceful degradation when Redis connection fails."""
        with patch("redis.asyncio.from_url", side_effect=RedisError("Connection failed")):
            await cache_service.initialize()

            assert cache_service._client is None
            assert cache_service._enabled is False

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache_service, mock_redis):
        """Test successful cache hit."""
        cache_service._client = mock_redis
        test_data = {"key": "value"}
        mock_redis.get.return_value = json.dumps(test_data)

        result = await cache_service.get("test_key")

        assert result == test_data
        mock_redis.get.assert_awaited_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache_service, mock_redis):
        """Test cache miss returns None."""
        cache_service._client = mock_redis
        mock_redis.get.return_value = None

        result = await cache_service.get("test_key")

        assert result is None
        mock_redis.get.assert_awaited_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_when_disabled(self, cache_service):
        """Test get returns None when cache is disabled."""
        cache_service._enabled = False

        result = await cache_service.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_redis_error(self, cache_service, mock_redis):
        """Test graceful handling of Redis errors on get."""
        cache_service._client = mock_redis
        mock_redis.get.side_effect = RedisError("Connection lost")

        result = await cache_service.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_json_decode_error(self, cache_service, mock_redis):
        """Test handling of invalid JSON in cache."""
        cache_service._client = mock_redis
        mock_redis.get.return_value = "invalid json {"

        result = await cache_service.get("test_key")

        assert result is None
        # Should also delete the invalid entry
        mock_redis.delete.assert_awaited_once_with("test_key")

    @pytest.mark.asyncio
    async def test_set_success(self, cache_service, mock_redis):
        """Test successful cache set."""
        cache_service._client = mock_redis
        test_data = {"key": "value"}

        result = await cache_service.set("test_key", test_data, ttl=60)

        assert result is True
        mock_redis.setex.assert_awaited_once_with("test_key", 60, json.dumps(test_data))

    @pytest.mark.asyncio
    async def test_set_no_ttl(self, cache_service, mock_redis):
        """Test cache set without TTL."""
        cache_service._client = mock_redis
        test_data = {"key": "value"}

        result = await cache_service.set("test_key", test_data)

        assert result is True
        mock_redis.set.assert_awaited_once_with("test_key", json.dumps(test_data))

    @pytest.mark.asyncio
    async def test_set_when_disabled(self, cache_service):
        """Test set returns False when cache is disabled."""
        cache_service._enabled = False

        result = await cache_service.set("test_key", {"data": "value"})

        assert result is False

    @pytest.mark.asyncio
    async def test_set_redis_error(self, cache_service, mock_redis):
        """Test graceful handling of Redis errors on set."""
        cache_service._client = mock_redis
        mock_redis.setex.side_effect = RedisError("Connection lost")

        result = await cache_service.set("test_key", {"data": "value"}, ttl=60)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_success(self, cache_service, mock_redis):
        """Test successful cache delete."""
        cache_service._client = mock_redis
        mock_redis.delete.return_value = 1

        result = await cache_service.delete("test_key")

        assert result is True
        mock_redis.delete.assert_awaited_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache_service, mock_redis):
        """Test delete of nonexistent key."""
        cache_service._client = mock_redis
        mock_redis.delete.return_value = 0

        result = await cache_service.delete("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_pattern_success(self, cache_service, mock_redis):
        """Test successful pattern delete."""
        cache_service._client = mock_redis
        # Mock scan_iter to return some keys
        async def mock_scan(**kwargs):
            for key in ["user:1:data", "user:1:prefs"]:
                yield key

        mock_redis.scan_iter = mock_scan
        mock_redis.delete.return_value = 2

        result = await cache_service.delete_pattern("user:1:*")

        assert result == 2

    @pytest.mark.asyncio
    async def test_delete_pattern_no_matches(self, cache_service, mock_redis):
        """Test pattern delete with no matching keys."""
        cache_service._client = mock_redis

        async def mock_scan(**kwargs):
            return
            yield  # Empty generator

        mock_redis.scan_iter = mock_scan

        result = await cache_service.delete_pattern("user:999:*")

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_hit(self, cache_service, mock_redis):
        """Test get_or_compute with cache hit."""
        cache_service._client = mock_redis
        cached_data = {"result": "cached"}
        mock_redis.get.return_value = json.dumps(cached_data)

        compute_fn = AsyncMock(return_value={"result": "computed"})
        result = await cache_service.get_or_compute("test_key", compute_fn, ttl=60)

        assert result == cached_data
        compute_fn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_miss(self, cache_service, mock_redis):
        """Test get_or_compute with cache miss."""
        cache_service._client = mock_redis
        mock_redis.get.return_value = None
        computed_data = {"result": "computed"}

        compute_fn = AsyncMock(return_value=computed_data)
        result = await cache_service.get_or_compute("test_key", compute_fn, ttl=60)

        assert result == computed_data
        compute_fn.assert_awaited_once()
        mock_redis.setex.assert_awaited_once_with("test_key", 60, json.dumps(computed_data))

    @pytest.mark.asyncio
    async def test_get_or_compute_cache_disabled(self, cache_service):
        """Test get_or_compute when cache is disabled."""
        cache_service._enabled = False
        computed_data = {"result": "computed"}

        compute_fn = AsyncMock(return_value=computed_data)
        result = await cache_service.get_or_compute("test_key", compute_fn, ttl=60)

        assert result == computed_data
        compute_fn.assert_awaited_once()

    def test_make_key(self):
        """Test cache key generation."""
        key = CacheService.make_key("networks", "user", "abc123")
        assert key == "networks:user:abc123"

    def test_make_hash_key(self):
        """Test hash-based cache key generation."""
        data = {"user_id": "123", "network_id": "456", "active": True}
        key1 = CacheService.make_hash_key("query:networks", data)
        key2 = CacheService.make_hash_key("query:networks", data)

        # Same data should produce same hash
        assert key1 == key2
        assert key1.startswith("query:networks:")
        assert len(key1.split(":")[-1]) == 8  # Hash suffix is 8 chars

        # Different data should produce different hash
        data2 = {"user_id": "999", "network_id": "456", "active": True}
        key3 = CacheService.make_hash_key("query:networks", data2)
        assert key1 != key3

    def test_make_hash_key_deterministic(self):
        """Test that hash keys are deterministic regardless of dict order."""
        data1 = {"b": 2, "a": 1, "c": 3}
        data2 = {"a": 1, "c": 3, "b": 2}

        key1 = CacheService.make_hash_key("test", data1)
        key2 = CacheService.make_hash_key("test", data2)

        # Different dict order should produce same hash
        assert key1 == key2

