"""
Configuration for the Metrics Service.

Centralized configuration using Pydantic BaseSettings.
All environment variables are defined here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Metrics service configuration from environment variables."""

    # External service URLs
    health_service_url: str = "http://localhost:8001"
    backend_service_url: str = "http://localhost:8000"

    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0

    # JWT configuration (must match auth service)
    jwt_secret: str = "cartographer-dev-secret-change-in-production"
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


settings = Settings()
