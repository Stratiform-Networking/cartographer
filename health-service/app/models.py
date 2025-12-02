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


class SpeedTestResult(BaseModel):
    """Result of a speed test"""
    download_mbps: Optional[float] = None
    upload_mbps: Optional[float] = None
    test_server: Optional[str] = None
    test_timestamp: Optional[datetime] = None
    error: Optional[str] = None


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
    
    # Speed test results (for external IPs / internet connectivity)
    speed_test: Optional[SpeedTestResult] = None
    
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

