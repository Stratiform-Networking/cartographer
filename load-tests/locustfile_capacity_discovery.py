"""
Capacity Discovery Load Test for Cartographer

This load test automatically discovers system capacity by ramping up load
until performance degrades. It finds the "knee" of the performance curve.
Runs until failure (P95 or error rate thresholds exceeded) or max duration.

Usage:
    locust -f locustfile_capacity_discovery.py --host http://localhost:8000 \
           --html capacity_report.html --headless

Environment Variables:
    LOADTEST_USERNAME: Username for authentication (required)
    LOADTEST_PASSWORD: Password for authentication (required)

    RAMP_INITIAL_USERS: Starting number of users (default: 10)
    RAMP_STEP: Users to add per step (default: 10)
    RAMP_INTERVAL: Seconds between steps (default: 30)
    RAMP_MAX_DURATION: Maximum test duration in seconds (default: 3600 = 1 hour)
    RAMP_P95_THRESHOLD: P95 latency threshold in ms (default: 200)
    RAMP_ERROR_THRESHOLD: Error rate threshold (default: 0.01 = 1%)
    RAMP_SPAWN_RATE: User spawn rate per second (default: 5)
"""

import random
from locust import HttpUser, task, tag, between, events
from common.assertions import expect_status
from common.auth import (
    get_auth_host,
    get_auth_password,
    get_auth_username,
    login_with_locust_client,
)
from capacity_window_metrics import rolling_window_metrics

# Import the capacity discovery shape
from capacity_discovery_shape import CapacityDiscoveryShape


# Authentication credentials from environment
USERNAME = get_auth_username()
PASSWORD = get_auth_password()
AUTH_HOST = get_auth_host()


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Print test configuration and reset rolling metrics.
    """
    rolling_window_metrics.reset()
    print("\n" + "="*70)
    print("🔐 Capacity discovery test configuration")
    print("="*70)
    print(f"Auth user: {USERNAME}")
    print(f"Auth host: {AUTH_HOST}")
    print(f"Target host: {environment.host}")
    print("="*70 + "\n")


@events.request.add_listener
def on_request(
    request_type,
    name,
    response_time,
    response_length,
    response,
    context,
    exception,
    **kwargs,
):
    """Collect rolling-window request metrics for capacity decisions."""
    if name == "/api/auth/login":
        return

    is_failure = exception is not None
    if response is not None and getattr(response, "status_code", 0) >= 400:
        is_failure = True
    rolling_window_metrics.add(response_time_ms=response_time, is_failure=is_failure)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Print final capacity discovery results.
    """
    print("\n" + "="*70)
    print("📊 CAPACITY DISCOVERY TEST COMPLETE")
    print("="*70)
    
    # Get the shape to access knee point
    if hasattr(environment, 'shape_class'):
        shape = environment.shape_class
        if hasattr(shape, 'knee_point') and shape.knee_point:
            print(f"🎯 Maximum Sustainable Capacity: {shape.knee_point} concurrent users")
            if hasattr(shape, 'stop_reason') and shape.stop_reason:
                print(f"📉 Stopped because: {shape.stop_reason}")
        else:
            print(f"⚠️  No capacity limit found (test may still be running)")
    
    # Print overall statistics
    stats = environment.stats.total
    if stats.num_requests > 0:
        print(f"\n📈 Overall Statistics:")
        print(f"   Total Requests:   {stats.num_requests:,}")
        print(f"   Total Failures:   {stats.num_failures:,}")
        print(f"   Failure Rate:     {stats.num_failures/stats.num_requests*100:.2f}%")
        print(f"   Avg Response:     {stats.avg_response_time:.0f}ms")
        print(f"   Min Response:     {stats.min_response_time:.0f}ms")
        print(f"   Max Response:     {stats.max_response_time:.0f}ms")
    
    print("="*70 + "\n")


class CartographerCapacityUser(HttpUser):
    """
    User that performs typical read/write operations for capacity discovery.
    
    Focuses on representative endpoints to find overall system capacity.
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    access_token = None

    def on_start(self):
        auth_result = login_with_locust_client(
            self.client,
            USERNAME,
            PASSWORD,
            auth_host=AUTH_HOST,
        )
        self.access_token = auth_result.access_token
    
    def _auth_headers(self):
        """Get authorization headers with authenticated token."""
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}
    
    # ============================================================================
    # AUTH SERVICE - High frequency, low latency
    # ============================================================================
    
    @task(10)
    @tag("auth", "read", "critical")
    def auth_verify_token(self):
        """Verify JWT token"""
        with self.client.post(
            "/api/auth/verify",
            headers=self._auth_headers(),
            json={"token": self.access_token},
            name="/api/auth/verify",
            catch_response=True
        ) as r:
            expect_status(r, [200], "auth_verify_token")
    
    @task(5)
    @tag("auth", "read")
    def auth_get_session(self):
        """Get current session info"""
        with self.client.get(
            "/api/auth/session",
            headers=self._auth_headers(),
            name="/api/auth/session",
            catch_response=True
        ) as r:
            expect_status(r, [200], "auth_get_session")
    
    # ============================================================================
    # HEALTH SERVICE - Medium frequency, low latency
    # ============================================================================
    
    @task(15)
    @tag("health", "read", "critical")
    def health_monitoring_status(self):
        """Get health monitoring status"""
        self.client.get(
            "/api/health/monitoring/status",
            headers=self._auth_headers(),
            name="/api/health/monitoring/status"
        )
    
    @task(10)
    @tag("health", "read")
    def health_cached(self):
        """Get cached health data"""
        self.client.get(
            "/api/health/cached",
            headers=self._auth_headers(),
            name="/api/health/cached"
        )
    
    @task(3)
    @tag("health", "read")
    def health_gateway_metrics(self):
        """Get gateway test IP metrics"""
        self.client.get(
            "/api/health/gateway/test-ips/all/metrics",
            headers=self._auth_headers(),
            name="/api/health/gateway/test-ips/all/metrics"
        )
    
    # ============================================================================
    # METRICS SERVICE - High frequency, medium latency
    # ============================================================================
    
    @task(15)
    @tag("metrics", "read", "critical")
    def metrics_config(self):
        """Get metrics configuration"""
        self.client.get(
            "/api/metrics/config",
            headers=self._auth_headers(),
            name="/api/metrics/config"
        )
    
    @task(12)
    @tag("metrics", "read", "critical")
    def metrics_snapshot(self):
        """Get current metrics snapshot"""
        self.client.get(
            "/api/metrics/snapshot",
            headers=self._auth_headers(),
            name="/api/metrics/snapshot"
        )
    
    @task(10)
    @tag("metrics", "read")
    def metrics_summary(self):
        """Get metrics summary"""
        self.client.get(
            "/api/metrics/summary",
            headers=self._auth_headers(),
            name="/api/metrics/summary"
        )
    
    @task(5)
    @tag("metrics", "read")
    def usage_stats(self):
        """Get usage statistics"""
        self.client.get(
            "/api/metrics/usage/stats",
            headers=self._auth_headers(),
            name="/api/metrics/usage/stats"
        )
    
    # ============================================================================
    # NOTIFICATION SERVICE - Medium frequency, low latency
    # ============================================================================
    
    @task(10)
    @tag("notifications", "read", "critical")
    def notifications_status(self):
        """Get notification service status"""
        self.client.get(
            "/api/notifications/status",
            headers=self._auth_headers(),
            name="/api/notifications/status"
        )
    
    @task(5)
    @tag("notifications", "read")
    def notifications_preferences(self):
        """Get notification preferences"""
        self.client.get(
            "/api/notifications/preferences",
            headers=self._auth_headers(),
            name="/api/notifications/preferences"
        )
    
    # ============================================================================
    # ASSISTANT SERVICE - Lower frequency, higher latency
    # ============================================================================
    
    @task(5)
    @tag("assistant", "read")
    def assistant_config(self):
        """Get assistant configuration"""
        self.client.get(
            "/api/assistant/config",
            headers=self._auth_headers(),
            name="/api/assistant/config"
        )
    
    @task(2)
    @tag("assistant", "read")
    def assistant_providers(self):
        """List AI providers"""
        self.client.get(
            "/api/assistant/providers",
            headers=self._auth_headers(),
            name="/api/assistant/providers"
        )
    
    # ============================================================================
    # WRITE OPERATIONS - Lower frequency, represents mutations
    # ============================================================================
    
    @task(2)
    @tag("metrics", "write")
    def metrics_generate_snapshot(self):
        """Generate new metrics snapshot"""
        with self.client.post(
            "/api/metrics/snapshot/generate",
            headers=self._auth_headers(),
            name="/api/metrics/snapshot/generate",
            catch_response=True
        ) as r:
            expect_status(r, [200], "metrics_generate_snapshot")
    
    @task(1)
    @tag("notifications", "write")
    def notifications_update_preferences(self):
        """Update notification preferences"""
        with self.client.put(
            "/api/notifications/global/preferences",
            headers=self._auth_headers(),
            json={
                "email_enabled": random.choice([True, False]),
                "discord_enabled": random.choice([True, False]),
            },
            name="/api/notifications/global/preferences",
            catch_response=True
        ) as r:
            expect_status(r, [200], "notifications_update_preferences")
    
    # ============================================================================
    # HEALTH CHECK - Very high frequency, ultra-low latency
    # ============================================================================
    
    @task(20)
    @tag("health", "read", "critical")
    def healthz(self):
        """Health check endpoint"""
        self.client.get("/healthz", name="/healthz")


# Set the LoadTestShape class for capacity discovery
# This is picked up by Locust automatically
class LoadTestShape(CapacityDiscoveryShape):
    """
    Use the CapacityDiscoveryShape for this test.
    This class name (LoadTestShape) is what Locust looks for.
    """
    pass
