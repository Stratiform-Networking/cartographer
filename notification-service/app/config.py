"""
Centralized configuration for the notification service.

All environment variables are loaded through Pydantic BaseSettings,
providing validation, type coercion, and a single source of truth.
"""

import logging
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All configuration is centralized here to:
    - Provide a single source of truth
    - Enable validation and type coercion
    - Support .env files for local development
    - Make configuration discoverable and documented
    """

    # Environment mode
    env: str = "development"

    # Database - must be set via DATABASE_URL environment variable
    database_url: str = ""

    # Data persistence directory for JSON state files
    notification_data_dir: str = "/app/data"

    # Discord Bot Configuration
    discord_bot_token: str = ""
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = "http://localhost:8005/api/auth/discord/callback"

    # Email Configuration (Resend)
    resend_api_key: str = ""
    email_from: str = "Cartographer <notifications@cartographer.app>"

    # External Service URLs
    application_url: str = "http://localhost:5173"
    metrics_service_url: str = "http://localhost:8003"

    # Version Information
    cartographer_version: str = "0.1.1"

    # Application Settings
    cors_origins: str = "*"
    disable_docs: bool = False

    # PostHog analytics
    posthog_api_key: str = ""  # To be set via environment variable
    posthog_host: str = "https://us.i.posthog.com"
    posthog_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def effective_discord_redirect_uri(self) -> str:
        """
        The redirect URI sent to Discord during OAuth.

        Derived from application_url when discord_redirect_uri is not explicitly
        set, keeping the two values automatically in sync across environments.
        An explicit override is only needed if the callback path differs from
        the standard location.
        """
        if self.discord_redirect_uri:
            return self.discord_redirect_uri
        return f"{self.application_url}/api/notifications/auth/discord/callback"

    @property
    def data_dir(self) -> Path:
        """Get the data directory as a Path object."""
        return Path(self.notification_data_dir)

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_discord_configured(self) -> bool:
        """Check if Discord bot is configured."""
        return bool(self.discord_bot_token)

    @property
    def is_email_configured(self) -> bool:
        """Check if email sending is configured."""
        return bool(self.resend_api_key)

    @property
    def is_discord_oauth_configured(self) -> bool:
        """Check if Discord OAuth is configured."""
        return bool(self.discord_client_id and self.discord_client_secret)

    @model_validator(mode="after")
    def validate_discord_redirect_uri(self) -> "Settings":
        """Warn when an explicit redirect URI doesn't match the expected derived value."""
        if self.discord_redirect_uri:
            expected = f"{self.application_url}/api/notifications/auth/discord/callback"
            if self.discord_redirect_uri != expected:
                logger.warning(
                    "DISCORD_REDIRECT_URI (%s) does not match the value derived from "
                    "APPLICATION_URL (%s). Using the explicit value — verify this is intentional.",
                    self.discord_redirect_uri,
                    expected,
                )
        return self

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Validate security-sensitive settings."""
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL must be set. "
                "Example: DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cartographer"
            )
        if "cartographer_secret" in self.database_url:
            raise ValueError(
                "DATABASE_URL contains default credentials. "
                "Set a secure password in the DATABASE_URL environment variable."
            )

        if self.env == "production":
            if "*" in self.cors_origins:
                raise ValueError(
                    "CORS wildcard (*) is not allowed in production. "
                    "Set CORS_ORIGINS to specific allowed origins."
                )
        elif "*" in self.cors_origins:
            logger.warning(
                "CORS is set to allow all origins (*). "
                "This is acceptable for development but should be restricted in production."
            )
        return self


# Global settings instance - import this throughout the application
settings = Settings()


def reload_env_overrides(overrides: dict[str, str]) -> list[str]:
    """
    Hot-reload specific settings fields on the running singleton.

    Called by the /_internal/reload-env endpoint during blue/green swaps
    so that environment-specific values (APPLICATION_URL, DISCORD_REDIRECT_URI, etc.)
    take effect without restarting the container.

    Returns the list of field names that were updated.
    """
    updated = []
    for key, value in overrides.items():
        field_name = key.lower()
        if field_name in settings.model_fields:
            old = getattr(settings, field_name)
            if old != value:
                object.__setattr__(settings, field_name, value)
                updated.append(field_name)
                logger.info("Hot-reloaded %s: %s -> %s", field_name, old, value)
    return updated
