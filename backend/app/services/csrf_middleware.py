"""
CSRF middleware for cookie-authenticated browser sessions.
"""

from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import get_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Public browser-auth endpoints that should not require an existing CSRF header.
CSRF_EXEMPT_PATH_PREFIXES = (
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/setup/owner",
    "/api/auth/clerk/exchange",
    "/api/auth/invite/accept",
    "/api/auth/invite/verify/",
)


def _origin_host(origin: str) -> str | None:
    try:
        parsed = urlparse(origin)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF token and origin for unsafe cookie-authenticated requests."""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        # Only enforce for unsafe methods.
        if request.method in SAFE_METHODS:
            return await call_next(request)

        path = request.url.path
        if path.startswith(CSRF_EXEMPT_PATH_PREFIXES):
            return await call_next(request)

        # Enforce only when browser session cookie is present.
        session_token = request.cookies.get(settings.auth_cookie_name)
        if not session_token:
            return await call_next(request)

        csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_cookie or not csrf_header:
            return JSONResponse(status_code=403, content={"detail": "Missing CSRF token"})
        if csrf_cookie != csrf_header:
            return JSONResponse(status_code=403, content={"detail": "Invalid CSRF token"})

        trusted = set(settings.csrf_trusted_origins_list)
        if not trusted:
            trusted.add(f"{request.url.scheme}://{request.url.netloc}")

        if "*" not in trusted:
            origin = request.headers.get("Origin")
            referer = request.headers.get("Referer")
            candidate = _origin_host(origin) or _origin_host(referer or "")
            if not candidate:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Missing Origin/Referer for CSRF validation"},
                )
            if candidate not in trusted:
                return JSONResponse(status_code=403, content={"detail": "Untrusted request origin"})

        return await call_next(request)
