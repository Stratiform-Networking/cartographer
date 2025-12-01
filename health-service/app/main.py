import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Cartographer Health Service",
        description="Health monitoring microservice for network devices",
        version="0.1.0"
    )

    # Allow CORS for development and integration with main app
    allowed_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix="/api")

    @app.get("/")
    def root():
        return {
            "service": "Cartographer Health Service",
            "status": "running",
            "version": "0.1.0"
        }

    @app.get("/healthz")
    def healthz():
        """Health check endpoint for container orchestration"""
        return {"status": "healthy"}

    return app


app = create_app()

