"""
Notification reporter service.

Reports health check results to the notification service for
anomaly detection and alerting.
"""

import os
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# Notification service URL
NOTIFICATION_SERVICE_URL = os.environ.get("NOTIFICATION_SERVICE_URL", "http://localhost:8005")

# Track previous states for state change detection
_previous_states: Dict[str, str] = {}


async def report_health_check(
    device_ip: str,
    success: bool,
    latency_ms: Optional[float] = None,
    packet_loss: Optional[float] = None,
    device_name: Optional[str] = None,
) -> bool:
    """
    Report a health check result to the notification service.
    
    This enables:
    - ML-based anomaly detection
    - Automatic notification dispatch
    
    Returns True if successfully reported, False otherwise.
    """
    global _previous_states
    
    # Get previous state for this device
    previous_state = _previous_states.get(device_ip)
    
    # Update tracked state
    current_state = "online" if success else "offline"
    _previous_states[device_ip] = current_state
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            params = {
                "device_ip": device_ip,
                "success": success,
            }
            
            if latency_ms is not None:
                params["latency_ms"] = latency_ms
            if packet_loss is not None:
                params["packet_loss"] = packet_loss
            if device_name is not None:
                params["device_name"] = device_name
            if previous_state is not None:
                params["previous_state"] = previous_state
            
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/api/notifications/process-health-check",
                params=params,
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Notification service returned {response.status_code}: {response.text}")
                return False
                
    except httpx.ConnectError:
        logger.debug("Notification service not available")
        return False
    except Exception as e:
        logger.warning(f"Failed to report health check to notification service: {e}")
        return False


async def report_health_checks_batch(
    results: Dict[str, tuple],  # ip -> (success, latency_ms, packet_loss, device_name)
) -> int:
    """
    Report multiple health check results in parallel.
    
    Returns the number of successfully reported checks.
    """
    tasks = []
    for device_ip, (success, latency_ms, packet_loss, device_name) in results.items():
        tasks.append(report_health_check(
            device_ip=device_ip,
            success=success,
            latency_ms=latency_ms,
            packet_loss=packet_loss,
            device_name=device_name,
        ))
    
    results = await asyncio.gather(*tasks)
    return sum(1 for r in results if r)


def clear_state_tracking():
    """Clear tracked device states (for testing/reset)"""
    global _previous_states
    _previous_states.clear()

