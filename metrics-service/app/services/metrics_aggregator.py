"""
Metrics Aggregator Service

Collects and aggregates data from the health service and backend
to produce comprehensive network topology snapshots.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt

from ..config import settings
from ..models import (
    CheckHistoryEntry,
    DeviceRole,
    DnsMetrics,
    GatewayISPInfo,
    HealthStatus,
    LanPort,
    LanPortsConfig,
    NetworkTopologySnapshot,
    NodeConnection,
    NodeMetrics,
    PingMetrics,
    PoeStatus,
    PortInfo,
    PortStatus,
    PortType,
    SpeedTestMetrics,
    TestIPMetrics,
    UptimeMetrics,
)
from .redis_publisher import redis_publisher

logger = logging.getLogger(__name__)


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

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
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
        self._publish_interval = settings.metrics_publish_interval
        self._publishing_enabled = True
        self._publish_task: asyncio.Task | None = None
        # Multi-tenant: store snapshots per network_id (None key for legacy single-network mode)
        self._snapshots: dict[str | None, NetworkTopologySnapshot] = {}
        self._last_speed_test: dict[str, SpeedTestMetrics] = {}  # gateway_ip -> last speed test

    @property
    def _last_snapshot(self) -> NetworkTopologySnapshot | None:
        """Backwards compatibility: get the first/only snapshot (legacy mode)."""
        if None in self._snapshots:
            return self._snapshots[None]
        # Return first available snapshot for backwards compatibility
        if self._snapshots:
            return next(iter(self._snapshots.values()))
        return None

    @_last_snapshot.setter
    def _last_snapshot(self, value: NetworkTopologySnapshot | None):
        """Backwards compatibility: set snapshot without network_id."""
        self._snapshots[None] = value

    # ==================== Data Fetching ====================

    async def _fetch_all_network_ids(self) -> list[str]:
        """Fetch all network IDs from the backend for multi-tenant snapshot generation.

        Returns:
            List of network IDs (UUIDs) that have layouts configured.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.backend_service_url}/api/networks", headers=SERVICE_AUTH_HEADER
                )
                if response.status_code == 200:
                    networks = response.json()
                    # Extract network IDs from the response
                    network_ids = [n.get("id") for n in networks if n.get("id") is not None]
                    logger.info(f"Found {len(network_ids)} networks to generate snapshots for")
                    return network_ids
                elif response.status_code == 401:
                    logger.error("Authentication failed fetching networks - check JWT_SECRET")
                else:
                    logger.warning(f"Failed to fetch networks: {response.status_code}")
        except httpx.ConnectError:
            logger.warning("Backend service unavailable - cannot fetch networks list")
        except Exception as e:
            logger.error(f"Failed to fetch networks: {e}")

        return []

    async def _fetch_network_layout(self, network_id: str | None = None) -> dict[str, Any] | None:
        """Fetch the saved network layout from the backend.

        Args:
            network_id: The network ID to fetch layout for. Required for multi-tenant
                       mode. If None, falls back to the legacy single-file endpoint
                       for backwards compatibility only.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if network_id is not None:
                    # Use multi-tenant endpoint - requires explicit network_id
                    response = await client.get(
                        f"{settings.backend_service_url}/api/networks/{network_id}/layout",
                        headers=SERVICE_AUTH_HEADER,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        # Multi-tenant endpoint returns layout_data directly (not wrapped in exists/layout)
                        layout_data = data.get("layout_data")
                        if layout_data:
                            logger.debug(f"Fetched layout for network {network_id}")
                            return layout_data
                        else:
                            logger.debug(f"Network {network_id} has no layout data yet")
                    elif response.status_code == 401:
                        logger.error("Authentication failed fetching layout - check JWT_SECRET")
                    elif response.status_code == 404:
                        logger.warning(f"Network {network_id} not found or no layout exists")
                    elif response.status_code == 500:
                        logger.error(f"Backend error fetching layout for network {network_id}")
                    return None
                else:
                    # Legacy single-file endpoint for backwards compatibility only
                    # This should only be used for non-multi-tenant deployments
                    response = await client.get(
                        f"{settings.backend_service_url}/api/load-layout",
                        headers=SERVICE_AUTH_HEADER,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("exists") and data.get("layout"):
                            logger.debug("Using legacy single-file layout")
                            return data.get("layout")
                    elif response.status_code == 401:
                        logger.error("Authentication failed fetching layout - check JWT_SECRET")

                    # No legacy layout - this is expected in multi-tenant mode
                    # Clients must provide network_id
                    logger.debug(
                        "No legacy layout found - network_id required for multi-tenant mode"
                    )
                    return None
        except httpx.ConnectError:
            logger.warning("Backend service unavailable - cannot fetch network layout")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch network layout: {e}")
            return None

    async def _fetch_health_metrics(self) -> dict[str, Any]:
        """Fetch all cached health metrics from the health service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.health_service_url}/api/health/cached")
                if response.status_code == 200:
                    return response.json()
                return {}
        except httpx.ConnectError:
            logger.warning("Health service unavailable - cannot fetch health metrics")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch health metrics: {e}")
            return {}

    async def _fetch_gateway_test_ips(self) -> dict[str, Any]:
        """Fetch all gateway test IP metrics (with status) from health service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use the metrics endpoint which includes status, not just config
                response = await client.get(
                    f"{settings.health_service_url}/api/health/gateway/test-ips/all/metrics"
                )
                if response.status_code == 200:
                    return response.json()
                # Fallback to old endpoint if new one doesn't exist
                logger.warning(
                    "New metrics endpoint not available, falling back to config endpoint"
                )
                response = await client.get(
                    f"{settings.health_service_url}/api/health/gateway/test-ips/all"
                )
                if response.status_code == 200:
                    return response.json()
                return {}
        except httpx.ConnectError:
            logger.warning("Health service unavailable - cannot fetch gateway test IPs")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch gateway test IPs: {e}")
            return {}

    async def _fetch_speed_test_results(self) -> dict[str, Any]:
        """Fetch all stored speed test results from health service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.health_service_url}/api/health/speedtest/all"
                )
                if response.status_code == 200:
                    return response.json()
                return {}
        except httpx.ConnectError:
            logger.warning("Health service unavailable - cannot fetch speed test results")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch speed test results: {e}")
            return {}

    async def _fetch_monitoring_status(self) -> dict[str, Any] | None:
        """Fetch monitoring status from health service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.health_service_url}/api/health/monitoring/status"
                )
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

    def _parse_device_role(self, role_str: str | None) -> DeviceRole | None:
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

    def _parse_health_status(self, status_str: str | None) -> HealthStatus:
        """Parse a health status string to HealthStatus enum."""
        if not status_str:
            return HealthStatus.UNKNOWN
        try:
            return HealthStatus(status_str.lower())
        except ValueError:
            return HealthStatus.UNKNOWN

    def _transform_ping_metrics(self, ping_data: dict | None) -> PingMetrics | None:
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

    def _transform_dns_metrics(self, dns_data: dict | None) -> DnsMetrics | None:
        """Transform DNS data from health service to DnsMetrics model."""
        if not dns_data:
            return None
        return DnsMetrics(
            success=dns_data.get("success", False),
            resolved_hostname=dns_data.get("resolved_hostname"),
            reverse_dns=dns_data.get("reverse_dns"),
            resolution_time_ms=dns_data.get("resolution_time_ms"),
        )

    def _transform_check_history(self, history_data: list[dict]) -> list[CheckHistoryEntry]:
        """Transform check history from health service."""
        result = []
        for entry in history_data or []:
            try:
                timestamp = entry.get("timestamp")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                result.append(
                    CheckHistoryEntry(
                        timestamp=timestamp,
                        success=entry.get("success", False),
                        latency_ms=entry.get("latency_ms"),
                    )
                )
            except Exception as e:
                logger.debug(f"Failed to parse history entry: {e}")
        return result

    def _transform_uptime_metrics(self, health_data: dict) -> UptimeMetrics:
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

    def _transform_test_ip_metrics(self, test_ip_data: dict) -> TestIPMetrics:
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

    def _transform_lan_ports(self, lan_ports_data: dict | None) -> LanPortsConfig | None:
        """Transform LAN ports configuration from layout data."""
        if not lan_ports_data:
            return None

        ports = []
        for port_data in lan_ports_data.get("ports", []):
            # Parse port type
            port_type_str = port_data.get("type", "rj45").lower()
            try:
                if port_type_str == "sfp+":
                    port_type = PortType.SFP_PLUS
                else:
                    port_type = PortType(port_type_str)
            except ValueError:
                port_type = PortType.RJ45

            # Parse port status
            port_status_str = port_data.get("status", "unused").lower()
            try:
                port_status = PortStatus(port_status_str)
            except ValueError:
                port_status = PortStatus.UNUSED

            # Parse PoE status
            poe_status = None
            poe_str = port_data.get("poe")
            if poe_str:
                try:
                    if poe_str == "poe+":
                        poe_status = PoeStatus.POE_PLUS
                    elif poe_str == "poe++":
                        poe_status = PoeStatus.POE_PLUS_PLUS
                    else:
                        poe_status = PoeStatus(poe_str.lower())
                except ValueError:
                    poe_status = None

            ports.append(
                LanPort(
                    row=port_data.get("row", 1),
                    col=port_data.get("col", 1),
                    port_number=port_data.get("portNumber"),
                    type=port_type,
                    status=port_status,
                    speed=port_data.get("speed"),
                    negotiated_speed=port_data.get("negotiatedSpeed"),
                    poe=poe_status,
                    connected_device_id=port_data.get("connectedDeviceId"),
                    connected_device_name=port_data.get("connectedDeviceName"),
                    connection_label=port_data.get("connectionLabel"),
                )
            )

        return LanPortsConfig(
            rows=lan_ports_data.get("rows", 1),
            cols=lan_ports_data.get("cols", 1),
            ports=ports,
            label_format=lan_ports_data.get("labelFormat", "numeric"),
            start_number=lan_ports_data.get("startNumber", 1),
        )

    # ==================== Node Processing ====================

    def _process_node(
        self,
        node_data: dict,
        health_metrics: dict[str, Any],
        gateway_test_ips: dict[str, Any],
        speed_test_results: dict[str, Any],
        depth: int = 0,
        parent_id: str | None = None,
    ) -> tuple[NodeMetrics, list[NodeConnection], list[dict]]:
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
            open_ports.append(
                PortInfo(
                    port=port_data.get("port", 0),
                    open=port_data.get("open", False),
                    service=port_data.get("service"),
                    response_time_ms=port_data.get("response_time_ms"),
                )
            )

        # Check if this is a gateway with test IPs
        isp_info = None
        role = self._parse_device_role(node_data.get("role"))
        if role == DeviceRole.GATEWAY_ROUTER and ip:
            gateway_data = gateway_test_ips.get(ip)
            if gateway_data:
                test_ips = [
                    self._transform_test_ip_metrics(tip) for tip in gateway_data.get("test_ips", [])
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
                                timestamp=(
                                    datetime.fromisoformat(
                                        speed_data["timestamp"].replace("Z", "+00:00")
                                    )
                                    if isinstance(speed_data.get("timestamp"), str)
                                    else speed_data.get("timestamp")
                                ),
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

        # Transform LAN ports if present
        lan_ports = self._transform_lan_ports(node_data.get("lanPorts"))

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
            lan_ports=lan_ports,
            monitoring_enabled=node_data.get("monitoringEnabled", True),
        )

        # Create connection to parent if applicable
        connections = []
        if parent_id:
            connections.append(
                NodeConnection(
                    source_id=parent_id,
                    target_id=node_id,
                    connection_speed=node_data.get("connectionSpeed"),
                    latency_ms=(
                        health_data.get("ping", {}).get("avg_latency_ms") if health_data else None
                    ),
                )
            )

        return node_metrics, connections, node_data.get("children", [])

    def _process_tree(
        self,
        root_data: dict,
        health_metrics: dict[str, Any],
        gateway_test_ips: dict[str, Any],
        speed_test_results: dict[str, Any],
    ) -> tuple[dict[str, NodeMetrics], list[NodeConnection], str]:
        """
        Process the entire node tree recursively.
        Returns (nodes_dict, connections_list, root_node_id)
        """
        nodes: dict[str, NodeMetrics] = {}
        connections: list[NodeConnection] = []

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

    async def generate_snapshot(
        self, network_id: str | None = None
    ) -> NetworkTopologySnapshot | None:
        """
        Generate a complete network topology snapshot by aggregating
        data from all sources.

        Args:
            network_id: The network ID to generate snapshot for. If None, falls back
                       to legacy single-file layout (for backwards compatibility).
        """
        logger.debug(f"Generating network topology snapshot for network_id={network_id}...")

        # Fetch data from all sources in parallel
        layout_task = self._fetch_network_layout(network_id)
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

        # Count node statuses (excluding group nodes to match frontend)
        # The frontend's flattenDevices filters out role="group" nodes
        # Note: The root node (gateway) IS counted as a device since it appears as a child of a group
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.UNKNOWN: 0,
        }

        device_nodes = {
            node_id: node for node_id, node in nodes.items() if node.role != DeviceRole.GROUP
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

        # Store snapshot by network_id for multi-tenant support
        self._snapshots[network_id] = snapshot
        logger.info(
            f"Generated snapshot for network_id={network_id} with {len(device_nodes)} devices "
            f"(healthy={status_counts[HealthStatus.HEALTHY]}, "
            f"degraded={status_counts[HealthStatus.DEGRADED]}, "
            f"unhealthy={status_counts[HealthStatus.UNHEALTHY]}, "
            f"total tree nodes={len(nodes)})"
        )

        return snapshot

    # ==================== Publishing ====================

    async def generate_all_snapshots(self) -> dict[str, NetworkTopologySnapshot]:
        """Generate snapshots for all networks in the system.

        This fetches the list of all networks and generates a snapshot for each.
        Used at startup and in the background publish loop.

        Returns:
            Dict mapping network_id (UUID string) to generated snapshot.
        """
        snapshots: dict[str, NetworkTopologySnapshot] = {}

        # Fetch all network IDs
        network_ids = await self._fetch_all_network_ids()

        if not network_ids:
            # Fallback to legacy mode if no networks found
            logger.debug("No networks found, trying legacy single-network mode")
            legacy_snapshot = await self.generate_snapshot(None)
            if legacy_snapshot:
                logger.info("Generated legacy snapshot (no network_id)")
            return snapshots

        # Generate snapshot for each network
        for network_id in network_ids:
            try:
                snapshot = await self.generate_snapshot(network_id)
                if snapshot:
                    snapshots[network_id] = snapshot
                    logger.debug(f"Generated snapshot for network {network_id}")
            except Exception as e:
                logger.error(f"Failed to generate snapshot for network {network_id}: {e}")

        if snapshots:
            logger.info(
                f"Generated snapshots for {len(snapshots)} networks: {list(snapshots.keys())}"
            )
        else:
            logger.warning("No snapshots generated for any network")

        return snapshots

    async def publish_snapshot(self, network_id: str | None = None) -> bool:
        """Generate and publish a network topology snapshot.

        Args:
            network_id: The network ID to publish snapshot for. If None, uses
                       legacy single-network mode for backwards compatibility.
        """
        snapshot = await self.generate_snapshot(network_id)
        if not snapshot:
            return False

        # Publish to Redis
        success = await redis_publisher.publish_topology_snapshot(snapshot)

        if success:
            # Store as last snapshot for new subscribers
            await redis_publisher.store_last_snapshot(snapshot)

        return success

    async def publish_all_snapshots(self) -> int:
        """Generate and publish snapshots for all networks.

        Returns:
            Number of snapshots successfully published.
        """
        snapshots = await self.generate_all_snapshots()
        published_count = 0

        for network_id, snapshot in snapshots.items():
            try:
                success = await redis_publisher.publish_topology_snapshot(snapshot)
                if success:
                    await redis_publisher.store_last_snapshot(snapshot)
                    published_count += 1
            except Exception as e:
                logger.error(f"Failed to publish snapshot for network {network_id}: {e}")

        return published_count

    async def _publish_loop(self, skip_initial: bool = False):
        """Background loop that periodically publishes snapshots for all networks."""
        logger.info(f"Starting metrics publish loop (interval: {self._publish_interval}s)")

        # If skip_initial is True, wait before first publish (initial was already done at startup)
        if skip_initial:
            logger.debug(f"Skipping initial publish, waiting {self._publish_interval}s")
            await asyncio.sleep(self._publish_interval)

        while True:
            try:
                if self._publishing_enabled:
                    # Generate and publish snapshots for ALL networks
                    await self.publish_all_snapshots()

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

    async def trigger_speed_test(self, gateway_ip: str) -> SpeedTestMetrics | None:
        """
        Trigger a speed test via the health service and publish the result.
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{settings.health_service_url}/api/health/speedtest")
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
            "last_snapshot_timestamp": (
                self._last_snapshot.timestamp.isoformat() if self._last_snapshot else None
            ),
        }

    def get_last_snapshot(self, network_id: str | None = None) -> NetworkTopologySnapshot | None:
        """Get the last generated snapshot for a specific network.

        Args:
            network_id: The network ID to get snapshot for. Required for multi-tenant
                       mode. If None, returns the legacy single-network snapshot
                       for backwards compatibility only.
        """
        # Try to get exact match for the requested network_id
        if network_id in self._snapshots:
            return self._snapshots[network_id]

        # If specific network_id requested but not found, don't fall back
        # This is intentional for security - users should only see their own networks
        if network_id is not None:
            return None

        # Legacy mode only: if network_id=None and we have a legacy snapshot
        if None in self._snapshots:
            return self._snapshots[None]

        return None


# Singleton instance
metrics_aggregator = MetricsAggregator()
