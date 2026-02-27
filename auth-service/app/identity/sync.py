"""
User synchronization service for external auth providers.

Syncs external provider users to the local PostgreSQL database,
which remains the source of truth for user data.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db_models import ProviderLink, User, UserRole
from ..services.plan_settings import initialize_default_plan_settings_for_new_user
from .claims import AuthProvider, IdentityClaims

logger = logging.getLogger(__name__)


def _update_user_profile(user: User, claims: IdentityClaims) -> bool:
    """Update user profile fields from claims. Returns True if updated."""
    if claims.first_name:
        user.first_name = claims.first_name
    if claims.last_name:
        user.last_name = claims.last_name
    if claims.email:
        user.email = claims.email.strip().lower()
    user.avatar_url = claims.avatar_url
    user.is_verified = claims.email_verified
    user.updated_at = datetime.now(timezone.utc)
    return True


async def _get_unique_username(db: AsyncSession, base_username: str) -> str:
    """Generate a unique username based on the base username."""
    username = base_username
    counter = 1
    while True:
        existing = await db.execute(select(User).where(User.username == username))
        if not existing.scalar_one_or_none():
            return username
        username = f"{base_username}{counter}"
        counter += 1


async def _handle_existing_link(
    db: AsyncSession,
    link: ProviderLink,
    claims: IdentityClaims,
    update_profile: bool,
) -> tuple[UUID | None, bool, bool]:
    """Handle sync when provider link already exists."""
    user_result = await db.execute(select(User).where(User.id == link.user_id))
    user = user_result.scalar_one_or_none()

    updated = False
    if user and update_profile:
        _update_user_profile(user, claims)
        await db.commit()
        updated = True

    return UUID(link.user_id) if link.user_id else None, False, updated


async def _handle_email_match(
    db: AsyncSession,
    user: User,
    claims: IdentityClaims,
    update_profile: bool,
) -> tuple[UUID, bool, bool]:
    """Handle sync when user exists with matching email but no provider link."""
    new_link = ProviderLink(
        user_id=user.id,
        provider=claims.provider.value,
        provider_user_id=claims.provider_user_id,
    )
    db.add(new_link)

    updated = False
    if update_profile:
        _update_user_profile(user, claims)
        updated = True

    await db.commit()
    return UUID(user.id), False, updated


async def _create_new_user(
    db: AsyncSession,
    claims: IdentityClaims,
) -> tuple[UUID, bool, bool]:
    """Create a new user from claims."""
    # Generate username from email if not provided
    username = claims.username
    if not username:
        base_username = claims.email.split("@")[0].lower()
        username = await _get_unique_username(db, base_username)

    logger.info(f"Creating new user: {username} ({claims.email})")

    new_user = User(
        id=str(uuid4()),
        username=username,
        email=claims.email.strip().lower(),
        first_name=claims.first_name or "",
        last_name=claims.last_name or "",
        avatar_url=claims.avatar_url,
        hashed_password="",  # No password for external auth
        role=UserRole.MEMBER,
        is_active=True,
        is_verified=claims.email_verified,
    )
    db.add(new_user)
    await db.flush()  # Get the ID

    # Create provider link
    new_link = ProviderLink(
        user_id=new_user.id,
        provider=claims.provider.value,
        provider_user_id=claims.provider_user_id,
    )
    db.add(new_link)
    await initialize_default_plan_settings_for_new_user(db, new_user.id, commit=False)

    await db.commit()
    logger.info(f"Created user {new_user.id} with provider link for {claims.provider.value}")
    return UUID(new_user.id), True, False


async def sync_provider_user(
    db: AsyncSession,
    claims: IdentityClaims,
    create_if_missing: bool = True,
    update_profile: bool = True,
) -> tuple[UUID | None, bool, bool]:
    """
    Sync an external provider user to the local database.

    This ensures the local database is the source of truth while
    allowing external providers to manage authentication.

    Args:
        db: Database session
        claims: The identity claims from the provider
        create_if_missing: Create local user if not found
        update_profile: Update profile fields from claims

    Returns:
        Tuple of (local_user_id, created, updated)
        - local_user_id: The local user ID, or None if user not found/created
        - created: True if a new user was created
        - updated: True if an existing user was updated
    """
    # Check for existing provider link
    result = await db.execute(
        select(ProviderLink).where(
            ProviderLink.provider == claims.provider.value,
            ProviderLink.provider_user_id == claims.provider_user_id,
        )
    )
    link = result.scalar_one_or_none()

    if link:
        return await _handle_existing_link(db, link, claims, update_profile)

    # No link found - try to match by email (case-insensitive, strip whitespace)
    email_normalized = claims.email.strip().lower() if claims.email else ""

    if email_normalized:
        result = await db.execute(select(User).where(func.lower(User.email) == email_normalized))
        user = result.scalar_one_or_none()

        if user:
            logger.info(
                f"Auto-linking provider {claims.provider.value} to existing user "
                f"{user.id} by email match ({email_normalized})"
            )
            return await _handle_email_match(db, user, claims, update_profile)
    else:
        logger.warning(
            f"Empty email in claims for provider {claims.provider.value} "
            f"(provider_user_id={claims.provider_user_id}), skipping email match"
        )

    # No user found - create if allowed
    if not create_if_missing:
        return None, False, False

    try:
        return await _create_new_user(db, claims)
    except IntegrityError:
        await db.rollback()
        # Email or username collision - attempt to link to existing user
        logger.warning(
            f"IntegrityError creating user for {email_normalized}, "
            f"attempting to link to existing user instead"
        )
        if email_normalized:
            result = await db.execute(
                select(User).where(func.lower(User.email) == email_normalized)
            )
            user = result.scalar_one_or_none()
            if user:
                return await _handle_email_match(db, user, claims, update_profile)
        raise


async def deactivate_provider_user(
    db: AsyncSession,
    provider: AuthProvider,
    provider_user_id: str,
) -> bool:
    """
    Deactivate a local user when deleted from external provider.

    Does not delete the user - just marks as inactive.

    Args:
        db: Database session
        provider: The auth provider
        provider_user_id: The user ID in the external provider

    Returns:
        True if user was deactivated, False if not found
    """
    result = await db.execute(
        select(ProviderLink).where(
            ProviderLink.provider == provider.value,
            ProviderLink.provider_user_id == provider_user_id,
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        return False

    user_result = await db.execute(select(User).where(User.id == link.user_id))
    user = user_result.scalar_one_or_none()

    if user:
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return True

    return False


async def get_provider_links(db: AsyncSession, user_id: str) -> list[ProviderLink]:
    """
    Get all provider links for a user.

    Args:
        db: Database session
        user_id: The local user ID

    Returns:
        List of ProviderLink objects
    """
    result = await db.execute(select(ProviderLink).where(ProviderLink.user_id == user_id))
    return list(result.scalars().all())


async def link_provider(
    db: AsyncSession,
    user_id: str,
    provider: AuthProvider,
    provider_user_id: str,
) -> ProviderLink:
    """
    Link an external provider to an existing user.

    Args:
        db: Database session
        user_id: The local user ID
        provider: The auth provider
        provider_user_id: The user ID in the external provider

    Returns:
        The created ProviderLink

    Raises:
        ValueError: If the provider is already linked to another user
    """
    # Check if this provider+provider_user_id is already linked
    result = await db.execute(
        select(ProviderLink).where(
            ProviderLink.provider == provider.value,
            ProviderLink.provider_user_id == provider_user_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.user_id != user_id:
            raise ValueError(f"This {provider.value} account is already linked to another user")
        return existing

    # Create new link
    link = ProviderLink(
        user_id=user_id,
        provider=provider.value,
        provider_user_id=provider_user_id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def unlink_provider(
    db: AsyncSession,
    user_id: str,
    provider: AuthProvider,
) -> bool:
    """
    Unlink an external provider from a user.

    Args:
        db: Database session
        user_id: The local user ID
        provider: The auth provider to unlink

    Returns:
        True if unlinked, False if not found
    """
    result = await db.execute(
        select(ProviderLink).where(
            ProviderLink.user_id == user_id,
            ProviderLink.provider == provider.value,
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        return False

    await db.delete(link)
    await db.commit()
    return True
