from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PingResult(BaseModel):
    """Result of a ping/ICMP check"""

    success: bool
    latency_ms: float | None = None
    packet_loss_percent: float = 0.0
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    avg_latency_ms: float | None = None
    jitter_ms: float | None = None


class DnsResult(BaseModel):
    """Result of DNS resolution check"""

    success: bool
    resolved_hostname: str | None = None
    reverse_dns: str | None = None
    resolution_time_ms: float | None = None


class PortCheckResult(BaseModel):
    """Result of a port check"""

    port: int
    open: bool
    service: str | None = None
    response_time_ms: float | None = None


class CheckHistoryEntry(BaseModel):
    """A single health check result in history"""

    timestamp: datetime
    success: bool
    latency_ms: float | None = None


class DeviceMetrics(BaseModel):
    """Comprehensive metrics for a device"""

    ip: str
    status: HealthStatus
    last_check: datetime

    # Ping metrics
    ping: PingResult | None = None

    # DNS metrics
    dns: DnsResult | None = None

    # Open ports discovered
    open_ports: list[PortCheckResult] = []

    # Historical data
    uptime_percent_24h: float | None = None
    avg_latency_24h_ms: float | None = None
    checks_passed_24h: int = 0
    checks_failed_24h: int = 0
    check_history: list[CheckHistoryEntry] = []  # Recent check history for timeline display

    # Additional info
    last_seen_online: datetime | None = None
    consecutive_failures: int = 0
    error_message: str | None = None


class HealthCheckRequest(BaseModel):
    """Request to check health of specific IPs"""

    ips: list[str]
    include_ports: bool = False
    include_dns: bool = True


class BatchHealthResponse(BaseModel):
    """Response with health data for multiple devices"""

    devices: dict[str, DeviceMetrics]
    check_timestamp: datetime


class DeviceToMonitor(BaseModel):
    """Device registered for monitoring"""

    ip: str
    hostname: str | None = None


class MonitoringConfig(BaseModel):
    """Configuration for passive monitoring"""

    enabled: bool = True
    check_interval_seconds: int = 30
    include_dns: bool = True


class MonitoringStatus(BaseModel):
    """Current status of the monitoring system"""

    enabled: bool
    check_interval_seconds: int
    include_dns: bool
    monitored_devices: list[str]
    last_check: datetime | None = None
    next_check: datetime | None = None


class RegisterDevicesRequest(BaseModel):
    """Request to register devices for monitoring"""

    ips: list[str]
    network_id: str  # UUID string - the network these devices belong to


# ==================== Gateway Test IP Models ====================


class GatewayTestIP(BaseModel):
    """A test IP configured for a gateway device (for internet connectivity checks)"""

    ip: str
    label: str | None = None  # Optional friendly name (e.g., "Google DNS", "Cloudflare")


class GatewayTestIPConfig(BaseModel):
    """Configuration for test IPs on a gateway"""

    gateway_ip: str
    test_ips: list[GatewayTestIP] = []
    enabled: bool = True


class GatewayTestIPMetrics(BaseModel):
    """Metrics for a single test IP"""

    ip: str
    label: str | None = None
    status: HealthStatus
    last_check: datetime

    # Ping metrics
    ping: PingResult | None = None

    # Historical data
    uptime_percent_24h: float | None = None
    avg_latency_24h_ms: float | None = None
    checks_passed_24h: int = 0
    checks_failed_24h: int = 0
    check_history: list[CheckHistoryEntry] = []

    # Additional info
    last_seen_online: datetime | None = None
    consecutive_failures: int = 0


class GatewayTestIPsResponse(BaseModel):
    """Response with all test IP metrics for a gateway"""

    gateway_ip: str
    test_ips: list[GatewayTestIPMetrics] = []
    last_check: datetime | None = None


class SetGatewayTestIPsRequest(BaseModel):
    """Request to set test IPs for a gateway"""

    gateway_ip: str
    test_ips: list[GatewayTestIP]


# ==================== Agent Sync Models ====================


class AgentHealthResult(BaseModel):
    """Health check result from Cartographer Agent"""

    ip: str
    reachable: bool
    response_time_ms: float | None = None


class AgentSyncRequest(BaseModel):
    """Request from agent (via cloud) to update health cache"""

    timestamp: datetime
    network_id: str  # UUID string
    results: list[AgentHealthResult]


class AgentSyncResponse(BaseModel):
    """Response after processing agent health sync"""

    success: bool
    results_processed: int
    cache_updated: int
    message: str = "Sync completed"


# ==================== Speed Test Models ====================


class SpeedTestResult(BaseModel):
    """Result of an ISP speed test"""

    success: bool
    timestamp: datetime

    # Speed results (in Mbps)
    download_mbps: float | None = None
    upload_mbps: float | None = None

    # Ping to speed test server
    ping_ms: float | None = None

    # Server info
    server_name: str | None = None
    server_location: str | None = None
    server_sponsor: str | None = None

    # Client info
    client_ip: str | None = None
    client_isp: str | None = None

    # Error info (if failed)
    error_message: str | None = None

    # Duration of the test
    duration_seconds: float | None = None
