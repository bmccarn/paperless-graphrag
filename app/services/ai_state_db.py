"""Database-backed state persistence for AI document processing."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AIProcessingJob, AISuggestion, AIProcessedDocument
from app.models.ai_processing import (
    DocumentSuggestion,
    JobStatus,
    ProcessingJob,
    ProcessingOptions,
    SuggestionStatus,
    TagSuggestion,
    DocumentTypeSuggestion,
)

logger = logging.getLogger(__name__)


class AIStateManagerDB:
    """Database-backed manager for AI processing state."""

    def __init__(self, session: AsyncSession):
        """Initialize with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # =========================================================================
    # Job Management
    # =========================================================================

    async def save_job(self, job: ProcessingJob) -> None:
        """Save or update a processing job.

        Args:
            job: The processing job to save
        """
        # Check if job exists
        existing = await self.session.get(AIProcessingJob, job.job_id)

        if existing:
            # Update existing job
            existing.status = job.status.value
            existing.progress_current = job.progress_current
            existing.progress_total = job.progress_total
            existing.current_document_title = job.current_document_title
            existing.options = job.options.model_dump() if job.options else {}
            existing.errors = job.errors
            existing.started_at = job.started_at
            existing.completed_at = job.completed_at
        else:
            # Create new job
            logger.info(
                "Creating new job %s: status=%s, total_documents=%d",
                job.job_id, job.status.value, job.progress_total
            )
            db_job = AIProcessingJob(
                job_id=job.job_id,
                status=job.status.value,
                progress_current=job.progress_current,
                progress_total=job.progress_total,
                current_document_title=job.current_document_title,
                options=job.options.model_dump() if job.options else {},
                errors=job.errors,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
            self.session.add(db_job)

        # Save suggestions
        for doc_id, suggestion in job.suggestions.items():
            await self._save_suggestion(doc_id, suggestion, job.job_id)

        await self.session.flush()

    async def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get a job by ID.

        Args:
            job_id: The job ID

        Returns:
            The job if found, None otherwise
        """
        result = await self.session.execute(
            select(AIProcessingJob)
            .options(selectinload(AIProcessingJob.suggestions))
            .where(AIProcessingJob.job_id == job_id)
        )
        db_job = result.scalar_one_or_none()
        if not db_job:
            return None
        return self._db_job_to_model(db_job)

    async def list_jobs(self, limit: int = 20) -> List[ProcessingJob]:
        """List recent jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of jobs, most recent first
        """
        result = await self.session.execute(
            select(AIProcessingJob)
            .options(selectinload(AIProcessingJob.suggestions))
            .order_by(AIProcessingJob.created_at.desc())
            .limit(limit)
        )
        db_jobs = result.scalars().all()
        return [self._db_job_to_model(j) for j in db_jobs]

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job.

        Args:
            job_id: The job ID to delete

        Returns:
            True if deleted, False if not found
        """
        db_job = await self.session.get(AIProcessingJob, job_id)
        if db_job:
            await self.session.delete(db_job)
            await self.session.flush()
            return True
        return False

    def _db_job_to_model(self, db_job: AIProcessingJob) -> ProcessingJob:
        """Convert database job to Pydantic model."""
        # Load suggestions for this job
        suggestions_dict: Dict[int, DocumentSuggestion] = {}
        for db_sugg in db_job.suggestions:
            suggestions_dict[db_sugg.document_id] = self._db_suggestion_to_model(db_sugg)

        return ProcessingJob(
            job_id=db_job.job_id,
            status=JobStatus(db_job.status),
            progress_current=db_job.progress_current,
            progress_total=db_job.progress_total,
            current_document_title=db_job.current_document_title,
            options=ProcessingOptions(**db_job.options) if db_job.options else ProcessingOptions(),
            errors=db_job.errors or [],
            created_at=db_job.created_at,
            started_at=db_job.started_at,
            completed_at=db_job.completed_at,
            suggestions=suggestions_dict,
        )

    # =========================================================================
    # Suggestion Management
    # =========================================================================

    async def _save_suggestion(
        self, doc_id: int, suggestion: DocumentSuggestion, job_id: Optional[str] = None
    ) -> None:
        """Save or update a suggestion."""
        # Check if suggestion exists
        result = await self.session.execute(
            select(AISuggestion).where(AISuggestion.document_id == doc_id)
        )
        existing = result.scalar_one_or_none()

        suggested_tags_data = [t.model_dump() for t in suggestion.suggested_tags]
        suggested_doc_type_data = (
            suggestion.suggested_document_type.model_dump()
            if suggestion.suggested_document_type
            else None
        )

        if existing:
            # Update existing
            existing.job_id = job_id or existing.job_id
            existing.current_title = suggestion.current_title
            existing.current_tags = suggestion.current_tags
            existing.current_document_type = suggestion.current_document_type
            existing.suggested_title = suggestion.suggested_title
            existing.suggested_tags = suggested_tags_data
            existing.suggested_document_type = suggested_doc_type_data
            existing.title_status = suggestion.title_status.value
            existing.tags_status = suggestion.tags_status.value
            existing.doc_type_status = suggestion.doc_type_status.value
            existing.modified_title = suggestion.modified_title
            existing.selected_tag_indices = suggestion.selected_tag_indices
            existing.additional_tag_ids = suggestion.additional_tag_ids
            existing.rejection_notes = suggestion.rejection_notes
            existing.processed_at = suggestion.processed_at
            existing.error = suggestion.error
        else:
            # Create new
            db_sugg = AISuggestion(
                document_id=doc_id,
                job_id=job_id,
                current_title=suggestion.current_title,
                current_tags=suggestion.current_tags,
                current_document_type=suggestion.current_document_type,
                suggested_title=suggestion.suggested_title,
                suggested_tags=suggested_tags_data,
                suggested_document_type=suggested_doc_type_data,
                title_status=suggestion.title_status.value,
                tags_status=suggestion.tags_status.value,
                doc_type_status=suggestion.doc_type_status.value,
                modified_title=suggestion.modified_title,
                selected_tag_indices=suggestion.selected_tag_indices,
                additional_tag_ids=suggestion.additional_tag_ids,
                rejection_notes=suggestion.rejection_notes,
                created_at=suggestion.created_at,
                processed_at=suggestion.processed_at,
                error=suggestion.error,
            )
            self.session.add(db_sugg)

        # Mark document as processed if it has been
        if suggestion.processed_at:
            await self._mark_processed(doc_id, suggestion.processed_at)

    async def get_pending_suggestions(self) -> List[DocumentSuggestion]:
        """Get all suggestions that need user action (pending or approved).

        Returns:
            List of suggestions needing attention
        """
        # A suggestion needs user action if any status is pending or approved
        result = await self.session.execute(
            select(AISuggestion).where(
                or_(
                    AISuggestion.title_status.in_(["pending", "approved"]),
                    AISuggestion.tags_status.in_(["pending", "approved"]),
                    AISuggestion.doc_type_status.in_(["pending", "approved"]),
                )
            )
        )
        db_suggestions = result.scalars().all()
        return [self._db_suggestion_to_model(s) for s in db_suggestions]

    async def get_suggestion(self, doc_id: int) -> Optional[DocumentSuggestion]:
        """Get suggestion for a specific document.

        Args:
            doc_id: Document ID

        Returns:
            The suggestion if found, None otherwise
        """
        result = await self.session.execute(
            select(AISuggestion).where(AISuggestion.document_id == doc_id)
        )
        db_sugg = result.scalar_one_or_none()
        if db_sugg:
            return self._db_suggestion_to_model(db_sugg)
        return None

    async def update_suggestion(self, doc_id: int, suggestion: DocumentSuggestion) -> None:
        """Update a suggestion.

        Args:
            doc_id: Document ID
            suggestion: Updated suggestion
        """
        await self._save_suggestion(doc_id, suggestion)
        await self.session.flush()

    async def update_suggestion_status(
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
        result = await self.session.execute(
            select(AISuggestion).where(AISuggestion.document_id == doc_id)
        )
        db_sugg = result.scalar_one_or_none()
        if not db_sugg:
            logger.warning("Cannot update status: suggestion for document %d not found", doc_id)
            return None

        if title_status is not None:
            db_sugg.title_status = title_status.value
        if tags_status is not None:
            db_sugg.tags_status = tags_status.value
        if doc_type_status is not None:
            db_sugg.doc_type_status = doc_type_status.value

        await self.session.flush()
        return self._db_suggestion_to_model(db_sugg)

    async def remove_suggestion(self, doc_id: int) -> bool:
        """Remove a suggestion.

        Args:
            doc_id: Document ID

        Returns:
            True if removed, False if not found
        """
        result = await self.session.execute(
            delete(AISuggestion).where(AISuggestion.document_id == doc_id)
        )
        await self.session.flush()
        return result.rowcount > 0

    def _db_suggestion_to_model(self, db_sugg: AISuggestion) -> DocumentSuggestion:
        """Convert database suggestion to Pydantic model."""
        # Parse suggested tags
        suggested_tags = [
            TagSuggestion(**t) for t in (db_sugg.suggested_tags or [])
        ]

        # Parse suggested document type
        suggested_doc_type = None
        if db_sugg.suggested_document_type:
            suggested_doc_type = DocumentTypeSuggestion(**db_sugg.suggested_document_type)

        return DocumentSuggestion(
            document_id=db_sugg.document_id,
            current_title=db_sugg.current_title,
            current_tags=db_sugg.current_tags or [],
            current_document_type=db_sugg.current_document_type,
            suggested_title=db_sugg.suggested_title,
            suggested_tags=suggested_tags,
            suggested_document_type=suggested_doc_type,
            title_status=SuggestionStatus(db_sugg.title_status),
            tags_status=SuggestionStatus(db_sugg.tags_status),
            doc_type_status=SuggestionStatus(db_sugg.doc_type_status),
            modified_title=db_sugg.modified_title,
            selected_tag_indices=db_sugg.selected_tag_indices,
            additional_tag_ids=db_sugg.additional_tag_ids,
            rejection_notes=db_sugg.rejection_notes,
            created_at=db_sugg.created_at,
            processed_at=db_sugg.processed_at,
            error=db_sugg.error,
        )

    # =========================================================================
    # Document Processing Tracking
    # =========================================================================

    async def is_document_processed(self, doc_id: int) -> bool:
        """Check if a document has been AI-processed.

        Args:
            doc_id: Document ID

        Returns:
            True if the document has been processed
        """
        result = await self.session.get(AIProcessedDocument, doc_id)
        return result is not None

    async def get_processed_time(self, doc_id: int) -> Optional[datetime]:
        """Get when a document was AI-processed.

        Args:
            doc_id: Document ID

        Returns:
            Processing timestamp, or None if not processed
        """
        result = await self.session.get(AIProcessedDocument, doc_id)
        return result.processed_at if result else None

    async def mark_document_processed(self, doc_id: int) -> None:
        """Mark a document as AI-processed.

        Args:
            doc_id: Document ID
        """
        await self._mark_processed(doc_id, datetime.utcnow())
        await self.session.flush()

    async def get_processed_document_count(self) -> int:
        """Get count of AI-processed documents.

        Returns:
            Number of processed documents
        """
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(AIProcessedDocument)
        )
        return result.scalar() or 0

    async def _mark_processed(self, doc_id: int, processed_at: datetime) -> None:
        """Internal method to mark a document as processed."""
        existing = await self.session.get(AIProcessedDocument, doc_id)
        if not existing:
            self.session.add(AIProcessedDocument(
                document_id=doc_id,
                processed_at=processed_at,
            ))

    async def clear_document_processed(self, doc_id: int) -> bool:
        """Clear a document's processed status so it can be reprocessed.

        Args:
            doc_id: Document ID

        Returns:
            True if cleared, False if wasn't marked as processed
        """
        # Remove from processed documents
        result = await self.session.execute(
            delete(AIProcessedDocument).where(AIProcessedDocument.document_id == doc_id)
        )
        cleared = result.rowcount > 0

        # Also remove any existing suggestions
        await self.session.execute(
            delete(AISuggestion).where(AISuggestion.document_id == doc_id)
        )

        await self.session.flush()
        return cleared

    async def get_unprocessed_document_ids(self, all_doc_ids: List[int]) -> List[int]:
        """Get document IDs that haven't been AI-processed.

        Args:
            all_doc_ids: List of all document IDs

        Returns:
            List of unprocessed document IDs
        """
        if not all_doc_ids:
            return []

        result = await self.session.execute(
            select(AIProcessedDocument.document_id).where(
                AIProcessedDocument.document_id.in_(all_doc_ids)
            )
        )
        processed_ids = set(result.scalars().all())
        return [doc_id for doc_id in all_doc_ids if doc_id not in processed_ids]

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def cleanup_old_jobs(self, max_age_days: int = 7) -> int:
        """Remove old completed jobs.

        Args:
            max_age_days: Maximum age of jobs to keep

        Returns:
            Number of jobs removed
        """
        logger.info("Cleaning up jobs older than %d days", max_age_days)
        cutoff = datetime.utcnow().timestamp() - (max_age_days * 24 * 60 * 60)
        cutoff_dt = datetime.fromtimestamp(cutoff)

        result = await self.session.execute(
            delete(AIProcessingJob).where(
                and_(
                    AIProcessingJob.status.in_(["completed", "failed", "cancelled"]),
                    AIProcessingJob.completed_at < cutoff_dt,
                )
            )
        )
        await self.session.flush()
        logger.info("Cleaned up %d old jobs", result.rowcount)
        return result.rowcount

    async def clear_all(self) -> None:
        """Clear all AI state (for testing/reset)."""
        logger.warning("Clearing all AI state (suggestions, jobs, processed documents)")
        await self.session.execute(delete(AISuggestion))
        await self.session.execute(delete(AIProcessingJob))
        await self.session.execute(delete(AIProcessedDocument))
        await self.session.flush()
        logger.info("All AI state cleared")
