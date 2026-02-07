"""
Cookie helpers for browser session and CSRF handling.
"""

import secrets
from collections.abc import Mapping
from typing import Any

from fastapi.responses import Response

from ..config import get_settings


def generate_csrf_token() -> str:
    """Generate a random CSRF token."""
    return secrets.token_urlsafe(32)


def set_auth_cookies(
    response: Response,
    *,
    session_token: str,
    expires_in: int,
    csrf_token: str | None = None,
) -> str:
    """
    Set session and CSRF cookies on a response.

    Returns:
        The CSRF token that was set.
    """
    settings = get_settings()
    token = csrf_token or generate_csrf_token()
    samesite = settings.auth_cookie_samesite.lower()
    secure = settings.auth_cookie_secure_value

    response.set_cookie(
        key=settings.auth_cookie_name,
        value=session_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=settings.auth_cookie_path,
        max_age=expires_in,
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        httponly=False,
        secure=secure,
        samesite=samesite,
        path=settings.auth_cookie_path,
        max_age=expires_in,
    )
    return token


def clear_auth_cookies(response: Response) -> None:
    """Delete session and CSRF cookies from a response."""
    settings = get_settings()
    response.delete_cookie(settings.auth_cookie_name, path=settings.auth_cookie_path)
    response.delete_cookie(settings.csrf_cookie_name, path=settings.auth_cookie_path)


def sanitize_browser_auth_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    Remove browser-inaccessible fields from auth payload.

    Immediate cutover policy: no access_token in browser auth responses.
    """
    sanitized = dict(payload)
    sanitized.pop("access_token", None)
    return sanitized
