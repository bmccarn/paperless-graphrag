"""Service for managing persistent chat history."""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.db.connection import get_db_session, is_db_configured
from app.db.models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """Service for CRUD operations on chat sessions and messages."""

    @staticmethod
    async def is_available() -> bool:
        """Check if chat history persistence is available."""
        return is_db_configured()

    @staticmethod
    async def list_sessions() -> List[dict]:
        """List all chat sessions ordered by most recent.

        Returns:
            List of session dictionaries without messages
        """
        async with get_db_session() as session:
            if session is None:
                return []

            result = await session.execute(
                select(ChatSession)
                .order_by(ChatSession.updated_at.desc())
            )
            sessions = result.scalars().all()
            return [s.to_dict(include_messages=False) for s in sessions]

    @staticmethod
    async def create_session(name: str, session_id: Optional[str] = None) -> Optional[dict]:
        """Create a new chat session.

        Args:
            name: Name for the session
            session_id: Optional UUID string to use (for frontend sync)

        Returns:
            Created session dictionary or None if DB unavailable
        """
        async with get_db_session() as session:
            if session is None:
                return None

            chat_session = ChatSession(
                id=uuid.UUID(session_id) if session_id else uuid.uuid4(),
                name=name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(chat_session)
            await session.flush()
            return chat_session.to_dict()

    @staticmethod
    async def get_session(session_id: str) -> Optional[dict]:
        """Get a session with all its messages.

        Args:
            session_id: UUID string of the session

        Returns:
            Session dictionary with messages or None
        """
        async with get_db_session() as session:
            if session is None:
                return None

            try:
                uid = uuid.UUID(session_id)
            except ValueError:
                return None

            result = await session.execute(
                select(ChatSession)
                .options(selectinload(ChatSession.messages))
                .where(ChatSession.id == uid)
            )
            chat_session = result.scalar_one_or_none()

            if chat_session:
                return chat_session.to_dict(include_messages=True)
            return None

    @staticmethod
    async def delete_session(session_id: str) -> bool:
        """Delete a chat session and all its messages.

        Args:
            session_id: UUID string of the session

        Returns:
            True if deleted, False otherwise
        """
        async with get_db_session() as session:
            if session is None:
                return False

            try:
                uid = uuid.UUID(session_id)
            except ValueError:
                return False

            result = await session.execute(
                delete(ChatSession).where(ChatSession.id == uid)
            )
            return result.rowcount > 0

    @staticmethod
    async def rename_session(session_id: str, name: str) -> Optional[dict]:
        """Rename a chat session.

        Args:
            session_id: UUID string of the session
            name: New name for the session

        Returns:
            Updated session dictionary or None
        """
        async with get_db_session() as session:
            if session is None:
                return None

            try:
                uid = uuid.UUID(session_id)
            except ValueError:
                return None

            result = await session.execute(
                select(ChatSession).where(ChatSession.id == uid)
            )
            chat_session = result.scalar_one_or_none()

            if chat_session:
                chat_session.name = name
                chat_session.updated_at = datetime.utcnow()
                await session.flush()
                return chat_session.to_dict()
            return None

    @staticmethod
    async def add_message(
        session_id: str,
        role: str,
        content: str,
        message_id: Optional[str] = None,
        method: Optional[str] = None,
        source_documents: Optional[List[dict]] = None,
        timestamp: Optional[str] = None,
    ) -> Optional[dict]:
        """Add a message to a session.

        Args:
            session_id: UUID string of the session
            role: 'user' or 'assistant'
            content: Message content
            message_id: Optional UUID string (for frontend sync)
            method: Query method used (for assistant messages)
            source_documents: Source document references
            timestamp: ISO timestamp string (optional)

        Returns:
            Created message dictionary or None
        """
        async with get_db_session() as session:
            if session is None:
                return None

            try:
                session_uid = uuid.UUID(session_id)
            except ValueError:
                return None

            # Verify session exists
            result = await session.execute(
                select(ChatSession).where(ChatSession.id == session_uid)
            )
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                return None

            # Parse timestamp if provided
            msg_timestamp = datetime.utcnow()
            if timestamp:
                try:
                    msg_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    pass

            message = ChatMessage(
                id=uuid.UUID(message_id) if message_id else uuid.uuid4(),
                session_id=session_uid,
                role=role,
                content=content,
                method=method,
                source_documents=source_documents,
                timestamp=msg_timestamp,
                created_at=datetime.utcnow(),
            )
            session.add(message)

            # Update session's updated_at
            chat_session.updated_at = datetime.utcnow()

            await session.flush()
            return message.to_dict()

    @staticmethod
    async def get_recent_messages(session_id: str, limit: int = 6) -> List[dict]:
        """Get the most recent messages from a session.

        Args:
            session_id: UUID string of the session
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        async with get_db_session() as session:
            if session is None:
                return []

            try:
                uid = uuid.UUID(session_id)
            except ValueError:
                return []

            result = await session.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == uid)
                .order_by(ChatMessage.timestamp.desc())
                .limit(limit)
            )
            messages = result.scalars().all()
            # Return in chronological order
            return [m.to_dict() for m in reversed(messages)]
