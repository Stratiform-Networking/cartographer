"""
Database configuration and session management for auth service.
Uses the same PostgreSQL database as the main application.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class DatabaseSettings:
    """Database settings loaded from environment variables."""
    
    @property
    def database_url(self) -> str:
        return os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://cartographer:cartographer_secret@localhost:5432/cartographer"
        )


db_settings = DatabaseSettings()

# Create async engine with appropriate settings based on database type
_engine_kwargs = {
    "echo": False,
}

# Only add pool settings for PostgreSQL (not SQLite)
if "sqlite" not in db_settings.database_url:
    _engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    })

engine = create_async_engine(
    db_settings.database_url,
    **_engine_kwargs
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models in auth service."""
    pass


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
