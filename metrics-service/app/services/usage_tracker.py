"""
Usage Tracker Service

Tracks and aggregates endpoint usage statistics across all microservices.
Uses Redis for persistent storage and real-time aggregation.
"""

import logging
from datetime import datetime

from ..models import EndpointUsage, EndpointUsageRecord, ServiceUsageSummary, UsageStatsResponse
from .redis_publisher import redis_publisher

logger = logging.getLogger(__name__)

# Redis keys for usage data
USAGE_KEY_PREFIX = "usage:"
USAGE_SERVICE_KEY = "usage:services"
USAGE_META_KEY = "usage:meta"


class UsageTracker:
    """
    Tracks endpoint usage statistics across all microservices.

    Stores aggregated data in Redis for persistence and
    provides real-time usage metrics.
    """

    def __init__(self):
        self._local_cache: dict[str, ServiceUsageSummary] = {}
        self._collection_started: datetime | None = None
        self._last_updated: datetime | None = None

    def _get_endpoint_key(self, service: str, method: str, endpoint: str) -> str:
        """Generate a unique Redis key for an endpoint."""
        # Normalize endpoint path
        normalized = endpoint.replace("/", "_").strip("_")
        return f"{USAGE_KEY_PREFIX}{service}:{method}:{normalized}"

    async def record_usage(self, record: EndpointUsageRecord) -> bool:
        """
        Record a single endpoint usage event.

        Updates both Redis storage and local cache.
        """
        try:
            redis = redis_publisher._redis
            if not redis:
                logger.warning("Redis not connected - storing usage locally only")
                self._update_local_cache(record)
                return False

            # Generate keys
            endpoint_key = self._get_endpoint_key(record.service, record.method, record.endpoint)
            service_key = f"{USAGE_KEY_PREFIX}{record.service}:summary"

            # Use Redis transaction for atomic updates
            pipe = redis.pipeline()

            # Update endpoint-specific stats using hash
            pipe.hincrby(endpoint_key, "request_count", 1)
            if 200 <= record.status_code < 400:
                pipe.hincrby(endpoint_key, "success_count", 1)
            else:
                pipe.hincrby(endpoint_key, "error_count", 1)

            pipe.hincrbyfloat(endpoint_key, "total_response_time_ms", record.response_time_ms)
            pipe.hincrby(endpoint_key, f"status:{record.status_code}", 1)

            # Store endpoint metadata
            pipe.hset(endpoint_key, "endpoint", record.endpoint)
            pipe.hset(endpoint_key, "method", record.method)
            pipe.hset(endpoint_key, "service", record.service)
            pipe.hset(endpoint_key, "last_accessed", record.timestamp.isoformat())

            # Update min/max response times
            pipe.hget(endpoint_key, "min_response_time_ms")
            pipe.hget(endpoint_key, "max_response_time_ms")

            # Track this endpoint in the service's endpoint set
            pipe.sadd(f"{USAGE_KEY_PREFIX}{record.service}:endpoints", endpoint_key)

            # Track this service in the global service set
            pipe.sadd(USAGE_SERVICE_KEY, record.service)

            # Update service-level summary
            pipe.hincrby(service_key, "total_requests", 1)
            if 200 <= record.status_code < 400:
                pipe.hincrby(service_key, "total_successes", 1)
            else:
                pipe.hincrby(service_key, "total_errors", 1)
            pipe.hincrbyfloat(service_key, "total_response_time_ms", record.response_time_ms)
            pipe.hset(service_key, "last_updated", record.timestamp.isoformat())

            # Update global metadata
            pipe.hset(USAGE_META_KEY, "last_updated", record.timestamp.isoformat())
            pipe.hsetnx(USAGE_META_KEY, "collection_started", record.timestamp.isoformat())

            results = await pipe.execute()

            # Handle min/max updates (need separate operation)
            current_min = results[10]  # hget min
            current_max = results[11]  # hget max

            update_pipe = redis.pipeline()

            if current_min is None or record.response_time_ms < float(current_min):
                update_pipe.hset(endpoint_key, "min_response_time_ms", str(record.response_time_ms))

            if current_max is None or record.response_time_ms > float(current_max):
                update_pipe.hset(endpoint_key, "max_response_time_ms", str(record.response_time_ms))

            # Set first_accessed only if not already set
            update_pipe.hsetnx(endpoint_key, "first_accessed", record.timestamp.isoformat())

            await update_pipe.execute()

            # Also update local cache for fast reads
            self._update_local_cache(record)

            return True

        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            # Fall back to local cache
            self._update_local_cache(record)
            return False

    async def record_batch(self, records: list[EndpointUsageRecord]) -> int:
        """
        Record multiple usage events efficiently.

        Returns the number of successfully recorded events.
        """
        success_count = 0
        for record in records:
            if await self.record_usage(record):
                success_count += 1
        return success_count

    def _update_local_cache(self, record: EndpointUsageRecord):
        """Update the local in-memory cache."""
        if record.service not in self._local_cache:
            self._local_cache[record.service] = ServiceUsageSummary(service=record.service)

        summary = self._local_cache[record.service]
        summary.total_requests += 1

        if 200 <= record.status_code < 400:
            summary.total_successes += 1
        else:
            summary.total_errors += 1

        summary.last_updated = record.timestamp

        if self._collection_started is None:
            self._collection_started = record.timestamp
        self._last_updated = record.timestamp

    async def get_usage_stats(self, service: str | None = None) -> UsageStatsResponse:
        """
        Get aggregated usage statistics.

        Args:
            service: Optional service name to filter by

        Returns:
            Aggregated usage statistics
        """
        try:
            redis = redis_publisher._redis
            if not redis:
                return self._get_local_stats(service)

            response = UsageStatsResponse()

            # Get metadata
            # Note: Redis client uses decode_responses=True, so keys/values are strings
            meta = await redis.hgetall(USAGE_META_KEY)
            if meta:
                if "collection_started" in meta:
                    response.collection_started = datetime.fromisoformat(meta["collection_started"])
                if "last_updated" in meta:
                    response.last_updated = datetime.fromisoformat(meta["last_updated"])

            # Get all services or filter by specific service
            if service:
                services = [service] if await redis.sismember(USAGE_SERVICE_KEY, service) else []
            else:
                services = list(await redis.smembers(USAGE_SERVICE_KEY))

            response.total_services = len(services)

            for svc in services:
                svc_summary = await self._get_service_summary(redis, svc)
                if svc_summary:
                    response.services[svc] = svc_summary
                    response.total_requests += svc_summary.total_requests

            return response

        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return self._get_local_stats(service)

    async def _get_service_summary(self, redis, service: str) -> ServiceUsageSummary | None:
        """Get usage summary for a specific service."""
        try:
            service_key = f"{USAGE_KEY_PREFIX}{service}:summary"
            summary_data = await redis.hgetall(service_key)

            if not summary_data:
                return None

            # Note: Redis client uses decode_responses=True, so keys/values are strings
            total_requests = int(summary_data.get("total_requests", 0))
            total_response_time = float(summary_data.get("total_response_time_ms", 0))

            summary = ServiceUsageSummary(
                service=service,
                total_requests=total_requests,
                total_successes=int(summary_data.get("total_successes", 0)),
                total_errors=int(summary_data.get("total_errors", 0)),
                avg_response_time_ms=(
                    total_response_time / total_requests if total_requests > 0 else None
                ),
            )

            if "last_updated" in summary_data:
                summary.last_updated = datetime.fromisoformat(summary_data["last_updated"])

            # Get all endpoints for this service
            endpoint_keys = await redis.smembers(f"{USAGE_KEY_PREFIX}{service}:endpoints")

            for key in endpoint_keys:
                endpoint = await self._get_endpoint_usage(redis, key)
                if endpoint:
                    summary.endpoints.append(endpoint)

            # Sort endpoints by request count
            summary.endpoints.sort(key=lambda e: e.request_count, reverse=True)

            return summary

        except Exception as e:
            logger.error(f"Failed to get service summary for {service}: {e}")
            return None

    async def _get_endpoint_usage(self, redis, key: str) -> EndpointUsage | None:
        """Get usage statistics for a specific endpoint."""
        try:
            data = await redis.hgetall(key)

            if not data:
                return None

            # Note: Redis client uses decode_responses=True, so keys/values are strings
            request_count = int(data.get("request_count", 0))
            total_time = float(data.get("total_response_time_ms", 0))

            # Parse status codes
            status_codes = {}
            for k, v in data.items():
                if k.startswith("status:"):
                    code = k.replace("status:", "")
                    status_codes[code] = int(v)

            endpoint = EndpointUsage(
                endpoint=data.get("endpoint", ""),
                method=data.get("method", ""),
                service=data.get("service", ""),
                request_count=request_count,
                success_count=int(data.get("success_count", 0)),
                error_count=int(data.get("error_count", 0)),
                total_response_time_ms=total_time,
                avg_response_time_ms=total_time / request_count if request_count > 0 else None,
                status_codes=status_codes,
            )

            if "min_response_time_ms" in data:
                endpoint.min_response_time_ms = float(data["min_response_time_ms"])

            if "max_response_time_ms" in data:
                endpoint.max_response_time_ms = float(data["max_response_time_ms"])

            if "last_accessed" in data:
                endpoint.last_accessed = datetime.fromisoformat(data["last_accessed"])

            if "first_accessed" in data:
                endpoint.first_accessed = datetime.fromisoformat(data["first_accessed"])

            return endpoint

        except Exception as e:
            logger.error(f"Failed to get endpoint usage for {key}: {e}")
            return None

    def _get_local_stats(self, service: str | None = None) -> UsageStatsResponse:
        """Get statistics from local cache when Redis is unavailable."""
        response = UsageStatsResponse(
            collection_started=self._collection_started,
            last_updated=self._last_updated,
        )

        if service:
            if service in self._local_cache:
                response.services[service] = self._local_cache[service]
                response.total_requests = self._local_cache[service].total_requests
                response.total_services = 1
        else:
            response.services = self._local_cache.copy()
            response.total_services = len(self._local_cache)
            response.total_requests = sum(s.total_requests for s in self._local_cache.values())

        return response

    async def reset_stats(self, service: str | None = None) -> bool:
        """
        Reset usage statistics.

        Args:
            service: Optional service to reset. If None, resets all stats.

        Returns:
            True if successful
        """
        try:
            redis = redis_publisher._redis

            if service:
                # Reset specific service
                if redis:
                    # Get all endpoint keys for this service
                    # Note: Redis client uses decode_responses=True, so keys are already strings
                    endpoint_keys = await redis.smembers(f"{USAGE_KEY_PREFIX}{service}:endpoints")

                    pipe = redis.pipeline()
                    for key in endpoint_keys:
                        pipe.delete(key)

                    pipe.delete(f"{USAGE_KEY_PREFIX}{service}:endpoints")
                    pipe.delete(f"{USAGE_KEY_PREFIX}{service}:summary")
                    pipe.srem(USAGE_SERVICE_KEY, service)

                    await pipe.execute()

                if service in self._local_cache:
                    del self._local_cache[service]
            else:
                # Reset all stats
                if redis:
                    # Get all services
                    # Note: Redis client uses decode_responses=True, so keys are already strings
                    services = await redis.smembers(USAGE_SERVICE_KEY)

                    pipe = redis.pipeline()
                    for svc_name in services:
                        endpoint_keys = await redis.smembers(
                            f"{USAGE_KEY_PREFIX}{svc_name}:endpoints"
                        )

                        for key in endpoint_keys:
                            pipe.delete(key)

                        pipe.delete(f"{USAGE_KEY_PREFIX}{svc_name}:endpoints")
                        pipe.delete(f"{USAGE_KEY_PREFIX}{svc_name}:summary")

                    pipe.delete(USAGE_SERVICE_KEY)
                    pipe.delete(USAGE_META_KEY)

                    await pipe.execute()

                self._local_cache = {}
                self._collection_started = None
                self._last_updated = None

            logger.info(
                f"Reset usage stats for {'service ' + service if service else 'all services'}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to reset stats: {e}")
            return False


# Global instance
usage_tracker = UsageTracker()
