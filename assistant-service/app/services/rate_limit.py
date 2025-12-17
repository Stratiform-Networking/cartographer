import os
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from fastapi import HTTPException, Request
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB = int(os.getenv("REDIS_DB", "1"))

_redis: Redis | None = None

async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            REDIS_URL,
            db=REDIS_DB,
            decode_responses=True,
        )
    return _redis

def _seconds_until_utc_midnight() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).date()
    midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)
    return max(1, int((midnight - now).total_seconds()))

# Atomic: increment and set expiry only if first time
LUA_INCR_EXPIRE = """
local v = redis.call('INCR', KEYS[1])
if v == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return v
"""


async def check_rate_limit(user_id: str, endpoint: str, limit: int) -> None:
    """
    Check if user has exceeded their daily rate limit.
    Raises HTTPException with 429 if limit exceeded.
    
    Args:
        user_id: The user's ID
        endpoint: Endpoint identifier for the rate limit key
        limit: Maximum requests per day
    """
    redis = await get_redis()
    
    # Include date so keys naturally partition by day
    day = datetime.now(timezone.utc).date().isoformat()
    key = f"rl:assistant:{user_id}:{endpoint}:{day}"
    
    ttl = _seconds_until_utc_midnight()
    count = await redis.eval(LUA_INCR_EXPIRE, 1, key, ttl)
    
    if int(count) > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit exceeded for this endpoint ({limit}/day). Try again tomorrow.",
            headers={"Retry-After": str(ttl)},
        )


async def get_rate_limit_status(user_id: str, endpoint: str, limit: int) -> dict:
    """
    Get the current rate limit status for a user.
    
    Returns:
        dict with 'used', 'limit', 'remaining', 'resets_in_seconds'
    """
    redis = await get_redis()
    
    day = datetime.now(timezone.utc).date().isoformat()
    key = f"rl:assistant:{user_id}:{endpoint}:{day}"
    
    count = await redis.get(key)
    used = int(count) if count else 0
    ttl = _seconds_until_utc_midnight()
    
    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "resets_in_seconds": ttl,
    }
