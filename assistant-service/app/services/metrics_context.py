"""
Service for fetching and formatting network context from the metrics service.
"""

import asyncio
import logging
from typing import Any
from datetime import datetime

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class MetricsContextService:
    """Service to fetch network context from metrics service"""
    
    def __init__(self):
        self.timeout = 10.0
        # Multi-tenant cache: network_id -> (context, summary, timestamp)
        self._context_cache: dict[str | None, tuple[str, dict[str, Any], datetime]] = {}
        self._cache_ttl_seconds = 30  # Cache for 30 seconds
        
        # Loading state tracking (per network_id)
        self._snapshot_available: dict[str | None, bool] = {}
        self._last_check_time: datetime | None = None
        self._check_interval_seconds = 5  # Recheck every 5 seconds when no snapshot
        self._max_wait_attempts = 6  # Max attempts when waiting for snapshot (30 seconds total)
    
    # Backwards compatibility properties
    @property
    def _cached_context(self) -> str | None:
        """Backwards compatibility: get legacy cached context."""
        if None in self._context_cache:
            return self._context_cache[None][0]
        return None
    
    @property
    def _cached_summary(self) -> dict[str, Any] | None:
        """Backwards compatibility: get legacy cached summary."""
        if None in self._context_cache:
            return self._context_cache[None][1]
        return None
    
    @property
    def _cache_timestamp(self) -> datetime | None:
        """Backwards compatibility: get legacy cache timestamp."""
        if None in self._context_cache:
            return self._context_cache[None][2]
        return None
    
    async def fetch_network_snapshot(self, force_refresh: bool = False, network_id: str | None = None) -> dict[str, Any] | None:
        """Fetch the current network topology snapshot
        
        Args:
            force_refresh: If True, ask the metrics service to generate a fresh snapshot
                          instead of returning the cached one. Use this after data changes
                          (like a speed test) to get the latest data.
            network_id: The network ID to fetch snapshot for (multi-tenant support).
                       If None, uses legacy single-network mode for backwards compatibility.
        """
        self._last_check_time = datetime.utcnow()
        
        # Build query params for network_id
        params = {}
        if network_id is not None:
            params["network_id"] = network_id
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if force_refresh:
                    # Ask metrics service to generate a fresh snapshot with latest data
                    response = await client.post(f"{settings.metrics_service_url}/api/metrics/snapshot/generate", params=params)
                else:
                    response = await client.get(f"{settings.metrics_service_url}/api/metrics/snapshot", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("snapshot"):
                        self._snapshot_available[network_id] = True
                        logger.debug(f"Successfully fetched snapshot for network_id={network_id}")
                        return data["snapshot"]
                    else:
                        # Log why we didn't get a snapshot
                        logger.warning(
                            f"Metrics service returned 200 but no valid snapshot for network_id={network_id}: "
                            f"success={data.get('success')}, has_snapshot={data.get('snapshot') is not None}, "
                            f"message={data.get('message', 'no message')}"
                        )
                
                # Snapshot not yet available (service may be starting up)
                self._snapshot_available[network_id] = False
                logger.info(f"Snapshot not yet available for network_id={network_id}: status={response.status_code}")
                return None
                
        except httpx.ConnectError:
            self._snapshot_available[network_id] = False
            logger.warning(f"Cannot connect to metrics service at {settings.metrics_service_url}")
            return None
        except Exception as e:
            self._snapshot_available[network_id] = False
            logger.error(f"Error fetching network snapshot: {e}")
            return None
    
    async def wait_for_snapshot(self, max_attempts: int | None = None, network_id: str | None = None) -> dict[str, Any] | None:
        """
        Wait for a snapshot to become available, retrying periodically.
        
        Args:
            max_attempts: Maximum number of attempts (defaults to self._max_wait_attempts)
            network_id: The network ID to wait for snapshot (multi-tenant support).
            
        Returns:
            The snapshot if available, None if max attempts exceeded
        """
        attempts = max_attempts or self._max_wait_attempts
        
        for attempt in range(attempts):
            snapshot = await self.fetch_network_snapshot(network_id=network_id)
            if snapshot:
                logger.info(f"Snapshot for network_id={network_id} available after {attempt + 1} attempt(s)")
                return snapshot
            
            if attempt < attempts - 1:
                logger.debug(f"Waiting for snapshot network_id={network_id} (attempt {attempt + 1}/{attempts})...")
                await asyncio.sleep(self._check_interval_seconds)
        
        logger.warning(f"Snapshot for network_id={network_id} not available after {attempts} attempts")
        return None
    
    def is_snapshot_available(self, network_id: str | None = None) -> bool:
        """Check if a snapshot has ever been successfully fetched for a network"""
        return self._snapshot_available.get(network_id, False)
    
    def should_recheck(self) -> bool:
        """Check if we should try fetching the snapshot again"""
        if self._snapshot_available:
            return False
        
        if not self._last_check_time:
            return True
        
        elapsed = (datetime.utcnow() - self._last_check_time).total_seconds()
        return elapsed >= self._check_interval_seconds
    
    async def fetch_network_summary(self, network_id: str | None = None) -> dict[str, Any] | None:
        """Fetch network summary (lighter weight than full snapshot)
        
        Args:
            network_id: The network ID to fetch summary for (multi-tenant support).
        """
        try:
            params = {}
            if network_id is not None:
                params["network_id"] = network_id
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{settings.metrics_service_url}/api/metrics/summary", params=params)
                
                if response.status_code == 200:
                    return response.json()
                
                return None
                
        except Exception as e:
            logger.error(f"Error fetching network summary: {e}")
            return None
    
    def _format_node_info(self, node: dict[str, Any]) -> str:
        """Format a single node's information"""
        lines = []
        
        name = node.get("name", "Unknown")
        ip = node.get("ip", "N/A")
        role = node.get("role", "unknown")
        status = node.get("status", "unknown")
        hostname = node.get("hostname", "")
        
        lines.append(f"  - {name}")
        lines.append(f"    IP: {ip}")
        lines.append(f"    Role: {role}")
        lines.append(f"    Status: {status}")
        
        if hostname and hostname != name:
            lines.append(f"    Hostname: {hostname}")
        
        # Connection info
        if node.get("connection_speed"):
            lines.append(f"    Connection: {node['connection_speed']}")
        
        # Ping metrics
        ping = node.get("ping")
        if ping and ping.get("success"):
            latency = ping.get("avg_latency_ms") or ping.get("latency_ms")
            if latency:
                lines.append(f"    Latency: {latency:.1f}ms")
        
        # Uptime info
        uptime = node.get("uptime")
        if uptime and uptime.get("uptime_percent_24h") is not None:
            lines.append(f"    Uptime (24h): {uptime['uptime_percent_24h']:.1f}%")
        
        # Open ports
        open_ports = node.get("open_ports", [])
        if open_ports:
            ports_str = ", ".join(
                f"{p['port']}" + (f" ({p['service']})" if p.get('service') else "")
                for p in open_ports[:5]  # Limit to first 5
            )
            lines.append(f"    Open Ports: {ports_str}")
        
        # LAN Ports configuration
        lan_ports = node.get("lan_ports")
        if lan_ports:
            lines.append(self._format_lan_ports(lan_ports))
        
        # Notes
        if node.get("notes"):
            lines.append(f"    Notes: {node['notes']}")
        
        return "\n".join(lines)
    
    def _format_lan_ports(self, lan_ports: dict[str, Any]) -> str:
        """Format LAN ports configuration for a device"""
        lines = []
        
        rows = lan_ports.get("rows", 0)
        cols = lan_ports.get("cols", 0)
        ports = lan_ports.get("ports", [])
        
        if not ports:
            return ""
        
        total_ports = len(ports)
        active_ports = [p for p in ports if p.get("status") == "active"]
        unused_ports = [p for p in ports if p.get("status") == "unused"]
        blocked_ports = [p for p in ports if p.get("status") == "blocked"]
        
        # Count port types
        rj45_count = len([p for p in ports if p.get("type") == "rj45" and p.get("status") != "blocked"])
        sfp_count = len([p for p in ports if p.get("type") in ["sfp", "sfp+"] and p.get("status") != "blocked"])
        poe_count = len([p for p in ports if p.get("poe") and p.get("poe") != "off"])
        
        lines.append(f"    LAN Ports: {total_ports} total ({rows}x{cols} grid)")
        lines.append(f"      Port Types: {rj45_count} RJ45, {sfp_count} SFP/SFP+")
        lines.append(f"      Status: {len(active_ports)} active, {len(unused_ports)} unused, {len(blocked_ports)} blocked")
        
        if poe_count > 0:
            lines.append(f"      PoE Enabled: {poe_count} ports")
        
        # List active connections
        connected_ports = [p for p in active_ports if p.get("connected_device_id") or p.get("connected_device_name")]
        if connected_ports:
            lines.append(f"      Active Connections ({len(connected_ports)}):")
            for port in connected_ports[:10]:  # Limit to first 10 connections
                port_num = self._get_port_label(port, lan_ports)
                port_type = port.get("type", "rj45").upper()
                speed = port.get("negotiated_speed") or port.get("speed") or "auto"
                connected_to = port.get("connected_device_name") or port.get("connection_label") or "Unknown device"
                poe_info = ""
                if port.get("poe") and port.get("poe") != "off":
                    poe_info = f" [PoE: {port.get('poe').upper()}]"
                
                lines.append(f"        Port {port_num} ({port_type}, {speed}) → {connected_to}{poe_info}")
        
        return "\n".join(lines)
    
    def _get_port_label(self, port: dict[str, Any], lan_ports: dict[str, Any]) -> str:
        """Get the display label for a port"""
        if port.get("port_number"):
            return str(port.get("port_number"))
        
        # Calculate port number from position
        row = port.get("row", 1)
        col = port.get("col", 1)
        cols = lan_ports.get("cols", 1)
        start_num = lan_ports.get("start_number", 1)
        
        return str((row - 1) * cols + col + start_num - 1)
    
    def _format_gateway_info(self, gateway: dict[str, Any], nodes: dict[str, Any]) -> str:
        """Format gateway/ISP information, including notes from the gateway node"""
        lines = []
        
        gw_ip = gateway.get("gateway_ip", "Unknown")
        lines.append(f"\n  Gateway: {gw_ip}")
        
        # Find the gateway node to get its name and notes
        # The nodes dict is keyed by node_id, so we need to search by IP
        gateway_node = None
        for node_id, node in nodes.items():
            node_ip = node.get("ip")
            if node_ip and node_ip == gw_ip:
                gateway_node = node
                logger.debug(f"Found gateway node for {gw_ip}: {node.get('name')}")
                break
        
        if gateway_node:
            gw_name = gateway_node.get("name")
            if gw_name and gw_name != gw_ip:
                lines.append(f"    Name: {gw_name}")
        else:
            logger.warning(f"Could not find gateway node for IP {gw_ip}")
        
        # Test IPs (external connectivity)
        test_ips = gateway.get("test_ips", [])
        if test_ips:
            # Count healthy test IPs - status can be "healthy" string or HealthStatus enum value
            healthy = 0
            for t in test_ips:
                status = t.get("status")
                # Handle both string "healthy" and potential dict/object forms
                if isinstance(status, str):
                    if status.lower() == "healthy":
                        healthy += 1
                elif isinstance(status, dict):
                    # In case it's serialized as {"value": "healthy"}
                    if status.get("value", "").lower() == "healthy":
                        healthy += 1
                logger.debug(f"Test IP {t.get('ip')}: status={status}, type={type(status)}")
            
            lines.append(f"    External Connectivity: {healthy}/{len(test_ips)} test IPs healthy")
            
            # List individual test IPs with their status
            for t in test_ips:
                tip_ip = t.get("ip", "Unknown")
                tip_label = t.get("label", "")
                tip_status = t.get("status", "unknown")
                if isinstance(tip_status, str):
                    tip_status = tip_status.lower()
                elif isinstance(tip_status, dict):
                    tip_status = tip_status.get("value", "unknown").lower()
                
                tip_display = f"{tip_ip}"
                if tip_label:
                    tip_display += f" ({tip_label})"
                lines.append(f"      - {tip_display}: {tip_status}")
        
        # Speed test results
        speed_test = gateway.get("last_speed_test")
        if speed_test and speed_test.get("success"):
            download = speed_test.get("download_mbps")
            upload = speed_test.get("upload_mbps")
            ping = speed_test.get("ping_ms")
            
            if download is not None or upload is not None:
                download_str = f"{download:.1f}" if download is not None else "N/A"
                upload_str = f"{upload:.1f}" if upload is not None else "N/A"
                lines.append(f"    Speed Test: ↓{download_str} Mbps / ↑{upload_str} Mbps")
            if ping is not None:
                lines.append(f"    ISP Latency: {ping:.1f}ms")
            
            isp = speed_test.get("client_isp")
            if isp:
                lines.append(f"    ISP: {isp}")
            
            # Server info
            server_sponsor = speed_test.get("server_sponsor")
            server_location = speed_test.get("server_location")
            if server_sponsor or server_location:
                server_info = server_sponsor or ""
                if server_location:
                    server_info += f" ({server_location})" if server_info else server_location
                lines.append(f"    Test Server: {server_info}")
            
            # Timestamp of the test
            timestamp = speed_test.get("timestamp")
            if timestamp:
                if isinstance(timestamp, str):
                    lines.append(f"    Tested: {timestamp}")
                else:
                    lines.append(f"    Tested: {timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)}")
        elif speed_test and not speed_test.get("success"):
            # Show error if speed test failed
            error_msg = speed_test.get("error_message", "Unknown error")
            lines.append(f"    Speed Test: Failed - {error_msg}")
        
        # Include notes from the gateway node
        if gateway_node and gateway_node.get("notes"):
            notes = gateway_node.get("notes")
            lines.append(f"    Notes: {notes}")
        
        return "\n".join(lines)
    
    async def build_context_string(self, wait_for_data: bool = True, force_refresh: bool = False, network_id: str | None = None) -> tuple[str, dict[str, Any]]:
        """
        Build a context string for the AI assistant with network information.
        Returns (context_string, summary_dict)
        
        Args:
            wait_for_data: If True and no snapshot available, wait and retry
            force_refresh: If True, bypass cache and fetch fresh data from the metrics service.
                          This also triggers the metrics service to regenerate its snapshot.
            network_id: The network ID to build context for (multi-tenant support).
                       If None, uses legacy single-network mode for backwards compatibility.
        """
        # Check per-network cache (skip if force_refresh)
        now = datetime.utcnow()
        if network_id in self._context_cache and not force_refresh:
            cached_context, cached_summary, cache_timestamp = self._context_cache[network_id]
            if (now - cache_timestamp).total_seconds() < self._cache_ttl_seconds:
                return cached_context, cached_summary
        
        # Try to fetch snapshot (force regeneration if force_refresh)
        snapshot = await self.fetch_network_snapshot(force_refresh=force_refresh, network_id=network_id)
        
        # If no snapshot and we should wait, try waiting for it
        if not snapshot and wait_for_data and not self.is_snapshot_available(network_id):
            logger.info(f"No snapshot available yet for network_id={network_id}, waiting for metrics service...")
            snapshot = await self.wait_for_snapshot(max_attempts=3, network_id=network_id)  # Wait up to 15 seconds
        
        if not snapshot:
            return self._build_loading_context() if not self.is_snapshot_available(network_id) else self._build_fallback_context()
        
        lines = []
        lines.append("=" * 60)
        lines.append("NETWORK TOPOLOGY INFORMATION")
        lines.append("=" * 60)
        
        # Timestamp
        timestamp = snapshot.get("timestamp", "")
        if timestamp:
            lines.append(f"\nSnapshot Time: {timestamp}")
        
        # Summary counts
        total = snapshot.get("total_nodes", 0)
        healthy = snapshot.get("healthy_nodes", 0)
        degraded = snapshot.get("degraded_nodes", 0)
        unhealthy = snapshot.get("unhealthy_nodes", 0)
        unknown = snapshot.get("unknown_nodes", 0)
        
        lines.append(f"\n📊 NETWORK SUMMARY")
        lines.append(f"Total Devices: {total}")
        lines.append(f"Health Status:")
        lines.append(f"  ✅ Healthy: {healthy}")
        if degraded > 0:
            lines.append(f"  ⚠️  Degraded: {degraded}")
        if unhealthy > 0:
            lines.append(f"  ❌ Unhealthy: {unhealthy}")
        if unknown > 0:
            lines.append(f"  ❓ Unknown: {unknown}")
        
        # Organize nodes by role
        # Filter out group nodes to match frontend's device count
        nodes = snapshot.get("nodes", {})
        nodes_by_role: dict[str, list[dict[str, Any]]] = {}
        for node_id, node in nodes.items():
            role = node.get("role", "unknown")
            # Normalize role string (handle both enum value and potential variations)
            if isinstance(role, str):
                role = role.lower()
            else:
                role = "unknown"
            
            # Skip group nodes
            if role == "group":
                continue
            
            # Map common variations
            if "gateway" in role or "router" in role:
                role = "gateway/router"
            elif "switch" in role or "ap" in role or "access" in role:
                role = "switch/ap"
            
            if role not in nodes_by_role:
                nodes_by_role[role] = []
            nodes_by_role[role].append(node)
            
            # Debug log for nodes with notes
            if node.get("notes"):
                logger.debug(f"Node with notes: {node.get('name')} ({node.get('ip')}): {node.get('notes')[:50]}...")
        
        # Role display order
        role_order = [
            "gateway/router",
            "firewall",
            "switch/ap",
            "server",
            "service",
            "nas",
            "client",
            "unknown",
        ]
        
        role_labels = {
            "gateway/router": "🌐 GATEWAYS & ROUTERS",
            "firewall": "🛡️  FIREWALLS",
            "switch/ap": "📡 SWITCHES & ACCESS POINTS",
            "server": "🖥️  SERVERS",
            "service": "⚙️  SERVICES",
            "nas": "💾 NAS DEVICES",
            "client": "💻 CLIENT DEVICES",
            "unknown": "❓ UNKNOWN DEVICES",
        }
        
        for role in role_order:
            if role in nodes_by_role and nodes_by_role[role]:
                lines.append(f"\n{role_labels.get(role, role.upper())}")
                lines.append("-" * 40)
                for node in nodes_by_role[role]:
                    lines.append(self._format_node_info(node))
        
        # Gateway/ISP information
        gateways = snapshot.get("gateways", [])
        logger.debug(f"Found {len(gateways)} gateways in snapshot")
        
        # Log all gateway nodes for debugging
        for node_id, node in nodes.items():
            node_role = node.get("role")
            if node_role and "gateway" in str(node_role).lower():
                logger.debug(f"Gateway node: id={node_id}, ip={node.get('ip')}, name={node.get('name')}, notes={node.get('notes')}")
        
        if gateways:
            lines.append(f"\n🌍 ISP & INTERNET CONNECTIVITY")
            lines.append("-" * 40)
            for gw in gateways:
                logger.debug(f"Processing gateway: {gw.get('gateway_ip')}, test_ips count: {len(gw.get('test_ips', []))}")
                lines.append(self._format_gateway_info(gw, nodes))
        
        # Connections summary
        connections = snapshot.get("connections", [])
        if connections:
            lines.append(f"\n🔗 NETWORK CONNECTIONS: {len(connections)} total")
        
        # LAN Infrastructure summary - devices with configured LAN ports
        lan_devices = []
        for node_id, node in nodes.items():
            lan_ports = node.get("lan_ports")
            if lan_ports and lan_ports.get("ports"):
                ports = lan_ports.get("ports", [])
                active_ports = [p for p in ports if p.get("status") == "active"]
                connected_ports = [p for p in active_ports if p.get("connected_device_id") or p.get("connected_device_name")]
                lan_devices.append({
                    "name": node.get("name", node_id),
                    "ip": node.get("ip", "N/A"),
                    "total_ports": len(ports),
                    "active_ports": len(active_ports),
                    "connected_ports": len(connected_ports),
                    "lan_ports": lan_ports,
                })
        
        if lan_devices:
            lines.append(f"\n🔌 LAN INFRASTRUCTURE")
            lines.append("-" * 40)
            total_lan_ports = sum(d["total_ports"] for d in lan_devices)
            total_active = sum(d["active_ports"] for d in lan_devices)
            total_connected = sum(d["connected_ports"] for d in lan_devices)
            lines.append(f"  Devices with LAN ports: {len(lan_devices)}")
            lines.append(f"  Total ports: {total_lan_ports}")
            lines.append(f"  Active ports: {total_active}")
            lines.append(f"  Connected ports: {total_connected}")
            lines.append(f"\n  Port details are listed under each device above.")
        
        # User notes summary - collect all nodes with notes (excluding groups)
        nodes_with_notes = []
        for node_id, node in nodes.items():
            # Skip group nodes
            node_role = node.get("role", "")
            if isinstance(node_role, str) and node_role.lower() == "group":
                continue
            
            if node.get("notes"):
                nodes_with_notes.append({
                    "name": node.get("name", node_id),
                    "ip": node.get("ip", "N/A"),
                    "notes": node.get("notes"),
                })
        
        if nodes_with_notes:
            lines.append(f"\n📝 USER NOTES")
            lines.append("-" * 40)
            for node_info in nodes_with_notes:
                lines.append(f"  {node_info['name']} ({node_info['ip']}):")
                # Handle multi-line notes
                note_lines = node_info['notes'].strip().split('\n')
                for note_line in note_lines:
                    lines.append(f"    {note_line}")
        
        lines.append("\n" + "=" * 60)
        
        context = "\n".join(lines)
        
        # Build summary
        summary = {
            "total_nodes": total,
            "healthy_nodes": healthy,
            "unhealthy_nodes": unhealthy,
            "gateway_count": len(gateways),
            "snapshot_timestamp": timestamp,
            "context_tokens_estimate": len(context) // 4,  # Rough estimate
        }
        
        # Update per-network cache
        self._context_cache[network_id] = (context, summary, now)
        
        return context, summary
    
    def _build_loading_context(self) -> tuple[str, dict[str, Any]]:
        """Build context when waiting for initial snapshot"""
        context = """
========================================
NETWORK TOPOLOGY INFORMATION
========================================

⏳ Network data is loading...

The network monitoring system is starting up and collecting initial data.
This typically takes 30-60 seconds after first launch.

I can still help answer general networking questions while we wait.
Once the network scan completes, I'll have full visibility into your topology.
========================================
"""
        summary = {
            "total_nodes": 0,
            "healthy_nodes": 0,
            "unhealthy_nodes": 0,
            "gateway_count": 0,
            "snapshot_timestamp": None,
            "context_tokens_estimate": len(context) // 4,
            "loading": True,
        }
        return context.strip(), summary
    
    def _build_fallback_context(self) -> tuple[str, dict[str, Any]]:
        """Build fallback context when metrics service is unavailable"""
        context = """
========================================
NETWORK TOPOLOGY INFORMATION
========================================

⚠️ Network data is temporarily unavailable.

The metrics service may be restarting or experiencing issues.
Previous network data should be restored shortly.

I can still help answer general networking questions or provide guidance
based on the information you provide directly.
========================================
"""
        summary = {
            "total_nodes": 0,
            "healthy_nodes": 0,
            "unhealthy_nodes": 0,
            "gateway_count": 0,
            "snapshot_timestamp": None,
            "context_tokens_estimate": len(context) // 4,
            "unavailable": True,
        }
        return context.strip(), summary
    
    def clear_cache(self, network_id: str | None = None):
        """Clear the cached context for a specific network or all networks.
        
        Args:
            network_id: If provided, only clear cache for this network.
                       If None, clears all cached contexts.
        """
        if network_id is not None:
            self._context_cache.pop(network_id, None)
        else:
            self._context_cache.clear()
    
    def reset_state(self, network_id: str | None = None):
        """Reset all state including snapshot availability.
        
        Args:
            network_id: If provided, only reset state for this network.
                       If None, resets all state.
        """
        self.clear_cache(network_id)
        if network_id is not None:
            self._snapshot_available.pop(network_id, None)
        else:
            self._snapshot_available.clear()
        self._last_check_time = None
    
    def get_status(self, network_id: str | None = None) -> dict[str, Any]:
        """Get current service status.
        
        Args:
            network_id: If provided, get status for specific network.
                       If None, returns overall status.
        """
        if network_id is not None:
            # Status for specific network
            cache_entry = self._context_cache.get(network_id)
            return {
                "network_id": network_id,
                "snapshot_available": self._snapshot_available.get(network_id, False),
                "cached": cache_entry is not None,
                "last_check": self._last_check_time.isoformat() if self._last_check_time else None,
                "cache_age_seconds": (
                    (datetime.utcnow() - cache_entry[2]).total_seconds()
                    if cache_entry else None
                ),
            }
        else:
            # Overall status (backwards compatible)
            any_snapshot_available = any(self._snapshot_available.values()) if self._snapshot_available else False
            any_cached = len(self._context_cache) > 0
            return {
                "snapshot_available": any_snapshot_available,
                "cached": any_cached,
                "cached_networks": list(self._context_cache.keys()),
                "available_networks": [k for k, v in self._snapshot_available.items() if v],
                "last_check": self._last_check_time.isoformat() if self._last_check_time else None,
            }


# Singleton instance
metrics_context_service = MetricsContextService()
