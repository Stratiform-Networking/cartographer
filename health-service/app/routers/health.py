from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from ..models import (
    AgentSyncRequest,
    AgentSyncResponse,
    BatchHealthResponse,
    DeviceMetrics,
    GatewayTestIPConfig,
    GatewayTestIPsResponse,
    HealthCheckRequest,
    MonitoringConfig,
    MonitoringStatus,
    RegisterDevicesRequest,
    SetGatewayTestIPsRequest,
    SpeedTestResult,
)
from ..services.health_checker import health_checker
from ..services.notification_reporter import sync_devices_with_notification_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/check/{ip}", response_model=DeviceMetrics)
async def check_single_device(
    ip: str,
    include_ports: bool = Query(False, description="Include port scanning"),
    include_dns: bool = Query(True, description="Include DNS resolution"),
):
    """
    Check the health of a single device by IP address.
    Returns comprehensive metrics including ping, DNS, and optionally open ports.
    """
    try:
        metrics = await health_checker.check_device_health(
            ip=ip,
            include_ports=include_ports,
            include_dns=include_dns,
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
            include_dns=request.include_dns,
        )
        return BatchHealthResponse(devices=metrics, check_timestamp=datetime.utcnow())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cached/{ip}", response_model=DeviceMetrics | None)
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


# ==================== Agent Sync Endpoint ====================


@router.post("/agent-sync", response_model=AgentSyncResponse)
async def sync_agent_health(request: AgentSyncRequest):
    """
    Receive health check data from Cartographer Agent (via cloud backend).

    This endpoint allows the desktop agent to report health check results
    for devices it monitors locally. The results are merged into the
    health-service cache so they appear in the frontend dashboard.

    This is called by the core backend when it receives health data
    from the cloud backend's agent proxy.
    """
    if not request.results:
        return AgentSyncResponse(
            success=True,
            results_processed=0,
            cache_updated=0,
            message="No results to process",
        )

    updated_count = 0
    for result in request.results:
        if await health_checker.update_from_agent_health(
            ip=result.ip,
            reachable=result.reachable,
            response_time_ms=result.response_time_ms,
            network_id=request.network_id,
            include_dns=True,  # Perform DNS lookups for agent-reported devices
        ):
            updated_count += 1

    return AgentSyncResponse(
        success=True,
        results_processed=len(request.results),
        cache_updated=updated_count,
        message=f"Updated health cache for {updated_count} devices",
    )


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


# ==================== Monitoring Endpoints ====================


@router.post("/monitoring/devices")
async def register_devices(request: RegisterDevicesRequest):
    """
    Register devices for passive monitoring.
    These devices will be checked periodically in the background.

    Args:
        request: Contains list of IPs and network_id (UUID string)
    """
    # Create mapping of IP to network_id (now a UUID string)
    devices_map = {ip: request.network_id for ip in request.ips}
    health_checker.set_monitored_devices(devices_map)

    # Sync with notification service so ML anomaly detection tracks only current devices
    await sync_devices_with_notification_service(request.ips, network_id=request.network_id)

    return {
        "message": f"Registered {len(request.ips)} devices for monitoring",
        "devices": request.ips,
        "network_id": request.network_id,
    }


@router.get("/monitoring/devices")
async def get_monitored_devices():
    """Get list of devices currently being monitored"""
    return {"devices": health_checker.get_monitored_devices()}


@router.delete("/monitoring/devices")
async def clear_monitored_devices():
    """Clear all devices from monitoring"""
    health_checker.set_monitored_devices({})

    # Sync with notification service to clear device tracking
    await sync_devices_with_notification_service([])

    return {"message": "Cleared all monitored devices"}


@router.get("/monitoring/config", response_model=MonitoringConfig)
async def get_monitoring_config():
    """Get current monitoring configuration"""
    return health_checker.get_monitoring_config()


@router.post("/monitoring/config", response_model=MonitoringConfig)
async def set_monitoring_config(config: MonitoringConfig):
    """
    Update monitoring configuration.
    Changes take effect immediately.
    """
    health_checker.set_monitoring_config(config)
    return health_checker.get_monitoring_config()


@router.get("/monitoring/status", response_model=MonitoringStatus)
async def get_monitoring_status():
    """
    Get current monitoring status including:
    - Whether monitoring is enabled
    - Current check interval
    - List of monitored devices
    - Last and next check timestamps
    """
    return health_checker.get_monitoring_status()


@router.post("/monitoring/start")
async def start_monitoring():
    """Manually start the monitoring loop (usually auto-started)"""
    health_checker.start_monitoring()
    return {"message": "Monitoring started"}


@router.post("/monitoring/stop")
async def stop_monitoring():
    """Stop the background monitoring loop"""
    health_checker.stop_monitoring()
    return {"message": "Monitoring stopped"}


@router.post("/monitoring/check-now")
async def trigger_immediate_check():
    """
    Trigger an immediate health check of all monitored devices.
    Useful for forcing a refresh outside the normal interval.
    """
    if not health_checker.get_monitored_devices():
        raise HTTPException(status_code=400, detail="No devices registered for monitoring")

    await health_checker._perform_monitoring_check()
    return {
        "message": "Check completed",
        "checked_devices": len(health_checker.get_monitored_devices()),
        "timestamp": datetime.utcnow(),
    }


# ==================== Gateway Test IP Endpoints ====================


# Note: Specific route must come before parameterized routes
@router.get("/gateway/test-ips/all")
async def get_all_gateway_test_ips():
    """
    Get all gateway test IP configurations (without metrics/status).
    """
    return health_checker.get_all_gateway_test_ips()


@router.get("/gateway/test-ips/all/metrics")
async def get_all_gateway_test_ip_metrics():
    """
    Get all gateway test IP metrics (with status) from cache.
    Returns a dict mapping gateway_ip -> {test_ips: [...metrics...]}
    """
    result = {}
    for gateway_ip in health_checker.get_all_gateway_test_ips().keys():
        metrics = health_checker.get_cached_test_ip_metrics(gateway_ip)
        result[gateway_ip] = {
            "gateway_ip": gateway_ip,
            "test_ips": [tip.model_dump(mode="json") for tip in metrics.test_ips],
            "last_check": metrics.last_check.isoformat() if metrics.last_check else None,
        }
    return result


@router.post("/gateway/{gateway_ip}/test-ips", response_model=GatewayTestIPConfig)
async def set_gateway_test_ips(gateway_ip: str, request: SetGatewayTestIPsRequest):
    """
    Set test IPs for a gateway device.
    These IPs will be checked periodically to test internet connectivity.
    """
    if request.gateway_ip != gateway_ip:
        raise HTTPException(status_code=400, detail="Gateway IP in path must match request body")

    config = health_checker.set_gateway_test_ips(gateway_ip, request.test_ips)
    return config


@router.get("/gateway/{gateway_ip}/test-ips", response_model=GatewayTestIPConfig)
async def get_gateway_test_ips(gateway_ip: str):
    """
    Get test IP configuration for a gateway device.
    """
    config = health_checker.get_gateway_test_ips(gateway_ip)
    if config is None:
        raise HTTPException(status_code=404, detail="No test IPs configured for this gateway")
    return config


@router.delete("/gateway/{gateway_ip}/test-ips")
async def remove_gateway_test_ips(gateway_ip: str):
    """
    Remove all test IPs for a gateway device.
    """
    if health_checker.remove_gateway_test_ips(gateway_ip):
        return {"message": f"Removed test IPs for gateway {gateway_ip}"}
    raise HTTPException(status_code=404, detail="No test IPs configured for this gateway")


@router.get("/gateway/{gateway_ip}/test-ips/check", response_model=GatewayTestIPsResponse)
async def check_gateway_test_ips(gateway_ip: str):
    """
    Perform an immediate check of all test IPs for a gateway.
    Returns current metrics for all configured test IPs.
    """
    config = health_checker.get_gateway_test_ips(gateway_ip)
    if config is None:
        raise HTTPException(status_code=404, detail="No test IPs configured for this gateway")

    return await health_checker.check_gateway_test_ips(gateway_ip)


@router.get("/gateway/{gateway_ip}/test-ips/cached", response_model=GatewayTestIPsResponse)
async def get_cached_test_ip_metrics(gateway_ip: str):
    """
    Get cached metrics for all test IPs of a gateway without performing a new check.
    """
    return health_checker.get_cached_test_ip_metrics(gateway_ip)


# ==================== Speed Test Endpoints ====================


@router.post("/speedtest", response_model=SpeedTestResult)
async def run_speed_test(gateway_ip: str | None = None):
    """
    Run an ISP speed test.
    This is a manual operation that takes 30-60 seconds to complete.
    Returns download/upload speeds in Mbps.

    Args:
        gateway_ip: Optional gateway IP to associate this test with (for storage/retrieval)
    """
    return await health_checker.run_speed_test(gateway_ip)


@router.post("/gateway/{gateway_ip}/speedtest", response_model=SpeedTestResult)
async def run_gateway_speed_test(gateway_ip: str):
    """
    Run an ISP speed test for a specific gateway.
    Results are stored and associated with the gateway.
    """
    return await health_checker.run_speed_test(gateway_ip)


@router.get("/gateway/{gateway_ip}/speedtest", response_model=SpeedTestResult | None)
async def get_gateway_speed_test(gateway_ip: str):
    """
    Get the last speed test result for a gateway.
    """
    result = health_checker.get_last_speed_test(gateway_ip)
    if not result:
        raise HTTPException(status_code=404, detail="No speed test results for this gateway")
    return result


@router.get("/speedtest/all")
async def get_all_speed_tests():
    """
    Get all stored speed test results.
    Returns a dict mapping gateway_ip -> SpeedTestResult
    """
    results = health_checker.get_all_speed_tests()
    return {gateway_ip: result.model_dump(mode="json") for gateway_ip, result in results.items()}
