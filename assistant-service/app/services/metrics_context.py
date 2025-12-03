"""
Service for fetching and formatting network context from the metrics service.
"""

import os
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
    
    async def fetch_network_snapshot(self) -> Optional[Dict[str, Any]]:
        """Fetch the current network topology snapshot"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{METRICS_SERVICE_URL}/api/metrics/snapshot")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("snapshot"):
                        return data["snapshot"]
                
                logger.warning(f"Failed to fetch snapshot: {response.status_code}")
                return None
                
        except httpx.ConnectError:
            logger.warning(f"Cannot connect to metrics service at {METRICS_SERVICE_URL}")
            return None
        except Exception as e:
            logger.error(f"Error fetching network snapshot: {e}")
            return None
    
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
            
            if download or upload:
                lines.append(f"    Speed Test: ↓{download:.1f} Mbps / ↑{upload:.1f} Mbps")
            if ping:
                lines.append(f"    ISP Latency: {ping:.1f}ms")
            
            isp = speed_test.get("client_isp")
            if isp:
                lines.append(f"    ISP: {isp}")
        
        # Include notes from the gateway node
        if gateway_node and gateway_node.get("notes"):
            notes = gateway_node.get("notes")
            lines.append(f"    Notes: {notes}")
        
        return "\n".join(lines)
    
    async def build_context_string(self) -> tuple[str, Dict[str, Any]]:
        """
        Build a context string for the AI assistant with network information.
        Returns (context_string, summary_dict)
        """
        # Check cache
        now = datetime.utcnow()
        if (
            self._cached_context and 
            self._cache_timestamp and 
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds
        ):
            return self._cached_context, self._cached_summary or {}
        
        snapshot = await self.fetch_network_snapshot()
        
        if not snapshot:
            return self._build_fallback_context()
        
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
        nodes = snapshot.get("nodes", {})
        nodes_by_role = {}
        for node_id, node in nodes.items():
            role = node.get("role", "unknown")
            # Normalize role string (handle both enum value and potential variations)
            if isinstance(role, str):
                role = role.lower()
            else:
                role = "unknown"
            
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
        
        # User notes summary - collect all nodes with notes
        nodes_with_notes = []
        for node_id, node in nodes.items():
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
    
    def _build_fallback_context(self) -> tuple[str, Dict[str, Any]]:
        """Build fallback context when metrics service is unavailable"""
        context = """
========================================
NETWORK TOPOLOGY INFORMATION
========================================

⚠️ Network data is currently unavailable.
The metrics service may be starting up or temporarily unreachable.

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
        }
        return context.strip(), summary
    
    def clear_cache(self):
        """Clear the cached context"""
        self._cached_context = None
        self._cached_summary = None
        self._cache_timestamp = None


# Singleton instance
metrics_context_service = MetricsContextService()
