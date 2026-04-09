"""
Load Test for Metrics Service (port 8003)

Tests network topology snapshots, Redis publishing, and WebSocket connections.

Authentication:
    Set environment variables before running:
    - LOADTEST_USERNAME: Username for authentication (default: admin)
    - LOADTEST_PASSWORD: Password for authentication (default: admin)
"""

import uuid
import random
from locust import HttpUser, task, between, tag, events
from common.assertions import expect_status
from common.auth import (
    get_auth_host,
    get_auth_password,
    get_auth_username,
    login_with_locust_client,
)


# Authentication credentials from environment variables
AUTH_USERNAME = get_auth_username()
AUTH_PASSWORD = get_auth_password()
AUTH_HOST = get_auth_host()


class AuthenticatedMetricsUser(HttpUser):
    """Base class for authenticated metrics service users."""
    
    abstract = True
    access_token = None
    
    def on_start(self):
        """Authenticate before running tests"""
        auth_result = login_with_locust_client(
            self.client,
            AUTH_USERNAME,
            AUTH_PASSWORD,
            auth_host=AUTH_HOST,
        )
        self.access_token = auth_result.access_token
    
    def _auth_headers(self):
        """Get headers with authorization token"""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers


class MetricsServiceUser(AuthenticatedMetricsUser):
    """
    Load test user for the Metrics Service.
    
    Run with:
        locust -f locustfile_metrics.py --host=http://localhost:8003
        
    Or via backend proxy:
        locust -f locustfile_metrics.py --host=http://localhost:8000
    """
    
    wait_time = between(1, 3)
    
    # ==================== Snapshot Endpoints ====================
    
    @task(15)
    @tag("snapshot", "read")
    def get_current_snapshot(self):
        """Get current network topology snapshot - highest frequency"""
        self.client.get("/api/metrics/snapshot", headers=self._auth_headers())
    
    @task(8)
    @tag("snapshot", "read")
    def get_cached_snapshot(self):
        """Get cached snapshot from Redis"""
        self.client.get("/api/metrics/snapshot/cached", headers=self._auth_headers())
    
    @task(3)
    @tag("snapshot", "write")
    def generate_snapshot(self):
        """Trigger snapshot generation"""
        with self.client.post(
            "/api/metrics/snapshot/generate",
            headers=self._auth_headers(),
            name="/api/metrics/snapshot/generate",
            catch_response=True,
            timeout=30
        ) as response:
            expect_status(response, [200], "generate_snapshot")
    
    @task(2)
    @tag("snapshot", "write")
    def publish_snapshot(self):
        """Generate and publish snapshot to Redis"""
        with self.client.post(
            "/api/metrics/snapshot/publish",
            headers=self._auth_headers(),
            name="/api/metrics/snapshot/publish",
            catch_response=True,
            timeout=30
        ) as response:
            expect_status(response, [200], "publish_snapshot")
    
    # ==================== Summary & Navigation ====================
    
    @task(12)
    @tag("summary", "read")
    def get_summary(self):
        """Get lightweight network summary - high frequency for dashboards"""
        self.client.get("/api/metrics/summary", headers=self._auth_headers())
    
    @task(6)
    @tag("navigation", "read")
    def get_connections(self):
        """Get all node connections"""
        self.client.get("/api/metrics/connections", headers=self._auth_headers())
    
    @task(5)
    @tag("navigation", "read")
    def get_gateways(self):
        """Get gateway/ISP information"""
        self.client.get("/api/metrics/gateways", headers=self._auth_headers())
    
    @task(4)
    @tag("navigation", "read")
    def get_node_metrics(self):
        """Get metrics for a specific node"""
        # Use common node ID patterns
        node_ids = [
            "192.168.1.1",
            "10.0.0.1",
            str(uuid.uuid4()),
            "router",
            "gateway",
        ]
        node_id = random.choice(node_ids)
        with self.client.get(
            f"/api/metrics/nodes/{node_id}",
            headers=self._auth_headers(),
            name="/api/metrics/nodes/[id]",
            catch_response=True
        ) as response:
            expect_status(response, [200, 404], "get_node_metrics")
    
    # ==================== Configuration ====================
    
    @task(4)
    @tag("config", "read")
    def get_config(self):
        """Get metrics service configuration"""
        self.client.get("/api/metrics/config", headers=self._auth_headers())
    
    @task(1)
    @tag("config", "write")
    def update_config(self):
        """Update publishing configuration"""
        with self.client.post(
            "/api/metrics/config",
            headers=self._auth_headers(),
            json={
                "enabled": True,
                "publish_interval_seconds": random.randint(15, 60)
            },
            name="/api/metrics/config (update)",
            catch_response=True
        ) as response:
            expect_status(response, [200], "update_config")
    
    # ==================== Redis Status ====================
    
    @task(5)
    @tag("redis", "read")
    def get_redis_status(self):
        """Check Redis connection status"""
        self.client.get("/api/metrics/redis/status", headers=self._auth_headers())
    
    @task(1)
    @tag("redis", "write")
    def reconnect_redis(self):
        """Attempt Redis reconnection - low frequency"""
        with self.client.post(
            "/api/metrics/redis/reconnect",
            headers=self._auth_headers(),
            name="/api/metrics/redis/reconnect",
            catch_response=True
        ) as response:
            expect_status(response, [200], "reconnect_redis")
    
    # ==================== Speed Test ====================
    
    # Note: Actual speed tests are NOT triggered as they take 30-60 seconds
    # The endpoint exists but we only test the trigger mechanism with invalid IPs
    
    @task(1)
    @tag("speedtest", "read")
    def trigger_speed_test_dry(self):
        """Test speed test trigger endpoint (won't complete actual test)"""
        with self.client.post(
            "/api/metrics/speed-test",
            headers=self._auth_headers(),
            json={"gateway_ip": "192.168.1.1"},
            name="/api/metrics/speed-test (dry)",
            catch_response=True,
            timeout=5  # Short timeout - we don't want actual test
        ) as response:
            expect_status(response, [200, 202], "trigger_speed_test_dry")
    
    # ==================== Debug Endpoints ====================
    
    @task(2)
    @tag("debug", "read")
    def debug_layout(self):
        """Get raw layout data - useful for debugging"""
        self.client.get("/api/metrics/debug/layout", headers=self._auth_headers())
    
    # ==================== Usage Statistics Endpoints ====================
    
    @task(6)
    @tag("usage", "read")
    def get_usage_stats(self):
        """Get endpoint usage statistics - common dashboard view"""
        self.client.get("/api/metrics/usage/stats", headers=self._auth_headers())
    
    @task(3)
    @tag("usage", "read")
    def get_usage_stats_filtered(self):
        """Get usage statistics for a specific service"""
        services = ["health-service", "metrics-service", "auth-service", "backend"]
        service = random.choice(services)
        with self.client.get(
            f"/api/metrics/usage/stats?service={service}",
            headers=self._auth_headers(),
            name="/api/metrics/usage/stats?service=[service]",
            catch_response=True
        ) as response:
            expect_status(response, [200], "get_usage_stats_filtered")
    
    @task(1)
    @tag("usage", "write")
    def reset_usage_stats(self):
        """Reset usage statistics - low frequency admin action"""
        # Only reset for a random service, not all
        services = ["test-service"]  # Use test service to avoid clearing real data
        service = random.choice(services)
        with self.client.delete(
            f"/api/metrics/usage/stats?service={service}",
            headers=self._auth_headers(),
            name="/api/metrics/usage/stats (reset)",
            catch_response=True
        ) as response:
            expect_status(response, [200, 404], "reset_usage_stats")
    
    # ==================== Healthcheck ====================
    
    @task(5)
    @tag("system", "read")
    def healthz(self):
        """Service health check endpoint"""
        self.client.get("/healthz")


class MetricsWebSocketUser(AuthenticatedMetricsUser):
    """
    Simulated WebSocket load test user.
    
    Note: Locust doesn't natively support WebSocket, so this simulates
    the HTTP upgrade request and initial snapshot fetch.
    """
    
    wait_time = between(5, 15)
    weight = 1
    
    @task(1)
    @tag("websocket", "connect")
    def simulate_ws_connect(self):
        """Simulate WebSocket connection initiation."""
        # Request initial snapshot like a WS client would
        self.client.get("/api/metrics/snapshot", headers=self._auth_headers())
        self.client.get("/api/metrics/snapshot/cached", headers=self._auth_headers())
        
        # Simulate periodic snapshot requests
        for _ in range(random.randint(1, 3)):
            self.client.get("/api/metrics/summary", headers=self._auth_headers())


# ==================== Event Hooks ====================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n{'='*60}")
    print(f"  Metrics Service Load Test")
    print(f"  Auth User: {AUTH_USERNAME}")
    print(f"  Auth Host: {AUTH_HOST}")
    print(f"  Target: {environment.host}")
    print(f"{'='*60}\n")
