"""Document models for paperless-ngx and GraphRAG integration."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PaperlessTag(BaseModel):
    """Tag from paperless-ngx."""
    id: int
    name: str
    color: Optional[str] = None
    match: Optional[str] = None
    matching_algorithm: Optional[int] = None
    is_inbox_tag: bool = False


class PaperlessCorrespondent(BaseModel):
    """Correspondent from paperless-ngx."""
    id: int
    name: str
    match: Optional[str] = None
    matching_algorithm: Optional[int] = None


class PaperlessDocumentType(BaseModel):
    """Document type from paperless-ngx."""
    id: int
    name: str
    match: Optional[str] = None
    matching_algorithm: Optional[int] = None


class PaperlessDocument(BaseModel):
    """Document from paperless-ngx API."""
    id: int
    title: str
    content: str = ""
    created: datetime
    modified: datetime
    added: datetime
    correspondent: Optional[PaperlessCorrespondent] = None
    document_type: Optional[PaperlessDocumentType] = None
    tags: List[PaperlessTag] = Field(default_factory=list)
    archive_serial_number: Optional[int] = None
    original_file_name: Optional[str] = None

    @property
    def tag_names(self) -> List[str]:
        """Get list of tag names."""
        return [tag.name for tag in self.tags]


class GraphRAGDocument(BaseModel):
    """Document format for GraphRAG input."""
    id: str
    title: str
    text: str
    source: str = "paperless-ngx"

    @classmethod
    def from_paperless(cls, doc: PaperlessDocument) -> "GraphRAGDocument":
        """Convert a PaperlessDocument to GraphRAG format.

        Creates a document with YAML frontmatter containing metadata,
        followed by the document content.
        """
        correspondent_name = doc.correspondent.name if doc.correspondent else "Unknown"
        doctype_name = doc.document_type.name if doc.document_type else "Unknown"
        tags_str = ", ".join(doc.tag_names) if doc.tag_names else "None"

        metadata_header = f"""---
title: {doc.title}
source: paperless-ngx
document_id: {doc.id}
created: {doc.created.isoformat()}
modified: {doc.modified.isoformat()}
correspondent: {correspondent_name}
document_type: {doctype_name}
tags: [{tags_str}]
archive_serial_number: {doc.archive_serial_number or 'N/A'}
---

# {doc.title}

**Correspondent:** {correspondent_name}
**Document Type:** {doctype_name}
**Tags:** {tags_str}
**Created:** {doc.created.strftime('%Y-%m-%d')}

---

"""
        return cls(
            id=f"paperless_{doc.id}",
            title=doc.title,
            text=metadata_header + (doc.content or ""),
        )
