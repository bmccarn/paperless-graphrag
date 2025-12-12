"""Database connection management for async PostgreSQL."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_async_session_factory = None


def _get_async_url(database_url: str) -> str:
    """Convert standard postgresql:// URL to async postgresql+asyncpg:// URL."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return database_url


def is_db_configured() -> bool:
    """Check if database is configured."""
    settings = get_settings()
    return bool(settings.database_url)


async def init_db() -> bool:
    """Initialize the database connection pool.

    Returns:
        True if database initialized successfully, False otherwise
    """
    global _engine, _async_session_factory

    settings = get_settings()

    if not settings.database_url:
        logger.info("No database URL configured - chat history will use browser storage only")
        return False

    try:
        async_url = _get_async_url(settings.database_url)

        _engine = create_async_engine(
            async_url,
            echo=False,
            poolclass=NullPool,  # Use NullPool for better connection handling in async context
        )

        _async_session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Test the connection and create tables
        from app.db.models import Base

        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")
        return True

    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        _engine = None
        _async_session_factory = None
        return False


async def close_db() -> None:
    """Close the database connection pool."""
    global _engine, _async_session_factory

    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connection closed")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """Get an async database session.

    Yields:
        AsyncSession if database is configured, None otherwise
    """
    if _async_session_factory is None:
        yield None
        return

    session = _async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def test_connection() -> dict:
    """Test the database connection.

    Returns:
        Dict with success status and message
    """
    settings = get_settings()

    if not settings.database_url:
        return {
            "success": False,
            "message": "No database URL configured"
        }

    try:
        async_url = _get_async_url(settings.database_url)

        # Create temporary engine for testing
        test_engine = create_async_engine(
            async_url,
            echo=False,
            poolclass=NullPool,
        )

        async with test_engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            await result.fetchone()

        await test_engine.dispose()

        return {
            "success": True,
            "message": "Database connection successful"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }
