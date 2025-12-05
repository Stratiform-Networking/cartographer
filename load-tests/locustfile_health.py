"""
Load Test for Health Service (port 8001)

Tests health checking, monitoring, and speed test endpoints.

Authentication:
    Set environment variables before running:
    - LOADTEST_USERNAME: Username for authentication (default: admin)
    - LOADTEST_PASSWORD: Password for authentication (default: admin)
"""

import os
import random
from locust import HttpUser, task, between, tag, events


# Authentication credentials from environment variables
AUTH_USERNAME = os.environ.get("LOADTEST_USERNAME", "admin")
AUTH_PASSWORD = os.environ.get("LOADTEST_PASSWORD", "admin")

# Sample IPs for testing (using common private ranges)
SAMPLE_IPS = [
    "192.168.1.1",
    "192.168.1.100",
    "192.168.1.254",
    "10.0.0.1",
    "10.0.0.50",
    "172.16.0.1",
]

SAMPLE_GATEWAY_IPS = [
    "192.168.1.1",
    "10.0.0.1",
]


class AuthenticatedHealthUser(HttpUser):
    """
    Base class for authenticated health service users.
    """
    
    abstract = True
    access_token = None
    
    def on_start(self):
        """Authenticate before running tests"""
        # Health service is accessed via backend proxy, so login through auth endpoint
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": AUTH_USERNAME,
                "password": AUTH_PASSWORD
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            response.success()
        else:
            # Try direct health service (no auth needed for direct access)
            response.success()
    
    def _auth_headers(self):
        """Get headers with authorization token"""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers


class HealthServiceUser(AuthenticatedHealthUser):
    """
    Load test user for the Health Service.
    
    Run with:
        locust -f locustfile_health.py --host=http://localhost:8001
        
    Or via backend proxy:
        locust -f locustfile_health.py --host=http://localhost:8000
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    # ==================== Health Check Endpoints ====================
    
    @task(10)
    @tag("health-check", "read")
    def get_cached_metrics_all(self):
        """Get all cached metrics - high frequency read operation"""
        self.client.get("/api/health/cached", headers=self._auth_headers())
    
    @task(5)
    @tag("health-check", "read")
    def get_cached_metrics_single(self):
        """Get cached metrics for a single device"""
        ip = random.choice(SAMPLE_IPS)
        with self.client.get(
            f"/api/health/cached/{ip}",
            headers=self._auth_headers(),
            name="/api/health/cached/[ip]",
            catch_response=True
        ) as response:
            # 404 is acceptable if no cached data exists
            if response.status_code in [200, 404]:
                response.success()
    
    @task(3)
    @tag("health-check", "write")
    def check_single_device(self):
        """Check health of a single device - involves actual ping"""
        ip = random.choice(SAMPLE_IPS)
        with self.client.get(
            f"/api/health/check/{ip}?include_ports=false&include_dns=true",
            headers=self._auth_headers(),
            name="/api/health/check/[ip]",
            catch_response=True,
            timeout=30
        ) as response:
            # Allow various status codes since device might not exist
            if response.status_code in [200, 500]:
                response.success()
    
    @task(2)
    @tag("health-check", "write")
    def check_batch_devices(self):
        """Check multiple devices at once"""
        ips = random.sample(SAMPLE_IPS, min(3, len(SAMPLE_IPS)))
        with self.client.post(
            "/api/health/check/batch",
            headers=self._auth_headers(),
            json={
                "ips": ips,
                "include_ports": False,
                "include_dns": True
            },
            name="/api/health/check/batch",
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code in [200, 400, 500]:
                response.success()
    
    # ==================== Quick Tests ====================
    
    @task(8)
    @tag("quick-test", "read")
    def quick_ping(self):
        """Lightweight ping test"""
        ip = random.choice(SAMPLE_IPS)
        with self.client.get(
            f"/api/health/ping/{ip}?count=2",
            headers=self._auth_headers(),
            name="/api/health/ping/[ip]",
            catch_response=True,
            timeout=15
        ) as response:
            if response.status_code in [200, 500]:
                response.success()
    
    @task(2)
    @tag("quick-test", "read")
    def dns_lookup(self):
        """DNS lookup for an IP"""
        ip = random.choice(SAMPLE_IPS)
        with self.client.get(
            f"/api/health/dns/{ip}",
            headers=self._auth_headers(),
            name="/api/health/dns/[ip]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()
    
    # ==================== Monitoring Endpoints ====================
    
    @task(6)
    @tag("monitoring", "read")
    def get_monitoring_status(self):
        """Get current monitoring status"""
        self.client.get("/api/health/monitoring/status", headers=self._auth_headers())
    
    @task(4)
    @tag("monitoring", "read")
    def get_monitoring_config(self):
        """Get monitoring configuration"""
        self.client.get("/api/health/monitoring/config", headers=self._auth_headers())
    
    @task(3)
    @tag("monitoring", "read")
    def get_monitored_devices(self):
        """Get list of monitored devices"""
        self.client.get("/api/health/monitoring/devices", headers=self._auth_headers())
    
    # ==================== Gateway Test IPs ====================
    
    @task(5)
    @tag("gateway", "read")
    def get_all_gateway_test_ips(self):
        """Get all gateway test IP configurations"""
        self.client.get("/api/health/gateway/test-ips/all", headers=self._auth_headers())
    
    @task(3)
    @tag("gateway", "read")
    def get_all_gateway_metrics(self):
        """Get all gateway test IP metrics"""
        self.client.get("/api/health/gateway/test-ips/all/metrics", headers=self._auth_headers())
    
    @task(2)
    @tag("gateway", "read")
    def get_gateway_test_ips(self):
        """Get test IPs for a specific gateway"""
        gateway_ip = random.choice(SAMPLE_GATEWAY_IPS)
        with self.client.get(
            f"/api/health/gateway/{gateway_ip}/test-ips",
            headers=self._auth_headers(),
            name="/api/health/gateway/[ip]/test-ips",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
    
    @task(2)
    @tag("gateway", "read")
    def get_cached_test_ip_metrics(self):
        """Get cached test IP metrics for a gateway"""
        gateway_ip = random.choice(SAMPLE_GATEWAY_IPS)
        with self.client.get(
            f"/api/health/gateway/{gateway_ip}/test-ips/cached",
            headers=self._auth_headers(),
            name="/api/health/gateway/[ip]/test-ips/cached",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
    
    # ==================== Speed Test Endpoints ====================
    
    @task(3)
    @tag("speedtest", "read")
    def get_all_speed_tests(self):
        """Get all speed test results"""
        self.client.get("/api/health/speedtest/all", headers=self._auth_headers())
    
    @task(2)
    @tag("speedtest", "read")
    def get_gateway_speed_test(self):
        """Get speed test result for a gateway"""
        gateway_ip = random.choice(SAMPLE_GATEWAY_IPS)
        with self.client.get(
            f"/api/health/gateway/{gateway_ip}/speedtest",
            headers=self._auth_headers(),
            name="/api/health/gateway/[ip]/speedtest",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
    
    # Note: Actual speed tests are NOT included as they take 30-60 seconds
    # and would severely impact load test performance
    
    # ==================== Cache Management ====================
    
    @task(1)
    @tag("cache", "write")
    def clear_cache(self):
        """Clear metrics cache - low frequency"""
        self.client.delete("/api/health/cache", headers=self._auth_headers())
    
    # ==================== Healthcheck ====================
    
    @task(5)
    @tag("system", "read")
    def healthz(self):
        """Service health check endpoint"""
        self.client.get("/healthz")


# ==================== Event Hooks ====================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n{'='*60}")
    print(f"  Health Service Load Test")
    print(f"  Auth User: {AUTH_USERNAME}")
    print(f"  Target: {environment.host}")
    print(f"{'='*60}\n")
