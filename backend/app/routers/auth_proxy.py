"""
Auth Proxy Router
Proxies authentication requests to the Auth microservice

Performance optimizations:
- Uses shared HTTP client pool with connection reuse
- Circuit breaker prevents cascade failures
- Connections are pre-warmed on startup
- Redis caching for session data

Security:
- Public endpoints (login, setup, invite accept) have no auth requirement
- Protected endpoints require authentication at proxy level for defense in depth
- Owner-only endpoints (user management, invitations) require owner role at proxy level
"""

from fastapi import APIRouter, Depends, Request

from ..dependencies import AuthenticatedUser, require_auth, require_owner
from ..services.cache_service import CacheService, get_cache
from ..services.proxy_service import proxy_auth_request

router = APIRouter(tags=["auth"])


# ==================== Setup Endpoints ====================
# These endpoints are intentionally public for initial application setup


@router.get("/auth/setup/status")
async def get_setup_status(request: Request):
    """Check if initial setup is complete (public endpoint)"""
    return await proxy_auth_request("GET", "/setup/status", request)


@router.post("/auth/setup/owner")
async def setup_owner(request: Request):
    """Create the initial owner account (public endpoint - only works once)"""
    body = await request.json()
    return await proxy_auth_request("POST", "/setup/owner", request, body)


# ==================== Authentication Endpoints ====================
# Login is public, logout/session require authentication


@router.post("/auth/login")
async def login(request: Request):
    """Authenticate and get access token (public endpoint)"""
    body = await request.json()
    return await proxy_auth_request("POST", "/login", request, body)


@router.post("/auth/logout")
async def logout(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Logout current user. Requires authentication."""
    return await proxy_auth_request("POST", "/logout", request)


@router.get("/auth/session")
async def get_session(
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """
    Get current session information. Requires authentication.
    
    Cached per-user for 60 seconds to reduce auth service load.
    """
    cache_key = cache.make_key("session", user.user_id)
    
    async def fetch_session():
        response = await proxy_auth_request("GET", "/session", request)
        # Extract JSON from response
        if hasattr(response, "body"):
            import json
            return json.loads(response.body)
        return response
    
    return await cache.get_or_compute(cache_key, fetch_session, ttl=60)


@router.post("/auth/verify")
async def verify_token(request: Request):
    """Verify if the current token is valid (public - returns valid: false if no token)"""
    return await proxy_auth_request("POST", "/verify", request)


# ==================== User Management Endpoints ====================
# Creating and deleting users requires owner role
# Listing and viewing requires authentication (auth service further restricts visibility)


@router.get("/auth/users")
async def list_users(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """List all users. Requires authentication (owners see all, others see only themselves)."""
    return await proxy_auth_request("GET", "/users", request)


@router.post("/auth/users")
async def create_user(request: Request, user: AuthenticatedUser = Depends(require_owner)):
    """Create a new user. Requires owner role."""
    body = await request.json()
    return await proxy_auth_request("POST", "/users", request, body)


@router.get("/auth/users/{user_id}")
async def get_user(user_id: str, request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Get user by ID. Requires authentication."""
    return await proxy_auth_request("GET", f"/users/{user_id}", request)


@router.patch("/auth/users/{user_id}")
async def update_user(
    user_id: str, request: Request, user: AuthenticatedUser = Depends(require_auth)
):
    """Update a user. Requires authentication."""
    body = await request.json()
    return await proxy_auth_request("PATCH", f"/users/{user_id}", request, body)


@router.delete("/auth/users/{user_id}")
async def delete_user(
    user_id: str, request: Request, user: AuthenticatedUser = Depends(require_owner)
):
    """Delete a user. Requires owner role."""
    return await proxy_auth_request("DELETE", f"/users/{user_id}", request)


# ==================== Profile Endpoints ====================
# All profile endpoints require authentication


@router.get("/auth/me")
async def get_current_profile(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Get current user's profile. Requires authentication."""
    return await proxy_auth_request("GET", "/me", request)


@router.patch("/auth/me")
async def update_current_profile(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Update current user's profile. Requires authentication."""
    body = await request.json()
    return await proxy_auth_request("PATCH", "/me", request, body)


@router.post("/auth/me/change-password")
async def change_password(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Change current user's password. Requires authentication."""
    body = await request.json()
    return await proxy_auth_request("POST", "/me/change-password", request, body)


# ==================== Invitation Endpoints ====================
# All invitation management endpoints require owner role


@router.get("/auth/invites")
async def list_invites(request: Request, user: AuthenticatedUser = Depends(require_owner)):
    """List all invitations. Requires owner role."""
    return await proxy_auth_request("GET", "/invites", request)


@router.post("/auth/invites")
async def create_invite(request: Request, user: AuthenticatedUser = Depends(require_owner)):
    """Create a new invitation. Requires owner role."""
    body = await request.json()
    return await proxy_auth_request("POST", "/invites", request, body)


@router.get("/auth/invites/{invite_id}")
async def get_invite(
    invite_id: str, request: Request, user: AuthenticatedUser = Depends(require_owner)
):
    """Get invitation by ID. Requires owner role."""
    return await proxy_auth_request("GET", f"/invites/{invite_id}", request)


@router.delete("/auth/invites/{invite_id}")
async def revoke_invite(
    invite_id: str, request: Request, user: AuthenticatedUser = Depends(require_owner)
):
    """Revoke an invitation. Requires owner role."""
    return await proxy_auth_request("DELETE", f"/invites/{invite_id}", request)


@router.post("/auth/invites/{invite_id}/resend")
async def resend_invite(
    invite_id: str, request: Request, user: AuthenticatedUser = Depends(require_owner)
):
    """Resend an invitation email. Requires owner role."""
    return await proxy_auth_request("POST", f"/invites/{invite_id}/resend", request)


# ==================== Public Invitation Endpoints ====================
# These endpoints are intentionally public - they allow users to accept invitations


@router.get("/auth/invite/verify/{token}")
async def verify_invite_token(token: str, request: Request):
    """Verify an invitation token (public endpoint)"""
    return await proxy_auth_request("GET", f"/invite/verify/{token}", request)


@router.post("/auth/invite/accept")
async def accept_invite(request: Request):
    """Accept an invitation and create account (public endpoint)"""
    body = await request.json()
    return await proxy_auth_request("POST", "/invite/accept", request, body)
