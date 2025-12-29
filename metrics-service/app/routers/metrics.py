"""
Metrics Router

API endpoints for the metrics service, including:
- Retrieving current network topology snapshots
- Triggering snapshot generation
- Managing publishing configuration
- WebSocket endpoint for real-time updates
"""

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..models import (
    EndpointUsageRecord,
    MetricsEvent,
    NetworkTopologySnapshot,
    PublishConfig,
    UsageRecordBatch,
    UsageStatsResponse,
)
from ..services.metrics_aggregator import metrics_aggregator
from ..services.redis_publisher import (
    CHANNEL_HEALTH,
    CHANNEL_SPEED_TEST,
    CHANNEL_TOPOLOGY,
    redis_publisher,
)
from ..services.usage_tracker import usage_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


# ==================== Request/Response Models ====================

class SnapshotResponse(BaseModel):
    """Response containing a network topology snapshot"""
    success: bool
    snapshot: NetworkTopologySnapshot | None = None
    message: str | None = None


class ConfigResponse(BaseModel):
    """Response containing service configuration"""
    redis_connected: bool
    publishing_enabled: bool
    publish_interval_seconds: int
    is_running: bool
    last_snapshot_id: str | None = None
    last_snapshot_timestamp: str | None = None


class TriggerResponse(BaseModel):
    """Response from triggering an action"""
    success: bool
    message: str


class SpeedTestRequest(BaseModel):
    """Request to trigger a speed test"""
    gateway_ip: str


# ==================== Snapshot Endpoints ====================

@router.get("/snapshot", response_model=SnapshotResponse)
async def get_current_snapshot(network_id: str | None = Query(None, description="Network ID (UUID) to get snapshot for")):
    """
    Get the current/latest network topology snapshot.
    Returns the last generated snapshot from memory.
    
    Args:
        network_id: Optional network ID for multi-tenant mode. If not provided,
                   returns the legacy single-network snapshot.
    """
    snapshot = metrics_aggregator.get_last_snapshot(network_id)
    
    if snapshot:
        return SnapshotResponse(
            success=True,
            snapshot=snapshot
        )
    
    return SnapshotResponse(
        success=False,
        message=f"No snapshot available for network_id={network_id}. Try triggering a snapshot generation."
    )


@router.post("/snapshot/generate", response_model=SnapshotResponse)
async def generate_snapshot(network_id: str | None = Query(None, description="Network ID (UUID) to generate snapshot for")):
    """
    Trigger immediate generation of a new network topology snapshot.
    This will fetch fresh data from all services and create a new snapshot.
    
    Args:
        network_id: Optional network ID for multi-tenant mode. If not provided,
                   uses legacy single-network mode.
    """
    try:
        snapshot = await metrics_aggregator.generate_snapshot(network_id)
        
        if snapshot:
            return SnapshotResponse(
                success=True,
                snapshot=snapshot
            )
        
        return SnapshotResponse(
            success=False,
            message=f"Failed to generate snapshot for network_id={network_id} - no network layout available"
        )
    except Exception as e:
        logger.error(f"Failed to generate snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate snapshot: {e}")


@router.post("/snapshot/publish", response_model=TriggerResponse)
async def publish_snapshot(network_id: str | None = Query(None, description="Network ID (UUID) to publish snapshot for")):
    """
    Generate and publish a new snapshot to Redis.
    This will make the snapshot available to all subscribers.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    try:
        success = await metrics_aggregator.publish_snapshot(network_id)
        
        if success:
            return TriggerResponse(
                success=True,
                message=f"Snapshot for network_id={network_id} generated and published to Redis"
            )
        
        return TriggerResponse(
            success=False,
            message=f"Failed to publish snapshot for network_id={network_id} - check Redis connection or layout"
        )
    except Exception as e:
        logger.error(f"Failed to publish snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to publish snapshot: {e}")


@router.get("/snapshot/cached")
async def get_cached_snapshot():
    """
    Get the last published snapshot from Redis.
    Useful for new subscribers to get initial state.
    """
    try:
        snapshot = await redis_publisher.get_last_snapshot()
        
        if snapshot:
            return JSONResponse({
                "success": True,
                "snapshot": snapshot.model_dump(mode="json")
            })
        
        return JSONResponse({
            "success": False,
            "message": "No cached snapshot in Redis"
        })
    except Exception as e:
        logger.error(f"Failed to get cached snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cached snapshot: {e}")


# ==================== Configuration Endpoints ====================

@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get the current metrics service configuration."""
    aggregator_config = metrics_aggregator.get_config()
    redis_info = await redis_publisher.get_connection_info()
    
    return ConfigResponse(
        redis_connected=redis_info["connected"],
        publishing_enabled=aggregator_config["publishing_enabled"],
        publish_interval_seconds=aggregator_config["publish_interval_seconds"],
        is_running=aggregator_config["is_running"],
        last_snapshot_id=aggregator_config["last_snapshot_id"],
        last_snapshot_timestamp=aggregator_config["last_snapshot_timestamp"],
    )


@router.post("/config")
async def update_config(config: PublishConfig):
    """Update the metrics publishing configuration."""
    try:
        metrics_aggregator.set_publishing_enabled(config.enabled)
        metrics_aggregator.set_publish_interval(config.publish_interval_seconds)
        
        return JSONResponse({
            "success": True,
            "message": "Configuration updated",
            "config": {
                "enabled": config.enabled,
                "publish_interval_seconds": config.publish_interval_seconds
            }
        })
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update config: {e}")


# ==================== Speed Test Endpoint ====================

@router.post("/speed-test")
async def trigger_speed_test(request: SpeedTestRequest):
    """
    Trigger an ISP speed test for a gateway device.
    The result will be published to Redis and included in subsequent snapshots.
    
    Note: Speed tests can take 30-60 seconds to complete.
    """
    try:
        result = await metrics_aggregator.trigger_speed_test(request.gateway_ip)
        
        if result:
            return JSONResponse({
                "success": True,
                "result": result.model_dump(mode="json")
            })
        
        return JSONResponse({
            "success": False,
            "message": "Failed to run speed test"
        }, status_code=500)
    except Exception as e:
        logger.error(f"Failed to run speed test: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run speed test: {e}")


# ==================== Redis Connection Endpoints ====================

@router.get("/redis/status")
async def get_redis_status():
    """Get Redis connection status and info."""
    info = await redis_publisher.get_connection_info()
    return JSONResponse(info)


@router.post("/redis/reconnect")
async def reconnect_redis():
    """Attempt to reconnect to Redis."""
    try:
        await redis_publisher.disconnect()
        success = await redis_publisher.connect()
        
        return JSONResponse({
            "success": success,
            "message": "Reconnected to Redis" if success else "Failed to reconnect"
        })
    except Exception as e:
        logger.error(f"Failed to reconnect to Redis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reconnect: {e}")


# ==================== WebSocket for Real-time Updates ====================

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


connection_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time metrics updates.
    
    Clients receive:
    - Full topology snapshots when published
    - Node updates
    - Health status changes
    - Speed test results
    """
    await connection_manager.connect(websocket)
    
    # Set up Redis subscriber for this connection
    async def on_topology_event(event: MetricsEvent):
        await connection_manager.broadcast({
            "type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "payload": event.payload
        })
    
    # Subscribe to Redis channels
    redis_publisher.add_handler(CHANNEL_TOPOLOGY, on_topology_event)
    redis_publisher.add_handler(CHANNEL_HEALTH, on_topology_event)
    redis_publisher.add_handler(CHANNEL_SPEED_TEST, on_topology_event)
    
    await redis_publisher.subscribe(CHANNEL_TOPOLOGY, CHANNEL_HEALTH, CHANNEL_SPEED_TEST)
    
    # Send initial snapshot if available (legacy mode - no network_id)
    snapshot = metrics_aggregator.get_last_snapshot()
    if snapshot:
        await websocket.send_json({
            "type": "initial_snapshot",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": snapshot.model_dump(mode="json")
        })
    
    try:
        while True:
            # Keep connection alive and handle client messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                
                # Handle client requests
                if data.get("action") == "request_snapshot":
                    # Support network_id in client request for multi-tenant mode
                    network_id = data.get("network_id")
                    snapshot = metrics_aggregator.get_last_snapshot(network_id)
                    if snapshot:
                        await websocket.send_json({
                            "type": "snapshot",
                            "timestamp": datetime.utcnow().isoformat(),
                            "network_id": network_id,
                            "payload": snapshot.model_dump(mode="json")
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "timestamp": datetime.utcnow().isoformat(),
                            "message": f"No snapshot available for network_id={network_id}"
                        })
                
                elif data.get("action") == "subscribe_network":
                    # Allow client to specify which network they want updates for
                    network_id = data.get("network_id")
                    snapshot = metrics_aggregator.get_last_snapshot(network_id)
                    if snapshot:
                        await websocket.send_json({
                            "type": "initial_snapshot",
                            "timestamp": datetime.utcnow().isoformat(),
                            "network_id": network_id,
                            "payload": snapshot.model_dump(mode="json")
                        })
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up handlers
        redis_publisher.remove_handler(CHANNEL_TOPOLOGY, on_topology_event)
        redis_publisher.remove_handler(CHANNEL_HEALTH, on_topology_event)
        redis_publisher.remove_handler(CHANNEL_SPEED_TEST, on_topology_event)
        connection_manager.disconnect(websocket)


# ==================== Summary Endpoints ====================

@router.get("/summary")
async def get_summary(network_id: str | None = Query(None, description="Network ID (UUID) to get summary for")):
    """
    Get a summary of the current network state without full details.
    Lighter weight than full snapshot for dashboards.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    snapshot = metrics_aggregator.get_last_snapshot(network_id)
    
    if not snapshot:
        return JSONResponse({
            "available": False,
            "message": "No snapshot available"
        })
    
    # Count nodes by role
    role_counts = {}
    for node in snapshot.nodes.values():
        role = node.role.value if node.role else "unknown"
        role_counts[role] = role_counts.get(role, 0) + 1
    
    # Get gateway ISP info summary
    gateways_summary = []
    for gw in snapshot.gateways:
        healthy_test_ips = sum(1 for tip in gw.test_ips if tip.status.value == "healthy")
        gateways_summary.append({
            "gateway_ip": gw.gateway_ip,
            "test_ip_count": len(gw.test_ips),
            "healthy_test_ips": healthy_test_ips,
            "has_speed_test": gw.last_speed_test is not None,
            "last_speed_test_timestamp": gw.last_speed_test_timestamp.isoformat() if gw.last_speed_test_timestamp else None,
        })
    
    return JSONResponse({
        "available": True,
        "snapshot_id": snapshot.snapshot_id,
        "timestamp": snapshot.timestamp.isoformat(),
        "total_nodes": snapshot.total_nodes,
        "health_summary": {
            "healthy": snapshot.healthy_nodes,
            "degraded": snapshot.degraded_nodes,
            "unhealthy": snapshot.unhealthy_nodes,
            "unknown": snapshot.unknown_nodes,
        },
        "role_counts": role_counts,
        "connection_count": len(snapshot.connections),
        "gateways": gateways_summary,
    })


@router.get("/nodes/{node_id}")
async def get_node_metrics(node_id: str, network_id: str | None = Query(None, description="Network ID (UUID)")):
    """Get metrics for a specific node by ID.
    
    Args:
        node_id: The node ID to get metrics for.
        network_id: Optional network ID for multi-tenant mode.
    """
    snapshot = metrics_aggregator.get_last_snapshot(network_id)
    
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No snapshot available for network_id={network_id}")
    
    node = snapshot.nodes.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    
    return JSONResponse(node.model_dump(mode="json"))


@router.get("/connections")
async def get_connections(network_id: str | None = Query(None, description="Network ID (UUID)")):
    """Get all node connections from the current snapshot.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    snapshot = metrics_aggregator.get_last_snapshot(network_id)
    
    if not snapshot:
        return JSONResponse({
            "available": False,
            "connections": []
        })
    
    return JSONResponse({
        "available": True,
        "count": len(snapshot.connections),
        "connections": [conn.model_dump(mode="json") for conn in snapshot.connections]
    })


@router.get("/gateways")
async def get_gateways(network_id: str | None = Query(None, description="Network ID (UUID)")):
    """Get ISP information for all gateway devices.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    snapshot = metrics_aggregator.get_last_snapshot(network_id)
    
    if not snapshot:
        return JSONResponse({
            "available": False,
            "gateways": []
        })
    
    return JSONResponse({
        "available": True,
        "count": len(snapshot.gateways),
        "gateways": [gw.model_dump(mode="json") for gw in snapshot.gateways]
    })


@router.get("/debug/layout")
async def debug_layout(network_id: str | None = Query(None, description="Network ID (UUID)")):
    """Debug endpoint to see raw layout data from backend.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    layout = await metrics_aggregator._fetch_network_layout(network_id)
    
    if not layout:
        return {"error": f"Failed to fetch layout for network_id={network_id}"}
    
    # Extract nodes with notes from the layout tree
    def extract_nodes(node, depth=0):
        result = [{
            "id": node.get("id"),
            "name": node.get("name"),
            "ip": node.get("ip"),
            "role": node.get("role"),
            "notes": node.get("notes"),
            "depth": depth,
        }]
        for child in node.get("children", []):
            result.extend(extract_nodes(child, depth + 1))
        return result
    
    root = layout.get("root", {})
    nodes = extract_nodes(root) if root else []
    
    # Filter to only nodes with notes
    nodes_with_notes = [n for n in nodes if n.get("notes")]
    
    return {
        "layout_exists": layout is not None,
        "has_root": "root" in layout,
        "total_nodes": len(nodes),
        "nodes_with_notes": nodes_with_notes,
        "all_nodes": nodes,
    }


# ==================== Usage Statistics Endpoints ====================

@router.post("/usage/record")
async def record_usage(record: EndpointUsageRecord):
    """
    Record a single endpoint usage event.
    
    This endpoint is called by microservices to report their endpoint usage.
    """
    try:
        success = await usage_tracker.record_usage(record)
        return JSONResponse({
            "success": success,
            "message": "Usage recorded" if success else "Recorded locally (Redis unavailable)"
        })
    except Exception as e:
        logger.error(f"Failed to record usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record usage: {e}")


@router.post("/usage/record/batch")
async def record_usage_batch(batch: UsageRecordBatch):
    """
    Record multiple endpoint usage events efficiently.
    
    This endpoint is called by microservices to batch report their endpoint usage.
    """
    try:
        success_count = await usage_tracker.record_batch(batch.records)
        return JSONResponse({
            "success": True,
            "recorded": success_count,
            "total": len(batch.records),
            "message": f"Recorded {success_count}/{len(batch.records)} usage events"
        })
    except Exception as e:
        logger.error(f"Failed to record batch usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record batch usage: {e}")


@router.get("/usage/stats", response_model=UsageStatsResponse)
async def get_usage_stats(service: str | None = Query(None, description="Filter by service name")):
    """
    Get aggregated endpoint usage statistics.
    
    Returns usage metrics for all services or a specific service.
    """
    try:
        stats = await usage_tracker.get_usage_stats(service)
        return stats
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage stats: {e}")


@router.delete("/usage/stats")
async def reset_usage_stats(service: str | None = Query(None, description="Service to reset, or all if not specified")):
    """
    Reset usage statistics.
    
    Can reset stats for a specific service or all services.
    """
    try:
        success = await usage_tracker.reset_stats(service)
        target = f"service '{service}'" if service else "all services"
        return JSONResponse({
            "success": success,
            "message": f"Reset usage stats for {target}" if success else "Failed to reset stats"
        })
    except Exception as e:
        logger.error(f"Failed to reset usage stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset usage stats: {e}")
