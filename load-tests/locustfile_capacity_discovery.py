"""
Capacity Discovery Load Test for Cartographer

This load test automatically discovers system capacity by ramping up load
until performance degrades. It finds the "knee" of the performance curve.

Usage:
    locust -f locustfile_capacity_discovery.py --host http://localhost:8000 \
           --html capacity_report.html --headless

Environment Variables:
    LOADTEST_USERNAME: Username for authentication (required)
    LOADTEST_PASSWORD: Password for authentication (required)
    
    RAMP_INITIAL_USERS: Starting number of users (default: 10)
    RAMP_STEP: Users to add per step (default: 10)
    RAMP_INTERVAL: Seconds between steps (default: 90)
    RAMP_MAX_USERS: Maximum users before stopping (default: 200)
    RAMP_P95_THRESHOLD: P95 latency threshold in ms (default: 200)
    RAMP_ERROR_THRESHOLD: Error rate threshold (default: 0.01 = 1%)
    RAMP_SPAWN_RATE: User spawn rate per second (default: 5)
"""

import os
import random
from locust import HttpUser, task, tag, between, events
from faker import Faker

# Import the capacity discovery shape
from capacity_discovery_shape import CapacityDiscoveryShape


# Authentication credentials from environment
USERNAME = os.getenv("LOADTEST_USERNAME", "loadtest_admin")
PASSWORD = os.getenv("LOADTEST_PASSWORD", "LoadTest123!")

# Initialize faker for generating test data
fake = Faker()

# Global token storage for authenticated requests
_auth_token = None


def get_auth_token():
    """Get cached auth token or return None if not authenticated yet."""
    return _auth_token


def set_auth_token(token):
    """Set the global auth token."""
    global _auth_token
    _auth_token = token


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Authenticate once at test start and cache the token.
    All users will share this token.
    """
    print("\n" + "="*70)
    print("🔐 Authenticating for capacity discovery test...")
    print("="*70)
    
    # Create a temporary HTTP client for authentication
    import httpx
    
    base_url = environment.host
    if not base_url:
        print("⚠️  Warning: No host specified, authentication will be handled per-user")
        print("="*70 + "\n")
        return
    
    try:
        # Use httpx for authentication instead of Locust's client
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            response = client.post(
                "/api/auth/login",
                json={"username": USERNAME, "password": PASSWORD}
            )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                set_auth_token(token)
                print(f"✓ Authentication successful")
                print(f"✓ Token cached for all virtual users")
                print("="*70 + "\n")
            else:
                print(f"✗ No token in response")
                print("="*70 + "\n")
                raise Exception("Authentication failed: No token in response")
        else:
            print(f"✗ Authentication failed: HTTP {response.status_code}")
            print(f"  Response: {response.text}")
            print("="*70 + "\n")
            raise Exception(f"Authentication failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"✗ Authentication error: {e}")
        print("="*70 + "\n")
        raise


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
            print(f"⚠️  No capacity limit found (may have reached max_users)")
    
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
    
    def _auth_headers(self):
        """Get authorization headers with cached token."""
        token = get_auth_token()
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}
    
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
            json={"token": get_auth_token()},
            name="/api/auth/verify",
            catch_response=True
        ) as r:
            if r.status_code in [200, 401]:
                r.success()
    
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
            if r.status_code in [200, 401]:
                r.success()
    
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
            if r.status_code in [200, 201, 400, 500]:
                r.success()
    
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
            if r.status_code in [200, 400, 500]:
                r.success()
    
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

