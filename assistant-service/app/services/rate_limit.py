"""Rate limiting service using Redis for per-user daily limits."""

import logging
from datetime import datetime, timedelta

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import select

from ..config import settings

logger = logging.getLogger(__name__)

# Unlimited limit value in database
UNLIMITED_LIMIT = -1

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.redis_url,
            db=settings.redis_db,
            decode_responses=True,
        )
    return _redis


def _get_local_date() -> str:
    """Get today's date in the server's local timezone as ISO format string."""
    return datetime.now().date().isoformat()


def _seconds_until_local_midnight() -> int:
    """Calculate seconds until midnight in the server's local timezone."""
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).date()
    # Midnight tomorrow in local time
    midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day)
    return max(1, int((midnight - now).total_seconds()))


# Atomic: increment and set expiry only if first time
LUA_INCR_EXPIRE = """
local v = redis.call('INCR', KEYS[1])
if v == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return v
"""


def is_role_exempt(user_role: str) -> bool:
    """Check if a user role is exempt from rate limiting."""
    return user_role.lower() in settings.rate_limit_exempt_roles


async def get_user_limit(user_id: str, default_limit: int, user_role: str | None = None) -> int:
    """
    Get the effective daily limit for a user.

    Priority:
    1. If user role is in ASSISTANT_RATE_LIMIT_EXEMPT_ROLES -> unlimited (-1)
    2. If user has a custom limit in the database -> use that
    3. Otherwise -> use default_limit from env var

    Also handles syncing role exemption status to the database.

    Args:
        user_id: The user's ID
        default_limit: Default limit from env var (ASSISTANT_CHAT_LIMIT_PER_DAY)
        user_role: The user's role (member, admin, owner)

    Returns:
        -1 for unlimited, or a positive number for the limit
    """
    from ..database import AsyncSessionLocal
    from ..db_models import UserRateLimit

    # Check if user role is exempt from rate limiting
    is_exempt = user_role and is_role_exempt(user_role)

    # Database not configured, fall back to role-based check only
    if AsyncSessionLocal is None:
        if is_exempt:
            return UNLIMITED_LIMIT
        return default_limit

    try:
        async with AsyncSessionLocal() as session:
            # Get or create user rate limit record
            result = await session.execute(
                select(UserRateLimit).where(UserRateLimit.user_id == user_id)
            )
            user_limit = result.scalar_one_or_none()

            if user_limit is None:
                # Create new record
                user_limit = UserRateLimit(
                    user_id=user_id,
                    daily_limit=UNLIMITED_LIMIT if is_exempt else None,  # NULL = use default
                    is_role_exempt=is_exempt,
                )
                session.add(user_limit)
                await session.commit()

                if is_exempt:
                    logger.info(f"[RateLimit] Created unlimited limit for exempt user {user_id}")
                    return UNLIMITED_LIMIT
                return default_limit

            # User exists - handle role exemption changes
            if is_exempt and not user_limit.is_role_exempt:
                # User became exempt (e.g., promoted to admin)
                user_limit.daily_limit = UNLIMITED_LIMIT
                user_limit.is_role_exempt = True
                await session.commit()
                logger.info(
                    f"[RateLimit] User {user_id} is now exempt (role: {user_role}), set to unlimited"
                )
                return UNLIMITED_LIMIT

            if not is_exempt and user_limit.is_role_exempt:
                # User lost exemption (e.g., demoted from admin)
                user_limit.daily_limit = None  # Revert to default
                user_limit.is_role_exempt = False
                await session.commit()
                logger.info(
                    f"[RateLimit] User {user_id} lost exemption (role: {user_role}), reverted to default"
                )
                return default_limit

            # User still exempt - keep unlimited
            if is_exempt:
                return UNLIMITED_LIMIT

            # Return stored limit or default
            if user_limit.daily_limit is not None:
                # Custom limit set (could be -1 for manual unlimited, or positive for custom)
                return user_limit.daily_limit

            # NULL means use system default
            return default_limit

    except Exception as e:
        logger.error(f"[RateLimit] Error getting user limit: {e}")
        # Fall back to role-based check
        if is_exempt:
            return UNLIMITED_LIMIT
        return default_limit


async def check_rate_limit(
    user_id: str, endpoint: str, limit: int, user_role: str | None = None
) -> None:
    """
    Check if user has exceeded their daily rate limit.
    Raises HTTPException with 429 if limit exceeded.

    The daily limit resets at midnight in the server's local timezone.

    Uses per-user limits from the database when available.

    Args:
        user_id: The user's ID
        endpoint: Endpoint identifier for the rate limit key
        limit: Default maximum requests per day (from env var)
        user_role: The user's role (member, admin, owner)
    """
    # Get user's effective limit (may be different from default)
    effective_limit = await get_user_limit(user_id, limit, user_role)

    # Unlimited users bypass rate limiting
    if effective_limit == UNLIMITED_LIMIT:
        return

    redis = await get_redis()

    # Include date (server local time) so keys naturally partition by day
    day = _get_local_date()
    key = f"rl:assistant:{user_id}:{endpoint}:{day}"

    ttl = _seconds_until_local_midnight()
    count = await redis.eval(LUA_INCR_EXPIRE, 1, key, ttl)

    if int(count) > effective_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit exceeded for this endpoint ({effective_limit}/day). Try again tomorrow.",
            headers={"Retry-After": str(ttl)},
        )


async def get_rate_limit_status(
    user_id: str, endpoint: str, limit: int, user_role: str | None = None
) -> dict:
    """
    Get the current rate limit status for a user.

    The daily limit resets at midnight in the server's local timezone.

    Uses per-user limits from the database when available.

    Args:
        user_id: The user's ID
        endpoint: Endpoint identifier for the rate limit key
        limit: Default maximum requests per day (from env var)
        user_role: The user's role

    Returns:
        dict with 'used', 'limit', 'remaining', 'resets_in_seconds', 'is_exempt'
    """
    # Get user's effective limit (may be different from default)
    effective_limit = await get_user_limit(user_id, limit, user_role)

    # Unlimited users
    if effective_limit == UNLIMITED_LIMIT:
        return {
            "used": 0,
            "limit": -1,  # -1 indicates unlimited
            "remaining": -1,  # -1 indicates unlimited
            "resets_in_seconds": 0,
            "is_exempt": True,
        }

    redis = await get_redis()

    day = _get_local_date()
    key = f"rl:assistant:{user_id}:{endpoint}:{day}"

    count = await redis.get(key)
    used = int(count) if count else 0
    ttl = _seconds_until_local_midnight()

    return {
        "used": used,
        "limit": effective_limit,
        "remaining": max(0, effective_limit - used),
        "resets_in_seconds": ttl,
        "is_exempt": False,
    }


async def set_user_limit(user_id: str, daily_limit: int | None, is_manual: bool = True) -> dict:
    """
    Set a custom daily limit for a user.

    Args:
        user_id: The user's ID
        daily_limit: The new limit. Use -1 for unlimited, None to reset to default.
        is_manual: If True, this is a manual admin override. If False, it's role-based.

    Returns:
        dict with updated user limit info
    """
    from ..database import AsyncSessionLocal
    from ..db_models import UserRateLimit

    if AsyncSessionLocal is None:
        raise RuntimeError("Database not configured")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserRateLimit).where(UserRateLimit.user_id == user_id)
        )
        user_limit = result.scalar_one_or_none()

        if user_limit is None:
            # Create new record
            user_limit = UserRateLimit(
                user_id=user_id,
                daily_limit=daily_limit,
                is_role_exempt=not is_manual,  # Manual overrides are not role-based
            )
            session.add(user_limit)
        else:
            user_limit.daily_limit = daily_limit
            if is_manual:
                # Manual override clears the role exempt flag
                user_limit.is_role_exempt = False

        await session.commit()

        limit_str = (
            "unlimited"
            if daily_limit == -1
            else ("default" if daily_limit is None else str(daily_limit))
        )
        logger.info(f"[RateLimit] Set user {user_id} limit to {limit_str} (manual={is_manual})")

        return {
            "user_id": user_id,
            "daily_limit": daily_limit,
            "is_role_exempt": user_limit.is_role_exempt,
        }


async def reset_user_to_default(user_id: str) -> dict:
    """
    Reset a user's limit to the system default.

    Args:
        user_id: The user's ID

    Returns:
        dict with updated user limit info
    """
    return await set_user_limit(user_id, None, is_manual=True)
