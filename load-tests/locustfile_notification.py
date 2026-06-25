"""
Load Test for Notification Service (port 8005)

Tests notification preferences, history, Discord integration, 
ML anomaly detection, and scheduled broadcasts.

Authentication:
    Set environment variables before running:
    - LOADTEST_USERNAME: Username for authentication (default: admin)
    - LOADTEST_PASSWORD: Password for authentication (default: admin)
"""

import random
import uuid
from datetime import datetime, timedelta
from locust import HttpUser, task, between, tag, events
from faker import Faker
from common.assertions import expect_status
from common.auth import (
    get_auth_host,
    get_auth_password,
    get_auth_username,
    login_with_locust_client,
)

fake = Faker()

# Authentication credentials from environment variables
AUTH_USERNAME = get_auth_username()
AUTH_PASSWORD = get_auth_password()
AUTH_HOST = get_auth_host()

# Sample device IPs
SAMPLE_DEVICE_IPS = [
    "192.168.1.1",
    "192.168.1.100",
    "192.168.1.254",
    "10.0.0.1",
    "10.0.0.50",
]


class AuthenticatedNotificationUser(HttpUser):
    """Base class for authenticated notification service users."""
    
    abstract = True
    access_token = None
    user_id = None
    
    def on_start(self):
        """Authenticate before running tests"""
        auth_result = login_with_locust_client(
            self.client,
            AUTH_USERNAME,
            AUTH_PASSWORD,
            auth_host=AUTH_HOST,
        )
        self.access_token = auth_result.access_token
        self.user_id = auth_result.user_id or str(uuid.uuid4())
    
    def _auth_headers(self):
        """Get headers with authorization token and user ID"""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        headers["X-User-Id"] = self.user_id or str(uuid.uuid4())
        headers["X-Username"] = AUTH_USERNAME
        return headers


class NotificationServiceUser(AuthenticatedNotificationUser):
    """
    Load test user for the Notification Service.
    
    Run with:
        locust -f locustfile_notification.py --host=http://localhost:8005
        
    Or via backend proxy:
        locust -f locustfile_notification.py --host=http://localhost:8000
    """
    
    wait_time = between(1, 3)
    
    # ==================== Service Status ====================
    
    @task(10)
    @tag("status", "read")
    def get_service_status(self):
        """Get notification service status - high frequency"""
        self.client.get("/api/notifications/status", headers=self._auth_headers())
    
    # ==================== Preferences ====================
    
    @task(8)
    @tag("preferences", "read")
    def get_preferences(self):
        """Get notification preferences for a user"""
        self.client.get("/api/notifications/preferences", headers=self._auth_headers())
    
    @task(2)
    @tag("preferences", "write")
    def update_preferences(self):
        """Update global notification preferences"""
        with self.client.put(
            "/api/notifications/global/preferences",
            headers=self._auth_headers(),
            json={
                "email_enabled": random.choice([True, False]),
                "discord_enabled": random.choice([True, False]),
            },
            name="/api/notifications/global/preferences (update)",
            catch_response=True
        ) as response:
            expect_status(response, [200], "update_preferences")
    
    # ==================== History & Stats ====================
    
    @task(6)
    @tag("history", "read")
    def get_notification_history(self):
        """Get notification history for a user"""
        page = random.randint(1, 5)
        self.client.get(
            f"/api/notifications/history?page={page}&per_page=20",
            headers=self._auth_headers(),
            name="/api/notifications/history"
        )
    
    @task(4)
    @tag("stats", "read")
    def get_notification_stats(self):
        """Get notification statistics"""
        self.client.get("/api/notifications/stats", headers=self._auth_headers())
    
    # ==================== Discord Integration ====================
    
    @task(5)
    @tag("discord", "read")
    def get_discord_info(self):
        """Get Discord bot information"""
        self.client.get("/api/notifications/discord/info", headers=self._auth_headers())
    
    @task(3)
    @tag("discord", "read")
    def get_discord_guilds(self):
        """Get Discord servers the bot is in"""
        with self.client.get(
            "/api/notifications/discord/guilds",
            headers=self._auth_headers(),
            name="/api/notifications/discord/guilds",
            catch_response=True
        ) as response:
            expect_status(response, [200, 503], "get_discord_guilds")
    
    @task(2)
    @tag("discord", "read")
    def get_discord_invite_url(self):
        """Get Discord bot invite URL"""
        with self.client.get(
            "/api/notifications/discord/invite-url",
            headers=self._auth_headers(),
            name="/api/notifications/discord/invite-url",
            catch_response=True
        ) as response:
            expect_status(response, [200, 503], "get_discord_invite_url")
    
    # ==================== ML/Anomaly Detection ====================
    
    @task(5)
    @tag("ml", "read")
    def get_ml_model_status(self):
        """Get ML anomaly detection model status"""
        self.client.get("/api/notifications/ml/status", headers=self._auth_headers())
    
    @task(3)
    @tag("ml", "read")
    def get_device_baseline(self):
        """Get learned baseline for a device"""
        device_ip = random.choice(SAMPLE_DEVICE_IPS)
        with self.client.get(
            f"/api/notifications/ml/baseline/{device_ip}",
            headers=self._auth_headers(),
            name="/api/notifications/ml/baseline/[ip]",
            catch_response=True
        ) as response:
            expect_status(response, [200, 404], "get_device_baseline")
    
    # ==================== Silenced Devices ====================
    
    @task(4)
    @tag("silenced", "read")
    def get_silenced_devices(self):
        """Get list of silenced devices"""
        self.client.get("/api/notifications/silenced-devices", headers=self._auth_headers())
    
    @task(2)
    @tag("silenced", "read")
    def check_device_silenced(self):
        """Check if a specific device is silenced"""
        device_ip = random.choice(SAMPLE_DEVICE_IPS)
        self.client.get(
            f"/api/notifications/silenced-devices/{device_ip}",
            headers=self._auth_headers(),
            name="/api/notifications/silenced-devices/[ip]"
        )
    
    # ==================== Scheduled Broadcasts ====================
    
    @task(4)
    @tag("scheduled", "read")
    def get_scheduled_broadcasts(self):
        """Get all scheduled broadcasts"""
        self.client.get("/api/notifications/scheduled", headers=self._auth_headers())
    
    @task(2)
    @tag("scheduled", "read")
    def get_scheduled_broadcast_by_id(self):
        """Get a specific scheduled broadcast"""
        broadcast_id = str(uuid.uuid4())
        with self.client.get(
            f"/api/notifications/scheduled/{broadcast_id}",
            headers=self._auth_headers(),
            name="/api/notifications/scheduled/[id]",
            catch_response=True
        ) as response:
            expect_status(response, [200, 404], "get_scheduled_broadcast_by_id")
    
    # ==================== Version Updates ====================
    
    @task(5)
    @tag("version", "read")
    def get_version_status(self):
        """Get version status and update info"""
        self.client.get("/api/notifications/version", headers=self._auth_headers())
    
    @task(2)
    @tag("version", "write")
    def check_for_updates(self):
        """Trigger version check"""
        with self.client.post(
            "/api/notifications/version/check",
            headers=self._auth_headers(),
            name="/api/notifications/version/check",
            catch_response=True
        ) as response:
            expect_status(response, [200], "check_for_updates")
    
    # ==================== Healthcheck ====================
    
    @task(5)
    @tag("system", "read")
    def healthz(self):
        """Service health check endpoint"""
        self.client.get("/healthz")


class NotificationWriteUser(AuthenticatedNotificationUser):
    """
    Load test user for notification write operations.
    """
    
    wait_time = between(3, 8)  # Slower for write operations
    weight = 1  # Lower weight
    
    @task(2)
    @tag("health-check", "write")
    def process_health_check(self):
        """Process a health check result"""
        device_ip = random.choice(SAMPLE_DEVICE_IPS)
        
        with self.client.post(
            "/api/notifications/process-health-check",
            headers=self._auth_headers(),
            params={
                "device_ip": device_ip,
                "success": random.choice([True, True, True, False]),  # 75% success
                "latency_ms": random.uniform(1, 100),
                "packet_loss": random.uniform(0, 0.1),
                "device_name": f"Device-{device_ip.split('.')[-1]}",
            },
            name="/api/notifications/process-health-check",
            catch_response=True
        ) as response:
            expect_status(response, [200], "process_health_check")
    
    @task(1)
    @tag("silenced", "write")
    def toggle_device_silence(self):
        """Silence and unsilence a device"""
        device_ip = random.choice(SAMPLE_DEVICE_IPS)
        
        # Silence the device
        self.client.post(
            f"/api/notifications/silenced-devices/{device_ip}",
            headers=self._auth_headers(),
            name="/api/notifications/silenced-devices/[ip] (silence)"
        )
        
        # Unsilence the device
        self.client.delete(
            f"/api/notifications/silenced-devices/{device_ip}",
            headers=self._auth_headers(),
            name="/api/notifications/silenced-devices/[ip] (unsilence)"
        )
    
    @task(1)
    @tag("scheduled", "write")
    def create_and_cancel_broadcast(self):
        """Create and immediately cancel a scheduled broadcast"""
        headers = self._auth_headers()
        
        # Schedule for 1 hour from now
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
        
        create_response = self.client.post(
            "/api/notifications/scheduled",
            headers=headers,
            json={
                "title": f"Load Test Broadcast {random.randint(1000, 9999)}",
                "message": "This is a load test broadcast that will be cancelled.",
                "scheduled_at": scheduled_time,
                "event_type": "system_status",
                "priority": "low",
            },
            name="/api/notifications/scheduled (create)",
            catch_response=True
        )

        if expect_status(create_response, [200], "create_and_cancel_broadcast.create"):
            data = create_response.json()
            broadcast_id = data.get("id")
            
            if broadcast_id:
                # Cancel the broadcast
                cancel_response = self.client.post(
                    f"/api/notifications/scheduled/{broadcast_id}/cancel",
                    headers=headers,
                    name="/api/notifications/scheduled/[id]/cancel",
                    catch_response=True
                )
                expect_status(cancel_response, [200, 404], "create_and_cancel_broadcast.cancel")
                
                # Delete the broadcast
                delete_response = self.client.delete(
                    f"/api/notifications/scheduled/{broadcast_id}",
                    headers=headers,
                    name="/api/notifications/scheduled/[id] (delete)",
                    catch_response=True
                )
                expect_status(delete_response, [200, 404], "create_and_cancel_broadcast.delete")


# ==================== Event Hooks ====================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n{'='*60}")
    print(f"  Notification Service Load Test")
    print(f"  Auth User: {AUTH_USERNAME}")
    print(f"  Auth Host: {AUTH_HOST}")
    print(f"  Target: {environment.host}")
    print(f"{'='*60}\n")
