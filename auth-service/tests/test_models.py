"""
Unit tests for auth service models.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    UserRole,
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB,
    LoginRequest,
    LoginResponse,
    TokenPayload,
    SetupStatus,
    ChangePasswordRequest,
    SessionInfo,
    ErrorResponse,
    OwnerSetupRequest,
    InviteStatus,
    InviteCreate,
    InviteResponse,
    InviteInDB,
    AcceptInviteRequest,
    InviteTokenInfo,
)


class TestUserRole:
    """Tests for UserRole enum"""
    
    def test_role_values(self):
        """Should have expected enum values"""
        assert UserRole.OWNER.value == "owner"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.MEMBER.value == "member"


class TestUserBase:
    """Tests for UserBase model"""
    
    def test_valid_user_base(self):
        """Should create valid user base"""
        user = UserBase(
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
    
    def test_username_lowercase(self):
        """Should lowercase username"""
        user = UserBase(
            username="TestUser",
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
        assert user.username == "testuser"
    
    def test_username_validation_start_with_letter(self):
        """Should require username to start with letter"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(
                username="1invalid",
                first_name="Test",
                last_name="User",
                email="test@example.com"
            )
        assert "start with a letter" in str(exc_info.value)
    
    def test_username_validation_allowed_chars(self):
        """Should allow valid username characters"""
        # Valid usernames
        user1 = UserBase(username="test_user", first_name="T", last_name="U", email="t@t.com")
        user2 = UserBase(username="test-user", first_name="T", last_name="U", email="t@t.com")
        user3 = UserBase(username="testUser123", first_name="T", last_name="U", email="t@t.com")
        
        assert user1.username == "test_user"
        assert user2.username == "test-user"
    
    def test_username_invalid_chars(self):
        """Should reject invalid characters"""
        with pytest.raises(ValidationError):
            UserBase(username="test@user", first_name="T", last_name="U", email="t@t.com")
    
    def test_username_min_length(self):
        """Should require minimum length"""
        with pytest.raises(ValidationError):
            UserBase(username="ab", first_name="T", last_name="U", email="t@t.com")
    
    def test_invalid_email(self):
        """Should reject invalid email"""
        with pytest.raises(ValidationError):
            UserBase(username="testuser", first_name="T", last_name="U", email="invalid")


class TestUserCreate:
    """Tests for UserCreate model"""
    
    def test_valid_user_create(self):
        """Should create valid user create request"""
        user = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="securepass123",
            role=UserRole.MEMBER
        )
        assert user.password == "securepass123"
        assert user.role == UserRole.MEMBER
    
    def test_password_min_length(self):
        """Should require minimum password length"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="newuser",
                first_name="New",
                last_name="User",
                email="new@test.com",
                password="short"
            )
        assert "8 characters" in str(exc_info.value)
    
    def test_default_role(self):
        """Should default to read-only role"""
        user = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="securepass123"
        )
        assert user.role == UserRole.MEMBER


class TestOwnerSetupRequest:
    """Tests for OwnerSetupRequest model"""
    
    def test_valid_owner_setup(self):
        """Should create valid owner setup request"""
        request = OwnerSetupRequest(
            username="admin",
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password="adminpass123"
        )
        assert request.username == "admin"
    
    def test_password_validation(self):
        """Should validate password length"""
        with pytest.raises(ValidationError):
            OwnerSetupRequest(
                username="admin",
                first_name="Admin",
                last_name="User",
                email="admin@test.com",
                password="short"
            )


class TestUserUpdate:
    """Tests for UserUpdate model"""
    
    def test_all_fields_optional(self):
        """Should allow all fields to be optional"""
        update = UserUpdate()
        assert update.first_name is None
        assert update.role is None
    
    def test_partial_update(self):
        """Should allow partial updates"""
        update = UserUpdate(first_name="NewName")
        assert update.first_name == "NewName"
        assert update.last_name is None


class TestUserResponse:
    """Tests for UserResponse model"""
    
    def test_user_response(self):
        """Should create valid user response"""
        now = datetime.utcnow()
        response = UserResponse(
            id="user-123",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@test.com",
            role=UserRole.MEMBER,
            created_at=now,
            updated_at=now,
            is_active=True
        )
        assert response.id == "user-123"
        assert response.last_login is None


class TestLoginModels:
    """Tests for login-related models"""
    
    def test_login_request(self):
        """Should create login request"""
        request = LoginRequest(username="testuser", password="testpass")
        assert request.username == "testuser"
    
    def test_login_response(self):
        """Should create login response"""
        now = datetime.utcnow()
        user = UserResponse(
            id="user-123",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@test.com",
            role=UserRole.MEMBER,
            created_at=now,
            updated_at=now
        )
        response = LoginResponse(
            access_token="token123",
            expires_in=3600,
            user=user
        )
        assert response.token_type == "bearer"


class TestTokenPayload:
    """Tests for TokenPayload model"""
    
    def test_token_payload(self):
        """Should create token payload"""
        now = datetime.utcnow()
        payload = TokenPayload(
            sub="user-123",
            username="testuser",
            role=UserRole.OWNER,
            exp=now,
            iat=now
        )
        assert payload.sub == "user-123"
        assert payload.role == UserRole.OWNER


class TestSetupStatus:
    """Tests for SetupStatus model"""
    
    def test_setup_status(self):
        """Should create setup status"""
        status = SetupStatus(
            is_setup_complete=True,
            owner_exists=True,
            total_users=3
        )
        assert status.is_setup_complete is True


class TestChangePasswordRequest:
    """Tests for ChangePasswordRequest model"""
    
    def test_valid_change_password(self):
        """Should create valid request"""
        request = ChangePasswordRequest(
            current_password="oldpass123",
            new_password="newpass123"
        )
        assert request.new_password == "newpass123"
    
    def test_new_password_validation(self):
        """Should validate new password length"""
        with pytest.raises(ValidationError):
            ChangePasswordRequest(
                current_password="oldpass",
                new_password="short"
            )


class TestSessionInfo:
    """Tests for SessionInfo model"""
    
    def test_session_info(self):
        """Should create session info"""
        now = datetime.utcnow()
        user = UserResponse(
            id="user-123",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@test.com",
            role=UserRole.MEMBER,
            created_at=now,
            updated_at=now
        )
        session = SessionInfo(
            user=user,
            permissions=["read:map", "read:health"]
        )
        assert len(session.permissions) == 2


class TestInviteStatus:
    """Tests for InviteStatus enum"""
    
    def test_invite_status_values(self):
        """Should have expected values"""
        assert InviteStatus.PENDING.value == "pending"
        assert InviteStatus.ACCEPTED.value == "accepted"
        assert InviteStatus.EXPIRED.value == "expired"
        assert InviteStatus.REVOKED.value == "revoked"


class TestInviteCreate:
    """Tests for InviteCreate model"""
    
    def test_valid_invite_create(self):
        """Should create valid invite"""
        invite = InviteCreate(
            email="invite@test.com",
            role=UserRole.MEMBER
        )
        assert invite.email == "invite@test.com"
    
    def test_cannot_invite_owner(self):
        """Should reject owner role"""
        with pytest.raises(ValidationError) as exc_info:
            InviteCreate(
                email="invite@test.com",
                role=UserRole.OWNER
            )
        assert "owner role" in str(exc_info.value).lower()
    
    def test_default_role(self):
        """Should default to read-only"""
        invite = InviteCreate(email="invite@test.com")
        assert invite.role == UserRole.MEMBER


class TestInviteResponse:
    """Tests for InviteResponse model"""
    
    def test_invite_response(self):
        """Should create invite response"""
        now = datetime.utcnow()
        response = InviteResponse(
            id="invite-123",
            email="invite@test.com",
            role=UserRole.MEMBER,
            status=InviteStatus.PENDING,
            invited_by="admin",
            invited_by_name="Admin User",
            created_at=now,
            expires_at=now
        )
        assert response.accepted_at is None


class TestAcceptInviteRequest:
    """Tests for AcceptInviteRequest model"""
    
    def test_valid_accept_invite(self):
        """Should create valid request"""
        request = AcceptInviteRequest(
            token="abc123",
            username="newuser",
            first_name="New",
            last_name="User",
            password="securepass123"
        )
        assert request.username == "newuser"
    
    def test_username_validation(self):
        """Should validate username"""
        with pytest.raises(ValidationError):
            AcceptInviteRequest(
                token="abc123",
                username="1invalid",
                first_name="New",
                last_name="User",
                password="securepass123"
            )
    
    def test_password_validation(self):
        """Should validate password"""
        with pytest.raises(ValidationError):
            AcceptInviteRequest(
                token="abc123",
                username="newuser",
                first_name="New",
                last_name="User",
                password="short"
            )


class TestInviteTokenInfo:
    """Tests for InviteTokenInfo model"""
    
    def test_invite_token_info(self):
        """Should create token info"""
        now = datetime.utcnow()
        info = InviteTokenInfo(
            email="invite@test.com",
            role=UserRole.MEMBER,
            invited_by_name="Admin User",
            expires_at=now,
            is_valid=True
        )
        assert info.is_valid is True

