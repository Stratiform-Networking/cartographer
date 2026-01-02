"""
Service for managing user notification preferences from database.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import (
    DEFAULT_NOTIFICATION_TYPE_PRIORITIES,
    NotificationPriority,
    NotificationType,
    get_default_priority_for_type,
)
from ..models.database import (
    DiscordUserLink,
    NotificationPriorityEnum,
    UserGlobalNotificationPrefs,
    UserNetworkNotificationPrefs,
)

logger = logging.getLogger(__name__)


class UserPreferencesService:
    """Service for managing user notification preferences"""

    async def get_network_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        network_id: str,
    ) -> UserNetworkNotificationPrefs | None:
        """Get user's notification preferences for a specific network"""
        result = await db.execute(
            select(UserNetworkNotificationPrefs).where(
                UserNetworkNotificationPrefs.user_id == user_id,
                UserNetworkNotificationPrefs.network_id == network_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_network_preferences_batch(
        self,
        db: AsyncSession,
        user_ids: list[str],
        network_id: str,
    ) -> dict[str, UserNetworkNotificationPrefs]:
        """
        Batch fetch network preferences for multiple users.

        Instead of querying preferences one user at a time, fetch all at once.

        Args:
            db: Database session
            user_ids: List of user IDs to fetch preferences for
            network_id: Network ID

        Returns:
            Dictionary mapping user_id -> preferences (only users with prefs)
        """
        if not user_ids:
            return {}

        result = await db.execute(
            select(UserNetworkNotificationPrefs).where(
                UserNetworkNotificationPrefs.user_id.in_(user_ids),
                UserNetworkNotificationPrefs.network_id == network_id,
            )
        )
        prefs_list = result.scalars().all()

        # Return as dict for O(1) lookup
        return {prefs.user_id: prefs for prefs in prefs_list}

    async def get_user_emails_batch(
        self,
        db: AsyncSession,
        user_ids: list[str],
    ) -> dict[str, str]:
        """
        Batch fetch user emails for multiple users.

        Args:
            db: Database session
            user_ids: List of user IDs to fetch emails for

        Returns:
            Dictionary mapping user_id -> email (only users with emails)
        """
        if not user_ids:
            return {}

        try:
            result = await db.execute(
                text("SELECT id, email FROM users WHERE id = ANY(:user_ids) AND is_active = true"),
                {"user_ids": user_ids},
            )
            rows = result.fetchall()
            return {row[0]: row[1] for row in rows if row[1]}
        except Exception as e:
            logger.warning(f"Could not batch fetch user emails: {e}")
            return {}

    async def get_or_create_network_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        network_id: str,
        user_email: str | None = None,
    ) -> UserNetworkNotificationPrefs:
        """Get or create user's notification preferences for a network"""
        prefs = await self.get_network_preferences(db, user_id, network_id)

        if prefs is None:
            # Create with defaults: all notification types enabled
            default_types = [
                NotificationType.DEVICE_OFFLINE,
                NotificationType.DEVICE_ONLINE,
                NotificationType.DEVICE_DEGRADED,
                NotificationType.ANOMALY_DETECTED,
                NotificationType.HIGH_LATENCY,
                NotificationType.PACKET_LOSS,
                NotificationType.ISP_ISSUE,
                NotificationType.SECURITY_ALERT,
                NotificationType.SCHEDULED_MAINTENANCE,
                NotificationType.SYSTEM_STATUS,
            ]

            prefs = UserNetworkNotificationPrefs(
                user_id=user_id,
                network_id=network_id,
                email_enabled=bool(user_email),  # Enable if email provided
                discord_enabled=False,
                enabled_types=[t.value for t in default_types],
                type_priorities={},
                minimum_priority="medium",
                quiet_hours_enabled=False,
            )
            db.add(prefs)
            await db.commit()
            await db.refresh(prefs)

        return prefs

    async def update_network_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        network_id: str,
        update_data: dict[str, Any],
    ) -> UserNetworkNotificationPrefs:
        """Update user's network notification preferences"""
        prefs = await self.get_or_create_network_preferences(db, user_id, network_id)

        # Update fields
        for key, value in update_data.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)

        prefs.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(prefs)

        return prefs

    async def delete_network_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        network_id: str,
    ) -> bool:
        """Delete user's network notification preferences"""
        prefs = await self.get_network_preferences(db, user_id, network_id)
        if prefs:
            await db.delete(prefs)
            await db.commit()
            return True
        return False

    async def get_global_preferences(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> UserGlobalNotificationPrefs | None:
        """Get user's global notification preferences"""
        result = await db.execute(
            select(UserGlobalNotificationPrefs).where(
                UserGlobalNotificationPrefs.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_global_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        user_email: str | None = None,
    ) -> UserGlobalNotificationPrefs:
        """Get or create user's global notification preferences"""
        prefs = await self.get_global_preferences(db, user_id)

        if prefs is None:
            prefs = UserGlobalNotificationPrefs(
                user_id=user_id,
                email_enabled=bool(user_email),
                discord_enabled=False,
                cartographer_up_enabled=True,
                cartographer_down_enabled=True,
                minimum_priority="medium",
                quiet_hours_enabled=False,
            )
            db.add(prefs)
            await db.commit()
            await db.refresh(prefs)

        return prefs

    async def update_global_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        update_data: dict[str, Any],
    ) -> UserGlobalNotificationPrefs:
        """Update user's global notification preferences"""
        prefs = await self.get_or_create_global_preferences(db, user_id)

        # Update fields
        for key, value in update_data.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)

        prefs.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(prefs)

        return prefs

    async def get_discord_link(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> DiscordUserLink | None:
        """Get user's Discord OAuth link"""
        result = await db.execute(select(DiscordUserLink).where(DiscordUserLink.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_user_email(self, db: AsyncSession, user_id: str) -> str | None:
        """Get user's email from the users table in the database"""
        try:
            # Query the users table directly using raw SQL
            from sqlalchemy import text

            result = await db.execute(
                text("SELECT email FROM users WHERE id = :user_id AND is_active = true"),
                {"user_id": user_id},
            )
            row = result.fetchone()
            if row:
                return row[0]
            return None
        except Exception as e:
            logger.warning(f"Could not fetch user email from database: {e}")
            return None

    async def get_users_with_enabled_notifications(
        self,
        db: AsyncSession,
        network_id: str,
        notification_type: NotificationType,
    ) -> list[UserNetworkNotificationPrefs]:
        """Get all users in a network who have this notification type enabled"""
        result = await db.execute(
            select(UserNetworkNotificationPrefs).where(
                UserNetworkNotificationPrefs.network_id == network_id,
                # Check if notification type is in enabled_types JSON array
                # This is a simplified check - in production you'd want proper JSON query
            )
        )
        all_prefs = result.scalars().all()

        # Filter by enabled type and channels
        enabled_users = []
        for prefs in all_prefs:
            enabled_types = prefs.enabled_types or []
            if notification_type.value in enabled_types:
                # Check if at least one channel is enabled
                if prefs.email_enabled or prefs.discord_enabled:
                    enabled_users.append(prefs)

        return enabled_users

    async def get_users_with_global_notifications_enabled(
        self,
        db: AsyncSession,
        notification_type: NotificationType,
    ) -> list[UserGlobalNotificationPrefs]:
        """Get all users who have global notifications enabled for this type"""
        if notification_type == NotificationType.CARTOGRAPHER_UP:
            result = await db.execute(
                select(UserGlobalNotificationPrefs).where(
                    UserGlobalNotificationPrefs.cartographer_up_enabled == True,
                    # At least one channel enabled
                    (
                        (UserGlobalNotificationPrefs.email_enabled == True)
                        | (UserGlobalNotificationPrefs.discord_enabled == True)
                    ),
                )
            )
        elif notification_type == NotificationType.CARTOGRAPHER_DOWN:
            result = await db.execute(
                select(UserGlobalNotificationPrefs).where(
                    UserGlobalNotificationPrefs.cartographer_down_enabled == True,
                    # At least one channel enabled
                    (
                        (UserGlobalNotificationPrefs.email_enabled == True)
                        | (UserGlobalNotificationPrefs.discord_enabled == True)
                    ),
                )
            )
        else:
            return []

        return list(result.scalars().all())

    async def get_network_member_user_ids(
        self,
        db: AsyncSession,
        network_id: str,
    ) -> list[str]:
        """Get all user IDs who are members of a network (owner + users with permissions)"""
        try:
            from sqlalchemy import text

            # Query to get network owner and all users with permissions
            # Since we're using the same database, we can query the networks and network_permissions tables
            result = await db.execute(
                text(
                    """
                    SELECT user_id FROM networks WHERE id = :network_id
                    UNION
                    SELECT user_id FROM network_permissions WHERE network_id = :network_id
                """
                ),
                {"network_id": network_id},
            )
            rows = result.fetchall()
            return [str(row[0]) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get network member user IDs for network {network_id}: {e}")
            return []


# Singleton instance
user_preferences_service = UserPreferencesService()
