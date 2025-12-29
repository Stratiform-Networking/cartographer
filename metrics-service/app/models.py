"""
Pydantic models for the Metrics Service.

These models define the structure of network topology metrics
that are published to Redis for other services to consume.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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
    latency_ms: float | None = None
    packet_loss_percent: float = 0.0
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    avg_latency_ms: float | None = None
    jitter_ms: float | None = None


class DnsMetrics(BaseModel):
    """DNS resolution metrics"""
    success: bool
    resolved_hostname: str | None = None
    reverse_dns: str | None = None
    resolution_time_ms: float | None = None


class PortInfo(BaseModel):
    """Open port information"""
    port: int
    open: bool
    service: str | None = None
    response_time_ms: float | None = None


# ==================== Uptime Metrics ====================

class UptimeMetrics(BaseModel):
    """24-hour uptime statistics"""
    uptime_percent_24h: float | None = None
    avg_latency_24h_ms: float | None = None
    checks_passed_24h: int = 0
    checks_failed_24h: int = 0
    last_seen_online: datetime | None = None
    consecutive_failures: int = 0


class CheckHistoryEntry(BaseModel):
    """Single health check history entry"""
    timestamp: datetime
    success: bool
    latency_ms: float | None = None


# ==================== ISP / Speed Test Metrics ====================

class SpeedTestMetrics(BaseModel):
    """ISP speed test results"""
    success: bool
    timestamp: datetime
    download_mbps: float | None = None
    upload_mbps: float | None = None
    ping_ms: float | None = None
    server_name: str | None = None
    server_location: str | None = None
    server_sponsor: str | None = None
    client_ip: str | None = None
    client_isp: str | None = None
    error_message: str | None = None
    duration_seconds: float | None = None


class TestIPMetrics(BaseModel):
    """Metrics for a gateway test IP (external connectivity test)"""
    ip: str
    label: str | None = None
    status: HealthStatus
    last_check: datetime | None = None
    ping: PingMetrics | None = None
    uptime: UptimeMetrics | None = None
    check_history: list[CheckHistoryEntry] = []


class GatewayISPInfo(BaseModel):
    """ISP information for a gateway device"""
    gateway_ip: str
    test_ips: list[TestIPMetrics] = []
    last_speed_test: SpeedTestMetrics | None = None
    last_speed_test_timestamp: datetime | None = None


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
    port_number: int | None = None  # Optional port label/number
    type: PortType = PortType.RJ45
    status: PortStatus = PortStatus.UNUSED
    
    # Speed configuration
    speed: str | None = None  # Configured speed (e.g., "1G", "10G")
    negotiated_speed: str | None = None  # Actual negotiated speed
    
    # PoE configuration
    poe: PoeStatus | None = None
    
    # Connection info
    connected_device_id: str | None = None
    connected_device_name: str | None = None
    connection_label: str | None = None


class LanPortsConfig(BaseModel):
    """LAN ports configuration for a network device"""
    # Grid dimensions
    rows: int
    cols: int
    
    # Port definitions
    ports: list[LanPort] = []
    
    # Display options
    label_format: str | None = "numeric"  # "numeric", "alpha", or "custom"
    start_number: int = 1


# ==================== Node Connection Metrics ====================

class NodeConnection(BaseModel):
    """Connection information between two nodes"""
    source_id: str
    target_id: str
    connection_speed: str | None = None  # e.g., "1GbE", "10GbE", "WiFi"
    latency_ms: float | None = None  # Measured latency between nodes


class ConnectionSpeedInfo(BaseModel):
    """Speed information for a connection"""
    speed_label: str  # e.g., "1GbE", "10GbE", "WiFi 6"
    speed_mbps: float | None = None  # Measured speed in Mbps
    last_measured: datetime | None = None


# ==================== Node Metrics ====================

class NodeMetrics(BaseModel):
    """Complete metrics for a single network node"""
    # Identity
    id: str
    name: str
    ip: str | None = None
    hostname: str | None = None
    role: DeviceRole | None = None
    
    # Topology
    parent_id: str | None = None
    connection_speed: str | None = None
    depth: int = 0
    
    # Health status
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: datetime | None = None
    
    # Connectivity metrics
    ping: PingMetrics | None = None
    dns: DnsMetrics | None = None
    open_ports: list[PortInfo] = []
    
    # Uptime metrics
    uptime: UptimeMetrics | None = None
    check_history: list[CheckHistoryEntry] = []
    
    # User notes
    notes: str | None = None
    
    # Version info
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int | None = None
    
    # ISP info (for gateway devices)
    isp_info: GatewayISPInfo | None = None
    
    # LAN port configuration (for switches, routers, servers)
    lan_ports: LanPortsConfig | None = None
    
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
    nodes: dict[str, NodeMetrics] = Field(default_factory=dict, description="Map of node ID to NodeMetrics")
    
    # Connection graph
    connections: list[NodeConnection] = Field(default_factory=list, description="All connections between nodes")
    
    # Gateway/ISP information
    gateways: list[GatewayISPInfo] = Field(default_factory=list, description="ISP info for all gateway devices")
    
    # Root node ID (for tree representation)
    root_node_id: str | None = None


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
    payload: dict[str, Any]


class SubscriptionRequest(BaseModel):
    """Request to subscribe to metrics events"""
    channels: list[str] = Field(default=["metrics:topology"], description="Redis channels to subscribe to")


class PublishConfig(BaseModel):
    """Configuration for metrics publishing"""
    enabled: bool = True
    publish_interval_seconds: int = 30
    include_history: bool = True
    history_hours: int = 24
    channels: list[str] = Field(default=["metrics:topology"])


# ==================== Endpoint Usage Statistics ====================

class EndpointUsage(BaseModel):
    """Usage statistics for a single endpoint"""
    endpoint: str = Field(description="The endpoint path (e.g., /api/health/status)")
    method: str = Field(description="HTTP method (GET, POST, etc.)")
    service: str = Field(description="Service name (e.g., health-service)")
    request_count: int = Field(default=0, description="Total number of requests")
    success_count: int = Field(default=0, description="Number of successful responses (2xx)")
    error_count: int = Field(default=0, description="Number of error responses (4xx, 5xx)")
    total_response_time_ms: float = Field(default=0.0, description="Sum of response times in ms")
    avg_response_time_ms: float | None = Field(default=None, description="Average response time in ms")
    min_response_time_ms: float | None = Field(default=None, description="Minimum response time in ms")
    max_response_time_ms: float | None = Field(default=None, description="Maximum response time in ms")
    last_accessed: datetime | None = Field(default=None, description="Last access timestamp")
    first_accessed: datetime | None = Field(default=None, description="First access timestamp")
    status_codes: dict[str, int] = Field(default_factory=dict, description="Count by status code")


class EndpointUsageRecord(BaseModel):
    """A single request record to be sent to the metrics service"""
    endpoint: str
    method: str
    service: str
    status_code: int
    response_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceUsageSummary(BaseModel):
    """Aggregated usage statistics for a service"""
    service: str
    total_requests: int = 0
    total_successes: int = 0
    total_errors: int = 0
    avg_response_time_ms: float | None = None
    endpoints: list[EndpointUsage] = []
    last_updated: datetime | None = None


class UsageStatsResponse(BaseModel):
    """Response containing usage statistics"""
    services: dict[str, ServiceUsageSummary] = Field(default_factory=dict)
    total_requests: int = 0
    total_services: int = 0
    collection_started: datetime | None = None
    last_updated: datetime | None = None


class UsageRecordBatch(BaseModel):
    """Batch of usage records for efficient reporting"""
    records: list[EndpointUsageRecord]
