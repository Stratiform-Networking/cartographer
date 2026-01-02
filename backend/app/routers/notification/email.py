"""
Email and test notification router.

Handles email-related notification endpoints:
- Test notifications (all channels including email)
- Network test notifications
- User-specific test notifications
"""

from fastapi import APIRouter, Depends, Request

from ...dependencies import AuthenticatedUser, require_auth
from ...services.proxy_service import proxy_notification_request

router = APIRouter(tags=["notification-email"])


# ==================== Test Notifications ====================


@router.post("/test")
async def send_test_notification(
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Send a test notification via a specific channel (email, discord, etc.)."""
    body = await request.json()
    return await proxy_notification_request(
        "POST",
        "/test",
        json_body=body,
        headers={"X-User-Id": user.user_id},
    )


@router.post("/networks/{network_id}/test")
async def send_network_test_notification(
    network_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Send a test notification for a specific network."""
    body = await request.json()
    return await proxy_notification_request(
        "POST",
        f"/networks/{network_id}/test",
        json_body=body,
        headers={"X-User-Id": user.user_id},
    )


@router.post("/users/me/networks/{network_id}/test")
async def test_user_network_notification(
    network_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Send a test notification for current user's network preferences."""
    body = await request.json()
    return await proxy_notification_request(
        "POST",
        f"/users/{user.user_id}/networks/{network_id}/test",
        json_body=body,
        use_user_path=True,
    )


@router.post("/users/me/global/test")
async def test_user_global_notification(
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Send a test notification for current user's global preferences."""
    body = await request.json()
    return await proxy_notification_request(
        "POST",
        f"/users/{user.user_id}/global/test",
        json_body=body,
        use_user_path=True,
    )
