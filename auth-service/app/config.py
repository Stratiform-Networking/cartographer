"""
Centralized configuration for the Auth Service.

All environment variables should be accessed through the settings object.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Auth Service configuration loaded from environment variables."""

    # Database
    database_url: str = (
        "postgresql+asyncpg://cartographer:cartographer_secret@localhost:5432/cartographer"
    )

    # JWT Configuration
    jwt_secret: str = "cartographer-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
