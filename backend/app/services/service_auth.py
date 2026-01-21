"""
Service-to-Service Authentication Module.

Provides secure authentication between Cartographer microservices using:
- Short-lived JWT tokens (5-minute expiry)
- HMAC request signing for request integrity
- Service identity verification
- Token caching with automatic refresh
- Circuit breaker for auth failures

Usage:
    # Generate a service token for outbound requests
    from app.services.service_auth import generate_service_token
    token = generate_service_token("backend")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify incoming service token
    from app.services.service_auth import verify_service_token
    service_identity = verify_service_token(token)
"""

import hashlib
import hmac
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from jose import JWTError, jwt

from ..config import get_settings

logger = logging.getLogger(__name__)

# Token configuration
SERVICE_TOKEN_EXPIRY_SECONDS = 300  # 5 minutes
TOKEN_REFRESH_THRESHOLD_SECONDS = 60  # Refresh when < 1 minute remaining
SERVICE_TOKEN_TYPE = "service"
TOKEN_ISSUER = "cartographer"

# Circuit breaker configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 30  # seconds

# Known service identities
VALID_SERVICES = frozenset(
    [
        "backend",
        "health-service",
        "auth-service",
        "metrics-service",
        "assistant-service",
        "notification-service",
        "cloud-backend",
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# Circuit Breaker Implementation
# ─────────────────────────────────────────────────────────────────────────────


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for service authentication.

    Prevents cascading failures by temporarily stopping auth attempts
    when the auth service is unavailable.
    """

    failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD
    recovery_timeout: int = CIRCUIT_BREAKER_RECOVERY_TIMEOUT
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: Optional[float] = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time and (
                    time.time() - self._last_failure_time > self.recovery_timeout
                ):
                    self._state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
            return self._state

    def record_success(self) -> None:
        """Record a successful auth operation."""
        with self._lock:
            self._failure_count = 0
            if self._state != CircuitState.CLOSED:
                logger.info("Circuit breaker CLOSED after successful auth")
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed auth operation."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    logger.warning(f"Circuit breaker OPEN after {self._failure_count} failures")
                self._state = CircuitState.OPEN

    def is_available(self) -> bool:
        """Check if requests should be allowed."""
        state = self.state
        return state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)


# Global circuit breaker instance
_circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global circuit breaker instance."""
    return _circuit_breaker


# ─────────────────────────────────────────────────────────────────────────────
# Token Cache for Refresh
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CachedToken:
    """Cached service token with expiry tracking."""

    token: str
    expires_at: datetime

    def is_valid(self) -> bool:
        """Check if token is still valid with refresh threshold."""
        remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return remaining > TOKEN_REFRESH_THRESHOLD_SECONDS


# Token cache: service_name -> CachedToken
_token_cache: dict[str, CachedToken] = {}
_cache_lock = threading.Lock()


def _get_cached_token(service_name: str) -> Optional[str]:
    """Get a valid cached token for the service."""
    with _cache_lock:
        cached = _token_cache.get(service_name)
        if cached and cached.is_valid():
            return cached.token
        return None


def _cache_token(service_name: str, token: str, expires_at: datetime) -> None:
    """Cache a token for the service."""
    with _cache_lock:
        _token_cache[service_name] = CachedToken(token=token, expires_at=expires_at)


@dataclass
class ServiceIdentity:
    """Verified service identity from a service token."""

    service_name: str
    issued_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


class ServiceAuthError(Exception):
    """Service authentication error."""

    pass


def generate_service_token(service_name: str, force_refresh: bool = False) -> str:
    """
    Generate a short-lived JWT token for service-to-service authentication.

    Tokens are cached and automatically refreshed when close to expiry.
    Uses circuit breaker to prevent cascading failures.

    Args:
        service_name: The name of the calling service (e.g., "backend", "health-service")
        force_refresh: If True, bypass cache and generate new token

    Returns:
        JWT token string

    Raises:
        ServiceAuthError: If service name is invalid or token generation fails
    """
    if service_name not in VALID_SERVICES:
        logger.warning(f"Service auth: invalid service name attempted: {service_name}")
        raise ServiceAuthError(f"Invalid service name: {service_name}")

    # Check circuit breaker
    if not _circuit_breaker.is_available():
        logger.error(
            f"Service auth: circuit breaker OPEN, rejecting token generation for {service_name}"
        )
        raise ServiceAuthError("Auth service circuit breaker is open")

    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = _get_cached_token(service_name)
        if cached:
            logger.debug(f"Service auth: using cached token for {service_name}")
            return cached

    settings = get_settings()
    if not settings.jwt_secret:
        _circuit_breaker.record_failure()
        raise ServiceAuthError("JWT_SECRET not configured")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=SERVICE_TOKEN_EXPIRY_SECONDS)

    payload = {
        "iss": TOKEN_ISSUER,
        "sub": service_name,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": SERVICE_TOKEN_TYPE,
    }

    try:
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        # Cache the token
        _cache_token(service_name, token, exp)
        _circuit_breaker.record_success()

        logger.info(
            f"Service auth: generated new token for {service_name}, expires {exp.isoformat()}"
        )
        return token
    except Exception as e:
        _circuit_breaker.record_failure()
        logger.error(f"Service auth: failed to generate token for {service_name}: {e}")
        raise ServiceAuthError(f"Token generation failed: {e}")


def refresh_service_token(service_name: str) -> str:
    """
    Force refresh a service token, bypassing the cache.

    Args:
        service_name: The name of the calling service

    Returns:
        New JWT token string
    """
    logger.info(f"Service auth: force refreshing token for {service_name}")
    return generate_service_token(service_name, force_refresh=True)


def verify_service_token(token: str) -> ServiceIdentity:
    """
    Verify a service-to-service JWT token.

    Args:
        token: JWT token string

    Returns:
        ServiceIdentity with verified service information

    Raises:
        ServiceAuthError: If token is invalid, expired, or from unknown service
    """
    settings = get_settings()
    if not settings.jwt_secret:
        logger.error("Service auth: JWT_SECRET not configured for token verification")
        raise ServiceAuthError("JWT_SECRET not configured")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require_exp": True, "require_iat": True},
        )
    except JWTError as e:
        logger.warning(f"Service auth: token verification failed - {e}")
        raise ServiceAuthError(f"Invalid token: {e}")

    # Verify token type
    if payload.get("type") != SERVICE_TOKEN_TYPE:
        logger.warning(f"Service auth: rejected non-service token type: {payload.get('type')}")
        raise ServiceAuthError("Not a service token")

    # Verify issuer
    if payload.get("iss") != TOKEN_ISSUER:
        logger.warning(f"Service auth: rejected invalid issuer: {payload.get('iss')}")
        raise ServiceAuthError("Invalid token issuer")

    # Verify service name
    service_name = payload.get("sub")
    if service_name not in VALID_SERVICES:
        logger.warning(f"Service auth: rejected unknown service: {service_name}")
        raise ServiceAuthError(f"Unknown service: {service_name}")

    identity = ServiceIdentity(
        service_name=service_name,
        issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )

    logger.info(
        f"Service auth: verified token from {service_name}, expires {identity.expires_at.isoformat()}"
    )
    return identity


def sign_request(
    method: str,
    path: str,
    body: Optional[bytes] = None,
    timestamp: Optional[int] = None,
) -> tuple[str, int]:
    """
    Generate HMAC signature for a request.

    This provides request integrity verification - the receiving service
    can verify the request wasn't tampered with in transit.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path (e.g., /api/health/status)
        body: Request body bytes (optional)
        timestamp: Unix timestamp (optional, uses current time if not provided)

    Returns:
        Tuple of (signature, timestamp)

    Raises:
        ServiceAuthError: If signing fails
    """
    settings = get_settings()
    if not settings.jwt_secret:
        raise ServiceAuthError("JWT_SECRET not configured")

    if timestamp is None:
        timestamp = int(time.time())

    # Build canonical request string
    body_hash = hashlib.sha256(body or b"").hexdigest()
    canonical = f"{method.upper()}\n{path}\n{timestamp}\n{body_hash}"

    # Generate HMAC signature
    signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return signature, timestamp


def verify_request_signature(
    method: str,
    path: str,
    signature: str,
    timestamp: int,
    body: Optional[bytes] = None,
    max_age_seconds: int = 300,
) -> bool:
    """
    Verify HMAC signature for a request.

    Args:
        method: HTTP method
        path: Request path
        signature: HMAC signature to verify
        timestamp: Request timestamp
        body: Request body bytes (optional)
        max_age_seconds: Maximum age of request in seconds (default 5 minutes)

    Returns:
        True if signature is valid, False otherwise
    """
    # Check timestamp is recent (prevent replay attacks)
    current_time = int(time.time())
    if abs(current_time - timestamp) > max_age_seconds:
        logger.warning(f"Request signature expired: timestamp {timestamp}, current {current_time}")
        return False

    try:
        expected_signature, _ = sign_request(method, path, body, timestamp)
        return hmac.compare_digest(signature, expected_signature)
    except ServiceAuthError:
        return False


def get_service_auth_headers(service_name: str) -> dict[str, str]:
    """
    Generate headers for authenticated service-to-service requests.

    Args:
        service_name: The name of the calling service

    Returns:
        Dict of headers to include in the request
    """
    token = generate_service_token(service_name)
    return {
        "Authorization": f"Bearer {token}",
        "X-Service-Name": service_name,
    }


def get_signed_request_headers(
    service_name: str,
    method: str,
    path: str,
    body: Optional[bytes] = None,
) -> dict[str, str]:
    """
    Generate headers for authenticated and signed service-to-service requests.

    This provides both authentication (who is making the request) and
    integrity (the request wasn't tampered with).

    Args:
        service_name: The name of the calling service
        method: HTTP method
        path: Request path
        body: Request body bytes (optional)

    Returns:
        Dict of headers to include in the request
    """
    headers = get_service_auth_headers(service_name)
    signature, timestamp = sign_request(method, path, body)
    headers["X-Request-Signature"] = signature
    headers["X-Request-Timestamp"] = str(timestamp)
    return headers
