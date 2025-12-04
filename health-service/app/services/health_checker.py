import asyncio
import socket
import time
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from collections import deque
import logging

from ..models import (
    DeviceMetrics, 
    HealthStatus, 
    PingResult, 
    DnsResult, 
    PortCheckResult,
    CheckHistoryEntry,
    MonitoringConfig,
    MonitoringStatus,
    GatewayTestIP,
    GatewayTestIPConfig,
    GatewayTestIPMetrics,
    GatewayTestIPsResponse,
    SpeedTestResult,
)
from .notification_reporter import report_health_check

logger = logging.getLogger(__name__)

# Data persistence directory
DATA_DIR = Path(os.environ.get("HEALTH_DATA_DIR", "/app/data"))
GATEWAY_TEST_IPS_FILE = DATA_DIR / "gateway_test_ips.json"
SPEED_TEST_RESULTS_FILE = DATA_DIR / "speed_test_results.json"

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
        
        # Gateway test IP state
        self._gateway_test_ips: Dict[str, GatewayTestIPConfig] = {}  # gateway_ip -> config
        self._test_ip_metrics_cache: Dict[str, Dict[str, GatewayTestIPMetrics]] = {}  # gateway_ip -> {test_ip -> metrics}
        self._test_ip_history: Dict[str, deque] = {}  # "gateway_ip:test_ip" -> deque of (timestamp, success, latency)
        
        # Speed test results storage
        self._speed_test_results: Dict[str, SpeedTestResult] = {}  # gateway_ip -> last result
        
        # Load persisted data
        self._load_gateway_test_ips()
        self._load_speed_test_results()
    
    def _save_gateway_test_ips(self) -> None:
        """Save gateway test IP configurations to disk"""
        try:
            # Ensure data directory exists
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            # Convert to serializable format
            data = {}
            for gateway_ip, config in self._gateway_test_ips.items():
                data[gateway_ip] = {
                    "gateway_ip": config.gateway_ip,
                    "test_ips": [{"ip": tip.ip, "label": tip.label} for tip in config.test_ips],
                    "enabled": config.enabled
                }
            
            # Write to file
            with open(GATEWAY_TEST_IPS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(data)} gateway test IP configurations to {GATEWAY_TEST_IPS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save gateway test IPs: {e}")
    
    def _load_gateway_test_ips(self) -> None:
        """Load gateway test IP configurations from disk"""
        try:
            if not GATEWAY_TEST_IPS_FILE.exists():
                logger.debug(f"No gateway test IPs file found at {GATEWAY_TEST_IPS_FILE}")
                return
            
            with open(GATEWAY_TEST_IPS_FILE, 'r') as f:
                data = json.load(f)
            
            # Convert back to model objects
            for gateway_ip, config_data in data.items():
                test_ips = [
                    GatewayTestIP(ip=tip["ip"], label=tip.get("label"))
                    for tip in config_data.get("test_ips", [])
                ]
                self._gateway_test_ips[gateway_ip] = GatewayTestIPConfig(
                    gateway_ip=config_data["gateway_ip"],
                    test_ips=test_ips,
                    enabled=config_data.get("enabled", True)
                )
            
            logger.info(f"Loaded {len(self._gateway_test_ips)} gateway test IP configurations from {GATEWAY_TEST_IPS_FILE}")
        except Exception as e:
            logger.error(f"Failed to load gateway test IPs: {e}")
    
    def _save_speed_test_results(self) -> None:
        """Save speed test results to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for gateway_ip, result in self._speed_test_results.items():
                data[gateway_ip] = result.model_dump(mode="json")
            
            with open(SPEED_TEST_RESULTS_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved {len(data)} speed test results to {SPEED_TEST_RESULTS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save speed test results: {e}")
    
    def _load_speed_test_results(self) -> None:
        """Load speed test results from disk"""
        try:
            if not SPEED_TEST_RESULTS_FILE.exists():
                logger.debug(f"No speed test results file found at {SPEED_TEST_RESULTS_FILE}")
                return
            
            with open(SPEED_TEST_RESULTS_FILE, 'r') as f:
                data = json.load(f)
            
            for gateway_ip, result_data in data.items():
                # Parse timestamp if string
                if isinstance(result_data.get("timestamp"), str):
                    result_data["timestamp"] = datetime.fromisoformat(result_data["timestamp"].replace("Z", "+00:00"))
                self._speed_test_results[gateway_ip] = SpeedTestResult(**result_data)
            
            logger.info(f"Loaded {len(self._speed_test_results)} speed test results from {SPEED_TEST_RESULTS_FILE}")
        except Exception as e:
            logger.error(f"Failed to load speed test results: {e}")
    
    def get_last_speed_test(self, gateway_ip: str) -> Optional[SpeedTestResult]:
        """Get the last speed test result for a gateway"""
        return self._speed_test_results.get(gateway_ip)
    
    def get_all_speed_tests(self) -> Dict[str, SpeedTestResult]:
        """Get all stored speed test results"""
        return self._speed_test_results.copy()
    
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
        
        # Report to notification service (async, fire-and-forget to not slow down checks)
        asyncio.create_task(report_health_check(
            device_ip=ip,
            success=ping_result.success,
            latency_ms=ping_result.avg_latency_ms,
            packet_loss=ping_result.packet_loss_percent / 100.0 if ping_result.packet_loss_percent else None,
            device_name=dns_result.resolved_hostname if dns_result and dns_result.resolved_hostname else None,
        ))
        
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
    
    # ==================== Gateway Test IP Methods ====================
    
    def set_gateway_test_ips(self, gateway_ip: str, test_ips: List[GatewayTestIP]) -> GatewayTestIPConfig:
        """Set test IPs for a gateway device"""
        config = GatewayTestIPConfig(
            gateway_ip=gateway_ip,
            test_ips=test_ips,
            enabled=True
        )
        self._gateway_test_ips[gateway_ip] = config
        
        # Initialize metrics cache for this gateway if not exists
        if gateway_ip not in self._test_ip_metrics_cache:
            self._test_ip_metrics_cache[gateway_ip] = {}
        
        # Persist to disk
        self._save_gateway_test_ips()
        
        logger.info(f"Set {len(test_ips)} test IPs for gateway {gateway_ip}")
        return config
    
    def get_gateway_test_ips(self, gateway_ip: str) -> Optional[GatewayTestIPConfig]:
        """Get test IP configuration for a gateway"""
        return self._gateway_test_ips.get(gateway_ip)
    
    def get_all_gateway_test_ips(self) -> Dict[str, GatewayTestIPConfig]:
        """Get all gateway test IP configurations"""
        return self._gateway_test_ips.copy()
    
    def remove_gateway_test_ips(self, gateway_ip: str) -> bool:
        """Remove test IPs configuration for a gateway"""
        if gateway_ip in self._gateway_test_ips:
            del self._gateway_test_ips[gateway_ip]
            if gateway_ip in self._test_ip_metrics_cache:
                del self._test_ip_metrics_cache[gateway_ip]
            # Persist to disk
            self._save_gateway_test_ips()
            logger.info(f"Removed test IPs for gateway {gateway_ip}")
            return True
        return False
    
    def _get_test_ip_history_key(self, gateway_ip: str, test_ip: str) -> str:
        """Generate unique key for test IP history"""
        return f"{gateway_ip}:{test_ip}"
    
    def _record_test_ip_check(self, gateway_ip: str, test_ip: str, success: bool, latency_ms: Optional[float]):
        """Record a test IP check result for historical tracking"""
        key = self._get_test_ip_history_key(gateway_ip, test_ip)
        if key not in self._test_ip_history:
            self._test_ip_history[key] = deque(maxlen=self._history_max_size)
        self._test_ip_history[key].append((datetime.utcnow(), success, latency_ms))
    
    def _calculate_test_ip_historical_stats(self, gateway_ip: str, test_ip: str) -> tuple[Optional[float], Optional[float], int, int]:
        """Calculate 24-hour historical statistics for a test IP"""
        key = self._get_test_ip_history_key(gateway_ip, test_ip)
        if key not in self._test_ip_history or len(self._test_ip_history[key]) == 0:
            return None, None, 0, 0
        
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = [(ts, success, lat) for ts, success, lat in self._test_ip_history[key] if ts > cutoff]
        
        if not recent:
            return None, None, 0, 0
        
        passed = sum(1 for _, s, _ in recent if s)
        failed = sum(1 for _, s, _ in recent if not s)
        
        latencies = [lat for _, _, lat in recent if lat is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else None
        
        uptime_percent = (passed / len(recent)) * 100 if recent else None
        
        return uptime_percent, avg_latency, passed, failed
    
    def _get_test_ip_check_history(self, gateway_ip: str, test_ip: str, hours: int = 24) -> List[CheckHistoryEntry]:
        """Get check history for a test IP"""
        key = self._get_test_ip_history_key(gateway_ip, test_ip)
        if key not in self._test_ip_history or len(self._test_ip_history[key]) == 0:
            return []
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        history = []
        
        for ts, success, latency in self._test_ip_history[key]:
            if ts > cutoff:
                history.append(CheckHistoryEntry(
                    timestamp=ts,
                    success=success,
                    latency_ms=latency
                ))
        
        return history
    
    async def check_test_ip(self, gateway_ip: str, test_ip: str, label: Optional[str] = None) -> GatewayTestIPMetrics:
        """Check a single test IP and return metrics"""
        now = datetime.utcnow()
        
        # Get cached metrics if available
        cached = self._test_ip_metrics_cache.get(gateway_ip, {}).get(test_ip)
        
        # Perform ping check
        ping_result = await self.ping_host(test_ip)
        
        # Record for historical tracking
        self._record_test_ip_check(gateway_ip, test_ip, ping_result.success, ping_result.avg_latency_ms)
        
        # Calculate historical stats
        uptime_24h, avg_lat_24h, passed_24h, failed_24h = self._calculate_test_ip_historical_stats(gateway_ip, test_ip)
        
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
        
        # Get check history
        check_history = self._get_test_ip_check_history(gateway_ip, test_ip)
        
        metrics = GatewayTestIPMetrics(
            ip=test_ip,
            label=label,
            status=status,
            last_check=now,
            ping=ping_result,
            uptime_percent_24h=uptime_24h,
            avg_latency_24h_ms=avg_lat_24h,
            checks_passed_24h=passed_24h,
            checks_failed_24h=failed_24h,
            check_history=check_history,
            last_seen_online=now if ping_result.success else (cached.last_seen_online if cached else None),
            consecutive_failures=consecutive_failures,
        )
        
        # Cache the results
        if gateway_ip not in self._test_ip_metrics_cache:
            self._test_ip_metrics_cache[gateway_ip] = {}
        self._test_ip_metrics_cache[gateway_ip][test_ip] = metrics
        
        return metrics
    
    async def check_gateway_test_ips(self, gateway_ip: str) -> GatewayTestIPsResponse:
        """Check all test IPs for a gateway"""
        config = self._gateway_test_ips.get(gateway_ip)
        if not config or not config.enabled:
            return GatewayTestIPsResponse(gateway_ip=gateway_ip, test_ips=[], last_check=None)
        
        # Check all test IPs in parallel
        tasks = [
            self.check_test_ip(gateway_ip, tip.ip, tip.label)
            for tip in config.test_ips
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        metrics_list = []
        for tip, result in zip(config.test_ips, results):
            if isinstance(result, Exception):
                logger.error(f"Test IP check failed for {tip.ip}: {result}")
                # Create a failed metrics entry
                metrics_list.append(GatewayTestIPMetrics(
                    ip=tip.ip,
                    label=tip.label,
                    status=HealthStatus.UNKNOWN,
                    last_check=datetime.utcnow(),
                ))
            else:
                metrics_list.append(result)
        
        return GatewayTestIPsResponse(
            gateway_ip=gateway_ip,
            test_ips=metrics_list,
            last_check=datetime.utcnow()
        )
    
    def get_cached_test_ip_metrics(self, gateway_ip: str) -> GatewayTestIPsResponse:
        """Get cached metrics for all test IPs of a gateway"""
        config = self._gateway_test_ips.get(gateway_ip)
        cached_metrics = self._test_ip_metrics_cache.get(gateway_ip, {})
        
        metrics_list = []
        if config:
            for tip in config.test_ips:
                if tip.ip in cached_metrics:
                    metrics_list.append(cached_metrics[tip.ip])
        
        # Determine last check time from metrics
        last_check = None
        if metrics_list:
            last_check = max(m.last_check for m in metrics_list)
        
        return GatewayTestIPsResponse(
            gateway_ip=gateway_ip,
            test_ips=metrics_list,
            last_check=last_check
        )
    
    # ==================== Speed Test ====================
    
    async def run_speed_test(self, gateway_ip: Optional[str] = None) -> SpeedTestResult:
        """
        Run an ISP speed test using speedtest-cli.
        This is a blocking operation that can take 30-60 seconds.
        
        Args:
            gateway_ip: Optional gateway IP to associate this test with
        """
        start_time = time.time()
        
        try:
            import speedtest
            
            logger.info("Starting speed test...")
            
            # Run speedtest in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def do_speed_test():
                st = speedtest.Speedtest()
                st.get_best_server()
                st.download()
                st.upload()
                return st.results.dict()
            
            # Run in thread pool executor
            results = await loop.run_in_executor(None, do_speed_test)
            
            duration = time.time() - start_time
            
            # Extract results
            download_mbps = results.get('download', 0) / 1_000_000  # Convert to Mbps
            upload_mbps = results.get('upload', 0) / 1_000_000  # Convert to Mbps
            ping_ms = results.get('ping', None)
            
            server = results.get('server', {})
            client = results.get('client', {})
            
            logger.info(f"Speed test completed: {download_mbps:.2f} Mbps down, {upload_mbps:.2f} Mbps up")
            
            result = SpeedTestResult(
                success=True,
                timestamp=datetime.utcnow(),
                download_mbps=round(download_mbps, 2),
                upload_mbps=round(upload_mbps, 2),
                ping_ms=ping_ms,
                server_name=server.get('name'),
                server_location=f"{server.get('city', '')}, {server.get('country', '')}".strip(', '),
                server_sponsor=server.get('sponsor'),
                client_ip=client.get('ip'),
                client_isp=client.get('isp'),
                duration_seconds=round(duration, 1)
            )
            
            # Store result if gateway_ip provided
            if gateway_ip:
                self._speed_test_results[gateway_ip] = result
                self._save_speed_test_results()
            
            return result
            
        except ImportError:
            logger.error("speedtest-cli not installed")
            return SpeedTestResult(
                success=False,
                timestamp=datetime.utcnow(),
                error_message="speedtest-cli is not installed",
                duration_seconds=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Speed test failed: {e}")
            return SpeedTestResult(
                success=False,
                timestamp=datetime.utcnow(),
                error_message=str(e),
                duration_seconds=time.time() - start_time
            )
    
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
        """Perform a single monitoring check of all registered devices and test IPs"""
        if not self._monitored_devices and not self._gateway_test_ips:
            return
        
        if self._is_checking:
            logger.warning("Previous check still in progress, skipping this cycle")
            return
        
        self._is_checking = True
        try:
            self._last_check_time = datetime.utcnow()
            
            # Check all devices in parallel
            if self._monitored_devices:
                logger.debug(f"Starting passive health check for {len(self._monitored_devices)} devices")
                await self.check_multiple_devices(
                    ips=list(self._monitored_devices),
                    include_ports=False,  # Don't scan ports during passive checks (too slow)
                    include_dns=self._monitoring_config.include_dns
                )
            
            # Check all gateway test IPs in parallel
            if self._gateway_test_ips:
                enabled_gateways = [gw for gw, config in self._gateway_test_ips.items() if config.enabled]
                if enabled_gateways:
                    logger.debug(f"Starting passive test IP check for {len(enabled_gateways)} gateways")
                    tasks = [self.check_gateway_test_ips(gw) for gw in enabled_gateways]
                    await asyncio.gather(*tasks, return_exceptions=True)
            
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

