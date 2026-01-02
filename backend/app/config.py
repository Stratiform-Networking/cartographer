"""
Application configuration using pydantic-settings.
All configuration is read from environment variables.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # JWT / Auth
    jwt_secret: str = "cartographer-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    # Usage tracking middleware
    usage_batch_size: int = 10
    usage_batch_interval_seconds: float = 5.0

    # Redis for caching
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 2  # DB 2 for backend cache (0=metrics, 1=assistant)
    redis_cache_enabled: bool = True

    # Cache TTLs (seconds)
    cache_ttl_network_list: int = 60  # 1 minute
    cache_ttl_provider_list: int = 300  # 5 minutes
    cache_ttl_config: int = 60  # 1 minute

    @property
    def resolved_frontend_dist(self) -> Path:
        """Resolve frontend dist path, auto-detecting if not set."""
        if self.frontend_dist:
            return Path(self.frontend_dist)
        # Default: relative to backend/app/config.py -> frontend/dist
        return Path(__file__).resolve().parents[3] / "frontend" / "dist"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
