"""FastAPI routes for chat history management."""

import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.chat_history import ChatHistoryService
from app.db.connection import test_connection, is_db_configured
from app.config import Settings, get_settings

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


class GenerateTitleRequest(BaseModel):
    """Request to generate a chat title from user message."""
    message: str = Field(..., description="User message to generate title from")


class GenerateTitleResponse(BaseModel):
    """Response with generated chat title."""
    title: str


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


@router.post("/generate-title", response_model=GenerateTitleResponse)
async def generate_chat_title(
    request: GenerateTitleRequest,
    settings: Settings = Depends(get_settings),
):
    """Generate a meaningful chat title from a user message using AI.

    Uses the configured LLM to create a short, descriptive title
    based on the user's first message in the conversation.
    """
    if not settings.litellm_base_url or not settings.litellm_api_key:
        # Fallback to truncation if LLM not configured
        title = request.message[:40].strip()
        if len(request.message) > 40:
            title += "..."
        return GenerateTitleResponse(title=title)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.litellm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.litellm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.query_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Generate a very short, descriptive title (3-6 words max) for a chat conversation based on the user's message. Return ONLY the title, no quotes, no punctuation at the end, no explanation."
                        },
                        {
                            "role": "user",
                            "content": request.message
                        }
                    ],
                    "max_tokens": 30,
                    "temperature": 0.7,
                },
            )

            if response.status_code == 200:
                data = response.json()
                title = data["choices"][0]["message"]["content"].strip()
                # Clean up the title - remove quotes if present
                title = title.strip('"\'')
                # Limit length just in case
                if len(title) > 60:
                    title = title[:57] + "..."
                return GenerateTitleResponse(title=title)
            else:
                logger.warning("LLM title generation failed: %s", response.text)

    except Exception as e:
        logger.warning("Failed to generate title via LLM: %s", e)

    # Fallback to simple truncation
    title = request.message[:40].strip()
    if len(request.message) > 40:
        title += "..."
    return GenerateTitleResponse(title=title)
