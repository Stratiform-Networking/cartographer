"""
Database configuration and session management for auth service.
Uses the same PostgreSQL database as the main application.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from .config import settings


# Create async engine with appropriate settings based on database type
_engine_kwargs: dict = {
    "echo": False,
}

# Only add pool settings for PostgreSQL (not SQLite)
if "sqlite" not in settings.database_url:
    _engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    })

engine = create_async_engine(
    settings.database_url,
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


async def get_db() -> AsyncSession:  # type: ignore[misc]
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
