"""Models for AI-powered document processing."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SuggestionStatus(str, Enum):
    """Status of an AI suggestion."""

    PENDING = "pending"  # Waiting for user review
    APPROVED = "approved"  # User approved, ready to apply
    REJECTED = "rejected"  # User rejected
    APPLIED = "applied"  # Successfully applied to paperless
    FAILED = "failed"  # Application failed


class JobStatus(str, Enum):
    """Status of a processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingScope(str, Enum):
    """Scope of documents to process."""

    SELECTED = "selected"  # User-selected documents
    UNPROCESSED = "unprocessed"  # Documents not yet AI-processed
    ALL = "all"  # All documents


# =============================================================================
# Suggestion Models
# =============================================================================


class TagSuggestion(BaseModel):
    """A suggested tag for a document."""

    tag_id: Optional[int] = None  # Existing tag ID, or None if new
    tag_name: str
    is_new: bool = False  # True if suggesting creation of new tag
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class DocumentTypeSuggestion(BaseModel):
    """A suggested document type."""

    doc_type_id: Optional[int] = None  # Existing ID, or None if new
    doc_type_name: str
    is_new: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class DocumentSuggestion(BaseModel):
    """AI suggestions for a single document."""

    document_id: int
    current_title: str
    current_tags: List[str] = Field(default_factory=list)
    current_document_type: Optional[str] = None

    # Suggestions (None = no change suggested)
    suggested_title: Optional[str] = None
    suggested_tags: List[TagSuggestion] = Field(default_factory=list)
    suggested_document_type: Optional[DocumentTypeSuggestion] = None

    # Status tracking for each suggestion type
    title_status: SuggestionStatus = SuggestionStatus.PENDING
    tags_status: SuggestionStatus = SuggestionStatus.PENDING
    doc_type_status: SuggestionStatus = SuggestionStatus.PENDING

    # User modifications (if they edited before approving)
    modified_title: Optional[str] = None
    selected_tag_indices: Optional[List[int]] = None  # Which suggested tags to apply
    additional_tag_ids: Optional[List[int]] = None  # Extra tags user added (not from suggestions)
    rejection_notes: Optional[str] = None  # User's explanation for their choices

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error: Optional[str] = None

    def has_pending_suggestions(self) -> bool:
        """Check if there are any pending suggestions."""
        return (
            self.title_status == SuggestionStatus.PENDING
            or self.tags_status == SuggestionStatus.PENDING
            or self.doc_type_status == SuggestionStatus.PENDING
        )

    def has_approved_suggestions(self) -> bool:
        """Check if there are any approved suggestions ready to apply."""
        return (
            self.title_status == SuggestionStatus.APPROVED
            or self.tags_status == SuggestionStatus.APPROVED
            or self.doc_type_status == SuggestionStatus.APPROVED
        )

    def needs_user_action(self) -> bool:
        """Check if this suggestion needs user action (pending review or ready to apply)."""
        return self.has_pending_suggestions() or self.has_approved_suggestions()


# =============================================================================
# Processing Job Models
# =============================================================================


class ProcessingOptions(BaseModel):
    """Options for AI processing."""

    scope: ProcessingScope = ProcessingScope.SELECTED
    document_ids: List[int] = Field(default_factory=list)  # For SELECTED scope

    # What to analyze
    generate_titles: bool = True
    suggest_tags: bool = True
    suggest_document_type: bool = True

    # Behavior
    auto_apply: bool = False  # Auto-apply without review
    skip_already_processed: bool = True  # Skip docs already AI-processed


class ProcessingJob(BaseModel):
    """A batch AI processing job."""

    job_id: str
    options: ProcessingOptions

    # Results
    suggestions: Dict[int, DocumentSuggestion] = Field(
        default_factory=dict
    )  # doc_id -> suggestion

    # Progress tracking
    status: JobStatus = JobStatus.PENDING
    progress_current: int = 0
    progress_total: int = 0
    current_document_title: Optional[str] = None

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error tracking
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# API Request/Response Models
# =============================================================================


class ProcessingRequest(BaseModel):
    """Request to start AI processing."""

    scope: ProcessingScope = ProcessingScope.SELECTED
    document_ids: List[int] = Field(default_factory=list)

    generate_titles: bool = True
    suggest_tags: bool = True
    suggest_document_type: bool = True

    auto_apply: bool = False


class ProcessingResponse(BaseModel):
    """Response after starting AI processing."""

    job_id: str
    status: JobStatus
    document_count: int


class JobStatusResponse(BaseModel):
    """Response for job status query."""

    job_id: str
    status: JobStatus
    progress_current: int
    progress_total: int
    current_document_title: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    errors: List[str] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    """Request to approve/modify suggestions for a document."""

    # Which suggestions to approve (True = approve, False = reject, None = skip)
    approve_title: Optional[bool] = None
    approve_tags: Optional[bool] = None
    approve_document_type: Optional[bool] = None

    # Optional modifications before applying
    modified_title: Optional[str] = None
    selected_tag_indices: Optional[List[int]] = None  # Subset of suggested tags to use

    # Additional tags to add beyond suggestions (list of tag IDs from existing tags)
    additional_tag_ids: Optional[List[int]] = None

    # User's notes explaining their choices (helps AI learn)
    rejection_notes: Optional[str] = None


class BulkApprovalRequest(BaseModel):
    """Request to approve multiple documents at once."""

    document_ids: List[int]
    approve_titles: bool = True
    approve_tags: bool = True
    approve_document_types: bool = True


class ApplyResult(BaseModel):
    """Result of applying suggestions."""

    document_id: int
    success: bool
    title_applied: bool = False
    tags_applied: bool = False
    document_type_applied: bool = False
    tags_created: List[str] = Field(default_factory=list)
    document_type_created: Optional[str] = None
    error: Optional[str] = None


class BulkApplyResponse(BaseModel):
    """Response for bulk apply operation."""

    total: int
    successful: int
    failed: int
    results: List[ApplyResult] = Field(default_factory=list)


# =============================================================================
# Document List Models (for the explorer UI)
# =============================================================================


class DocumentListItem(BaseModel):
    """Document summary for list display."""

    id: int
    title: str
    correspondent: Optional[str] = None
    document_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created: datetime
    added: datetime

    # AI processing status
    has_pending_suggestions: bool = False
    ai_processed_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """Paginated document list response."""

    documents: List[DocumentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentFilters(BaseModel):
    """Filters for document list."""

    search: Optional[str] = None
    has_tags: Optional[bool] = None  # True = has tags, False = no tags
    has_document_type: Optional[bool] = None
    ai_processed: Optional[bool] = None  # True = processed, False = not processed
    has_pending_suggestions: Optional[bool] = None


# =============================================================================
# Taxonomy Models
# =============================================================================


class CreateTagRequest(BaseModel):
    """Request to create a new tag."""

    name: str
    color: Optional[str] = None


class CreateDocumentTypeRequest(BaseModel):
    """Request to create a new document type."""

    name: str
