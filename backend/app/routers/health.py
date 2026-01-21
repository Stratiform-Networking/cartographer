"""
Internal health check router.

Provides health endpoints for load balancers, orchestrators,
and monitoring systems.
"""

from fastapi import APIRouter

from ..config import get_settings
from ..services.http_client import http_pool

router = APIRouter(tags=["internal"])


@router.get("/healthz")
async def healthz():
    """
    Health check endpoint for load balancers.

    Returns service status and HTTP pool state including
    circuit breaker status for each downstream service.
    """
    services_status = {}
    for name, service in http_pool._services.items():
        services_status[name] = {
            "circuit_state": service.circuit_breaker.state.value,
            "failure_count": service.circuit_breaker.failure_count,
        }

    return {"status": "healthy", "services": services_status}


@router.get("/ready")
async def readyz():
    """
    Readiness check endpoint.

    Returns ready status indicating whether the service
    can accept traffic. Checks if HTTP pool is initialized.
    """
    # Check if services are registered
    if not http_pool._services:
        return {"status": "not_ready", "reason": "HTTP pool not initialized"}

    # Check circuit breaker states
    open_circuits = [
        name
        for name, service in http_pool._services.items()
        if service.circuit_breaker.state.value == "open"
    ]

    if open_circuits:
        return {"status": "degraded", "open_circuits": open_circuits}

    return {"status": "ready"}


@router.get("/config-check")
async def config_check():
    """
    Configuration security check endpoint.

    Returns the status of security-sensitive configuration settings.
    Does NOT expose actual secret values, only whether they are configured.

    This endpoint helps operators verify their deployment is properly configured
    before going to production.
    """
    settings = get_settings()

    checks = {
        "jwt_secret_configured": bool(settings.jwt_secret),
        "cors_restricted": "*" not in settings.cors_origins,
        "environment": settings.env,
        "docs_disabled": settings.disable_docs,
    }

    # Determine overall status
    issues = []
    if not checks["jwt_secret_configured"]:
        issues.append("JWT_SECRET is not set")
    if not checks["cors_restricted"]:
        issues.append("CORS allows all origins (*)")

    if settings.env == "production" and issues:
        status = "misconfigured"
    elif issues:
        status = "warning"
    else:
        status = "ok"

    return {
        "status": status,
        "checks": checks,
        "issues": issues if issues else None,
    }
