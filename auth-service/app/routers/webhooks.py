"""
Webhook router for external auth provider events.

Handles webhooks from Clerk and WorkOS for user synchronization.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..identity.claims import AuthProvider
from ..identity.sync import deactivate_provider_user, sync_provider_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/clerk")
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Clerk webhook events.

    Supported events:
    - user.created: Create local user from Clerk
    - user.updated: Update local user profile
    - user.deleted: Deactivate local user

    Args:
        request: The webhook request from Clerk
        db: Database session

    Returns:
        Acknowledgment of the webhook
    """
    if settings.auth_provider.lower() != "cloud":
        raise HTTPException(
            status_code=400,
            detail="Clerk webhooks are only available in cloud mode",
        )

    try:
        import svix
    except ImportError:
        logger.error("svix package not installed - cannot verify Clerk webhooks")
        raise HTTPException(
            status_code=500,
            detail="Webhook verification not available",
        )

    # Verify webhook signature
    webhook_secret = settings.clerk_webhook_secret
    if not webhook_secret:
        logger.error("Clerk webhook secret not configured")
        raise HTTPException(
            status_code=500,
            detail="Webhook not configured",
        )

    svix_headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }

    body = await request.body()
    wh = svix.Webhook(webhook_secret)

    try:
        payload = wh.verify(body, svix_headers)
    except svix.WebhookVerificationError as e:
        logger.warning(f"Clerk webhook signature verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid signature")

    event_type = payload.get("type")
    data = payload.get("data", {})

    logger.info(f"Received Clerk webhook event: {event_type}")

    # Route to appropriate handler
    if event_type == "user.created":
        return await _handle_clerk_user_created(db, data)
    elif event_type == "user.updated":
        return await _handle_clerk_user_updated(db, data)
    elif event_type == "user.deleted":
        return await _handle_clerk_user_deleted(db, data)
    else:
        logger.debug(f"Ignoring unhandled Clerk event type: {event_type}")
        return {"received": True, "handled": False}


async def _handle_clerk_user_created(db: AsyncSession, data: dict) -> dict:
    """
    Handle user.created event from Clerk.

    Creates a new local user synced with the Clerk user.

    Args:
        db: Database session
        data: User data from Clerk webhook

    Returns:
        Response indicating success/failure
    """
    from ..identity.providers.clerk import ClerkAuthProvider
    from ..identity.claims import ProviderConfig, AuthProvider as AP

    logger.info(f"Creating local user from Clerk user: {data.get('id')}")

    # Create a temporary provider instance to convert data to claims
    provider = ClerkAuthProvider(
        ProviderConfig(
            provider=AP.CLERK,
            enabled=True,
            clerk_secret_key=settings.clerk_secret_key,
        )
    )

    claims = provider.data_to_claims(data)

    local_user_id, created, updated = await sync_provider_user(
        db=db,
        claims=claims,
        create_if_missing=True,
        update_profile=True,
    )

    logger.info(
        f"Clerk user sync complete: local_user_id={local_user_id}, "
        f"created={created}, updated={updated}"
    )

    return {
        "received": True,
        "handled": True,
        "local_user_id": str(local_user_id) if local_user_id else None,
        "created": created,
        "updated": updated,
    }


async def _handle_clerk_user_updated(db: AsyncSession, data: dict) -> dict:
    """
    Handle user.updated event from Clerk.

    Updates the local user profile with changes from Clerk.

    Args:
        db: Database session
        data: User data from Clerk webhook

    Returns:
        Response indicating success/failure
    """
    from ..identity.providers.clerk import ClerkAuthProvider
    from ..identity.claims import ProviderConfig, AuthProvider as AP

    logger.info(f"Updating local user from Clerk user: {data.get('id')}")

    provider = ClerkAuthProvider(
        ProviderConfig(
            provider=AP.CLERK,
            enabled=True,
            clerk_secret_key=settings.clerk_secret_key,
        )
    )

    claims = provider.data_to_claims(data)

    local_user_id, created, updated = await sync_provider_user(
        db=db,
        claims=claims,
        create_if_missing=False,  # Don't create on update events
        update_profile=True,
    )

    logger.info(
        f"Clerk user update complete: local_user_id={local_user_id}, updated={updated}"
    )

    return {
        "received": True,
        "handled": True,
        "local_user_id": str(local_user_id) if local_user_id else None,
        "updated": updated,
    }


async def _handle_clerk_user_deleted(db: AsyncSession, data: dict) -> dict:
    """
    Handle user.deleted event from Clerk.

    Deactivates the local user when deleted from Clerk.
    Does not delete the local user - only marks as inactive.

    Args:
        db: Database session
        data: User data from Clerk webhook

    Returns:
        Response indicating success/failure
    """
    clerk_user_id = data.get("id")
    logger.info(f"Deactivating local user for deleted Clerk user: {clerk_user_id}")

    deactivated = await deactivate_provider_user(
        db=db,
        provider=AuthProvider.CLERK,
        provider_user_id=clerk_user_id,
    )

    logger.info(f"Clerk user deactivation complete: deactivated={deactivated}")

    return {
        "received": True,
        "handled": True,
        "deactivated": deactivated,
    }


@router.get("/clerk/health")
async def clerk_webhook_health():
    """
    Health check for Clerk webhook endpoint.

    Returns configuration status for debugging.
    """
    return {
        "status": "ok",
        "auth_provider": settings.auth_provider,
        "webhook_configured": bool(settings.clerk_webhook_secret),
    }
