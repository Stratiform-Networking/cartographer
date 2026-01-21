"""
Configuration for the Metrics Service.

Centralized configuration using Pydantic BaseSettings.
All environment variables are defined here.
"""

import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Metrics service configuration from environment variables."""

    # Environment mode
    env: str = "development"

    # External service URLs
    health_service_url: str = "http://localhost:8001"
    backend_service_url: str = "http://localhost:8000"

    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0

    # JWT configuration (must match auth service) - no default, must be set
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"

    # Publishing configuration
    metrics_publish_interval: int = 30

    # Usage tracking configuration
    usage_batch_size: int = 10
    usage_batch_interval_seconds: float = 5.0

    # CORS configuration
    cors_origins: str = "*"

    # API documentation
    disable_docs: bool = False

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
            if not self.jwt_secret:
                raise ValueError(
                    "JWT_SECRET must be set in production. "
                    "Generate one with: openssl rand -hex 32"
                )
        else:
            if "*" in self.cors_origins:
                logger.warning(
                    "CORS is set to allow all origins (*). "
                    "This should be restricted in production."
                )
            if not self.jwt_secret:
                logger.warning("JWT_SECRET is not set. " "Generate one with: openssl rand -hex 32")
        return self


settings = Settings()
