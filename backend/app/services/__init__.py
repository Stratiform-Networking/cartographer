# Makes services a package
from .http_client import HTTPClientPool, http_pool
from .service_auth import (
    CircuitBreaker,
    ServiceAuthError,
    ServiceIdentity,
    generate_service_token,
    get_circuit_breaker,
    get_service_auth_headers,
    get_signed_request_headers,
    refresh_service_token,
    sign_request,
    verify_request_signature,
    verify_service_token,
)

__all__ = [
    # HTTP client pool
    "http_pool",
    "HTTPClientPool",
    # Service authentication
    "ServiceAuthError",
    "ServiceIdentity",
    "CircuitBreaker",
    "generate_service_token",
    "refresh_service_token",
    "verify_service_token",
    "sign_request",
    "verify_request_signature",
    "get_service_auth_headers",
    "get_signed_request_headers",
    "get_circuit_breaker",
]
