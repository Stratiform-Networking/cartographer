"""
Combined Load Test for All Cartographer Microservices

This file imports and exposes all service-specific load test users,
allowing you to run a comprehensive load test across the entire application.

IMPORTANT: This assumes all services are accessible through a single host
(e.g., through the main backend proxy at port 8000 or individual service ports).

Authentication:
    Set environment variables before running:
    - LOADTEST_USERNAME: Username for authentication (default: admin)
    - LOADTEST_PASSWORD: Password for authentication (default: admin)

For testing individual services directly, use their specific locustfiles.

Run with:
    LOADTEST_USERNAME=myuser LOADTEST_PASSWORD=mypass locust -f locustfile_all.py --host=http://localhost:8000
    
    # Or on Windows PowerShell:
    $env:LOADTEST_USERNAME="myuser"; $env:LOADTEST_PASSWORD="mypass"; locust -f locustfile_all.py --host=http://localhost:8000
"""

import os
import random
import uuid
from locust import HttpUser, task, between, tag, events
from faker import Faker

fake = Faker()

# ==================== Configuration ====================

# Authentication credentials from environment variables
AUTH_USERNAME = os.environ.get("LOADTEST_USERNAME", "admin")
AUTH_PASSWORD = os.environ.get("LOADTEST_PASSWORD", "admin")

# Sample data for testing
SAMPLE_IPS = [
    "192.168.1.1",
    "192.168.1.100", 
    "192.168.1.254",
    "10.0.0.1",
    "10.0.0.50",
]

SAMPLE_USER_IDS = [str(uuid.uuid4()) for _ in range(10)]
AI_PROVIDERS = ["openai", "anthropic", "gemini", "ollama"]


class AuthenticatedUser(HttpUser):
    """
    Base class for authenticated load test users.
    Handles login and token management.
    """
    
    abstract = True  # Don't instantiate this class directly
    
    access_token = None
    user_id = None
    
    def on_start(self):
        """Setup: Authenticate before running tests"""
        self._login()
    
    def _login(self):
        """Authenticate and store the access token"""
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
            user_data = data.get("user", {})
            self.user_id = user_data.get("id", str(uuid.uuid4()))
            response.success()
        else:
            # Log the failure but don't crash - tests will fail with 401
            response.failure(f"Login failed: {response.status_code}")
    
    def _auth_headers(self):
        """Get headers with authorization token"""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        # Use actual user_id if available, otherwise random
        headers["X-User-Id"] = self.user_id or random.choice(SAMPLE_USER_IDS)
        headers["X-Username"] = AUTH_USERNAME
        return headers


class CartographerReadUser(AuthenticatedUser):
    """
    Primary load test user focusing on read operations.
    
    This user simulates typical dashboard/monitoring usage patterns
    with high-frequency read operations across all services.
    """
    
    wait_time = between(1, 3)
    weight = 10  # High weight - most users are readers
    
    # ==================== Health Service (via proxy) ====================
    
    @task(10)
    @tag("health", "read")
    def health_get_cached_all(self):
        """Get all cached health metrics"""
        self.client.get("/api/health/cached", headers=self._auth_headers())
    
    @task(5)
    @tag("health", "read")
    def health_monitoring_status(self):
        """Get monitoring status"""
        self.client.get("/api/health/monitoring/status", headers=self._auth_headers())
    
    @task(4)
    @tag("health", "read")
    def health_gateway_metrics(self):
        """Get gateway test IP metrics"""
        self.client.get("/api/health/gateway/test-ips/all/metrics", headers=self._auth_headers())
    
    # ==================== Auth Service (via proxy) ====================
    
    @task(8)
    @tag("auth", "read")
    def auth_verify_token(self):
        """Verify current token"""
        self.client.post("/api/auth/verify", headers=self._auth_headers())
    
    @task(5)
    @tag("auth", "read")
    def auth_get_session(self):
        """Get current session"""
        with self.client.get(
            "/api/auth/session",
            headers=self._auth_headers(),
            catch_response=True
        ) as r:
            if r.status_code in [200, 401]:
                r.success()
    
    @task(3)
    @tag("auth", "read")
    def auth_setup_status(self):
        """Check setup status"""
        self.client.get("/api/auth/setup/status")  # Public endpoint, no auth needed
    
    # ==================== Metrics Service (via proxy) ====================
    
    @task(15)
    @tag("metrics", "read")
    def metrics_get_snapshot(self):
        """Get current network snapshot - highest frequency"""
        self.client.get("/api/metrics/snapshot", headers=self._auth_headers())
    
    @task(12)
    @tag("metrics", "read")
    def metrics_get_summary(self):
        """Get network summary"""
        self.client.get("/api/metrics/summary", headers=self._auth_headers())
    
    @task(6)
    @tag("metrics", "read")
    def metrics_get_gateways(self):
        """Get gateway information"""
        self.client.get("/api/metrics/gateways", headers=self._auth_headers())
    
    @task(4)
    @tag("metrics", "read")
    def metrics_get_config(self):
        """Get metrics config"""
        self.client.get("/api/metrics/config", headers=self._auth_headers())
    
    # ==================== Assistant Service (via proxy) ====================
    
    @task(6)
    @tag("assistant", "read")
    def assistant_get_config(self):
        """Get assistant configuration"""
        self.client.get("/api/assistant/config", headers=self._auth_headers())
    
    @task(4)
    @tag("assistant", "read")
    def assistant_get_context(self):
        """Get network context"""
        self.client.get("/api/assistant/context", headers=self._auth_headers())
    
    @task(3)
    @tag("assistant", "read")
    def assistant_list_providers(self):
        """List AI providers"""
        self.client.get("/api/assistant/providers", headers=self._auth_headers())
    
    # ==================== Notification Service (via proxy) ====================
    
    @task(6)
    @tag("notifications", "read")
    def notifications_status(self):
        """Get notification service status"""
        self.client.get("/api/notifications/status", headers=self._auth_headers())
    
    @task(5)
    @tag("notifications", "read")
    def notifications_preferences(self):
        """Get notification preferences"""
        self.client.get("/api/notifications/preferences", headers=self._auth_headers())
    
    @task(4)
    @tag("notifications", "read")
    def notifications_ml_status(self):
        """Get ML model status"""
        self.client.get("/api/notifications/ml/status", headers=self._auth_headers())
    
    @task(3)
    @tag("notifications", "read")
    def notifications_version(self):
        """Get version status"""
        self.client.get("/api/notifications/version", headers=self._auth_headers())


class CartographerWriteUser(AuthenticatedUser):
    """
    Load test user for write operations.
    
    This simulates admin/power user activities with lower frequency
    write operations that modify system state.
    """
    
    wait_time = between(3, 8)  # Slower for writes
    weight = 2  # Lower weight - fewer writers
    
    @task(3)
    @tag("health", "write")
    def health_ping_device(self):
        """Ping a device"""
        ip = random.choice(SAMPLE_IPS)
        with self.client.get(
            f"/api/health/ping/{ip}?count=2",
            headers=self._auth_headers(),
            name="/api/health/ping/[ip]",
            catch_response=True,
            timeout=15
        ) as r:
            if r.status_code in [200, 500]:
                r.success()
    
    @task(2)
    @tag("metrics", "write")
    def metrics_generate_snapshot(self):
        """Generate new snapshot"""
        with self.client.post(
            "/api/metrics/snapshot/generate",
            headers=self._auth_headers(),
            catch_response=True,
            timeout=30
        ) as r:
            if r.status_code in [200, 500]:
                r.success()
    
    @task(2)
    @tag("assistant", "write")
    def assistant_refresh_context(self):
        """Refresh assistant context"""
        with self.client.post(
            "/api/assistant/context/refresh",
            headers=self._auth_headers(),
            catch_response=True,
            timeout=15
        ) as r:
            if r.status_code in [200, 500]:
                r.success()
    
    @task(1)
    @tag("notifications", "write")
    def notifications_process_health(self):
        """Process health check"""
        ip = random.choice(SAMPLE_IPS)
        with self.client.post(
            "/api/notifications/process-health-check",
            params={
                "device_ip": ip,
                "success": random.choice([True, True, True, False]),
                "latency_ms": random.uniform(1, 50),
            },
            headers=self._auth_headers(),
            catch_response=True
        ) as r:
            if r.status_code in [200, 500]:
                r.success()


class CartographerHealthCheckUser(AuthenticatedUser):
    """
    Simulates external monitoring/health check systems.
    
    This user continuously checks service health endpoints
    at a high rate to ensure all services are responsive.
    """
    
    wait_time = between(0.5, 2)
    weight = 3
    
    @task(5)
    @tag("system", "healthcheck")
    def check_backend(self):
        """Check main backend health"""
        self.client.get("/healthz")  # Health endpoint typically doesn't need auth
    
    @task(3)
    @tag("system", "healthcheck")
    def check_health_service(self):
        """Check health service via proxy"""
        with self.client.get(
            "/api/health/monitoring/status",
            headers=self._auth_headers(),
            catch_response=True
        ) as r:
            if r.status_code in [200, 500, 503]:
                r.success()
    
    @task(3)
    @tag("system", "healthcheck")
    def check_metrics_service(self):
        """Check metrics service via proxy"""
        with self.client.get(
            "/api/metrics/config",
            headers=self._auth_headers(),
            catch_response=True
        ) as r:
            if r.status_code in [200, 500, 503]:
                r.success()
    
    @task(3)
    @tag("system", "healthcheck")
    def check_auth_service(self):
        """Check auth service via proxy"""
        self.client.get("/api/auth/setup/status")  # Public endpoint
    
    @task(3)
    @tag("system", "healthcheck")
    def check_notifications_service(self):
        """Check notifications service via proxy"""
        with self.client.get(
            "/api/notifications/status",
            headers=self._auth_headers(),
            catch_response=True
        ) as r:
            if r.status_code in [200, 500, 503]:
                r.success()
    
    @task(2)
    @tag("system", "healthcheck")
    def check_assistant_service(self):
        """Check assistant service via proxy"""
        with self.client.get(
            "/api/assistant/config",
            headers=self._auth_headers(),
            catch_response=True
        ) as r:
            if r.status_code in [200, 500, 503]:
                r.success()


# ==================== Event Hooks ====================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print auth configuration at test start"""
    print(f"\n{'='*60}")
    print(f"  Cartographer Load Test")
    print(f"  Auth User: {AUTH_USERNAME}")
    print(f"  Target: {environment.host}")
    print(f"{'='*60}\n")


@events.quitting.add_listener  
def on_quitting(environment, **kwargs):
    """Print summary on test end"""
    print(f"\n{'='*60}")
    print(f"  Load Test Complete")
    print(f"{'='*60}\n")
