"""
Application configuration using pydantic-settings.
All configuration is read from environment variables.
"""

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Environment
    env: str = "development"
    debug: bool = False

    # Database
    database_url: str = (
        "postgresql+asyncpg://cartographer:cartographer_secret@localhost:5432/cartographer"
    )

    # Service URLs (for microservice communication)
    health_service_url: str = "http://localhost:8001"
    auth_service_url: str = "http://localhost:8002"
    metrics_service_url: str = "http://localhost:8003"
    assistant_service_url: str = "http://localhost:8004"
    notification_service_url: str = "http://localhost:8005"

    # Frontend / SPA serving
    frontend_dist: str = ""  # Empty = auto-detect from project structure
    disable_docs: bool = False
    application_url: str = ""  # Base URL for the application

    # JWT / Auth - no default, must be set via environment variable
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"

    # Usage tracking middleware
    usage_batch_size: int = 10
    usage_batch_interval_seconds: float = 5.0

    # PostHog analytics
    posthog_api_key: str = "phc_wva5vQhVaZRCEUh691CYejTmZK60EdyqkRFToNIBVl2"
    posthog_host: str = "https://us.i.posthog.com"
    posthog_enabled: bool = True

    # Redis for caching
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 2  # DB 2 for backend cache (0=metrics, 1=assistant)
    redis_cache_enabled: bool = True

    # Cache TTLs (seconds)
    cache_ttl_network_list: int = 60  # 1 minute
    cache_ttl_provider_list: int = 300  # 5 minutes
    cache_ttl_config: int = 60  # 1 minute

    # CORS configuration
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resolved_frontend_dist(self) -> Path:
        """Resolve frontend dist path, auto-detecting if not set."""
        if self.frontend_dist:
            return Path(self.frontend_dist)
        # Default: relative to backend/app/config.py -> frontend/dist
        return Path(__file__).resolve().parents[3] / "frontend" / "dist"

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
