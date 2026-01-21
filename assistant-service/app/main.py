"""
Cartographer Assistant Service

An AI-powered assistant microservice that provides network insights
by integrating with multiple LLM providers (OpenAI, Anthropic, Gemini, Ollama).

This service:
- Queries the metrics service for network context
- Supports multiple AI providers with streaming responses
- Provides contextual answers about network topology and health
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers.assistant import router as assistant_router
from .services.usage_middleware import UsageTrackingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    """
    # Startup
    logger.info("Starting Cartographer Assistant Service...")
    logger.info(f"Metrics service URL: {settings.metrics_service_url}")

    # Initialize database
    from .database import init_db

    await init_db()

    # Log provider availability
    from .providers import AnthropicProvider, GeminiProvider, OllamaProvider, OpenAIProvider
    from .providers.base import ProviderConfig

    config = ProviderConfig()
    providers = [
        ("OpenAI", OpenAIProvider(config)),
        ("Anthropic", AnthropicProvider(config)),
        ("Gemini", GeminiProvider(config)),
        ("Ollama", OllamaProvider(config)),
    ]

    for name, provider in providers:
        try:
            available = await provider.is_available()
            status = "✓ configured" if available else "✗ not configured"
            logger.info(f"  {name}: {status}")
        except Exception as e:
            logger.warning(f"  {name}: ✗ error checking ({e})")

    yield

    # Shutdown
    logger.info("Shutting down Cartographer Assistant Service...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Cartographer Assistant Service",
        description="""
AI-powered assistant for the Cartographer network mapping application.

This service provides intelligent assistance by:
- Integrating network topology data from the metrics service
- Supporting multiple AI providers (OpenAI, Anthropic, Gemini, Ollama)
- Streaming responses for real-time interaction
- Answering questions about network health, connectivity, and configuration

## Features

- **Multi-Provider Support**: Choose between OpenAI, Anthropic (Claude), Google Gemini, or local Ollama models
- **Network Context**: Automatically includes network topology as context for relevant answers
- **Streaming**: Real-time response streaming via Server-Sent Events
- **Conversation History**: Maintains context across messages in a session

## Endpoints

- `POST /api/assistant/chat` - Non-streaming chat
- `POST /api/assistant/chat/stream` - Streaming chat (SSE)
- `GET /api/assistant/config` - Get provider configuration
- `GET /api/assistant/context` - Get current network context summary
        """,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.disable_docs else "/docs",
        redoc_url=None if settings.disable_docs else "/redoc",
        openapi_url=None if settings.disable_docs else "/openapi.json",
    )

    # CORS middleware - read origins from settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Usage tracking middleware - reports endpoint usage to metrics service
    app.add_middleware(UsageTrackingMiddleware, service_name="assistant-service")

    # Include routers
    app.include_router(assistant_router, prefix="/api")

    # Root endpoint
    @app.get("/")
    def root():
        """Service information endpoint."""
        return {
            "service": "Cartographer Assistant Service",
            "description": "AI-powered network assistant",
            "status": "running",
            "version": "0.1.0",
            "endpoints": {
                "chat": "/api/assistant/chat",
                "chat_stream": "/api/assistant/chat/stream",
                "config": "/api/assistant/config",
                "docs": "/docs",
                "health": "/healthz",
            },
        }

    # Health check endpoint
    @app.get("/healthz")
    async def healthz():
        """
        Health check endpoint for container orchestration.
        """
        from .providers import AnthropicProvider, GeminiProvider, OllamaProvider, OpenAIProvider
        from .providers.base import ProviderConfig

        config = ProviderConfig()

        # Check which providers are available
        providers_available = {}
        for name, provider_class in [
            ("openai", OpenAIProvider),
            ("anthropic", AnthropicProvider),
            ("gemini", GeminiProvider),
            ("ollama", OllamaProvider),
        ]:
            try:
                provider = provider_class(config)
                providers_available[name] = await provider.is_available()
            except Exception:
                providers_available[name] = False

        any_available = any(providers_available.values())

        return {
            "status": "healthy" if any_available else "degraded",
            "providers": providers_available,
            "any_provider_available": any_available,
        }

    # Readiness check endpoint
    @app.get("/ready")
    async def readyz():
        """
        Readiness check endpoint.
        Service is ready if at least one provider is available.
        """
        from .providers import AnthropicProvider, GeminiProvider, OllamaProvider, OpenAIProvider
        from .providers.base import ProviderConfig

        config = ProviderConfig()

        for provider_class in [OpenAIProvider, AnthropicProvider, GeminiProvider, OllamaProvider]:
            try:
                provider = provider_class(config)
                if await provider.is_available():
                    return {"ready": True}
            except Exception:
                continue

        return {"ready": False, "reason": "No AI providers configured"}

    return app


# Create the application instance
app = create_app()
