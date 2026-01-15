"""
Agent sync schemas for receiving device data from Cartographer Agent.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SyncDevice(BaseModel):
    """Device discovered by the agent."""

    ip: str = Field(..., description="IP address of the device")
    mac: Optional[str] = Field(None, description="MAC address if available")
    hostname: Optional[str] = Field(None, description="Hostname if resolved")
    response_time_ms: Optional[float] = Field(None, description="Ping response time in ms")
    is_gateway: bool = Field(False, description="Whether this device is the gateway")


class NetworkInfo(BaseModel):
    """Network information from the agent."""

    subnet: Optional[str] = Field(None, description="Network subnet (e.g., 192.168.1.0/24)")
    interface: Optional[str] = Field(None, description="Network interface name")


class AgentSyncRequest(BaseModel):
    """Request body for agent scan sync."""

    timestamp: datetime = Field(..., description="When the scan was performed")
    scan_duration_ms: Optional[int] = Field(None, description="How long the scan took")
    devices: list[SyncDevice] = Field(default_factory=list, description="Discovered devices")
    network_info: Optional[NetworkInfo] = Field(None, description="Network information")


class AgentSyncResponse(BaseModel):
    """Response from agent sync."""

    success: bool
    devices_received: int
    devices_added: int = 0
    devices_updated: int = 0
    message: str = "Sync completed"


class HealthCheckResult(BaseModel):
    """Result of a single device health check."""

    ip: str = Field(..., description="IP address of the device")
    reachable: bool = Field(..., description="Whether the device responded to ping")
    response_time_ms: Optional[float] = Field(None, description="Response time in ms if reachable")


class AgentHealthCheckRequest(BaseModel):
    """Request body for agent health check upload."""

    timestamp: datetime = Field(..., description="When the health check was performed")
    results: list[HealthCheckResult] = Field(
        default_factory=list, description="Health check results"
    )


class AgentHealthCheckResponse(BaseModel):
    """Response from agent health check upload."""

    success: bool
    results_received: int
    results_applied: int = 0
    message: str = "Health check processed"
