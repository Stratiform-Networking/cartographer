"""
Centralized configuration for the notification service.

All environment variables are loaded through Pydantic BaseSettings,
providing validation, type coercion, and a single source of truth.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All configuration is centralized here to:
    - Provide a single source of truth
    - Enable validation and type coercion
    - Support .env files for local development
    - Make configuration discoverable and documented
    """

    # Database
    database_url: str = (
        "postgresql+asyncpg://cartographer:cartographer_secret@localhost:5432/cartographer"
    )

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

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


# Global settings instance - import this throughout the application
settings = Settings()
