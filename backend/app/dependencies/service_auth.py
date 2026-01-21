"""
FastAPI Dependencies for Service-to-Service Authentication.

Provides dependencies for authenticating requests from other Cartographer services.

Usage:
    from app.dependencies.service_auth import require_service_auth, require_signed_request

    @router.post("/internal/sync")
    async def sync_data(
        service: ServiceIdentity = Depends(require_service_auth),
    ):
        # Only accessible by authenticated services
        print(f"Request from {service.service_name}")

    @router.post("/internal/sensitive")
    async def sensitive_op(
        service: ServiceIdentity = Depends(require_signed_request),
    ):
        # Requires both authentication AND request signature
        pass
"""

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status

from ..services.service_auth import (
    ServiceAuthError,
    ServiceIdentity,
    verify_request_signature,
    verify_service_token,
)

logger = logging.getLogger(__name__)


async def get_service_token(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[str]:
    """
    Extract service token from Authorization header.

    Returns None if no authorization header is present.
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


async def require_service_auth(
    token: Optional[str] = Depends(get_service_token),
    x_service_name: Optional[str] = Header(None, alias="X-Service-Name"),
) -> ServiceIdentity:
    """
    Dependency that requires a valid service-to-service token.

    Use this for internal endpoints that should only be accessible
    by other Cartographer services.

    Raises:
        HTTPException: 401 if token is missing or invalid
        HTTPException: 403 if service is not authorized
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        identity = verify_service_token(token)
    except ServiceAuthError as e:
        logger.warning(f"Service auth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Optionally verify X-Service-Name header matches token
    if x_service_name and x_service_name != identity.service_name:
        logger.warning(
            f"Service name mismatch: header={x_service_name}, token={identity.service_name}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service identity mismatch",
        )

    logger.debug(f"Authenticated service request from {identity.service_name}")
    return identity


async def optional_service_auth(
    token: Optional[str] = Depends(get_service_token),
) -> Optional[ServiceIdentity]:
    """
    Dependency that optionally validates a service token.

    Use this for endpoints that can be called by both services and users.
    Returns None if no service token is present.
    """
    if not token:
        return None

    try:
        return verify_service_token(token)
    except ServiceAuthError:
        return None


async def require_signed_request(
    request: Request,
    identity: ServiceIdentity = Depends(require_service_auth),
    x_request_signature: Optional[str] = Header(None, alias="X-Request-Signature"),
    x_request_timestamp: Optional[str] = Header(None, alias="X-Request-Timestamp"),
) -> ServiceIdentity:
    """
    Dependency that requires both service auth AND request signature.

    Use this for sensitive internal operations where request integrity
    must be verified (prevents tampering in transit).

    Raises:
        HTTPException: 401 if service auth fails
        HTTPException: 400 if signature headers are missing
        HTTPException: 403 if signature is invalid
    """
    if not x_request_signature or not x_request_timestamp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request signature headers required",
        )

    try:
        timestamp = int(x_request_timestamp)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request timestamp",
        )

    # Get request body for signature verification
    body = await request.body()

    # Verify signature
    is_valid = verify_request_signature(
        method=request.method,
        path=request.url.path,
        signature=x_request_signature,
        timestamp=timestamp,
        body=body,
    )

    if not is_valid:
        logger.warning(f"Invalid request signature from {identity.service_name}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid request signature",
        )

    logger.debug(f"Verified signed request from {identity.service_name}")
    return identity


def require_specific_service(allowed_services: set[str]):
    """
    Create a dependency that only allows specific services.

    Usage:
        @router.post("/sync")
        async def sync(
            service: ServiceIdentity = Depends(
                require_specific_service({"health-service", "metrics-service"})
            ),
        ):
            pass
    """

    async def _require_specific(
        identity: ServiceIdentity = Depends(require_service_auth),
    ) -> ServiceIdentity:
        if identity.service_name not in allowed_services:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Service {identity.service_name} is not authorized for this operation",
            )
        return identity

    return _require_specific
