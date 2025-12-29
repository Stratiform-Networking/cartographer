"""
Health check router for Auth Service.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@router.get("/ready")
def ready():
    """Readiness check endpoint for container orchestration."""
    return {"status": "ready"}

