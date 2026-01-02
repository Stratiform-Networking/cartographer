"""
Redis-backed caching service for query results and computed data.

This service provides:
- Key-value caching with TTL support
- Cache invalidation patterns
- Graceful degradation if Redis unavailable
- Typed cache key generation
"""

import hashlib
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Callable

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from ..config import get_settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis-backed cache service with graceful degradation.
    
    Features:
    - Automatic JSON serialization
    - TTL support per operation
    - Cache miss/hit logging
    - Graceful fallback if Redis unavailable
    """

    def __init__(self):
        self._client: aioredis.Redis | None = None
        self._enabled: bool = True
        self._connection_attempted: bool = False

    async def initialize(self):
        """Initialize Redis connection."""
        if self._connection_attempted:
            return

        settings = get_settings()
        self._enabled = settings.redis_cache_enabled

        if not self._enabled:
            logger.info("Redis caching disabled by configuration")
            self._connection_attempted = True
            return

        try:
            # Parse Redis URL and create connection
            self._client = await aioredis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5.0,
                socket_timeout=5.0,
            )

            # Test connection
            await self._client.ping()
            logger.info(
                f"Redis cache initialized: {settings.redis_url} (DB {settings.redis_db})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            logger.warning("Cache service will operate in pass-through mode")
            self._client = None
            self._enabled = False
        finally:
            self._connection_attempted = True

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Redis cache connection closed")

    async def get(self, key: str) -> Any | None:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized value or None if not found/error
        """
        if not self._enabled or not self._client:
            return None

        try:
            cached = await self._client.get(key)
            if cached:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(cached)
            logger.debug(f"Cache MISS: {key}")
            return None
        except RedisError as e:
            logger.warning(f"Cache GET error for key {key}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Cache JSON decode error for key {key}: {e}")
            # Invalid cache entry - delete it
            await self.delete(key)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds (None = no expiration)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self._enabled or not self._client:
            return False

        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.warning(f"Cache SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        if not self._enabled or not self._client:
            return False

        try:
            result = await self._client.delete(key)
            logger.debug(f"Cache DELETE: {key} (existed: {result > 0})")
            return result > 0
        except RedisError as e:
            logger.warning(f"Cache DELETE error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "user:123:*")
            
        Returns:
            Number of keys deleted
        """
        if not self._enabled or not self._client:
            return 0

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern, count=100):
                keys.append(key)

            if keys:
                deleted = await self._client.delete(*keys)
                logger.info(f"Cache DELETE pattern '{pattern}': {deleted} keys")
                return deleted
            return 0
        except RedisError as e:
            logger.warning(f"Cache DELETE pattern error for '{pattern}': {e}")
            return 0

    async def get_or_compute(
        self,
        key: str,
        compute_fn: Callable,
        ttl: int | None = None
    ) -> Any:
        """
        Get from cache or compute and cache the result.
        
        This is the primary caching pattern for query results.
        
        Args:
            key: Cache key
            compute_fn: Async function to compute value on cache miss
            ttl: TTL in seconds for cached value
            
        Returns:
            Cached or computed value
        """
        # Try cache first
        cached = await self.get(key)
        if cached is not None:
            return cached

        # Cache miss - compute value
        value = await compute_fn()

        # Cache the result (best effort - don't fail if caching fails)
        await self.set(key, value, ttl)

        return value

    @staticmethod
    def make_key(*parts: str) -> str:
        """
        Generate a cache key from parts.
        
        Args:
            *parts: Key components (e.g., "networks", "user", user_id)
            
        Returns:
            Formatted cache key (e.g., "networks:user:abc123")
        """
        return ":".join(str(p) for p in parts)

    @staticmethod
    def make_hash_key(prefix: str, data: dict) -> str:
        """
        Generate a cache key with hash suffix for complex query parameters.
        
        Useful for caching query results with many parameters.
        
        Args:
            prefix: Key prefix (e.g., "query:networks")
            data: Dictionary of query parameters
            
        Returns:
            Cache key with deterministic hash (e.g., "query:networks:a1b2c3")
        """
        # Sort dict for consistent hashing
        serialized = json.dumps(data, sort_keys=True, default=str)
        hash_suffix = hashlib.md5(serialized.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_suffix}"


# Global singleton instance
cache_service = CacheService()


@asynccontextmanager
async def lifespan_cache():
    """
    Async context manager for FastAPI lifespan.
    Handles initialization and cleanup of the cache service.
    """
    await cache_service.initialize()
    yield
    await cache_service.close()


# Dependency injection for FastAPI routes
async def get_cache() -> CacheService:
    """FastAPI dependency to inject cache service."""
    return cache_service

