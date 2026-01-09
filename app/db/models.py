"""SQLAlchemy models for persistent data storage."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, CheckConstraint, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


# =============================================================================
# AI Processing Models
# =============================================================================

class AIProcessingJob(Base):
    """Model for AI processing jobs."""

    __tablename__ = "ai_processing_jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    current_document_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    options: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship to suggestions
    suggestions: Mapped[List["AISuggestion"]] = relationship(
        "AISuggestion",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            status.in_(["pending", "processing", "completed", "failed", "cancelled"]),
            name="check_job_status_valid"
        ),
        Index("idx_ai_jobs_status", "status"),
        Index("idx_ai_jobs_created", "created_at"),
    )


class AISuggestion(Base):
    """Model for document AI suggestions."""

    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    job_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("ai_processing_jobs.job_id", ondelete="SET NULL"),
        nullable=True
    )

    # Current document state
    current_title: Mapped[str] = mapped_column(String(500), nullable=False)
    current_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    current_document_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Suggestions
    suggested_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    suggested_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # List of TagSuggestion dicts
    suggested_document_type: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # DocumentTypeSuggestion dict

    # Status for each suggestion type
    title_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    tags_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    doc_type_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # User modifications
    modified_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    selected_tag_indices: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    additional_tag_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    rejection_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship to job
    job: Mapped[Optional["AIProcessingJob"]] = relationship("AIProcessingJob", back_populates="suggestions")

    __table_args__ = (
        Index("idx_ai_suggestions_document_id", "document_id"),
        Index("idx_ai_suggestions_job_id", "job_id"),
        Index("idx_ai_suggestions_status", "title_status", "tags_status", "doc_type_status"),
    )


class AIProcessedDocument(Base):
    """Track which documents have been AI-processed."""

    __tablename__ = "ai_processed_documents"

    document_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_ai_processed_at", "processed_at"),
    )


# =============================================================================
# AI Preferences Models
# =============================================================================

class AITagDefinition(Base):
    """Definition of what a tag means."""

    __tablename__ = "ai_tag_definitions"

    tag_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    examples: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    exclude_contexts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    include_contexts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AIDocTypeDefinition(Base):
    """Definition of what a document type means."""

    __tablename__ = "ai_doc_type_definitions"

    doc_type_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    examples: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    exclude_contexts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    include_contexts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AICorrespondentDefinition(Base):
    """Definition of what a correspondent means."""

    __tablename__ = "ai_correspondent_definitions"

    correspondent_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    standard_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    standard_document_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AITagCorrection(Base):
    """A learned correction from user feedback."""

    __tablename__ = "ai_tag_corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    document_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rejected_tag: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_ai_corrections_rejected_tag", "rejected_tag"),
    )


class AITagApproval(Base):
    """A learned approval pattern from user accepting suggestions."""

    __tablename__ = "ai_tag_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    correspondent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approved_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    document_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approval_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_ai_approvals_correspondent", "correspondent"),
        Index("idx_ai_approvals_doc_type", "document_type"),
    )


class AISettings(Base):
    """Global AI preference settings (singleton table)."""

    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    consistency_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prefer_existing_tags: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_similar_docs_for_tag: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    similar_doc_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    min_tag_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    min_doc_type_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    allow_new_tags: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_new_doc_types: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    new_tag_confidence_boost: Mapped[float] = mapped_column(Float, nullable=False, default=-0.15)
    auto_learn_from_corrections: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatSession(Base):
    """Model for chat sessions."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationship to messages
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.timestamp"
    )

    def to_dict(self, include_messages: bool = False) -> dict:
        """Convert to dictionary for API response."""
        result = {
            "id": str(self.id),
            "name": self.name,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }
        if include_messages:
            result["messages"] = [msg.to_dict() for msg in self.messages]
        return result


class ChatMessage(Base):
    """Model for chat messages."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_documents: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationship to session
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint(role.in_(["user", "assistant"]), name="check_role_valid"),
        Index("idx_messages_session_id", "session_id"),
        Index("idx_messages_timestamp", "session_id", "timestamp"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "role": self.role,
            "content": self.content,
            "method": self.method,
            "sourceDocuments": self.source_documents,
            "timestamp": self.timestamp.isoformat(),
        }
