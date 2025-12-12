"""FastAPI routes for chat history management."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.chat_history import ChatHistoryService
from app.db.connection import test_connection, is_db_configured

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# Request/Response Models

class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""
    name: str = Field(..., description="Name for the session")
    id: Optional[str] = Field(None, description="Optional UUID to use for the session")


class RenameSessionRequest(BaseModel):
    """Request to rename a chat session."""
    name: str = Field(..., description="New name for the session")


class AddMessageRequest(BaseModel):
    """Request to add a message to a session."""
    id: Optional[str] = Field(None, description="Optional UUID for the message")
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    method: Optional[str] = Field(None, description="Query method used")
    sourceDocuments: Optional[List[dict]] = Field(None, description="Source document references")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")


class ChatStatusResponse(BaseModel):
    """Response for chat history status."""
    enabled: bool
    message: str


class SessionResponse(BaseModel):
    """Response for a single session."""
    id: str
    name: str
    createdAt: str
    updatedAt: str
    messages: Optional[List[dict]] = None


class MessageResponse(BaseModel):
    """Response for a single message."""
    id: str
    role: str
    content: str
    method: Optional[str] = None
    sourceDocuments: Optional[List[dict]] = None
    timestamp: str


# Endpoints

@router.get("/status", response_model=ChatStatusResponse)
async def get_chat_status():
    """Check if persistent chat history is enabled and working."""
    if not is_db_configured():
        return ChatStatusResponse(
            enabled=False,
            message="No database configured - using browser storage only"
        )

    result = await test_connection()
    return ChatStatusResponse(
        enabled=result["success"],
        message=result["message"]
    )


@router.post("/test-connection")
async def test_db_connection():
    """Test the database connection."""
    result = await test_connection()
    return result


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions():
    """List all chat sessions."""
    if not await ChatHistoryService.is_available():
        return []

    sessions = await ChatHistoryService.list_sessions()
    return sessions


@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new chat session."""
    if not await ChatHistoryService.is_available():
        raise HTTPException(
            status_code=503,
            detail="Chat history database not configured"
        )

    session = await ChatHistoryService.create_session(
        name=request.name,
        session_id=request.id
    )

    if not session:
        raise HTTPException(
            status_code=500,
            detail="Failed to create session"
        )

    return session


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get a chat session with all messages."""
    if not await ChatHistoryService.is_available():
        raise HTTPException(
            status_code=503,
            detail="Chat history database not configured"
        )

    session = await ChatHistoryService.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return session


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session and all its messages."""
    if not await ChatHistoryService.is_available():
        raise HTTPException(
            status_code=503,
            detail="Chat history database not configured"
        )

    deleted = await ChatHistoryService.delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return {"success": True, "message": "Session deleted"}


@router.put("/sessions/{session_id}", response_model=SessionResponse)
async def rename_session(session_id: str, request: RenameSessionRequest):
    """Rename a chat session."""
    if not await ChatHistoryService.is_available():
        raise HTTPException(
            status_code=503,
            detail="Chat history database not configured"
        )

    session = await ChatHistoryService.rename_session(session_id, request.name)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return session


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def add_message(session_id: str, request: AddMessageRequest):
    """Add a message to a chat session."""
    if not await ChatHistoryService.is_available():
        raise HTTPException(
            status_code=503,
            detail="Chat history database not configured"
        )

    if request.role not in ["user", "assistant"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be 'user' or 'assistant'"
        )

    message = await ChatHistoryService.add_message(
        session_id=session_id,
        role=request.role,
        content=request.content,
        message_id=request.id,
        method=request.method,
        source_documents=request.sourceDocuments,
        timestamp=request.timestamp,
    )

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return message


@router.get("/sessions/{session_id}/messages/recent", response_model=List[MessageResponse])
async def get_recent_messages(session_id: str, limit: int = 6):
    """Get recent messages from a session for conversation context."""
    if not await ChatHistoryService.is_available():
        return []

    messages = await ChatHistoryService.get_recent_messages(session_id, limit)
    return messages
