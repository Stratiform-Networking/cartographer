"""
Discord integration router.

Handles Discord-specific notification endpoints:
- Bot information and status
- Guild/channel management
- OAuth linking/unlinking
- Discord account info
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse

from ...dependencies import AuthenticatedUser, require_auth
from ...services.proxy_service import proxy_notification_request

router = APIRouter(tags=["notification-discord"])


# ==================== Discord Bot Information ====================


@router.get("/discord/info")
async def get_discord_info(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get Discord bot information and invite URL."""
    return await proxy_notification_request("GET", "/discord/info")


@router.get("/discord/guilds")
async def get_discord_guilds(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get list of Discord servers (guilds) the bot is in."""
    return await proxy_notification_request("GET", "/discord/guilds")


@router.get("/discord/guilds/{guild_id}/channels")
async def get_discord_channels(
    guild_id: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get list of text channels in a Discord server."""
    return await proxy_notification_request("GET", f"/discord/guilds/{guild_id}/channels")


@router.get("/discord/invite-url")
async def get_discord_invite_url(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get the bot invite URL."""
    return await proxy_notification_request("GET", "/discord/invite-url")


# ==================== Discord OAuth ====================


@router.get("/auth/discord/link")
async def initiate_discord_oauth(
    context_type: str = Query("global", description="Context type: 'network' or 'global'"),
    network_id: str | None = Query(
        None, description="Network ID (UUID) if context_type is 'network'"
    ),
    user: AuthenticatedUser = Depends(require_auth),
):
    """
    Initiate Discord OAuth flow for current user.

    Args:
        context_type: "network" for per-network Discord link, "global" for global link
        network_id: The network_id if context_type is "network"
    """
    params = f"user_id={user.user_id}&context_type={context_type}"
    if network_id is not None:
        params += f"&network_id={network_id}"
    return await proxy_notification_request(
        "GET",
        f"/auth/discord/link?{params}",
        use_user_path=True,
    )


@router.get("/auth/discord/callback")
async def discord_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """Handle Discord OAuth callback (no auth required - handled by notification service)."""
    # For OAuth callbacks, we need to handle redirects specially
    # The notification service returns a RedirectResponse, not JSON
    from ...services.http_client import http_pool

    service = http_pool._services.get("notification")
    if not service:
        raise HTTPException(status_code=500, detail="Notification service not available")

    if not service.client:
        await service.initialize()

    # Make request with follow_redirects=False to get the redirect response
    response = await service.client.get(
        "/api/auth/discord/callback",
        params={"code": code, "state": state},
        follow_redirects=False,
    )

    # If it's a redirect (302/303), return a RedirectResponse
    if response.status_code in (302, 303, 307, 308):
        redirect_url = response.headers.get("location")
        if redirect_url:
            return RedirectResponse(url=redirect_url)

    # Otherwise, try to parse as JSON
    try:
        content = response.json()
    except Exception:
        content = {"detail": response.text or "Empty response"}

    return JSONResponse(
        content=content,
        status_code=response.status_code,
    )


# ==================== User Discord Account Management ====================


@router.get("/users/me/discord")
async def get_user_discord_info(
    context_type: str = Query("global", description="Context type: 'network' or 'global'"),
    network_id: str | None = Query(
        None, description="Network ID (UUID) if context_type is 'network'"
    ),
    user: AuthenticatedUser = Depends(require_auth),
):
    """
    Get linked Discord account info for current user in a specific context.

    Args:
        context_type: "network" for per-network Discord link, "global" for global link
        network_id: The network_id if context_type is "network"
    """
    params = {"context_type": context_type}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_notification_request(
        "GET",
        f"/users/{user.user_id}/discord",
        params=params,
        use_user_path=True,
    )


@router.delete("/users/me/discord/link")
async def unlink_discord(
    context_type: str = Query("global", description="Context type: 'network' or 'global'"),
    network_id: str | None = Query(
        None, description="Network ID (UUID) if context_type is 'network'"
    ),
    user: AuthenticatedUser = Depends(require_auth),
):
    """
    Unlink Discord account from current user for a specific context.

    Args:
        context_type: "network" for per-network Discord link, "global" for global link
        network_id: The network_id if context_type is "network"
    """
    params = {"context_type": context_type}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_notification_request(
        "DELETE",
        f"/users/{user.user_id}/discord/link",
        params=params,
        use_user_path=True,
    )
