"""
Service for fetching and formatting network context from the metrics service.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# Metrics service URL
METRICS_SERVICE_URL = os.environ.get("METRICS_SERVICE_URL", "http://localhost:8003")


class MetricsContextService:
    """Service to fetch network context from metrics service"""
    
    def __init__(self):
        self.timeout = 10.0
        self._cached_context: Optional[str] = None
        self._cached_summary: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 30  # Cache for 30 seconds
        
        # Loading state tracking
        self._snapshot_available = False
        self._last_check_time: Optional[datetime] = None
        self._check_interval_seconds = 5  # Recheck every 5 seconds when no snapshot
        self._max_wait_attempts = 6  # Max attempts when waiting for snapshot (30 seconds total)
    
    async def fetch_network_snapshot(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch the current network topology snapshot
        
        Args:
            force_refresh: If True, ask the metrics service to generate a fresh snapshot
                          instead of returning the cached one. Use this after data changes
                          (like a speed test) to get the latest data.
        """
        self._last_check_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if force_refresh:
                    # Ask metrics service to generate a fresh snapshot with latest data
                    response = await client.post(f"{METRICS_SERVICE_URL}/api/metrics/snapshot/generate")
                else:
                    response = await client.get(f"{METRICS_SERVICE_URL}/api/metrics/snapshot")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("snapshot"):
                        self._snapshot_available = True
                        return data["snapshot"]
                
                # Snapshot not yet available (service may be starting up)
                self._snapshot_available = False
                logger.info(f"Snapshot not yet available: {response.status_code}")
                return None
                
        except httpx.ConnectError:
            self._snapshot_available = False
            logger.warning(f"Cannot connect to metrics service at {METRICS_SERVICE_URL}")
            return None
        except Exception as e:
            self._snapshot_available = False
            logger.error(f"Error fetching network snapshot: {e}")
            return None
    
    async def wait_for_snapshot(self, max_attempts: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Wait for a snapshot to become available, retrying periodically.
        
        Args:
            max_attempts: Maximum number of attempts (defaults to self._max_wait_attempts)
            
        Returns:
            The snapshot if available, None if max attempts exceeded
        """
        attempts = max_attempts or self._max_wait_attempts
        
        for attempt in range(attempts):
            snapshot = await self.fetch_network_snapshot()
            if snapshot:
                logger.info(f"Snapshot available after {attempt + 1} attempt(s)")
                return snapshot
            
            if attempt < attempts - 1:
                logger.debug(f"Waiting for snapshot (attempt {attempt + 1}/{attempts})...")
                await asyncio.sleep(self._check_interval_seconds)
        
        logger.warning(f"Snapshot not available after {attempts} attempts")
        return None
    
    def is_snapshot_available(self) -> bool:
        """Check if a snapshot has ever been successfully fetched"""
        return self._snapshot_available
    
    def should_recheck(self) -> bool:
        """Check if we should try fetching the snapshot again"""
        if self._snapshot_available:
            return False
        
        if not self._last_check_time:
            return True
        
        elapsed = (datetime.utcnow() - self._last_check_time).total_seconds()
        return elapsed >= self._check_interval_seconds
    
    async def fetch_network_summary(self) -> Optional[Dict[str, Any]]:
        """Fetch network summary (lighter weight than full snapshot)"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{METRICS_SERVICE_URL}/api/metrics/summary")
                
                if response.status_code == 200:
                    return response.json()
                
                return None
                
        except Exception as e:
            logger.error(f"Error fetching network summary: {e}")
            return None
    
    def _format_node_info(self, node: Dict[str, Any]) -> str:
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
        
        # Notes
        if node.get("notes"):
            lines.append(f"    Notes: {node['notes']}")
        
        return "\n".join(lines)
    
    def _format_gateway_info(self, gateway: Dict[str, Any], nodes: Dict[str, Any]) -> str:
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
    
    async def build_context_string(self, wait_for_data: bool = True, force_refresh: bool = False) -> tuple[str, Dict[str, Any]]:
        """
        Build a context string for the AI assistant with network information.
        Returns (context_string, summary_dict)
        
        Args:
            wait_for_data: If True and no snapshot available, wait and retry
            force_refresh: If True, bypass cache and fetch fresh data from the metrics service.
                          This also triggers the metrics service to regenerate its snapshot.
        """
        # Check cache (skip if force_refresh)
        now = datetime.utcnow()
        if (
            not force_refresh and
            self._cached_context and 
            self._cache_timestamp and 
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds
        ):
            return self._cached_context, self._cached_summary or {}
        
        # Try to fetch snapshot (force regeneration if force_refresh)
        snapshot = await self.fetch_network_snapshot(force_refresh=force_refresh)
        
        # If no snapshot and we should wait, try waiting for it
        if not snapshot and wait_for_data and not self._snapshot_available:
            logger.info("No snapshot available yet, waiting for metrics service...")
            snapshot = await self.wait_for_snapshot(max_attempts=3)  # Wait up to 15 seconds
        
        if not snapshot:
            return self._build_loading_context() if not self._snapshot_available else self._build_fallback_context()
        
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
        nodes_by_role = {}
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
        
        # Update cache
        self._cached_context = context
        self._cached_summary = summary
        self._cache_timestamp = now
        
        return context, summary
    
    def _build_loading_context(self) -> tuple[str, Dict[str, Any]]:
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
    
    def _build_fallback_context(self) -> tuple[str, Dict[str, Any]]:
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
    
    def clear_cache(self):
        """Clear the cached context"""
        self._cached_context = None
        self._cached_summary = None
        self._cache_timestamp = None
    
    def reset_state(self):
        """Reset all state including snapshot availability"""
        self.clear_cache()
        self._snapshot_available = False
        self._last_check_time = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            "snapshot_available": self._snapshot_available,
            "cached": self._cached_context is not None,
            "last_check": self._last_check_time.isoformat() if self._last_check_time else None,
            "cache_age_seconds": (
                (datetime.utcnow() - self._cache_timestamp).total_seconds()
                if self._cache_timestamp else None
            ),
        }


# Singleton instance
metrics_context_service = MetricsContextService()
