"""
Centralized configuration for the Auth Service.

All environment variables should be accessed through the settings object.
"""

import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Auth Service configuration loaded from environment variables."""

    # Environment mode
    env: str = "development"

    # === Auth Provider Configuration ===
    # Determines which authentication system to use
    # "local" = bcrypt/JWT (self-hosted)
    # "cloud" = Clerk + WorkOS (cloud-hosted)
    auth_provider: str = "local"

    # Database
    database_url: str = (
        "postgresql+asyncpg://cartographer:cartographer_secret@localhost:5432/cartographer"
    )

    # JWT Configuration (used for both local and cloud modes)
    # No default - must be set via environment variable
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # === Clerk Configuration (cloud mode) ===
    clerk_publishable_key: str | None = None
    clerk_secret_key: str | None = None
    clerk_webhook_secret: str | None = None
    clerk_proxy_url: str | None = None  # Custom domain e.g. https://clerk.yourdomain.com

    # === WorkOS Configuration (enterprise SSO) ===
    workos_api_key: str | None = None
    workos_client_id: str | None = None
    workos_webhook_secret: str | None = None

    # Invitation Settings
    invite_expiration_hours: int = 72

    # Email Configuration (Resend)
    resend_api_key: str = ""
    email_from: str = "Cartographer <noreply@cartographer.app>"
    application_url: str = "http://localhost:5173"

    # External Services
    metrics_service_url: str = "http://localhost:8003"

    # Usage Tracking
    usage_batch_size: int = 10
    usage_batch_interval_seconds: float = 5.0

    # App Configuration
    cors_origins: str = "*"
    disable_docs: bool = False
    allow_open_registration: bool = False

    # Network Limits
    network_limit_per_user: int = 1  # Default max networks per user
    network_limit_exempt_roles: str = "admin,owner"  # Comma-separated roles with unlimited networks
    network_limit_message: str = ""  # Custom message when limit reached (empty = use default)

    @property
    def network_limit_exempt_roles_set(self) -> set[str]:
        """Parse comma-separated exempt roles into a set."""
        return {
            role.strip().lower()
            for role in self.network_limit_exempt_roles.split(",")
            if role.strip()
        }

    @property
    def network_limit_message_text(self) -> str:
        """Get the network limit message, using default if not set."""
        if self.network_limit_message:
            return self.network_limit_message
        return "You've reached your network limit ({limit}). Contact an administrator to increase your limit."

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Validate security-sensitive settings for production environments."""
        if self.env == "production":
            # Strict validation in production
            if "*" in self.cors_origins:
                raise ValueError(
                    "CORS wildcard (*) is not allowed in production. "
                    "Set CORS_ORIGINS to specific allowed origins."
                )
            if not self.jwt_secret:
                raise ValueError(
                    "JWT_SECRET must be set in production. "
                    "Generate one with: openssl rand -hex 32"
                )
        else:
            # Warnings in development
            if "*" in self.cors_origins:
                logger.warning(
                    "CORS is set to allow all origins (*). "
                    "This should be restricted in production."
                )
            if not self.jwt_secret:
                logger.warning("JWT_SECRET is not set. " "Generate one with: openssl rand -hex 32")
        return self


settings = Settings()
