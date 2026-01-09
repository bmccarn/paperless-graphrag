"""Models for AI tagging preferences, corrections, and learned rules."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TagDefinition(BaseModel):
    """Definition of what a tag means in the user's taxonomy."""

    tag_name: str
    definition: str = ""  # e.g., "Human health records - doctor visits, prescriptions"
    examples: List[str] = Field(default_factory=list)  # Example document types/contexts
    exclude_contexts: List[str] = Field(default_factory=list)  # e.g., ["veterinary", "pet"]
    include_contexts: List[str] = Field(default_factory=list)  # e.g., ["doctor", "hospital"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TagCorrection(BaseModel):
    """A learned correction from user feedback."""

    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    document_id: Optional[int] = None  # The document where this was learned
    document_snippet: Optional[str] = None  # Brief context from the document
    context_keywords: List[str] = Field(default_factory=list)  # Keywords that trigger this rule
    rejected_tag: str  # The tag that was wrongly suggested
    preferred_tags: List[str] = Field(default_factory=list)  # What should be used instead
    reason: Optional[str] = None  # User's explanation (auto-inferred if not provided)


class TagApproval(BaseModel):
    """A learned approval pattern from user accepting suggestions."""

    id: str
    correspondent: Optional[str] = None  # Correspondent associated with this pattern
    document_type: Optional[str] = None  # Document type associated with this pattern
    approved_tags: List[str] = Field(default_factory=list)  # Tags that were approved together
    document_snippet: Optional[str] = None  # Brief context
    approval_count: int = 1  # How many times this pattern was approved
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentTypeDefinition(BaseModel):
    """Definition of what a document type means."""

    doc_type_name: str
    definition: str = ""
    examples: List[str] = Field(default_factory=list)
    exclude_contexts: List[str] = Field(default_factory=list)
    include_contexts: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CorrespondentDefinition(BaseModel):
    """Definition of what a correspondent means in the user's document library."""

    correspondent_name: str
    definition: str = ""  # e.g., "Chase Bank - our primary bank for personal checking"
    standard_tags: List[str] = Field(default_factory=list)  # Tags commonly associated
    standard_document_type: Optional[str] = None  # Common doc type
    notes: str = ""  # Additional context/notes
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SimilarDocumentExample(BaseModel):
    """A similar document used as a few-shot example."""

    document_id: int
    title: str
    similarity_score: float
    tags: List[str]
    document_type: Optional[str] = None
    correspondent: Optional[str] = None


class AIPreferences(BaseModel):
    """Complete AI preferences state."""

    # Tag definitions: tag_name -> definition
    tag_definitions: Dict[str, TagDefinition] = Field(default_factory=dict)

    # Document type definitions
    doc_type_definitions: Dict[str, DocumentTypeDefinition] = Field(default_factory=dict)

    # Correspondent definitions: correspondent_name -> definition
    correspondent_definitions: Dict[str, CorrespondentDefinition] = Field(default_factory=dict)

    # Learned corrections from user feedback
    corrections: List[TagCorrection] = Field(default_factory=list)

    # Global settings
    settings: "AIPreferenceSettings" = Field(default_factory=lambda: AIPreferenceSettings())

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AIPreferenceSettings(BaseModel):
    """Global settings for AI tagging behavior."""

    # Consistency settings
    consistency_mode: bool = True  # Prioritize consistency over novelty
    prefer_existing_tags: bool = True  # Strongly prefer existing tags over new ones
    min_similar_docs_for_tag: int = 2  # Need N similar docs with a tag to suggest it
    similar_doc_count: int = 5  # Number of similar docs to use as examples

    # Confidence thresholds
    min_tag_confidence: float = 0.6
    min_doc_type_confidence: float = 0.6

    # New taxonomy settings
    allow_new_tags: bool = True  # Allow suggesting new tags
    allow_new_doc_types: bool = True  # Allow suggesting new document types
    new_tag_confidence_boost: float = -0.15  # Penalty for new tags (require higher base confidence)

    # Learning settings
    auto_learn_from_corrections: bool = True


# Request/response models for API

class TagDefinitionRequest(BaseModel):
    """Request to create or update a tag definition."""

    tag_name: str
    definition: str = ""
    examples: List[str] = Field(default_factory=list)
    exclude_contexts: List[str] = Field(default_factory=list)
    include_contexts: List[str] = Field(default_factory=list)


class DocTypeDefinitionRequest(BaseModel):
    """Request to create or update a document type definition."""

    doc_type_name: str
    definition: str = ""
    examples: List[str] = Field(default_factory=list)
    exclude_contexts: List[str] = Field(default_factory=list)
    include_contexts: List[str] = Field(default_factory=list)


class CorrespondentDefinitionRequest(BaseModel):
    """Request to create or update a correspondent definition."""

    correspondent_name: str
    definition: str = ""
    standard_tags: List[str] = Field(default_factory=list)
    standard_document_type: Optional[str] = None
    notes: str = ""


class PreferenceSettingsRequest(BaseModel):
    """Request to update preference settings."""

    consistency_mode: Optional[bool] = None
    prefer_existing_tags: Optional[bool] = None
    min_similar_docs_for_tag: Optional[int] = None
    similar_doc_count: Optional[int] = None
    min_tag_confidence: Optional[float] = None
    min_doc_type_confidence: Optional[float] = None
    allow_new_tags: Optional[bool] = None
    allow_new_doc_types: Optional[bool] = None
    auto_learn_from_corrections: Optional[bool] = None
