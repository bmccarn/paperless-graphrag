"""FastAPI dependency injection for services."""

from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.paperless import PaperlessClient
from app.config import Settings, get_settings
from app.db.connection import get_db_session, is_db_configured
from app.services.graphrag import GraphRAGService
from app.services.graph_reader import GraphReaderService
from app.services.sync import SyncService
from app.services.ai_state_db import AIStateManagerDB
from app.services.ai_preferences_db import AIPreferencesManagerDB
from app.tasks.background import TaskManager, task_manager


def get_task_manager() -> TaskManager:
    """Get the global task manager instance."""
    return task_manager


def get_sync_service(settings: Settings = None) -> SyncService:
    """Get a sync service instance.

    Args:
        settings: Optional settings (uses default if not provided)

    Returns:
        SyncService instance
    """
    if settings is None:
        settings = get_settings()
    return SyncService(settings)


def get_graphrag_service(settings: Settings = None) -> GraphRAGService:
    """Get a GraphRAG service instance.

    Args:
        settings: Optional settings (uses default if not provided)

    Returns:
        GraphRAGService instance
    """
    if settings is None:
        settings = get_settings()
    return GraphRAGService(settings)


async def get_paperless_client(
    settings: Settings = None,
) -> AsyncGenerator[PaperlessClient, None]:
    """Get an initialized paperless client.

    This is an async generator that properly manages the client lifecycle.

    Args:
        settings: Optional settings (uses default if not provided)

    Yields:
        Initialized PaperlessClient
    """
    if settings is None:
        settings = get_settings()

    async with PaperlessClient(settings) as client:
        yield client


def get_graph_reader_service(settings: Settings = None) -> GraphReaderService:
    """Get a graph reader service instance.

    Args:
        settings: Optional settings (uses default if not provided)

    Returns:
        GraphReaderService instance
    """
    if settings is None:
        settings = get_settings()
    output_dir = Path(settings.graphrag_root) / "output"
    return GraphReaderService(output_dir)


# =============================================================================
# AI Processing Dependencies (Database-backed)
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.

    Raises HTTPException if database is not configured.
    """
    if not is_db_configured():
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Please set DATABASE_URL environment variable."
        )

    async with get_db_session() as session:
        if session is None:
            raise HTTPException(
                status_code=503,
                detail="Database connection failed."
            )
        yield session


async def get_ai_state_manager_db(
    session: AsyncSession,
) -> AIStateManagerDB:
    """Get AI state manager with database session."""
    return AIStateManagerDB(session)


async def get_ai_preferences_manager_db(
    session: AsyncSession,
) -> AIPreferencesManagerDB:
    """Get AI preferences manager with database session."""
    return AIPreferencesManagerDB(session)
