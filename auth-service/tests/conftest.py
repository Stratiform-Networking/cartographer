"""
Shared test fixtures for auth service unit tests.
"""
import os
import pytest
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set test environment before imports
os.environ["AUTH_DATA_DIR"] = "/tmp/test-auth-data"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
os.environ["JWT_EXPIRATION_HOURS"] = "24"
os.environ["RESEND_API_KEY"] = ""  # Disable email in tests


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory for tests"""
    data_dir = tmp_path / "auth_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def auth_service_instance(tmp_data_dir):
    """Create a fresh AuthService instance for testing"""
    with patch.dict(os.environ, {"AUTH_DATA_DIR": str(tmp_data_dir)}):
        from app.services.auth_service import AuthService
        service = AuthService()
        service.data_dir = tmp_data_dir
        service.users_file = tmp_data_dir / "users.json"
        service.invites_file = tmp_data_dir / "invites.json"
        service._users = {}
        service._invites = {}
        yield service


@pytest.fixture
def sample_owner(auth_service_instance):
    """Create a sample owner user"""
    from app.models import UserRole, UserInDB
    
    now = datetime.now(timezone.utc)
    owner = UserInDB(
        id="owner-id-123",
        username="owner",
        first_name="Test",
        last_name="Owner",
        email="owner@test.com",
        role=UserRole.OWNER,
        password_hash="$2b$10$test_hash_for_owner",
        created_at=now,
        updated_at=now,
        is_active=True
    )
    auth_service_instance._users[owner.id] = owner
    return owner


@pytest.fixture
def sample_user(auth_service_instance, sample_owner):
    """Create a sample regular user"""
    from app.models import UserRole, UserInDB
    
    now = datetime.now(timezone.utc)
    user = UserInDB(
        id="user-id-456",
        username="testuser",
        first_name="Test",
        last_name="User",
        email="testuser@test.com",
        role=UserRole.READ_ONLY,
        password_hash="$2b$10$test_hash_for_user",
        created_at=now,
        updated_at=now,
        is_active=True
    )
    auth_service_instance._users[user.id] = user
    return user


@pytest.fixture
def sample_readwrite_user(auth_service_instance, sample_owner):
    """Create a sample read-write user"""
    from app.models import UserRole, UserInDB
    
    now = datetime.now(timezone.utc)
    user = UserInDB(
        id="rw-user-id-789",
        username="rwuser",
        first_name="ReadWrite",
        last_name="User",
        email="rwuser@test.com",
        role=UserRole.READ_WRITE,
        password_hash="$2b$10$test_hash_for_rw_user",
        created_at=now,
        updated_at=now,
        is_active=True
    )
    auth_service_instance._users[user.id] = user
    return user


@pytest.fixture
def sample_invite(auth_service_instance, sample_owner):
    """Create a sample pending invitation"""
    from app.models import InviteStatus, InviteInDB, UserRole
    
    now = datetime.now(timezone.utc)
    invite = InviteInDB(
        id="invite-id-123",
        email="invited@test.com",
        role=UserRole.READ_ONLY,
        status=InviteStatus.PENDING,
        invited_by=sample_owner.username,
        invited_by_name=f"{sample_owner.first_name} {sample_owner.last_name}",
        invited_by_id=sample_owner.id,
        token="test-invite-token-abc123",
        created_at=now,
        expires_at=now + timedelta(hours=72)
    )
    auth_service_instance._invites[invite.id] = invite
    return invite


@pytest.fixture
def expired_invite(auth_service_instance, sample_owner):
    """Create an expired invitation"""
    from app.models import InviteStatus, InviteInDB, UserRole
    
    now = datetime.now(timezone.utc)
    invite = InviteInDB(
        id="expired-invite-id",
        email="expired@test.com",
        role=UserRole.READ_ONLY,
        status=InviteStatus.PENDING,
        invited_by=sample_owner.username,
        invited_by_name=f"{sample_owner.first_name} {sample_owner.last_name}",
        invited_by_id=sample_owner.id,
        token="expired-invite-token",
        created_at=now - timedelta(hours=100),
        expires_at=now - timedelta(hours=1)  # Expired
    )
    auth_service_instance._invites[invite.id] = invite
    return invite


@pytest.fixture
def client(auth_service_instance):
    """Create FastAPI test client with mocked auth service"""
    from fastapi.testclient import TestClient
    from app.main import create_app
    
    with patch('app.routers.auth.auth_service', auth_service_instance):
        app = create_app()
        yield TestClient(app)

