"""
Discord OAuth router for linking user Discord accounts.
Supports per-network and global Discord linking.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.database import (
    DiscordUserLink,
    UserGlobalNotificationPrefs,
    UserNetworkNotificationPrefs,
)
from ..services.discord_oauth import discord_oauth_service
from ..services.user_preferences import user_preferences_service

logger = logging.getLogger(__name__)

APPLICATION_URL = os.environ.get("APPLICATION_URL", "http://localhost:5173")

router = APIRouter()


@router.get("/auth/discord/link")
async def initiate_discord_oauth(
    user_id: str = Query(..., description="User ID"),
    context_type: str = Query("global", description="Context type: 'network' or 'global'"),
    network_id: Optional[str] = Query(None, description="Network ID if context_type is 'network'"),
):
    """
    Initiate Discord OAuth flow for a specific context.

    Args:
        user_id: The user initiating the OAuth flow
        context_type: "network" or "global"
        network_id: The network_id if context_type is "network"
    """
    try:
        context_id = network_id if context_type == "network" else None
        auth_url = discord_oauth_service.get_authorization_url(user_id, context_type, context_id)
        return {"authorization_url": auth_url}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/discord/callback")
async def discord_oauth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state token"),
    db: AsyncSession = Depends(get_db),
):
    """Handle Discord OAuth callback with context-aware linking"""
    # Validate state and get context
    state_data = discord_oauth_service.validate_state(state)
    if not state_data:
        return RedirectResponse(
            url=f"{APPLICATION_URL}?discord_oauth=error&message=Invalid or expired state token"
        )

    user_id, context_type, context_id = state_data

    try:
        # Exchange code for tokens
        token_data = await discord_oauth_service.exchange_code_for_tokens(code)
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        # Get user info
        user_info = await discord_oauth_service.get_user_info(access_token)
        discord_id = user_info["id"]
        discord_username = user_info.get("username", "Unknown")
        discord_avatar = user_info.get("avatar")
        if discord_avatar:
            discord_avatar = f"https://cdn.discordapp.com/avatars/{discord_id}/{discord_avatar}.png"

        # Create or update link for this specific context
        link = await discord_oauth_service.create_or_update_link(
            db=db,
            user_id=user_id,
            discord_id=discord_id,
            discord_username=discord_username,
            discord_avatar=discord_avatar,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            context_type=context_type,
            context_id=context_id,
        )

        # Update ONLY the specific preference record for this context
        if context_type == "network" and context_id is not None:
            # Update only the specific network preference
            await db.execute(
                update(UserNetworkNotificationPrefs)
                .where(
                    UserNetworkNotificationPrefs.user_id == user_id,
                    UserNetworkNotificationPrefs.network_id == context_id,
                )
                .values(discord_user_id=discord_id, discord_enabled=True)
            )
            logger.info("Linked Discord account for network context")

        else:
            # Update global preferences only
            global_prefs = await user_preferences_service.get_global_preferences(db, user_id)
            if global_prefs:
                global_prefs.discord_user_id = discord_id
                global_prefs.discord_enabled = True
            else:
                # Create global preferences if they don't exist
                new_prefs = UserGlobalNotificationPrefs(
                    user_id=user_id,
                    discord_user_id=discord_id,
                    discord_enabled=True,
                    minimum_priority="medium",
                )
                db.add(new_prefs)
            logger.info("Linked Discord account for global context")

        await db.commit()

        # Include context in redirect for frontend to know which link was updated
        context_param = f"&context_type={context_type}"
        if context_id is not None:
            context_param += f"&network_id={context_id}"

        return RedirectResponse(
            url=f"{APPLICATION_URL}?discord_oauth=success&username={discord_username}{context_param}"
        )

    except Exception as e:
        logger.error(f"Discord OAuth callback failed: {e}", exc_info=True)
        return RedirectResponse(url=f"{APPLICATION_URL}?discord_oauth=error&message={str(e)}")


@router.delete("/users/{user_id}/discord/link")
async def unlink_discord(
    user_id: str,
    context_type: str = Query("global", description="Context type: 'network' or 'global'"),
    network_id: Optional[str] = Query(None, description="Network ID if context_type is 'network'"),
    db: AsyncSession = Depends(get_db),
):
    """
    Unlink Discord account from user for a specific context.

    Args:
        user_id: The user's ID
        context_type: "network" or "global"
        network_id: The network_id if context_type is "network"
    """
    context_id = network_id if context_type == "network" else None
    success = await discord_oauth_service.delete_link(db, user_id, context_type, context_id)

    if success:
        # Clear discord_user_id from the specific preference record
        if context_type == "network" and context_id is not None:
            # Only update the specific network preference
            await db.execute(
                update(UserNetworkNotificationPrefs)
                .where(
                    UserNetworkNotificationPrefs.user_id == user_id,
                    UserNetworkNotificationPrefs.network_id == context_id,
                )
                .values(discord_user_id=None, discord_enabled=False)
            )
            logger.info("Unlinked Discord account for network context")
        else:
            # Only update global preferences
            await db.execute(
                update(UserGlobalNotificationPrefs)
                .where(UserGlobalNotificationPrefs.user_id == user_id)
                .values(discord_user_id=None, discord_enabled=False)
            )
            logger.info("Unlinked Discord account for global context")

        await db.commit()

    return {"success": success}


@router.get("/users/{user_id}/discord")
async def get_discord_info(
    user_id: str,
    context_type: str = Query("global", description="Context type: 'network' or 'global'"),
    network_id: Optional[str] = Query(None, description="Network ID if context_type is 'network'"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get linked Discord account info for a specific context.

    Args:
        user_id: The user's ID
        context_type: "network" or "global"
        network_id: The network_id if context_type is "network"
    """
    context_id = network_id if context_type == "network" else None
    link = await discord_oauth_service.get_link(db, user_id, context_type, context_id)

    if not link:
        return {
            "linked": False,
            "context_type": context_type,
            "network_id": network_id,
        }

    return {
        "linked": True,
        "discord_id": link.discord_id,
        "discord_username": link.discord_username,
        "discord_avatar": link.discord_avatar,
        "context_type": context_type,
        "network_id": network_id,
    }
