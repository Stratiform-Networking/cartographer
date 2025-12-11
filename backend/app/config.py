"""
Application configuration using pydantic-settings.
All configuration is read from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    env: str = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://cartographer:cartographer_secret@localhost:5432/cartographer"

    # Service URLs (for microservice communication)
    health_service_url: str = "http://localhost:8001"
    auth_service_url: str = "http://localhost:8002"
    metrics_service_url: str = "http://localhost:8003"
    assistant_service_url: str = "http://localhost:8004"
    notification_service_url: str = "http://localhost:8005"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

