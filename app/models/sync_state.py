"""Sync state tracking for incremental document synchronization."""

import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field


class DocumentSyncRecord(BaseModel):
    """Record of a synced document."""
    paperless_id: int
    content_hash: str
    last_modified: datetime
    last_synced: datetime
    graphrag_doc_id: str


class SyncState(BaseModel):
    """State tracking for document synchronization."""
    documents: Dict[int, DocumentSyncRecord] = Field(default_factory=dict)
    last_full_sync: Optional[datetime] = None
    last_incremental_sync: Optional[datetime] = None
    index_version: int = 0

    def needs_sync(self, doc_id: int, content_hash: str, modified: datetime) -> bool:
        """Check if a document needs to be synced.

        Returns True if:
        - Document is not in sync state (new document)
        - Content hash has changed (content modified)
        - Modified timestamp is newer than last sync (metadata changed)
        """
        if doc_id not in self.documents:
            return True

        record = self.documents[doc_id]

        # Check if content changed
        if record.content_hash != content_hash:
            return True

        # Check if modified since last sync
        if record.last_modified < modified:
            return True

        return False

    def get_deleted_ids(self, current_ids: Set[int]) -> Set[int]:
        """Get IDs of documents that have been deleted from paperless.

        Args:
            current_ids: Set of document IDs currently in paperless

        Returns:
            Set of document IDs that were synced but no longer exist
        """
        synced_ids = set(self.documents.keys())
        return synced_ids - current_ids

    def get_synced_graphrag_ids(self, paperless_ids: List[int]) -> List[str]:
        """Get GraphRAG document IDs for given paperless IDs."""
        return [
            self.documents[pid].graphrag_doc_id
            for pid in paperless_ids
            if pid in self.documents
        ]


def compute_content_hash(content: str, title: str, tags: List[str]) -> str:
    """Compute a hash of document content and key metadata.

    This hash is used to detect changes that require re-indexing.
    Includes title and tags as changes to these affect the document representation.

    Args:
        content: Document text content
        title: Document title
        tags: List of tag names

    Returns:
        First 16 characters of SHA256 hash
    """
    # Normalize and combine relevant fields
    combined = f"{title}|{content}|{'|'.join(sorted(tags))}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]
