from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PingResult(BaseModel):
    """Result of a ping/ICMP check"""
    success: bool
    latency_ms: Optional[float] = None
    packet_loss_percent: float = 0.0
    min_latency_ms: Optional[float] = None
    max_latency_ms: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None


class DnsResult(BaseModel):
    """Result of DNS resolution check"""
    success: bool
    resolved_hostname: Optional[str] = None
    reverse_dns: Optional[str] = None
    resolution_time_ms: Optional[float] = None


class PortCheckResult(BaseModel):
    """Result of a port check"""
    port: int
    open: bool
    service: Optional[str] = None
    response_time_ms: Optional[float] = None


class CheckHistoryEntry(BaseModel):
    """A single health check result in history"""
    timestamp: datetime
    success: bool
    latency_ms: Optional[float] = None


class DeviceMetrics(BaseModel):
    """Comprehensive metrics for a device"""
    ip: str
    status: HealthStatus
    last_check: datetime
    
    # Ping metrics
    ping: Optional[PingResult] = None
    
    # DNS metrics
    dns: Optional[DnsResult] = None
    
    # Open ports discovered
    open_ports: List[PortCheckResult] = []
    
    # Historical data
    uptime_percent_24h: Optional[float] = None
    avg_latency_24h_ms: Optional[float] = None
    checks_passed_24h: int = 0
    checks_failed_24h: int = 0
    check_history: List[CheckHistoryEntry] = []  # Recent check history for timeline display
    
    # Additional info
    last_seen_online: Optional[datetime] = None
    consecutive_failures: int = 0
    error_message: Optional[str] = None


class HealthCheckRequest(BaseModel):
    """Request to check health of specific IPs"""
    ips: List[str]
    include_ports: bool = False
    include_dns: bool = True


class BatchHealthResponse(BaseModel):
    """Response with health data for multiple devices"""
    devices: dict[str, DeviceMetrics]
    check_timestamp: datetime


class DeviceToMonitor(BaseModel):
    """Device registered for monitoring"""
    ip: str
    hostname: Optional[str] = None


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
    monitored_devices: List[str]
    last_check: Optional[datetime] = None
    next_check: Optional[datetime] = None


class RegisterDevicesRequest(BaseModel):
    """Request to register devices for monitoring"""
    ips: List[str]
    network_id: str  # UUID string - the network these devices belong to


# ==================== Gateway Test IP Models ====================

class GatewayTestIP(BaseModel):
    """A test IP configured for a gateway device (for internet connectivity checks)"""
    ip: str
    label: Optional[str] = None  # Optional friendly name (e.g., "Google DNS", "Cloudflare")


class GatewayTestIPConfig(BaseModel):
    """Configuration for test IPs on a gateway"""
    gateway_ip: str
    test_ips: List[GatewayTestIP] = []
    enabled: bool = True


class GatewayTestIPMetrics(BaseModel):
    """Metrics for a single test IP"""
    ip: str
    label: Optional[str] = None
    status: HealthStatus
    last_check: datetime
    
    # Ping metrics
    ping: Optional[PingResult] = None
    
    # Historical data
    uptime_percent_24h: Optional[float] = None
    avg_latency_24h_ms: Optional[float] = None
    checks_passed_24h: int = 0
    checks_failed_24h: int = 0
    check_history: List[CheckHistoryEntry] = []
    
    # Additional info
    last_seen_online: Optional[datetime] = None
    consecutive_failures: int = 0


class GatewayTestIPsResponse(BaseModel):
    """Response with all test IP metrics for a gateway"""
    gateway_ip: str
    test_ips: List[GatewayTestIPMetrics] = []
    last_check: Optional[datetime] = None


class SetGatewayTestIPsRequest(BaseModel):
    """Request to set test IPs for a gateway"""
    gateway_ip: str
    test_ips: List[GatewayTestIP]


# ==================== Speed Test Models ====================

class SpeedTestResult(BaseModel):
    """Result of an ISP speed test"""
    success: bool
    timestamp: datetime
    
    # Speed results (in Mbps)
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    
    # Ping to speed test server
    ping_ms: Optional[float] = None
    
    # Server info
    server_name: Optional[str] = None
    server_location: Optional[str] = None
    server_sponsor: Optional[str] = None
    
    # Client info
    client_ip: Optional[str] = None
    client_isp: Optional[str] = None
    
    # Error info (if failed)
    error_message: Optional[str] = None
    
    # Duration of the test
    duration_seconds: Optional[float] = None

