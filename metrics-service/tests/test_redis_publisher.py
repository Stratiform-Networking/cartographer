"""
Unit tests for RedisPublisher service.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis

from app.models import (
    HealthStatus,
    MetricsEvent,
    MetricsEventType,
    NetworkTopologySnapshot,
    NodeMetrics,
    SpeedTestMetrics,
)
from app.services.redis_publisher import (
    CHANNEL_HEALTH,
    CHANNEL_SPEED_TEST,
    CHANNEL_TOPOLOGY,
    RedisPublisher,
)


class TestRedisPublisherInit:
    """Tests for RedisPublisher initialization"""

    def test_init_defaults(self, redis_publisher_instance):
        """Should initialize with default values"""
        assert redis_publisher_instance._redis is None
        assert redis_publisher_instance._pubsub is None
        assert redis_publisher_instance._subscriber_tasks == []
        assert redis_publisher_instance._message_handlers == {}
        assert redis_publisher_instance._connected is False


class TestConnection:
    """Tests for Redis connection"""

    async def test_connect_success(self, redis_publisher_instance):
        """Should connect to Redis successfully"""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            result = await redis_publisher_instance.connect()

        assert result is True
        assert redis_publisher_instance._connected is True

    async def test_connect_failure(self, redis_publisher_instance):
        """Should handle connection failure"""
        with patch(
            "redis.asyncio.Redis.from_url", side_effect=redis.ConnectionError("Connection refused")
        ):
            result = await redis_publisher_instance.connect()

        assert result is False
        assert redis_publisher_instance._connected is False

    async def test_connect_unexpected_error(self, redis_publisher_instance):
        """Should handle unexpected errors"""
        with patch("redis.asyncio.Redis.from_url", side_effect=Exception("Unexpected")):
            result = await redis_publisher_instance.connect()

        assert result is False
        assert redis_publisher_instance._connected is False

    async def test_disconnect(self, redis_publisher_instance):
        """Should disconnect and cleanup"""
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._pubsub = mock_pubsub
        redis_publisher_instance._subscriber_tasks = []  # No tasks to simplify
        redis_publisher_instance._connected = True

        await redis_publisher_instance.disconnect()

        assert redis_publisher_instance._connected is False
        assert redis_publisher_instance._redis is None
        assert redis_publisher_instance._pubsub is None
        mock_redis.close.assert_called_once()
        mock_pubsub.close.assert_called_once()

    async def test_disconnect_with_tasks(self, redis_publisher_instance):
        """Should cancel and await subscriber tasks"""
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()

        # Create a real task that can be cancelled
        async def dummy_task():
            await asyncio.sleep(100)

        task = asyncio.create_task(dummy_task())

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._pubsub = mock_pubsub
        redis_publisher_instance._subscriber_tasks = [task]
        redis_publisher_instance._connected = True

        await redis_publisher_instance.disconnect()

        assert redis_publisher_instance._connected is False
        assert redis_publisher_instance._subscriber_tasks == []
        assert task.cancelled()

    def test_is_connected_false(self, redis_publisher_instance):
        """Should return False when not connected"""
        assert redis_publisher_instance.is_connected is False

    def test_is_connected_true(self, redis_publisher_instance):
        """Should return True when connected"""
        redis_publisher_instance._connected = True
        redis_publisher_instance._redis = MagicMock()

        assert redis_publisher_instance.is_connected is True


class TestPublishing:
    """Tests for publishing methods"""

    async def test_publish_success(self, redis_publisher_instance):
        """Should publish message successfully"""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.publish(
            "test:channel", MetricsEventType.FULL_SNAPSHOT, {"data": "test"}
        )

        assert result is True
        mock_redis.publish.assert_called_once()

    async def test_publish_not_connected(self, redis_publisher_instance):
        """Should return False when not connected"""
        with patch.object(
            redis_publisher_instance, "_ensure_connected", AsyncMock(return_value=False)
        ):
            result = await redis_publisher_instance.publish(
                "test:channel", MetricsEventType.FULL_SNAPSHOT, {"data": "test"}
            )

        assert result is False

    async def test_publish_redis_error(self, redis_publisher_instance):
        """Should handle Redis error"""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(side_effect=redis.RedisError("Error"))

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.publish(
            "test:channel", MetricsEventType.FULL_SNAPSHOT, {"data": "test"}
        )

        assert result is False
        assert redis_publisher_instance._connected is False

    async def test_publish_pydantic_model(self, redis_publisher_instance, sample_snapshot):
        """Should serialize Pydantic models"""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.publish(
            "test:channel", MetricsEventType.FULL_SNAPSHOT, sample_snapshot
        )

        assert result is True

    async def test_publish_topology_snapshot(self, redis_publisher_instance, sample_snapshot):
        """Should publish topology snapshot"""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.publish_topology_snapshot(sample_snapshot)

        assert result is True

    async def test_publish_node_update(self, redis_publisher_instance):
        """Should publish node update"""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        node = NodeMetrics(id="node-1", name="Test Node", status=HealthStatus.HEALTHY)

        result = await redis_publisher_instance.publish_node_update(node)

        assert result is True

    async def test_publish_health_update(self, redis_publisher_instance):
        """Should publish health update"""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.publish_health_update(
            "node-1", "healthy", {"latency_ms": 5.0}
        )

        assert result is True

    async def test_publish_speed_test_result(self, redis_publisher_instance):
        """Should publish speed test result"""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = SpeedTestMetrics(
            success=True, timestamp=datetime.now(timezone.utc), download_mbps=100.0
        )

        published = await redis_publisher_instance.publish_speed_test_result("192.168.1.1", result)

        assert published is True


class TestSubscription:
    """Tests for subscription methods"""

    def test_add_handler(self, redis_publisher_instance):
        """Should add message handler"""
        handler = MagicMock()

        redis_publisher_instance.add_handler("test:channel", handler)

        assert "test:channel" in redis_publisher_instance._message_handlers
        assert handler in redis_publisher_instance._message_handlers["test:channel"]

    def test_remove_handler(self, redis_publisher_instance):
        """Should remove message handler"""
        handler = MagicMock()
        redis_publisher_instance._message_handlers["test:channel"] = [handler]

        redis_publisher_instance.remove_handler("test:channel", handler)

        assert handler not in redis_publisher_instance._message_handlers["test:channel"]

    def test_remove_handler_not_exists(self, redis_publisher_instance):
        """Should handle removing non-existent handler"""
        handler = MagicMock()

        # Should not raise
        redis_publisher_instance.remove_handler("test:channel", handler)

    async def test_subscribe_success(self, redis_publisher_instance):
        """Should subscribe to channels"""
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        with patch("asyncio.create_task") as mock_create_task:
            result = await redis_publisher_instance.subscribe("test:channel")

        assert result is True
        mock_pubsub.subscribe.assert_called_once()

    async def test_subscribe_not_connected(self, redis_publisher_instance):
        """Should return False when not connected"""
        with patch.object(
            redis_publisher_instance, "_ensure_connected", AsyncMock(return_value=False)
        ):
            result = await redis_publisher_instance.subscribe("test:channel")

        assert result is False

    async def test_subscribe_redis_error(self, redis_publisher_instance):
        """Should handle Redis error"""
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock(side_effect=redis.RedisError("Error"))
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._pubsub = mock_pubsub
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.subscribe("test:channel")

        assert result is False

    async def test_unsubscribe_success(self, redis_publisher_instance):
        """Should unsubscribe from channels"""
        mock_pubsub = AsyncMock()
        redis_publisher_instance._pubsub = mock_pubsub

        result = await redis_publisher_instance.unsubscribe("test:channel")

        assert result is True
        mock_pubsub.unsubscribe.assert_called_once()

    async def test_unsubscribe_no_pubsub(self, redis_publisher_instance):
        """Should return True when no pubsub"""
        result = await redis_publisher_instance.unsubscribe("test:channel")

        assert result is True

    async def test_unsubscribe_redis_error(self, redis_publisher_instance):
        """Should handle Redis error"""
        mock_pubsub = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock(side_effect=redis.RedisError("Error"))
        redis_publisher_instance._pubsub = mock_pubsub

        result = await redis_publisher_instance.unsubscribe("test:channel")

        assert result is False


class TestUtilityMethods:
    """Tests for utility methods"""

    async def test_get_last_snapshot_success(self, redis_publisher_instance, sample_snapshot):
        """Should get last snapshot from Redis"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=sample_snapshot.model_dump_json())

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.get_last_snapshot()

        assert result is not None
        assert result.snapshot_id == sample_snapshot.snapshot_id

    async def test_get_last_snapshot_not_found(self, redis_publisher_instance):
        """Should return None when no snapshot"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.get_last_snapshot()

        assert result is None

    async def test_get_last_snapshot_not_connected(self, redis_publisher_instance):
        """Should return None when not connected"""
        with patch.object(
            redis_publisher_instance, "_ensure_connected", AsyncMock(return_value=False)
        ):
            result = await redis_publisher_instance.get_last_snapshot()

        assert result is None

    async def test_get_last_snapshot_error(self, redis_publisher_instance):
        """Should return None on error"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Error"))

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.get_last_snapshot()

        assert result is None

    async def test_store_last_snapshot_success(self, redis_publisher_instance, sample_snapshot):
        """Should store snapshot in Redis"""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.store_last_snapshot(sample_snapshot)

        assert result is True
        mock_redis.set.assert_called_once()

    async def test_store_last_snapshot_not_connected(
        self, redis_publisher_instance, sample_snapshot
    ):
        """Should return False when not connected"""
        with patch.object(
            redis_publisher_instance, "_ensure_connected", AsyncMock(return_value=False)
        ):
            result = await redis_publisher_instance.store_last_snapshot(sample_snapshot)

        assert result is False

    async def test_store_last_snapshot_error(self, redis_publisher_instance, sample_snapshot):
        """Should return False on error"""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(side_effect=Exception("Error"))

        redis_publisher_instance._redis = mock_redis
        redis_publisher_instance._connected = True

        result = await redis_publisher_instance.store_last_snapshot(sample_snapshot)

        assert result is False

    async def test_get_connection_info(self, redis_publisher_instance):
        """Should return connection info"""
        redis_publisher_instance._message_handlers = {"test:channel": []}

        info = await redis_publisher_instance.get_connection_info()

        assert "url" in info
        assert "db" in info
        assert "connected" in info
        assert "channels" in info


class TestSerialization:
    """Tests for serialization methods"""

    def test_serialize_event(self, redis_publisher_instance):
        """Should serialize event to JSON"""
        event = MetricsEvent(
            event_type=MetricsEventType.FULL_SNAPSHOT,
            timestamp=datetime.now(timezone.utc),
            payload={"data": "test"},
        )

        result = redis_publisher_instance._serialize_event(event)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["event_type"] == "full_snapshot"

    def test_serialize_payload_dict(self, redis_publisher_instance):
        """Should serialize dict payload"""
        result = redis_publisher_instance._serialize_payload({"data": "test"})

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["data"] == "test"

    def test_serialize_payload_pydantic(self, redis_publisher_instance, sample_snapshot):
        """Should serialize Pydantic model"""
        result = redis_publisher_instance._serialize_payload(sample_snapshot)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "snapshot_id" in parsed
