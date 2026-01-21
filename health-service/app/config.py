"""
Centralized configuration for the Health Service.

All environment variables are defined here using Pydantic BaseSettings.
"""

import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Health service configuration loaded from environment variables."""

    # Environment mode
    env: str = "development"

    # Data persistence directory
    health_data_dir: str = "/app/data"

    # External service URLs
    notification_service_url: str = "http://localhost:8005"
    metrics_service_url: str = "http://localhost:8003"

    # Usage tracking configuration
    usage_batch_size: int = 10
    usage_batch_interval_seconds: float = 5.0

    # CORS configuration
    cors_origins: str = "*"

    # API documentation
    disable_docs: bool = False

    # Security: Disable active health checks (ping, port scan, DNS)
    # When enabled, the service will only store/report agent-provided data
    # and will not perform any outbound network probes
    disable_active_checks: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Validate security-sensitive settings for production environments."""
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


settings = Settings()
