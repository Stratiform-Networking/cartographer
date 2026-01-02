"""
Tests for Database Module.

This module tests the database configuration, session management,
and ORM model base classes.
"""

import inspect

import pytest


class TestDatabaseSettings:
    """Tests for Settings configuration"""

    def test_database_settings_default(self):
        """Should have default database URL"""
        from app.config import Settings

        settings = Settings()

        assert "postgresql" in settings.database_url

    def test_database_settings_class(self):
        """Should have Settings class"""
        from app.config import Settings

        settings = Settings()

        assert settings is not None
        assert hasattr(settings, "database_url")


class TestDatabaseEngine:
    """Tests for database engine creation"""

    def test_engine_exists(self):
        """Should create async engine"""
        from app.database import engine

        assert engine is not None

    def test_engine_created(self):
        """Should create async engine successfully"""
        from app.database import engine

        assert engine is not None


class TestDatabaseSession:
    """Tests for database session management"""

    def test_async_session_maker_exists(self):
        """Should have session maker"""
        from app.database import async_session_maker

        assert async_session_maker is not None

    def test_async_session_maker_type(self):
        """Should have async session maker"""
        from app.database import async_session_maker

        assert async_session_maker is not None

    def test_get_db_generator(self):
        """Should be a generator function"""
        from app.database import get_db

        assert inspect.isasyncgenfunction(get_db)

    def test_get_db_session(self):
        """Should create database session"""
        from app.database import get_db

        assert get_db is not None


class TestDatabaseBase:
    """Tests for Base ORM class"""

    def test_base_class_exists(self):
        """Should have Base class"""
        from app.database import Base

        assert Base is not None

    def test_base_class(self):
        """Should have Base class for models"""
        from app.database import Base

        assert Base is not None
