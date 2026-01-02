"""Database connection and session management for assistant service."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

DATABASE_URL = settings.database_url

# Convert postgres:// to postgresql+asyncpg:// for async support
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Only create engine if DATABASE_URL is set
engine = None
AsyncSessionLocal = None

if DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


async def init_db():
    """Initialize database and create tables."""
    if engine is None:
        print("[Database] DATABASE_URL not configured, skipping database initialization")
        return

    from . import db_models  # Import models to register them

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("[Database] Tables created successfully")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session for FastAPI endpoints."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL environment variable.")

    async with AsyncSessionLocal() as session:
        yield session
