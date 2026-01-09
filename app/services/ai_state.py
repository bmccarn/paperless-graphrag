"""State persistence for AI document processing."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.ai_processing import (
    DocumentSuggestion,
    JobStatus,
    ProcessingJob,
    SuggestionStatus,
)

logger = logging.getLogger(__name__)


class AIProcessingState(BaseModel):
    """Persistent state for AI processing."""

    # Active and completed jobs
    jobs: Dict[str, ProcessingJob] = Field(default_factory=dict)

    # Pending suggestions (quick lookup by document ID)
    # Note: These are also stored in jobs, but this provides quick access
    pending_suggestions: Dict[int, DocumentSuggestion] = Field(default_factory=dict)

    # Track which documents have been AI-processed
    processed_documents: Dict[int, datetime] = Field(default_factory=dict)


class AIStateManager:
    """Manager for AI processing state persistence."""

    def __init__(self, state_path: Path):
        """Initialize the state manager.

        Args:
            state_path: Path to the state JSON file
        """
        self.state_path = state_path
        self._state: Optional[AIProcessingState] = None

    def _load_state(self) -> AIProcessingState:
        """Load state from disk."""
        if self._state is not None:
            return self._state

        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                self._state = AIProcessingState(**data)
                logger.info("Loaded AI processing state from %s", self.state_path)
            except Exception as e:
                logger.warning("Failed to load AI state: %s, starting fresh", e)
                self._state = AIProcessingState()
        else:
            self._state = AIProcessingState()

        return self._state

    def _save_state(self) -> None:
        """Save state to disk."""
        if self._state is None:
            return

        try:
            # Ensure directory exists
            self.state_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dict, handling datetime serialization
            state_dict = json.loads(self._state.model_dump_json())

            with open(self.state_path, "w") as f:
                json.dump(state_dict, f, indent=2, default=str)

            logger.debug("Saved AI processing state to %s", self.state_path)
        except Exception as e:
            logger.error("Failed to save AI state: %s", e)

    @property
    def state(self) -> AIProcessingState:
        """Get the current state."""
        return self._load_state()

    # =========================================================================
    # Job Management
    # =========================================================================

    def save_job(self, job: ProcessingJob) -> None:
        """Save or update a processing job.

        Args:
            job: The processing job to save
        """
        state = self._load_state()
        state.jobs[job.job_id] = job

        # Update pending suggestions index
        for doc_id, suggestion in job.suggestions.items():
            if suggestion.needs_user_action():
                state.pending_suggestions[doc_id] = suggestion
            elif doc_id in state.pending_suggestions:
                # Remove from pending if no longer pending
                del state.pending_suggestions[doc_id]

            # Mark document as processed
            if suggestion.processed_at:
                state.processed_documents[doc_id] = suggestion.processed_at

        self._save_state()

    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get a job by ID.

        Args:
            job_id: The job ID

        Returns:
            The job if found, None otherwise
        """
        return self.state.jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> List[ProcessingJob]:
        """List recent jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of jobs, most recent first
        """
        jobs = list(self.state.jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def delete_job(self, job_id: str) -> bool:
        """Delete a job.

        Args:
            job_id: The job ID to delete

        Returns:
            True if deleted, False if not found
        """
        state = self._load_state()
        if job_id in state.jobs:
            del state.jobs[job_id]
            self._save_state()
            return True
        return False

    # =========================================================================
    # Suggestion Management
    # =========================================================================

    def get_pending_suggestions(self) -> List[DocumentSuggestion]:
        """Get all pending suggestions across all jobs.

        Returns:
            List of suggestions with pending status
        """
        return list(self.state.pending_suggestions.values())

    def get_suggestion(self, doc_id: int) -> Optional[DocumentSuggestion]:
        """Get suggestion for a specific document.

        Args:
            doc_id: Document ID

        Returns:
            The suggestion if found, None otherwise
        """
        # First check pending
        if doc_id in self.state.pending_suggestions:
            return self.state.pending_suggestions[doc_id]

        # Then check all jobs
        for job in self.state.jobs.values():
            if doc_id in job.suggestions:
                return job.suggestions[doc_id]

        return None

    def update_suggestion(self, doc_id: int, suggestion: DocumentSuggestion) -> None:
        """Update a suggestion.

        Args:
            doc_id: Document ID
            suggestion: Updated suggestion
        """
        state = self._load_state()

        # Update in pending index
        if suggestion.needs_user_action():
            state.pending_suggestions[doc_id] = suggestion
        elif doc_id in state.pending_suggestions:
            del state.pending_suggestions[doc_id]

        # Update in job
        for job in state.jobs.values():
            if doc_id in job.suggestions:
                job.suggestions[doc_id] = suggestion
                break

        self._save_state()

    def update_suggestion_status(
        self,
        doc_id: int,
        title_status: Optional[SuggestionStatus] = None,
        tags_status: Optional[SuggestionStatus] = None,
        doc_type_status: Optional[SuggestionStatus] = None,
    ) -> Optional[DocumentSuggestion]:
        """Update the status of specific suggestion types.

        Args:
            doc_id: Document ID
            title_status: New status for title suggestion
            tags_status: New status for tags suggestion
            doc_type_status: New status for document type suggestion

        Returns:
            Updated suggestion, or None if not found
        """
        suggestion = self.get_suggestion(doc_id)
        if not suggestion:
            return None

        if title_status is not None:
            suggestion.title_status = title_status
        if tags_status is not None:
            suggestion.tags_status = tags_status
        if doc_type_status is not None:
            suggestion.doc_type_status = doc_type_status

        self.update_suggestion(doc_id, suggestion)
        return suggestion

    def remove_suggestion(self, doc_id: int) -> bool:
        """Remove a suggestion.

        Args:
            doc_id: Document ID

        Returns:
            True if removed, False if not found
        """
        state = self._load_state()
        removed = False

        if doc_id in state.pending_suggestions:
            del state.pending_suggestions[doc_id]
            removed = True

        for job in state.jobs.values():
            if doc_id in job.suggestions:
                del job.suggestions[doc_id]
                removed = True
                break

        if removed:
            self._save_state()

        return removed

    # =========================================================================
    # Document Processing Tracking
    # =========================================================================

    def is_document_processed(self, doc_id: int) -> bool:
        """Check if a document has been AI-processed.

        Args:
            doc_id: Document ID

        Returns:
            True if the document has been processed
        """
        return doc_id in self.state.processed_documents

    def get_processed_time(self, doc_id: int) -> Optional[datetime]:
        """Get when a document was AI-processed.

        Args:
            doc_id: Document ID

        Returns:
            Processing timestamp, or None if not processed
        """
        return self.state.processed_documents.get(doc_id)

    def mark_document_processed(self, doc_id: int) -> None:
        """Mark a document as AI-processed.

        Args:
            doc_id: Document ID
        """
        state = self._load_state()
        state.processed_documents[doc_id] = datetime.utcnow()
        self._save_state()

    def clear_document_processed(self, doc_id: int) -> bool:
        """Clear a document's processed status so it can be reprocessed.

        Args:
            doc_id: Document ID

        Returns:
            True if cleared, False if wasn't marked as processed
        """
        state = self._load_state()
        if doc_id in state.processed_documents:
            del state.processed_documents[doc_id]
            # Also remove any existing suggestions for this document
            if doc_id in state.pending_suggestions:
                del state.pending_suggestions[doc_id]
            for job in state.jobs.values():
                if doc_id in job.suggestions:
                    del job.suggestions[doc_id]
            self._save_state()
            return True
        return False

    def get_unprocessed_document_ids(self, all_doc_ids: List[int]) -> List[int]:
        """Get document IDs that haven't been AI-processed.

        Args:
            all_doc_ids: List of all document IDs

        Returns:
            List of unprocessed document IDs
        """
        processed = set(self.state.processed_documents.keys())
        return [doc_id for doc_id in all_doc_ids if doc_id not in processed]

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup_old_jobs(self, max_age_days: int = 7) -> int:
        """Remove old completed jobs.

        Args:
            max_age_days: Maximum age of jobs to keep

        Returns:
            Number of jobs removed
        """
        state = self._load_state()
        cutoff = datetime.utcnow().timestamp() - (max_age_days * 24 * 60 * 60)

        to_remove = []
        for job_id, job in state.jobs.items():
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                if job.completed_at and job.completed_at.timestamp() < cutoff:
                    to_remove.append(job_id)

        for job_id in to_remove:
            del state.jobs[job_id]

        if to_remove:
            self._save_state()

        return len(to_remove)

    def clear_all(self) -> None:
        """Clear all state (for testing/reset)."""
        self._state = AIProcessingState()
        self._save_state()
