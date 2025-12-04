"""
Pydantic models for the Metrics Service.

These models define the structure of network topology metrics
that are published to Redis for other services to consume.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    """Device health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DeviceRole(str, Enum):
    """Device role in the network topology"""
    GATEWAY_ROUTER = "gateway/router"
    SWITCH_AP = "switch/ap"
    FIREWALL = "firewall"
    SERVER = "server"
    SERVICE = "service"
    NAS = "nas"
    CLIENT = "client"
    UNKNOWN = "unknown"
    GROUP = "group"


# ==================== Connectivity Metrics ====================

class PingMetrics(BaseModel):
    """Ping/latency metrics for a device"""
    success: bool
    latency_ms: Optional[float] = None
    packet_loss_percent: float = 0.0
    min_latency_ms: Optional[float] = None
    max_latency_ms: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None


class DnsMetrics(BaseModel):
    """DNS resolution metrics"""
    success: bool
    resolved_hostname: Optional[str] = None
    reverse_dns: Optional[str] = None
    resolution_time_ms: Optional[float] = None


class PortInfo(BaseModel):
    """Open port information"""
    port: int
    open: bool
    service: Optional[str] = None
    response_time_ms: Optional[float] = None


# ==================== Uptime Metrics ====================

class UptimeMetrics(BaseModel):
    """24-hour uptime statistics"""
    uptime_percent_24h: Optional[float] = None
    avg_latency_24h_ms: Optional[float] = None
    checks_passed_24h: int = 0
    checks_failed_24h: int = 0
    last_seen_online: Optional[datetime] = None
    consecutive_failures: int = 0


class CheckHistoryEntry(BaseModel):
    """Single health check history entry"""
    timestamp: datetime
    success: bool
    latency_ms: Optional[float] = None


# ==================== ISP / Speed Test Metrics ====================

class SpeedTestMetrics(BaseModel):
    """ISP speed test results"""
    success: bool
    timestamp: datetime
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    ping_ms: Optional[float] = None
    server_name: Optional[str] = None
    server_location: Optional[str] = None
    server_sponsor: Optional[str] = None
    client_ip: Optional[str] = None
    client_isp: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None


class TestIPMetrics(BaseModel):
    """Metrics for a gateway test IP (external connectivity test)"""
    ip: str
    label: Optional[str] = None
    status: HealthStatus
    last_check: Optional[datetime] = None
    ping: Optional[PingMetrics] = None
    uptime: Optional[UptimeMetrics] = None
    check_history: List[CheckHistoryEntry] = []


class GatewayISPInfo(BaseModel):
    """ISP information for a gateway device"""
    gateway_ip: str
    test_ips: List[TestIPMetrics] = []
    last_speed_test: Optional[SpeedTestMetrics] = None
    last_speed_test_timestamp: Optional[datetime] = None


# ==================== LAN Port Metrics ====================

class PortType(str, Enum):
    """Physical port type"""
    RJ45 = "rj45"
    SFP = "sfp"
    SFP_PLUS = "sfp+"


class PortStatus(str, Enum):
    """Port status"""
    ACTIVE = "active"
    UNUSED = "unused"
    BLOCKED = "blocked"  # Does not exist or permanently disabled


class PoeStatus(str, Enum):
    """Power over Ethernet status"""
    OFF = "off"
    POE = "poe"      # 802.3af - 15W
    POE_PLUS = "poe+"  # 802.3at - 30W
    POE_PLUS_PLUS = "poe++"  # 802.3bt - 60W+


class LanPort(BaseModel):
    """Individual LAN port configuration and status"""
    # Position in the grid (1-indexed)
    row: int
    col: int
    
    # Port configuration
    port_number: Optional[int] = None  # Optional port label/number
    type: PortType = PortType.RJ45
    status: PortStatus = PortStatus.UNUSED
    
    # Speed configuration
    speed: Optional[str] = None  # Configured speed (e.g., "1G", "10G")
    negotiated_speed: Optional[str] = None  # Actual negotiated speed
    
    # PoE configuration
    poe: Optional[PoeStatus] = None
    
    # Connection info
    connected_device_id: Optional[str] = None
    connected_device_name: Optional[str] = None
    connection_label: Optional[str] = None


class LanPortsConfig(BaseModel):
    """LAN ports configuration for a network device"""
    # Grid dimensions
    rows: int
    cols: int
    
    # Port definitions
    ports: List[LanPort] = []
    
    # Display options
    label_format: Optional[str] = "numeric"  # "numeric", "alpha", or "custom"
    start_number: int = 1


# ==================== Node Connection Metrics ====================

class NodeConnection(BaseModel):
    """Connection information between two nodes"""
    source_id: str
    target_id: str
    connection_speed: Optional[str] = None  # e.g., "1GbE", "10GbE", "WiFi"
    latency_ms: Optional[float] = None  # Measured latency between nodes


class ConnectionSpeedInfo(BaseModel):
    """Speed information for a connection"""
    speed_label: str  # e.g., "1GbE", "10GbE", "WiFi 6"
    speed_mbps: Optional[float] = None  # Measured speed in Mbps
    last_measured: Optional[datetime] = None


# ==================== Node Metrics ====================

class NodeMetrics(BaseModel):
    """Complete metrics for a single network node"""
    # Identity
    id: str
    name: str
    ip: Optional[str] = None
    hostname: Optional[str] = None
    role: Optional[DeviceRole] = None
    
    # Topology
    parent_id: Optional[str] = None
    connection_speed: Optional[str] = None
    depth: int = 0
    
    # Health status
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[datetime] = None
    
    # Connectivity metrics
    ping: Optional[PingMetrics] = None
    dns: Optional[DnsMetrics] = None
    open_ports: List[PortInfo] = []
    
    # Uptime metrics
    uptime: Optional[UptimeMetrics] = None
    check_history: List[CheckHistoryEntry] = []
    
    # User notes
    notes: Optional[str] = None
    
    # Version info
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: Optional[int] = None
    
    # ISP info (for gateway devices)
    isp_info: Optional[GatewayISPInfo] = None
    
    # LAN port configuration (for switches, routers, servers)
    lan_ports: Optional[LanPortsConfig] = None
    
    # Monitoring config
    monitoring_enabled: bool = True


# ==================== Network Topology Snapshot ====================

class NetworkTopologySnapshot(BaseModel):
    """
    Complete network topology snapshot.
    This is the main event published to Redis.
    """
    # Metadata
    snapshot_id: str = Field(description="Unique identifier for this snapshot")
    timestamp: datetime = Field(description="When this snapshot was taken")
    version: int = Field(default=1, description="Schema version for backwards compatibility")
    
    # Network summary
    total_nodes: int = 0
    healthy_nodes: int = 0
    degraded_nodes: int = 0
    unhealthy_nodes: int = 0
    unknown_nodes: int = 0
    
    # All nodes with their metrics
    nodes: Dict[str, NodeMetrics] = Field(default_factory=dict, description="Map of node ID to NodeMetrics")
    
    # Connection graph
    connections: List[NodeConnection] = Field(default_factory=list, description="All connections between nodes")
    
    # Gateway/ISP information
    gateways: List[GatewayISPInfo] = Field(default_factory=list, description="ISP info for all gateway devices")
    
    # Root node ID (for tree representation)
    root_node_id: Optional[str] = None


# ==================== Event Types ====================

class MetricsEventType(str, Enum):
    """Types of metrics events published to Redis"""
    FULL_SNAPSHOT = "full_snapshot"  # Complete topology snapshot
    NODE_UPDATE = "node_update"  # Single node update
    HEALTH_UPDATE = "health_update"  # Health status change
    SPEED_TEST_RESULT = "speed_test_result"  # New speed test result
    CONNECTIVITY_CHANGE = "connectivity_change"  # Node connectivity changed


class MetricsEvent(BaseModel):
    """Base event structure for Redis pub/sub"""
    event_type: MetricsEventType
    timestamp: datetime
    payload: Dict[str, Any]


class SubscriptionRequest(BaseModel):
    """Request to subscribe to metrics events"""
    channels: List[str] = Field(default=["metrics:topology"], description="Redis channels to subscribe to")


class PublishConfig(BaseModel):
    """Configuration for metrics publishing"""
    enabled: bool = True
    publish_interval_seconds: int = 30
    include_history: bool = True
    history_hours: int = 24
    channels: List[str] = Field(default=["metrics:topology"])
