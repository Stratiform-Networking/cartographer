"""
User synchronization service for external auth providers.

Syncs external provider users to the local PostgreSQL database,
which remains the source of truth for user data.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db_models import ProviderLink, User, UserRole
from .claims import AuthProvider, IdentityClaims


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
    created = False
    updated = False

    # Check for existing provider link
    result = await db.execute(
        select(ProviderLink).where(
            ProviderLink.provider == claims.provider.value,
            ProviderLink.provider_user_id == claims.provider_user_id,
        )
    )
    link = result.scalar_one_or_none()

    if link:
        # Found existing link - update user if requested
        user_result = await db.execute(select(User).where(User.id == link.user_id))
        user = user_result.scalar_one_or_none()

        if user and update_profile:
            if claims.first_name:
                user.first_name = claims.first_name
            if claims.last_name:
                user.last_name = claims.last_name
            if claims.email:
                user.email = claims.email
            user.is_verified = claims.email_verified
            user.updated_at = datetime.now(timezone.utc)
            await db.commit()
            updated = True

        return UUID(link.user_id) if link.user_id else None, created, updated

    # No link found - try to match by email
    result = await db.execute(select(User).where(User.email == claims.email.lower()))
    user = result.scalar_one_or_none()

    if user:
        # Found user by email - create link
        new_link = ProviderLink(
            user_id=user.id,
            provider=claims.provider.value,
            provider_user_id=claims.provider_user_id,
        )
        db.add(new_link)

        if update_profile:
            if claims.first_name:
                user.first_name = claims.first_name
            if claims.last_name:
                user.last_name = claims.last_name
            user.is_verified = claims.email_verified
            user.updated_at = datetime.now(timezone.utc)
            updated = True

        await db.commit()
        return UUID(user.id), created, updated

    # No user found - create if allowed
    if not create_if_missing:
        return None, created, updated

    # Generate username from email if not provided
    username = claims.username
    if not username:
        username = claims.email.split("@")[0].lower()
        # Ensure uniqueness
        base_username = username
        counter = 1
        while True:
            existing = await db.execute(select(User).where(User.username == username))
            if not existing.scalar_one_or_none():
                break
            username = f"{base_username}{counter}"
            counter += 1

    # Create new user
    from uuid import uuid4

    new_user = User(
        id=str(uuid4()),
        username=username,
        email=claims.email.lower(),
        first_name=claims.first_name or "",
        last_name=claims.last_name or "",
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

    await db.commit()
    created = True
    return UUID(new_user.id), created, updated


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
