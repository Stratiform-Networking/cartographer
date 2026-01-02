"""
Internal health check router.

Provides health endpoints for load balancers, orchestrators,
and monitoring systems.
"""

from fastapi import APIRouter

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
