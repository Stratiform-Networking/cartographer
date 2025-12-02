import asyncio
import socket
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from collections import deque
import logging
import aiohttp

from ..models import (
    DeviceMetrics, 
    HealthStatus, 
    PingResult, 
    DnsResult, 
    PortCheckResult,
    CheckHistoryEntry,
    SpeedTestResult,
    MonitoringConfig,
    MonitoringStatus
)

logger = logging.getLogger(__name__)

# Common ports to check for different services
COMMON_PORTS = {
    22: "SSH",
    80: "HTTP", 
    443: "HTTPS",
    21: "FTP",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    110: "POP3",
    143: "IMAP",
    3389: "RDP",
    5900: "VNC",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
    445: "SMB",
    139: "NetBIOS",
}


class HealthChecker:
    """Service for checking device health and collecting metrics"""
    
    def __init__(self):
        self._metrics_cache: Dict[str, DeviceMetrics] = {}
        self._history: Dict[str, deque] = {}  # IP -> deque of (timestamp, success, latency)
        self._history_max_size = 1440  # 24 hours at 1-minute intervals
        
        # Background monitoring state
        self._monitored_devices: Set[str] = set()
        self._monitoring_config = MonitoringConfig()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._last_check_time: Optional[datetime] = None
        self._next_check_time: Optional[datetime] = None
        self._is_checking: bool = False
    
    def _record_check(self, ip: str, success: bool, latency_ms: Optional[float]):
        """Record a health check result for historical tracking"""
        if ip not in self._history:
            self._history[ip] = deque(maxlen=self._history_max_size)
        self._history[ip].append((datetime.utcnow(), success, latency_ms))
    
    def _calculate_historical_stats(self, ip: str) -> tuple[Optional[float], Optional[float], int, int]:
        """Calculate 24-hour historical statistics"""
        if ip not in self._history or len(self._history[ip]) == 0:
            return None, None, 0, 0
        
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = [(ts, success, lat) for ts, success, lat in self._history[ip] if ts > cutoff]
        
        if not recent:
            return None, None, 0, 0
        
        passed = sum(1 for _, s, _ in recent if s)
        failed = sum(1 for _, s, _ in recent if not s)
        
        latencies = [lat for _, _, lat in recent if lat is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else None
        
        uptime_percent = (passed / len(recent)) * 100 if recent else None
        
        return uptime_percent, avg_latency, passed, failed
    
    def _get_check_history(self, ip: str, hours: int = 24) -> List[CheckHistoryEntry]:
        """Get check history for timeline display"""
        if ip not in self._history or len(self._history[ip]) == 0:
            return []
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        history = []
        
        for ts, success, latency in self._history[ip]:
            if ts > cutoff:
                history.append(CheckHistoryEntry(
                    timestamp=ts,
                    success=success,
                    latency_ms=latency
                ))
        
        return history
    
    async def ping_host(self, ip: str, count: int = 3, timeout: float = 2.0) -> PingResult:
        """
        Ping a host and return results.
        Uses subprocess to run system ping for reliability.
        """
        try:
            # Use system ping command for reliability
            import subprocess
            
            # Build ping command (works on both Linux and macOS)
            cmd = ["ping", "-c", str(count), "-W", str(int(timeout)), ip]
            
            start_time = time.time()
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout * count + 5)
            
            output = stdout.decode('utf-8', errors='ignore')
            
            # Parse ping output
            latencies = []
            received = 0
            transmitted = count
            
            # Extract round-trip times from output
            import re
            
            # Match individual ping times: "time=X.XX ms" or "time=X ms"
            time_matches = re.findall(r'time[=<](\d+\.?\d*)\s*ms', output)
            latencies = [float(t) for t in time_matches]
            
            # Match packet statistics: "X packets transmitted, Y received"
            stats_match = re.search(r'(\d+)\s+packets?\s+transmitted.*?(\d+)\s+(?:packets?\s+)?received', output)
            if stats_match:
                transmitted = int(stats_match.group(1))
                received = int(stats_match.group(2))
            
            if latencies:
                min_lat = min(latencies)
                max_lat = max(latencies)
                avg_lat = sum(latencies) / len(latencies)
                
                # Calculate jitter (variance in latency)
                if len(latencies) > 1:
                    jitter = sum(abs(latencies[i] - latencies[i-1]) for i in range(1, len(latencies))) / (len(latencies) - 1)
                else:
                    jitter = 0.0
                
                packet_loss = ((transmitted - received) / transmitted) * 100 if transmitted > 0 else 100
                
                return PingResult(
                    success=received > 0,
                    latency_ms=avg_lat,
                    packet_loss_percent=packet_loss,
                    min_latency_ms=min_lat,
                    max_latency_ms=max_lat,
                    avg_latency_ms=avg_lat,
                    jitter_ms=jitter
                )
            else:
                return PingResult(
                    success=False,
                    packet_loss_percent=100.0
                )
                
        except asyncio.TimeoutError:
            return PingResult(success=False, packet_loss_percent=100.0)
        except Exception as e:
            logger.error(f"Ping failed for {ip}: {e}")
            return PingResult(success=False, packet_loss_percent=100.0)
    
    async def check_dns(self, ip: str) -> DnsResult:
        """Perform DNS resolution and reverse DNS lookup"""
        try:
            import dns.resolver
            import dns.reversename
            
            start_time = time.time()
            
            # Reverse DNS lookup
            reverse_name = None
            try:
                addr = dns.reversename.from_address(ip)
                answers = dns.resolver.resolve(addr, 'PTR')
                if answers:
                    reverse_name = str(answers[0]).rstrip('.')
            except Exception:
                pass
            
            resolution_time = (time.time() - start_time) * 1000
            
            # Also try socket reverse lookup as fallback
            resolved_hostname = None
            try:
                resolved_hostname = socket.gethostbyaddr(ip)[0]
            except Exception:
                pass
            
            return DnsResult(
                success=reverse_name is not None or resolved_hostname is not None,
                resolved_hostname=resolved_hostname,
                reverse_dns=reverse_name,
                resolution_time_ms=resolution_time
            )
        except Exception as e:
            logger.debug(f"DNS check failed for {ip}: {e}")
            return DnsResult(success=False)
    
    async def check_port(self, ip: str, port: int, timeout: float = 2.0) -> PortCheckResult:
        """Check if a specific port is open"""
        try:
            start_time = time.time()
            
            # Create socket and attempt connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            writer.close()
            await writer.wait_closed()
            
            return PortCheckResult(
                port=port,
                open=True,
                service=COMMON_PORTS.get(port),
                response_time_ms=response_time
            )
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return PortCheckResult(
                port=port,
                open=False,
                service=COMMON_PORTS.get(port)
            )
        except Exception:
            return PortCheckResult(
                port=port,
                open=False,
                service=COMMON_PORTS.get(port)
            )
    
    async def scan_common_ports(self, ip: str) -> List[PortCheckResult]:
        """Scan common ports on a device"""
        # Only scan a subset of common ports to keep it fast
        ports_to_scan = [22, 80, 443, 21, 23, 53, 3389, 445, 8080]
        
        tasks = [self.check_port(ip, port) for port in ports_to_scan]
        results = await asyncio.gather(*tasks)
        
        # Only return open ports
        return [r for r in results if r.open]
    
    async def run_speed_test(self) -> SpeedTestResult:
        """
        Run a speed test to measure internet download/upload speeds.
        Uses Cloudflare's speed test endpoints for reliable measurement.
        """
        result = SpeedTestResult(test_timestamp=datetime.utcnow())
        
        # Download test URLs (Cloudflare speed test endpoints)
        download_urls = [
            ("https://speed.cloudflare.com/__down?bytes=10000000", 10_000_000),  # 10MB
            ("https://speed.cloudflare.com/__down?bytes=1000000", 1_000_000),    # 1MB fallback
        ]
        
        # Upload test URL
        upload_url = "https://speed.cloudflare.com/__up"
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Download speed test
                for url, expected_bytes in download_urls:
                    try:
                        start_time = time.time()
                        bytes_received = 0
                        
                        async with session.get(url) as response:
                            if response.status == 200:
                                async for chunk in response.content.iter_chunked(8192):
                                    bytes_received += len(chunk)
                                
                                elapsed = time.time() - start_time
                                if elapsed > 0 and bytes_received > 0:
                                    # Calculate Mbps (megabits per second)
                                    result.download_mbps = round((bytes_received * 8) / (elapsed * 1_000_000), 2)
                                    result.test_server = "Cloudflare"
                                    logger.info(f"Speed test download: {result.download_mbps} Mbps ({bytes_received} bytes in {elapsed:.2f}s)")
                                    break
                    except asyncio.TimeoutError:
                        logger.warning(f"Download test timed out for {url}")
                        continue
                    except Exception as e:
                        logger.warning(f"Download test failed for {url}: {e}")
                        continue
                
                # Upload speed test (send 1MB of data)
                try:
                    upload_size = 1_000_000  # 1MB
                    upload_data = b'0' * upload_size
                    
                    start_time = time.time()
                    async with session.post(upload_url, data=upload_data) as response:
                        if response.status in (200, 201):
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                result.upload_mbps = round((upload_size * 8) / (elapsed * 1_000_000), 2)
                                logger.info(f"Speed test upload: {result.upload_mbps} Mbps")
                except asyncio.TimeoutError:
                    logger.warning("Upload test timed out")
                except Exception as e:
                    logger.warning(f"Upload test failed: {e}")
                    
        except Exception as e:
            error_msg = f"Speed test failed: {str(e)}"
            logger.error(error_msg)
            result.error = error_msg
        
        return result
    
    async def check_device_health(
        self, 
        ip: str, 
        include_ports: bool = False,
        include_dns: bool = True
    ) -> DeviceMetrics:
        """
        Perform a comprehensive health check on a device.
        """
        now = datetime.utcnow()
        
        # Get cached metrics or create new
        cached = self._metrics_cache.get(ip)
        
        # Perform ping check
        ping_result = await self.ping_host(ip)
        
        # Record for historical tracking
        self._record_check(ip, ping_result.success, ping_result.avg_latency_ms)
        
        # Calculate historical stats
        uptime_24h, avg_lat_24h, passed_24h, failed_24h = self._calculate_historical_stats(ip)
        
        # Determine health status
        if not ping_result.success:
            status = HealthStatus.UNHEALTHY
            consecutive_failures = (cached.consecutive_failures + 1) if cached else 1
        elif ping_result.packet_loss_percent > 50:
            status = HealthStatus.DEGRADED
            consecutive_failures = 0
        elif ping_result.avg_latency_ms and ping_result.avg_latency_ms > 200:
            status = HealthStatus.DEGRADED
            consecutive_failures = 0
        else:
            status = HealthStatus.HEALTHY
            consecutive_failures = 0
        
        # DNS check
        dns_result = None
        if include_dns:
            dns_result = await self.check_dns(ip)
        
        # Port scan (only if requested - can be slow)
        open_ports = []
        if include_ports:
            open_ports = await self.scan_common_ports(ip)
        
        # Get check history for timeline
        check_history = self._get_check_history(ip)
        
        # Build metrics object
        metrics = DeviceMetrics(
            ip=ip,
            status=status,
            last_check=now,
            ping=ping_result,
            dns=dns_result,
            open_ports=open_ports,
            uptime_percent_24h=uptime_24h,
            avg_latency_24h_ms=avg_lat_24h,
            checks_passed_24h=passed_24h,
            checks_failed_24h=failed_24h,
            check_history=check_history,
            last_seen_online=now if ping_result.success else (cached.last_seen_online if cached else None),
            consecutive_failures=consecutive_failures,
        )
        
        # Cache the results
        self._metrics_cache[ip] = metrics
        
        return metrics
    
    async def check_multiple_devices(
        self,
        ips: List[str],
        include_ports: bool = False,
        include_dns: bool = True
    ) -> Dict[str, DeviceMetrics]:
        """Check health of multiple devices in parallel"""
        tasks = [
            self.check_device_health(ip, include_ports, include_dns)
            for ip in ips
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        metrics_map = {}
        for ip, result in zip(ips, results):
            if isinstance(result, Exception):
                logger.error(f"Health check failed for {ip}: {result}")
                metrics_map[ip] = DeviceMetrics(
                    ip=ip,
                    status=HealthStatus.UNKNOWN,
                    last_check=datetime.utcnow(),
                    error_message=str(result)
                )
            else:
                metrics_map[ip] = result
        
        return metrics_map
    
    def get_cached_metrics(self, ip: str) -> Optional[DeviceMetrics]:
        """Get cached metrics for a device"""
        return self._metrics_cache.get(ip)
    
    def get_all_cached_metrics(self) -> Dict[str, DeviceMetrics]:
        """Get all cached metrics"""
        return self._metrics_cache.copy()
    
    def clear_cache(self):
        """Clear the metrics cache"""
        self._metrics_cache.clear()
        self._history.clear()
    
    # ==================== Background Monitoring ====================
    
    def register_devices(self, ips: List[str]) -> None:
        """Register devices to be monitored passively"""
        self._monitored_devices.update(ips)
        logger.info(f"Registered {len(ips)} devices for monitoring. Total: {len(self._monitored_devices)}")
    
    def unregister_devices(self, ips: List[str]) -> None:
        """Unregister devices from passive monitoring"""
        for ip in ips:
            self._monitored_devices.discard(ip)
        logger.info(f"Unregistered {len(ips)} devices. Remaining: {len(self._monitored_devices)}")
    
    def set_monitored_devices(self, ips: List[str]) -> None:
        """Set the full list of devices to monitor (replaces existing)"""
        self._monitored_devices = set(ips)
        logger.info(f"Set {len(self._monitored_devices)} devices for monitoring")
    
    def get_monitored_devices(self) -> List[str]:
        """Get list of currently monitored devices"""
        return list(self._monitored_devices)
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get current monitoring configuration"""
        return self._monitoring_config
    
    def set_monitoring_config(self, config: MonitoringConfig) -> None:
        """Update monitoring configuration"""
        self._monitoring_config = config
        logger.info(f"Updated monitoring config: interval={config.check_interval_seconds}s, enabled={config.enabled}")
        
        # Restart monitoring task if running to apply new interval
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            if config.enabled:
                self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    def get_monitoring_status(self) -> MonitoringStatus:
        """Get current monitoring status"""
        return MonitoringStatus(
            enabled=self._monitoring_config.enabled,
            check_interval_seconds=self._monitoring_config.check_interval_seconds,
            include_dns=self._monitoring_config.include_dns,
            monitored_devices=list(self._monitored_devices),
            last_check=self._last_check_time,
            next_check=self._next_check_time
        )
    
    async def _perform_monitoring_check(self) -> None:
        """Perform a single monitoring check of all registered devices"""
        if not self._monitored_devices:
            return
        
        if self._is_checking:
            logger.warning("Previous check still in progress, skipping this cycle")
            return
        
        self._is_checking = True
        try:
            logger.debug(f"Starting passive health check for {len(self._monitored_devices)} devices")
            self._last_check_time = datetime.utcnow()
            
            # Check all devices in parallel
            await self.check_multiple_devices(
                ips=list(self._monitored_devices),
                include_ports=False,  # Don't scan ports during passive checks (too slow)
                include_dns=self._monitoring_config.include_dns
            )
            
            logger.debug(f"Completed passive health check")
        except Exception as e:
            logger.error(f"Error during monitoring check: {e}")
        finally:
            self._is_checking = False
    
    async def _monitoring_loop(self) -> None:
        """Background loop that periodically checks all monitored devices"""
        logger.info("Starting background monitoring loop")
        
        while True:
            try:
                if self._monitoring_config.enabled and self._monitored_devices:
                    # Perform the check
                    await self._perform_monitoring_check()
                
                # Calculate next check time
                interval = self._monitoring_config.check_interval_seconds
                self._next_check_time = datetime.utcnow() + timedelta(seconds=interval)
                
                # Wait for next interval
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Wait a bit before retrying
    
    def start_monitoring(self) -> None:
        """Start the background monitoring task"""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Monitoring already running")
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Background monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the background monitoring task"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
            self._next_check_time = None
            logger.info("Background monitoring stopped")


# Singleton instance
health_checker = HealthChecker()

