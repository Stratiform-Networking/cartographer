"""
Token extraction utilities for user-authenticated browser and API requests.
"""

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials

from ..config import get_settings


def extract_bearer_token(authorization_header: str | None) -> str | None:
    """Extract a bearer token from an Authorization header value."""
    if not authorization_header:
        return None

    parts = authorization_header.strip().split(" ", 1)
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def resolve_request_token(
    request: Request | None = None,
    credentials: HTTPAuthorizationCredentials | None = None,
    query_token: str | None = None,
    cookie_name: str | None = None,
) -> str | None:
    """
    Resolve auth token with precedence: Authorization header -> cookie -> query param.
    """
    # 1) FastAPI HTTPBearer credentials (already parsed from Authorization header)
    if credentials and credentials.credentials:
        return credentials.credentials

    # 2) Raw Authorization header (fallback when HTTPBearer doesn't parse it)
    if request is not None:
        header_token = extract_bearer_token(request.headers.get("Authorization"))
        if header_token:
            return header_token

    # 3) Browser session cookie
    if request is not None:
        settings = get_settings()
        name = cookie_name or settings.auth_cookie_name
        cookie_token = request.cookies.get(name)
        if cookie_token:
            return cookie_token

    # 4) SSE/EventSource query token fallback
    if query_token:
        return query_token

    return None


def resolve_authorization_header(
    request: Request,
    cookie_name: str | None = None,
) -> str | None:
    """
    Resolve a forwardable Authorization header.

    Returns the existing Authorization header if present. Otherwise synthesizes
    one from the auth cookie.
    """
    auth_header = request.headers.get("Authorization")
    if extract_bearer_token(auth_header):
        return auth_header

    settings = get_settings()
    name = cookie_name or settings.auth_cookie_name
    cookie_token = request.cookies.get(name)
    if cookie_token:
        return f"Bearer {cookie_token}"

    return None
