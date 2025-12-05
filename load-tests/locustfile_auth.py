"""
Load Test for Auth Service (port 8002)

Tests authentication, user management, and invitation endpoints.

Authentication:
    Set environment variables before running:
    - LOADTEST_USERNAME: Username for authentication (default: admin)
    - LOADTEST_PASSWORD: Password for authentication (default: admin)
"""

import os
import uuid
import random
from locust import HttpUser, task, between, tag, events
from faker import Faker

fake = Faker()

# Authentication credentials from environment variables
AUTH_USERNAME = os.environ.get("LOADTEST_USERNAME", "admin")
AUTH_PASSWORD = os.environ.get("LOADTEST_PASSWORD", "admin")


class AuthServiceUser(HttpUser):
    """
    Load test user for the Auth Service.
    
    Run with:
        locust -f locustfile_auth.py --host=http://localhost:8002
        
    Or via backend proxy:
        locust -f locustfile_auth.py --host=http://localhost:8000
    """
    
    wait_time = between(1, 3)
    
    access_token = None
    test_user_id = None
    
    def on_start(self):
        """Setup: Authenticate"""
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
            self.test_user_id = user_data.get("id")
            response.success()
        else:
            response.failure(f"Login failed: {response.status_code}")
    
    def _auth_headers(self):
        """Get authorization headers if logged in"""
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}
    
    # ==================== Public Endpoints ====================
    
    @task(10)
    @tag("public", "read")
    def get_setup_status(self):
        """Check setup status - high frequency public endpoint"""
        self.client.get("/api/auth/setup/status")
    
    @task(2)
    @tag("public", "write")
    def failed_login(self):
        """Test invalid login - simulates brute force protection testing"""
        with self.client.post(
            "/api/auth/login",
            json={
                "username": fake.user_name(),
                "password": fake.password()
            },
            name="/api/auth/login (invalid)",
            catch_response=True
        ) as response:
            # 401 is expected for invalid credentials
            if response.status_code == 401:
                response.success()
    
    # ==================== Token Verification ====================
    
    @task(15)
    @tag("auth", "read")
    def verify_token(self):
        """Verify token validity - very high frequency in real apps"""
        headers = self._auth_headers()
        with self.client.post(
            "/api/auth/verify",
            headers=headers,
            name="/api/auth/verify",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
    
    @task(8)
    @tag("auth", "read")
    def get_session(self):
        """Get current session info"""
        headers = self._auth_headers()
        with self.client.get(
            "/api/auth/session",
            headers=headers,
            name="/api/auth/session",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
    
    # ==================== User Profile ====================
    
    @task(6)
    @tag("profile", "read")
    def get_current_profile(self):
        """Get current user profile"""
        headers = self._auth_headers()
        with self.client.get(
            "/api/auth/me",
            headers=headers,
            name="/api/auth/me",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
    
    # ==================== User Management ====================
    
    @task(4)
    @tag("users", "read")
    def list_users(self):
        """List all users"""
        headers = self._auth_headers()
        with self.client.get(
            "/api/auth/users",
            headers=headers,
            name="/api/auth/users",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
    
    @task(2)
    @tag("users", "read")
    def get_user_by_id(self):
        """Get user by ID"""
        if not self.test_user_id:
            user_id = str(uuid.uuid4())
        else:
            user_id = self.test_user_id
        
        headers = self._auth_headers()
        with self.client.get(
            f"/api/auth/users/{user_id}",
            headers=headers,
            name="/api/auth/users/[id]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 403, 404]:
                response.success()
    
    # ==================== Invitation Endpoints ====================
    
    @task(3)
    @tag("invites", "read")
    def list_invites(self):
        """List all invitations"""
        headers = self._auth_headers()
        with self.client.get(
            "/api/auth/invites",
            headers=headers,
            name="/api/auth/invites",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 403]:
                response.success()
    
    @task(2)
    @tag("invites", "read")
    def verify_invite_token(self):
        """Verify an invite token (public endpoint)"""
        fake_token = fake.sha256()[:32]
        with self.client.get(
            f"/api/auth/invite/verify/{fake_token}",
            name="/api/auth/invite/verify/[token]",
            catch_response=True
        ) as response:
            # 404 is expected for invalid tokens
            if response.status_code in [200, 404]:
                response.success()
    
    # ==================== Healthcheck ====================
    
    @task(5)
    @tag("system", "read")
    def healthz(self):
        """Service health check endpoint"""
        self.client.get("/healthz")


class AuthServiceOwnerUser(HttpUser):
    """
    Load test for owner-level operations.
    Separate user class with lower weight for write operations.
    """
    
    wait_time = between(3, 8)
    weight = 1
    
    access_token = None
    created_users = []
    created_invites = []
    
    def on_start(self):
        """Setup: Authenticate as owner"""
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
            response.failure(f"Login failed: {response.status_code}")
    
    def _auth_headers(self):
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}
    
    @task(1)
    @tag("users", "write")
    def create_and_delete_user(self):
        """Create and immediately delete a test user"""
        if not self.access_token:
            return
        
        headers = self._auth_headers()
        username = f"loadtest_{fake.user_name()}_{random.randint(1000, 9999)}"
        
        # Create user
        create_response = self.client.post(
            "/api/auth/users",
            headers=headers,
            json={
                "username": username,
                "password": fake.password(length=12),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "role": "readonly"
            },
            name="/api/auth/users (create)",
            catch_response=True
        )
        
        if create_response.status_code == 200:
            create_response.success()
            user_data = create_response.json()
            user_id = user_data.get("id")
            
            if user_id:
                delete_response = self.client.delete(
                    f"/api/auth/users/{user_id}",
                    headers=headers,
                    name="/api/auth/users/[id] (delete)",
                    catch_response=True
                )
                if delete_response.status_code in [200, 404]:
                    delete_response.success()
        else:
            if create_response.status_code in [400, 401, 403]:
                create_response.success()
    
    @task(1)
    @tag("invites", "write")
    def create_and_revoke_invite(self):
        """Create and immediately revoke an invitation"""
        if not self.access_token:
            return
        
        headers = self._auth_headers()
        email = fake.email()
        
        create_response = self.client.post(
            "/api/auth/invites",
            headers=headers,
            json={
                "email": email,
                "role": "readonly"
            },
            name="/api/auth/invites (create)",
            catch_response=True
        )
        
        if create_response.status_code == 200:
            create_response.success()
            invite_data = create_response.json()
            invite_id = invite_data.get("id")
            
            if invite_id:
                revoke_response = self.client.delete(
                    f"/api/auth/invites/{invite_id}",
                    headers=headers,
                    name="/api/auth/invites/[id] (revoke)",
                    catch_response=True
                )
                if revoke_response.status_code in [200, 400, 404]:
                    revoke_response.success()
        else:
            if create_response.status_code in [400, 401, 403]:
                create_response.success()


# ==================== Event Hooks ====================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n{'='*60}")
    print(f"  Auth Service Load Test")
    print(f"  Auth User: {AUTH_USERNAME}")
    print(f"  Target: {environment.host}")
    print(f"{'='*60}\n")
