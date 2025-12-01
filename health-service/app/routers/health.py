from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from ..models import (
    DeviceMetrics,
    HealthCheckRequest,
    BatchHealthResponse,
    DeviceToMonitor,
)
from ..services.health_checker import health_checker

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/check/{ip}", response_model=DeviceMetrics)
async def check_single_device(
    ip: str,
    include_ports: bool = Query(False, description="Include port scanning"),
    include_dns: bool = Query(True, description="Include DNS resolution")
):
    """
    Check the health of a single device by IP address.
    Returns comprehensive metrics including ping, DNS, and optionally open ports.
    """
    try:
        metrics = await health_checker.check_device_health(
            ip=ip,
            include_ports=include_ports,
            include_dns=include_dns
        )
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check/batch", response_model=BatchHealthResponse)
async def check_multiple_devices(request: HealthCheckRequest):
    """
    Check the health of multiple devices at once.
    More efficient than calling the single endpoint multiple times.
    """
    if not request.ips:
        raise HTTPException(status_code=400, detail="No IPs provided")
    
    if len(request.ips) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 IPs per request")
    
    try:
        metrics = await health_checker.check_multiple_devices(
            ips=request.ips,
            include_ports=request.include_ports,
            include_dns=request.include_dns
        )
        return BatchHealthResponse(
            devices=metrics,
            check_timestamp=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cached/{ip}", response_model=Optional[DeviceMetrics])
async def get_cached_metrics(ip: str):
    """
    Get cached metrics for a device without performing a new check.
    Returns None if no cached data exists.
    """
    metrics = health_checker.get_cached_metrics(ip)
    if metrics is None:
        raise HTTPException(status_code=404, detail="No cached data for this IP")
    return metrics


@router.get("/cached", response_model=dict[str, DeviceMetrics])
async def get_all_cached_metrics():
    """
    Get all cached metrics for all monitored devices.
    """
    return health_checker.get_all_cached_metrics()


@router.delete("/cache")
async def clear_cache():
    """
    Clear the metrics cache. Useful for testing or reset.
    """
    health_checker.clear_cache()
    return {"message": "Cache cleared"}


@router.get("/ping/{ip}")
async def quick_ping(ip: str, count: int = Query(3, ge=1, le=10)):
    """
    Perform a quick ping test on a device.
    Lightweight endpoint for just ping data.
    """
    try:
        result = await health_checker.ping_host(ip, count=count)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ports/{ip}")
async def scan_ports(ip: str):
    """
    Scan common ports on a device.
    Returns only open ports.
    """
    try:
        open_ports = await health_checker.scan_common_ports(ip)
        return {"ip": ip, "open_ports": open_ports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dns/{ip}")
async def check_dns(ip: str):
    """
    Perform DNS lookup for an IP address.
    Returns reverse DNS and hostname resolution.
    """
    try:
        result = await health_checker.check_dns(ip)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

