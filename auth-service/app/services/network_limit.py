"""Network limit service for enforcing per-user network creation limits."""

import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db_models import UserLimit

logger = logging.getLogger(__name__)

# Unlimited limit value in database
UNLIMITED_LIMIT = -1


def is_role_exempt(user_role: str) -> bool:
    """Check if a user role is exempt from network limits."""
    return user_role.lower() in settings.network_limit_exempt_roles_set


async def get_user_network_limit(
    db: AsyncSession, user_id: str, user_role: str | None = None
) -> int:
    """
    Get the effective network limit for a user.

    Priority:
    1. If user role is in NETWORK_LIMIT_EXEMPT_ROLES -> unlimited (-1)
    2. If user has a custom limit in the database -> use that
    3. Otherwise -> use default_limit from env var

    Args:
        db: Database session
        user_id: The user's ID
        user_role: The user's role (member, admin, owner)

    Returns:
        -1 for unlimited, or a positive number for the limit
    """
    is_exempt = user_role and is_role_exempt(user_role)

    result = await db.execute(select(UserLimit).where(UserLimit.user_id == user_id))
    user_limit = result.scalar_one_or_none()

    if user_limit is None:
        # No custom limit set
        if is_exempt:
            # Create record for exempt user
            new_limit = UserLimit(
                user_id=user_id,
                network_limit=UNLIMITED_LIMIT,
                is_role_exempt=True,
            )
            db.add(new_limit)
            try:
                await db.commit()
                logger.info(f"[NetworkLimit] Created unlimited limit for exempt user {user_id}")
                return UNLIMITED_LIMIT
            except IntegrityError:
                # Another concurrent request created this row first.
                await db.rollback()
                result = await db.execute(select(UserLimit).where(UserLimit.user_id == user_id))
                user_limit = result.scalar_one_or_none()
                if user_limit is None:
                    raise
        else:
            return settings.network_limit_per_user

    # Handle exemption status changes
    if is_exempt and not user_limit.is_role_exempt:
        user_limit.network_limit = UNLIMITED_LIMIT
        user_limit.is_role_exempt = True
        await db.commit()
        logger.info(f"[NetworkLimit] User {user_id} is now exempt (role: {user_role})")
        return UNLIMITED_LIMIT

    if not is_exempt and user_limit.is_role_exempt:
        user_limit.network_limit = None
        user_limit.is_role_exempt = False
        await db.commit()
        logger.info(f"[NetworkLimit] User {user_id} lost exemption (role: {user_role})")
        return settings.network_limit_per_user

    if is_exempt:
        return UNLIMITED_LIMIT

    return (
        user_limit.network_limit
        if user_limit.network_limit is not None
        else settings.network_limit_per_user
    )


async def get_network_count(db: AsyncSession, user_id: str) -> int:
    """
    Get the number of networks owned by a user.

    Args:
        db: Database session
        user_id: The user's ID

    Returns:
        Number of active networks owned by the user
    """
    # Import here to avoid circular imports - Network model is in backend
    # This function will be called from backend, which has access to the Network model
    from sqlalchemy import text

    result = await db.execute(
        text("SELECT COUNT(*) FROM networks WHERE user_id = :user_id AND is_active = true"),
        {"user_id": user_id},
    )
    return result.scalar() or 0


async def get_network_limit_status(
    db: AsyncSession, user_id: str, user_role: str | None = None
) -> dict:
    """
    Get the current network limit status for a user.

    Args:
        db: Database session
        user_id: The user's ID
        user_role: The user's role

    Returns:
        dict with 'used', 'limit', 'remaining', 'is_exempt', 'message'
    """
    effective_limit = await get_user_network_limit(db, user_id, user_role)
    is_exempt = effective_limit == UNLIMITED_LIMIT

    if is_exempt:
        # Still get the count for informational purposes
        used = await get_network_count(db, user_id)
        return {
            "used": used,
            "limit": -1,
            "remaining": -1,
            "is_exempt": True,
            "message": None,
        }

    used = await get_network_count(db, user_id)
    remaining = max(0, effective_limit - used)

    # Include message only when limit is reached
    message = None
    if remaining <= 0:
        message = settings.network_limit_message_text.format(limit=effective_limit)

    return {
        "used": used,
        "limit": effective_limit,
        "remaining": remaining,
        "is_exempt": False,
        "message": message,
    }


async def check_network_limit(db: AsyncSession, user_id: str, user_role: str | None = None) -> None:
    """
    Check if user can create another network.
    Raises HTTPException with 403 if limit exceeded.

    Args:
        db: Database session
        user_id: The user's ID
        user_role: The user's role
    """
    effective_limit = await get_user_network_limit(db, user_id, user_role)

    # Unlimited users bypass the check
    if effective_limit == UNLIMITED_LIMIT:
        return

    used = await get_network_count(db, user_id)

    if used >= effective_limit:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Network limit reached. You can have a maximum of {effective_limit} network(s)."
            ),
        )


async def set_user_network_limit(db: AsyncSession, user_id: str, network_limit: int | None) -> dict:
    """
    Set a custom network limit for a user.

    Args:
        db: Database session
        user_id: The user's ID
        network_limit: The new limit. Use -1 for unlimited, None to reset to default.

    Returns:
        dict with updated user limit info
    """
    result = await db.execute(select(UserLimit).where(UserLimit.user_id == user_id))
    user_limit = result.scalar_one_or_none()

    if user_limit is None:
        # Create new record
        user_limit = UserLimit(
            user_id=user_id,
            network_limit=network_limit,
            is_role_exempt=False,  # Manual override is not role-based
        )
        db.add(user_limit)
    else:
        user_limit.network_limit = network_limit
        # Manual override clears the role exempt flag
        user_limit.is_role_exempt = False

    try:
        await db.commit()
    except IntegrityError:
        # Concurrent create: reload and apply update so the request still succeeds.
        await db.rollback()
        result = await db.execute(select(UserLimit).where(UserLimit.user_id == user_id))
        user_limit = result.scalar_one_or_none()
        if user_limit is None:
            raise

        user_limit.network_limit = network_limit
        user_limit.is_role_exempt = False
        await db.commit()

    limit_str = (
        "unlimited"
        if network_limit == -1
        else ("default" if network_limit is None else str(network_limit))
    )
    logger.info(f"[NetworkLimit] Set user {user_id} network limit to {limit_str}")

    return {
        "user_id": user_id,
        "network_limit": network_limit,
        "is_role_exempt": user_limit.is_role_exempt,
    }
