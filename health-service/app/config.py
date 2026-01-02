"""
Centralized configuration for the Health Service.

All environment variables are defined here using Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Health service configuration loaded from environment variables."""

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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
