"""
Centralized configuration for the Assistant Service.

All environment variables are defined here using Pydantic BaseSettings.
"""

import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment mode
    env: str = "development"

    # Database
    database_url: str = ""

    # External services
    auth_service_url: str = "http://localhost:8002"
    metrics_service_url: str = "http://localhost:8003"

    # JWT Configuration - no default, must be set via environment variable
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"

    # Redis for rate limiting
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 1

    # Caching
    cache_ttl_providers: int = 3600  # 1 hour (provider availability rarely changes)

    # Rate limiting
    assistant_chat_limit_per_day: int = 99999
    assistant_rate_limit_exempt_roles: str = ""  # comma-separated, e.g., "admin,owner"

    # AI Providers - OpenAI
    openai_api_key: str = ""
    openai_base_url: str | None = None

    # AI Providers - Anthropic
    anthropic_api_key: str = ""
    anthropic_base_url: str | None = None

    # AI Providers - Google/Gemini
    google_api_key: str = ""
    gemini_api_key: str = ""  # Alias for google_api_key

    # AI Providers - Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_host: str = ""  # Legacy alias for ollama_base_url

    # Usage tracking
    usage_batch_size: int = 10
    usage_batch_interval_seconds: float = 5.0

    # App configuration
    cors_origins: str = "*"
    disable_docs: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def rate_limit_exempt_roles(self) -> set[str]:
        """Parse comma-separated exempt roles into a set."""
        return {
            role.strip().lower()
            for role in self.assistant_rate_limit_exempt_roles.split(",")
            if role.strip()
        }

    @property
    def effective_ollama_url(self) -> str:
        """Get the effective Ollama URL, checking both config options."""
        return self.ollama_base_url or self.ollama_host or "http://localhost:11434"

    @property
    def effective_google_api_key(self) -> str:
        """Get the effective Google API key, checking both config options."""
        return self.google_api_key or self.gemini_api_key

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
