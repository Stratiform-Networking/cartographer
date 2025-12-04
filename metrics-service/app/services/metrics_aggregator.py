"""
Metrics Aggregator Service

Collects and aggregates data from the health service and backend
to produce comprehensive network topology snapshots.
"""

import os
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any

import httpx
import jwt

from ..models import (
    NetworkTopologySnapshot,
    NodeMetrics,
    NodeConnection,
    HealthStatus,
    DeviceRole,
    PingMetrics,
    DnsMetrics,
    PortInfo,
    UptimeMetrics,
    CheckHistoryEntry,
    GatewayISPInfo,
    TestIPMetrics,
    SpeedTestMetrics,
    SpeedTestMetrics,
)
from .redis_publisher import redis_publisher

logger = logging.getLogger(__name__)

# Service URLs from environment
HEALTH_SERVICE_URL = os.environ.get("HEALTH_SERVICE_URL", "http://localhost:8001")
BACKEND_SERVICE_URL = os.environ.get("BACKEND_SERVICE_URL", "http://localhost:8000")

# JWT Configuration (must match auth service)
JWT_SECRET = os.environ.get("JWT_SECRET", "cartographer-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"

# Publishing configuration
DEFAULT_PUBLISH_INTERVAL = int(os.environ.get("METRICS_PUBLISH_INTERVAL", "30"))


def _generate_service_token() -> str:
    """
    Generate a long-lived service token for internal service-to-service communication.
    This token is used by the metrics service to authenticate with the backend.
    """
    now = datetime.now(timezone.utc)
    # Service token valid for 1 year
    expires = now + timedelta(days=365)
    
    payload = {
        "sub": "metrics-service",
        "username": "metrics-service",
        "role": "owner",  # Service has full access
        "exp": expires,
        "iat": now,
        "service": True,  # Mark as service token
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


# Generate service token on module load
SERVICE_TOKEN = _generate_service_token()
SERVICE_AUTH_HEADER = {"Authorization": f"Bearer {SERVICE_TOKEN}"}


class MetricsAggregator:
    """
    Aggregates metrics from multiple sources and publishes
    comprehensive network topology snapshots to Redis.
    """
    
    def __init__(self):
        self._publish_interval = DEFAULT_PUBLISH_INTERVAL
        self._publishing_enabled = True
        self._publish_task: Optional[asyncio.Task] = None
        self._last_snapshot: Optional[NetworkTopologySnapshot] = None
        self._last_speed_test: Dict[str, SpeedTestMetrics] = {}  # gateway_ip -> last speed test
    
    # ==================== Data Fetching ====================
    
    async def _fetch_network_layout(self) -> Optional[Dict[str, Any]]:
        """Fetch the saved network layout from the backend."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{BACKEND_SERVICE_URL}/api/load-layout",
                    headers=SERVICE_AUTH_HEADER
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("exists"):
                        return data.get("layout")
                elif response.status_code == 401:
                    logger.error("Authentication failed fetching layout - check JWT_SECRET")
                return None
        except httpx.ConnectError:
            logger.warning("Backend service unavailable - cannot fetch network layout")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch network layout: {e}")
            return None
    
    async def _fetch_health_metrics(self) -> Dict[str, Any]:
        """Fetch all cached health metrics from the health service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{HEALTH_SERVICE_URL}/api/health/cached")
                if response.status_code == 200:
                    return response.json()
                return {}
        except httpx.ConnectError:
            logger.warning("Health service unavailable - cannot fetch health metrics")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch health metrics: {e}")
            return {}
    
    async def _fetch_gateway_test_ips(self) -> Dict[str, Any]:
        """Fetch all gateway test IP metrics (with status) from health service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use the metrics endpoint which includes status, not just config
                response = await client.get(f"{HEALTH_SERVICE_URL}/api/health/gateway/test-ips/all/metrics")
                if response.status_code == 200:
                    return response.json()
                # Fallback to old endpoint if new one doesn't exist
                logger.warning("New metrics endpoint not available, falling back to config endpoint")
                response = await client.get(f"{HEALTH_SERVICE_URL}/api/health/gateway/test-ips/all")
                if response.status_code == 200:
                    return response.json()
                return {}
        except httpx.ConnectError:
            logger.warning("Health service unavailable - cannot fetch gateway test IPs")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch gateway test IPs: {e}")
            return {}
    
    async def _fetch_speed_test_results(self) -> Dict[str, Any]:
        """Fetch all stored speed test results from health service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{HEALTH_SERVICE_URL}/api/health/speedtest/all")
                if response.status_code == 200:
                    return response.json()
                return {}
        except httpx.ConnectError:
            logger.warning("Health service unavailable - cannot fetch speed test results")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch speed test results: {e}")
            return {}
    
    async def _fetch_monitoring_status(self) -> Optional[Dict[str, Any]]:
        """Fetch monitoring status from health service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{HEALTH_SERVICE_URL}/api/health/monitoring/status")
                if response.status_code == 200:
                    return response.json()
                return None
        except httpx.ConnectError:
            logger.warning("Health service unavailable - cannot fetch monitoring status")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch monitoring status: {e}")
            return None
    
    # ==================== Data Transformation ====================
    
    def _parse_device_role(self, role_str: Optional[str]) -> Optional[DeviceRole]:
        """Parse a device role string to DeviceRole enum."""
        if not role_str:
            return None
        try:
            # Handle the role format from frontend
            role_map = {
                "gateway/router": DeviceRole.GATEWAY_ROUTER,
                "switch/ap": DeviceRole.SWITCH_AP,
                "firewall": DeviceRole.FIREWALL,
                "server": DeviceRole.SERVER,
                "service": DeviceRole.SERVICE,
                "nas": DeviceRole.NAS,
                "client": DeviceRole.CLIENT,
                "unknown": DeviceRole.UNKNOWN,
                "group": DeviceRole.GROUP,
            }
            return role_map.get(role_str.lower(), DeviceRole.UNKNOWN)
        except Exception:
            return DeviceRole.UNKNOWN
    
    def _parse_health_status(self, status_str: Optional[str]) -> HealthStatus:
        """Parse a health status string to HealthStatus enum."""
        if not status_str:
            return HealthStatus.UNKNOWN
        try:
            return HealthStatus(status_str.lower())
        except ValueError:
            return HealthStatus.UNKNOWN
    
    def _transform_ping_metrics(self, ping_data: Optional[Dict]) -> Optional[PingMetrics]:
        """Transform ping data from health service to PingMetrics model."""
        if not ping_data:
            return None
        return PingMetrics(
            success=ping_data.get("success", False),
            latency_ms=ping_data.get("latency_ms"),
            packet_loss_percent=ping_data.get("packet_loss_percent", 0.0),
            min_latency_ms=ping_data.get("min_latency_ms"),
            max_latency_ms=ping_data.get("max_latency_ms"),
            avg_latency_ms=ping_data.get("avg_latency_ms"),
            jitter_ms=ping_data.get("jitter_ms"),
        )
    
    def _transform_dns_metrics(self, dns_data: Optional[Dict]) -> Optional[DnsMetrics]:
        """Transform DNS data from health service to DnsMetrics model."""
        if not dns_data:
            return None
        return DnsMetrics(
            success=dns_data.get("success", False),
            resolved_hostname=dns_data.get("resolved_hostname"),
            reverse_dns=dns_data.get("reverse_dns"),
            resolution_time_ms=dns_data.get("resolution_time_ms"),
        )
    
    def _transform_check_history(self, history_data: List[Dict]) -> List[CheckHistoryEntry]:
        """Transform check history from health service."""
        result = []
        for entry in history_data or []:
            try:
                timestamp = entry.get("timestamp")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                result.append(CheckHistoryEntry(
                    timestamp=timestamp,
                    success=entry.get("success", False),
                    latency_ms=entry.get("latency_ms"),
                ))
            except Exception as e:
                logger.debug(f"Failed to parse history entry: {e}")
        return result
    
    def _transform_uptime_metrics(self, health_data: Dict) -> UptimeMetrics:
        """Extract uptime metrics from health data."""
        last_seen = health_data.get("last_seen_online")
        if isinstance(last_seen, str):
            try:
                last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            except Exception:
                last_seen = None
        
        return UptimeMetrics(
            uptime_percent_24h=health_data.get("uptime_percent_24h"),
            avg_latency_24h_ms=health_data.get("avg_latency_24h_ms"),
            checks_passed_24h=health_data.get("checks_passed_24h", 0),
            checks_failed_24h=health_data.get("checks_failed_24h", 0),
            last_seen_online=last_seen,
            consecutive_failures=health_data.get("consecutive_failures", 0),
        )
    
    def _transform_test_ip_metrics(self, test_ip_data: Dict) -> TestIPMetrics:
        """Transform test IP metrics from health service."""
        last_check = test_ip_data.get("last_check")
        if isinstance(last_check, str):
            try:
                last_check = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
            except Exception:
                last_check = None
        
        return TestIPMetrics(
            ip=test_ip_data.get("ip", ""),
            label=test_ip_data.get("label"),
            status=self._parse_health_status(test_ip_data.get("status")),
            last_check=last_check,
            ping=self._transform_ping_metrics(test_ip_data.get("ping")),
            uptime=UptimeMetrics(
                uptime_percent_24h=test_ip_data.get("uptime_percent_24h"),
                avg_latency_24h_ms=test_ip_data.get("avg_latency_24h_ms"),
                checks_passed_24h=test_ip_data.get("checks_passed_24h", 0),
                checks_failed_24h=test_ip_data.get("checks_failed_24h", 0),
                last_seen_online=test_ip_data.get("last_seen_online"),
                consecutive_failures=test_ip_data.get("consecutive_failures", 0),
            ),
            check_history=self._transform_check_history(test_ip_data.get("check_history", [])),
        )
    
    # ==================== Node Processing ====================
    
    def _process_node(
        self,
        node_data: Dict,
        health_metrics: Dict[str, Any],
        gateway_test_ips: Dict[str, Any],
        speed_test_results: Dict[str, Any],
        depth: int = 0,
        parent_id: Optional[str] = None,
    ) -> tuple[NodeMetrics, List[NodeConnection], List[Dict]]:
        """
        Process a single node from the layout and merge with health data.
        Returns (NodeMetrics, connections, child_nodes_data)
        """
        node_id = node_data.get("id", "")
        ip = node_data.get("ip")
        
        # Get health data for this node
        health_data = health_metrics.get(ip, {}) if ip else {}
        
        # Parse timestamps
        created_at = node_data.get("createdAt")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                created_at = None
        
        updated_at = node_data.get("updatedAt")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except Exception:
                updated_at = None
        
        last_check = health_data.get("last_check")
        if isinstance(last_check, str):
            try:
                last_check = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
            except Exception:
                last_check = None
        
        # Build open ports list
        open_ports = []
        for port_data in health_data.get("open_ports", []):
            open_ports.append(PortInfo(
                port=port_data.get("port", 0),
                open=port_data.get("open", False),
                service=port_data.get("service"),
                response_time_ms=port_data.get("response_time_ms"),
            ))
        
        # Check if this is a gateway with test IPs
        isp_info = None
        role = self._parse_device_role(node_data.get("role"))
        if role == DeviceRole.GATEWAY_ROUTER and ip:
            gateway_data = gateway_test_ips.get(ip)
            if gateway_data:
                test_ips = [
                    self._transform_test_ip_metrics(tip)
                    for tip in gateway_data.get("test_ips", [])
                ]
                
                # Get speed test from fetched results or in-memory cache
                last_speed_test = None
                speed_data = speed_test_results.get(ip)
                if speed_data:
                    # Convert dict to SpeedTestMetrics if needed
                    if isinstance(speed_data, dict):
                        try:
                            last_speed_test = SpeedTestMetrics(
                                success=speed_data.get("success", False),
                                timestamp=datetime.fromisoformat(speed_data["timestamp"].replace("Z", "+00:00")) if isinstance(speed_data.get("timestamp"), str) else speed_data.get("timestamp"),
                                download_mbps=speed_data.get("download_mbps"),
                                upload_mbps=speed_data.get("upload_mbps"),
                                ping_ms=speed_data.get("ping_ms"),
                                server_name=speed_data.get("server_name"),
                                server_location=speed_data.get("server_location"),
                                server_sponsor=speed_data.get("server_sponsor"),
                                client_ip=speed_data.get("client_ip"),
                                client_isp=speed_data.get("client_isp"),
                                error_message=speed_data.get("error_message"),
                                duration_seconds=speed_data.get("duration_seconds"),
                            )
                        except Exception as e:
                            logger.warning(f"Failed to parse speed test for {ip}: {e}")
                    else:
                        last_speed_test = speed_data
                
                # Fallback to in-memory cache
                if not last_speed_test:
                    last_speed_test = self._last_speed_test.get(ip)
                
                last_speed_timestamp = None
                if last_speed_test:
                    last_speed_timestamp = last_speed_test.timestamp
                
                isp_info = GatewayISPInfo(
                    gateway_ip=ip,
                    test_ips=test_ips,
                    last_speed_test=last_speed_test,
                    last_speed_test_timestamp=last_speed_timestamp,
                )
        
        # Create the node metrics
        node_metrics = NodeMetrics(
            id=node_id,
            name=node_data.get("name", node_id),
            ip=ip,
            hostname=node_data.get("hostname"),
            role=role,
            parent_id=parent_id or node_data.get("parentId"),
            connection_speed=node_data.get("connectionSpeed"),
            depth=depth,
            status=self._parse_health_status(health_data.get("status")),
            last_check=last_check,
            ping=self._transform_ping_metrics(health_data.get("ping")),
            dns=self._transform_dns_metrics(health_data.get("dns")),
            open_ports=open_ports,
            uptime=self._transform_uptime_metrics(health_data) if health_data else None,
            check_history=self._transform_check_history(health_data.get("check_history", [])),
            notes=node_data.get("notes"),
            created_at=created_at,
            updated_at=updated_at,
            version=node_data.get("version"),
            isp_info=isp_info,
            monitoring_enabled=node_data.get("monitoringEnabled", True),
        )
        
        # Create connection to parent if applicable
        connections = []
        if parent_id:
            connections.append(NodeConnection(
                source_id=parent_id,
                target_id=node_id,
                connection_speed=node_data.get("connectionSpeed"),
                latency_ms=health_data.get("ping", {}).get("avg_latency_ms") if health_data else None,
            ))
        
        return node_metrics, connections, node_data.get("children", [])
    
    def _process_tree(
        self,
        root_data: Dict,
        health_metrics: Dict[str, Any],
        gateway_test_ips: Dict[str, Any],
        speed_test_results: Dict[str, Any],
    ) -> tuple[Dict[str, NodeMetrics], List[NodeConnection], str]:
        """
        Process the entire node tree recursively.
        Returns (nodes_dict, connections_list, root_node_id)
        """
        nodes: Dict[str, NodeMetrics] = {}
        connections: List[NodeConnection] = []
        
        # BFS to process all nodes
        queue = [(root_data, 0, None)]  # (node_data, depth, parent_id)
        root_node_id = root_data.get("id", "")
        
        while queue:
            node_data, depth, parent_id = queue.pop(0)
            
            node_metrics, node_connections, children = self._process_node(
                node_data, health_metrics, gateway_test_ips, speed_test_results, depth, parent_id
            )
            
            # Check if node already exists - if so, preserve notes from whichever has them
            existing = nodes.get(node_metrics.id)
            if existing:
                # If existing has notes but new doesn't, keep existing notes
                if existing.notes and not node_metrics.notes:
                    logger.debug(f"Preserving notes from existing node {node_metrics.id}")
                    node_metrics = node_metrics.model_copy(update={"notes": existing.notes})
                # If new has notes but existing doesn't, the new one will overwrite (which is fine)
                elif node_metrics.notes and not existing.notes:
                    logger.debug(f"New node {node_metrics.id} has notes, overwriting")
            
            nodes[node_metrics.id] = node_metrics
            connections.extend(node_connections)
            
            # Queue children
            for child in children:
                queue.append((child, depth + 1, node_metrics.id))

        return nodes, connections, root_node_id
    
    # ==================== Snapshot Generation ====================
    
    async def generate_snapshot(self) -> Optional[NetworkTopologySnapshot]:
        """
        Generate a complete network topology snapshot by aggregating
        data from all sources.
        """
        logger.debug("Generating network topology snapshot...")
        
        # Fetch data from all sources in parallel
        layout_task = self._fetch_network_layout()
        health_task = self._fetch_health_metrics()
        test_ips_task = self._fetch_gateway_test_ips()
        speed_test_task = self._fetch_speed_test_results()
        
        layout, health_metrics, gateway_test_ips, speed_test_results = await asyncio.gather(
            layout_task, health_task, test_ips_task, speed_test_task
        )
        
        if not layout or not layout.get("root"):
            logger.warning("No network layout available")
            return None
        
        # Process the node tree
        nodes, connections, root_node_id = self._process_tree(
            layout["root"],
            health_metrics,
            gateway_test_ips,
            speed_test_results,
        )
        
        # Count node statuses (excluding root and group nodes to match frontend)
        # The frontend's flattenDevices excludes the root node and filters out role="group"
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.UNKNOWN: 0,
        }

        device_nodes = {
            node_id: node for node_id, node in nodes.items()
            if node_id != root_node_id and node.role != DeviceRole.GROUP
        }
        for node in device_nodes.values():
            status_counts[node.status] = status_counts.get(node.status, 0) + 1
        
        # Build gateway ISP info list
        gateways = []
        for node in nodes.values():
            if node.isp_info:
                gateways.append(node.isp_info)
        
        # Create the snapshot
        # total_nodes uses device_nodes count (excludes root and group nodes) to match frontend
        snapshot = NetworkTopologySnapshot(
            snapshot_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            version=1,
            total_nodes=len(device_nodes),
            healthy_nodes=status_counts[HealthStatus.HEALTHY],
            degraded_nodes=status_counts[HealthStatus.DEGRADED],
            unhealthy_nodes=status_counts[HealthStatus.UNHEALTHY],
            unknown_nodes=status_counts[HealthStatus.UNKNOWN],
            nodes=nodes,  # Keep all nodes for topology/connections, but counts exclude root/groups
            connections=connections,
            gateways=gateways,
            root_node_id=root_node_id,
        )
        
        self._last_snapshot = snapshot
        logger.info(
            f"Generated snapshot with {len(device_nodes)} devices "
            f"(healthy={status_counts[HealthStatus.HEALTHY]}, "
            f"degraded={status_counts[HealthStatus.DEGRADED]}, "
            f"unhealthy={status_counts[HealthStatus.UNHEALTHY]}, "
            f"total tree nodes={len(nodes)})"
            f"Nodes: {nodes}"
        )
        
        return snapshot
    
    # ==================== Publishing ====================
    
    async def publish_snapshot(self) -> bool:
        """Generate and publish a network topology snapshot."""
        snapshot = await self.generate_snapshot()
        if not snapshot:
            return False
        
        # Publish to Redis
        success = await redis_publisher.publish_topology_snapshot(snapshot)
        
        if success:
            # Store as last snapshot for new subscribers
            await redis_publisher.store_last_snapshot(snapshot)
        
        return success
    
    async def _publish_loop(self, skip_initial: bool = False):
        """Background loop that periodically publishes snapshots."""
        logger.info(f"Starting metrics publish loop (interval: {self._publish_interval}s)")
        
        # If skip_initial is True, wait before first publish (initial was already done at startup)
        if skip_initial:
            logger.debug(f"Skipping initial publish, waiting {self._publish_interval}s")
            await asyncio.sleep(self._publish_interval)
        
        while True:
            try:
                if self._publishing_enabled:
                    await self.publish_snapshot()
                
                await asyncio.sleep(self._publish_interval)
                
            except asyncio.CancelledError:
                logger.info("Publish loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in publish loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def start_publishing(self, skip_initial: bool = False):
        """
        Start the background publishing task.
        
        Args:
            skip_initial: If True, wait for one interval before first publish
                         (useful when initial snapshot was already generated at startup)
        """
        if self._publish_task and not self._publish_task.done():
            logger.warning("Publishing already running")
            return
        
        self._publish_task = asyncio.create_task(self._publish_loop(skip_initial=skip_initial))
        logger.info("Background publishing started")
    
    def stop_publishing(self):
        """Stop the background publishing task."""
        if self._publish_task:
            self._publish_task.cancel()
            self._publish_task = None
            logger.info("Background publishing stopped")
    
    # ==================== Speed Test Integration ====================
    
    async def trigger_speed_test(self, gateway_ip: str) -> Optional[SpeedTestMetrics]:
        """
        Trigger a speed test via the health service and publish the result.
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{HEALTH_SERVICE_URL}/api/health/speedtest")
                if response.status_code == 200:
                    data = response.json()
                    
                    timestamp = data.get("timestamp")
                    if isinstance(timestamp, str):
                        try:
                            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        except Exception:
                            timestamp = datetime.utcnow()
                    
                    result = SpeedTestMetrics(
                        success=data.get("success", False),
                        timestamp=timestamp or datetime.utcnow(),
                        download_mbps=data.get("download_mbps"),
                        upload_mbps=data.get("upload_mbps"),
                        ping_ms=data.get("ping_ms"),
                        server_name=data.get("server_name"),
                        server_location=data.get("server_location"),
                        server_sponsor=data.get("server_sponsor"),
                        client_ip=data.get("client_ip"),
                        client_isp=data.get("client_isp"),
                        error_message=data.get("error_message"),
                        duration_seconds=data.get("duration_seconds"),
                    )
                    
                    # Store for inclusion in next snapshot
                    self._last_speed_test[gateway_ip] = result
                    
                    # Publish immediately
                    await redis_publisher.publish_speed_test_result(gateway_ip, result)
                    
                    return result
                    
        except httpx.ConnectError:
            logger.error("Health service unavailable - cannot run speed test")
        except Exception as e:
            logger.error(f"Failed to run speed test: {e}")
        
        return None
    
    # ==================== Configuration ====================
    
    def set_publish_interval(self, seconds: int):
        """Set the publishing interval in seconds."""
        self._publish_interval = max(5, seconds)  # Minimum 5 seconds
        logger.info(f"Publish interval set to {self._publish_interval}s")
    
    def set_publishing_enabled(self, enabled: bool):
        """Enable or disable publishing."""
        self._publishing_enabled = enabled
        logger.info(f"Publishing {'enabled' if enabled else 'disabled'}")
    
    def get_config(self) -> dict:
        """Get current aggregator configuration."""
        return {
            "publish_interval_seconds": self._publish_interval,
            "publishing_enabled": self._publishing_enabled,
            "is_running": self._publish_task is not None and not self._publish_task.done(),
            "last_snapshot_id": self._last_snapshot.snapshot_id if self._last_snapshot else None,
            "last_snapshot_timestamp": self._last_snapshot.timestamp.isoformat() if self._last_snapshot else None,
        }
    
    def get_last_snapshot(self) -> Optional[NetworkTopologySnapshot]:
        """Get the last generated snapshot."""
        return self._last_snapshot


# Singleton instance
metrics_aggregator = MetricsAggregator()
