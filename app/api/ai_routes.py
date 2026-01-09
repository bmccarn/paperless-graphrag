"""FastAPI routes for AI-powered document processing."""

import logging
import re
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.paperless import PaperlessClient
from app.config import Settings, get_settings
from app.models.ai_processing import (
    ApplyResult,
    ApprovalRequest,
    BulkApplyResponse,
    BulkApprovalRequest,
    CreateDocumentTypeRequest,
    CreateTagRequest,
    DocumentFilters,
    DocumentListItem,
    DocumentListResponse,
    DocumentSuggestion,
    JobStatus,
    JobStatusResponse,
    ProcessingJob,
    ProcessingOptions,
    ProcessingRequest,
    ProcessingResponse,
    ProcessingScope,
    SuggestionStatus,
)
from app.models.document import PaperlessDocumentType, PaperlessTag
from app.models.ai_preferences import (
    CorrespondentDefinitionRequest,
    DocTypeDefinitionRequest,
    PreferenceSettingsRequest,
    TagDefinitionRequest,
)
from app.api.dependencies import get_db
from app.services.ai_preferences_db import AIPreferencesManagerDB
from app.services.ai_processor import AIProcessorService
from app.services.ai_state_db import AIStateManagerDB
from app.services.similar_documents import SimilarDocumentFinder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


# =============================================================================
# Dependencies
# =============================================================================


def _get_data_dir() -> Path:
    """Get the data directory path based on environment."""
    if Path("/app").exists():
        return Path("/app/data")
    else:
        return Path(__file__).parent.parent.parent / "data"


async def get_state_manager(
    session: AsyncSession = Depends(get_db)
) -> AIStateManagerDB:
    """Get AI state manager instance (database-backed)."""
    return AIStateManagerDB(session)


async def get_preferences_manager(
    session: AsyncSession = Depends(get_db)
) -> AIPreferencesManagerDB:
    """Get AI preferences manager instance (database-backed)."""
    return AIPreferencesManagerDB(session)


def get_similar_doc_finder(settings: Settings = Depends(get_settings)) -> SimilarDocumentFinder:
    """Get similar document finder instance."""
    # Determine GraphRAG output directory
    graphrag_output = None
    if settings.graphrag_root_dir:
        graphrag_output = Path(settings.graphrag_root_dir) / "output"
        if not graphrag_output.exists():
            graphrag_output = None
    return SimilarDocumentFinder(settings, graphrag_output)


def get_ai_processor(settings: Settings = Depends(get_settings)) -> AIProcessorService:
    """Get AI processor service instance."""
    return AIProcessorService(settings)


async def get_paperless_client(
    settings: Settings = Depends(get_settings),
) -> PaperlessClient:
    """Get a paperless client (must be used as async context manager)."""
    return PaperlessClient(settings)


# =============================================================================
# Document Discovery Endpoints
# =============================================================================


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    has_tags: Optional[bool] = None,
    has_document_type: Optional[bool] = None,
    ai_processed: Optional[bool] = None,
    settings: Settings = Depends(get_settings),
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """List documents with optional filtering.

    Returns a paginated list of documents with their current metadata
    and AI processing status.
    """
    logger.debug(
        "Listing documents: page=%d, page_size=%d, search=%s, has_tags=%s, has_document_type=%s, ai_processed=%s",
        page, page_size, search, has_tags, has_document_type, ai_processed
    )
    if not settings.paperless_url or not settings.paperless_token:
        raise HTTPException(status_code=503, detail="Paperless-ngx not configured")

    async with PaperlessClient(settings) as client:
        # Get all documents (we'll filter in Python for now)
        # TODO: Use paperless API filters for better performance
        documents = []
        async for doc in client.iter_documents():
            # Apply filters
            if has_tags is not None:
                doc_has_tags = len(doc.tags) > 0
                if has_tags != doc_has_tags:
                    continue

            if has_document_type is not None:
                doc_has_type = doc.document_type is not None
                if has_document_type != doc_has_type:
                    continue

            if ai_processed is not None:
                is_processed = await state_manager.is_document_processed(doc.id)
                if ai_processed != is_processed:
                    continue

            if search:
                search_lower = search.lower()
                if search_lower not in doc.title.lower():
                    continue

            # Check for pending suggestions
            suggestion = await state_manager.get_suggestion(doc.id)
            has_pending = suggestion.has_pending_suggestions() if suggestion else False

            documents.append(
                DocumentListItem(
                    id=doc.id,
                    title=doc.title,
                    correspondent=doc.correspondent.name if doc.correspondent else None,
                    document_type=doc.document_type.name if doc.document_type else None,
                    tags=[tag.name for tag in doc.tags],
                    created=doc.created,
                    added=doc.added,
                    has_pending_suggestions=has_pending,
                    ai_processed_at=await state_manager.get_processed_time(doc.id),
                )
            )

        # Sort by created date (newest first)
        documents.sort(key=lambda d: d.created, reverse=True)

        # Paginate
        total = len(documents)
        total_pages = (total + page_size - 1) // page_size
        start = (page - 1) * page_size
        end = start + page_size
        page_documents = documents[start:end]

        logger.info("Returning %d documents (page %d of %d, total=%d)", len(page_documents), page, total_pages, total)
        return DocumentListResponse(
            documents=page_documents,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


@router.get("/documents/{doc_id}")
async def get_document_detail(
    doc_id: int,
    settings: Settings = Depends(get_settings),
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Get detailed information about a single document."""
    logger.debug("Fetching document detail for doc_id=%d", doc_id)
    if not settings.paperless_url or not settings.paperless_token:
        raise HTTPException(status_code=503, detail="Paperless-ngx not configured")

    async with PaperlessClient(settings) as client:
        try:
            doc = await client.get_document(doc_id)
            logger.debug("Found document %d: title='%s'", doc_id, doc.title)
        except Exception as e:
            logger.warning("Document %d not found: %s", doc_id, e)
            raise HTTPException(status_code=404, detail=f"Document not found: {e}")

        suggestion = await state_manager.get_suggestion(doc_id)
        processed_time = await state_manager.get_processed_time(doc_id)

        return {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content[:2000] if doc.content else "",  # Truncate for preview
            "correspondent": doc.correspondent.name if doc.correspondent else None,
            "document_type": doc.document_type.name if doc.document_type else None,
            "tags": [{"id": tag.id, "name": tag.name} for tag in doc.tags],
            "created": doc.created,
            "modified": doc.modified,
            "added": doc.added,
            "ai_processed_at": processed_time,
            "suggestion": suggestion.model_dump() if suggestion else None,
        }


# =============================================================================
# Taxonomy Endpoints
# =============================================================================


@router.get("/tags", response_model=List[dict])
async def list_tags(settings: Settings = Depends(get_settings)):
    """Get all available tags from paperless-ngx."""
    if not settings.paperless_url or not settings.paperless_token:
        raise HTTPException(status_code=503, detail="Paperless-ngx not configured")

    async with PaperlessClient(settings) as client:
        tags = client.get_all_tags()
        return [
            {"id": tag.id, "name": tag.name, "color": tag.color}
            for tag in sorted(tags, key=lambda t: t.name.lower())
        ]


@router.get("/document-types", response_model=List[dict])
async def list_document_types(settings: Settings = Depends(get_settings)):
    """Get all available document types from paperless-ngx."""
    if not settings.paperless_url or not settings.paperless_token:
        raise HTTPException(status_code=503, detail="Paperless-ngx not configured")

    async with PaperlessClient(settings) as client:
        doc_types = client.get_all_document_types()
        return [
            {"id": dt.id, "name": dt.name}
            for dt in sorted(doc_types, key=lambda d: d.name.lower())
        ]


@router.post("/tags", response_model=dict)
async def create_tag(
    request: CreateTagRequest,
    settings: Settings = Depends(get_settings),
):
    """Create a new tag in paperless-ngx."""
    if not settings.paperless_url or not settings.paperless_token:
        raise HTTPException(status_code=503, detail="Paperless-ngx not configured")

    async with PaperlessClient(settings) as client:
        try:
            tag = await client.create_tag(name=request.name, color=request.color)
            return {"id": tag.id, "name": tag.name, "color": tag.color}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create tag: {e}")


@router.post("/document-types", response_model=dict)
async def create_document_type(
    request: CreateDocumentTypeRequest,
    settings: Settings = Depends(get_settings),
):
    """Create a new document type in paperless-ngx."""
    if not settings.paperless_url or not settings.paperless_token:
        raise HTTPException(status_code=503, detail="Paperless-ngx not configured")

    async with PaperlessClient(settings) as client:
        try:
            doc_type = await client.create_document_type(name=request.name)
            return {"id": doc_type.id, "name": doc_type.name}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create document type: {e}")


@router.get("/correspondents", response_model=List[dict])
async def list_correspondents(settings: Settings = Depends(get_settings)):
    """Get all available correspondents from paperless-ngx."""
    if not settings.paperless_url or not settings.paperless_token:
        raise HTTPException(status_code=503, detail="Paperless-ngx not configured")

    async with PaperlessClient(settings) as client:
        correspondents = client.get_all_correspondents()
        return [
            {"id": c.id, "name": c.name}
            for c in sorted(correspondents, key=lambda c: c.name.lower())
        ]


# =============================================================================
# AI Processing Endpoints
# =============================================================================


async def run_processing_job(
    job_id: str,
    options: ProcessingOptions,
    settings: Settings,
):
    """Background task to run AI processing.

    Creates its own database session for the background task lifecycle.
    """
    import traceback
    from app.db.connection import get_db_session

    logger.info("Starting AI processing job %s", job_id)
    print(f"[DEBUG] Starting AI processing job {job_id}")

    job = ProcessingJob(job_id=job_id, options=options)

    # Use database session for the entire background task
    async with get_db_session() as session:
        if session is None:
            logger.error("Database not available for background processing job %s", job_id)
            return

        state_manager = AIStateManagerDB(session)
        preferences_manager = AIPreferencesManagerDB(session)

        await state_manager.save_job(job)
        print(f"[DEBUG] Saved initial job state")

        try:
            processor = AIProcessorService(settings)
            print(f"[DEBUG] Created AIProcessorService")

            # Initialize similar document finder for RAG-based consistency
            graphrag_output = None
            if settings.graphrag_root:
                graphrag_output = Path(settings.graphrag_root) / "output"
                if not graphrag_output.exists():
                    logger.warning("GraphRAG output dir not found: %s", graphrag_output)
                    graphrag_output = None
            similar_doc_finder = SimilarDocumentFinder(settings, graphrag_output)
            print(f"[DEBUG] Created SimilarDocumentFinder")

            logger.info(
                "Processing with preferences_manager=%s, similar_doc_finder=%s (graphrag=%s)",
                "enabled",
                "enabled" if graphrag_output else "disabled",
                graphrag_output,
            )

            async with PaperlessClient(settings) as client:
                print(f"[DEBUG] Connected to PaperlessClient")
                # Determine which documents to process
                if options.scope == ProcessingScope.SELECTED:
                    doc_ids = options.document_ids
                elif options.scope == ProcessingScope.UNPROCESSED:
                    all_ids = await client.get_all_document_ids()
                    doc_ids = await state_manager.get_unprocessed_document_ids(all_ids)
                else:  # ALL
                    doc_ids = await client.get_all_document_ids()

                # Filter out already-processed if requested
                if options.skip_already_processed and options.scope != ProcessingScope.UNPROCESSED:
                    doc_ids = await state_manager.get_unprocessed_document_ids(doc_ids)

                options.document_ids = doc_ids
                job.options = options
                print(f"[DEBUG] Processing {len(doc_ids)} documents")

                # Define async progress callback
                async def save_progress(cur: int, total: int, title: str) -> None:
                    await state_manager.save_job(job)

                # Process documents with preferences and similar doc context
                job = await processor.process_batch(
                    paperless=client,
                    job=job,
                    progress_callback=save_progress,
                    preferences_manager=preferences_manager,
                    similar_doc_finder=similar_doc_finder,
                )

        except Exception as e:
            logger.error("Processing job %s failed: %s", job_id, e)
            print(f"[DEBUG] Processing job {job_id} failed: {e}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            job.status = JobStatus.FAILED
            job.errors.append(str(e))

        await state_manager.save_job(job)
        logger.info("Completed AI processing job %s: %s", job_id, job.status)
        print(f"[DEBUG] Completed AI processing job {job_id}: {job.status}")


@router.post("/process", response_model=ProcessingResponse)
async def start_processing(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Start AI processing for selected documents.

    Returns a job ID for tracking progress.
    """
    logger.info(
        "Starting AI processing: scope=%s, doc_count=%d, titles=%s, tags=%s, doc_type=%s, auto_apply=%s",
        request.scope, len(request.document_ids) if request.document_ids else 0,
        request.generate_titles, request.suggest_tags, request.suggest_document_type, request.auto_apply
    )
    if not settings.paperless_url or not settings.paperless_token:
        logger.error("Cannot start processing: Paperless-ngx not configured")
        raise HTTPException(status_code=503, detail="Paperless-ngx not configured")

    if not settings.litellm_base_url or not settings.litellm_api_key:
        logger.error("Cannot start processing: LiteLLM not configured")
        raise HTTPException(status_code=503, detail="LiteLLM not configured")

    # Validate request
    if request.scope == ProcessingScope.SELECTED and not request.document_ids:
        raise HTTPException(
            status_code=400,
            detail="document_ids required when scope is 'selected'",
        )

    job_id = str(uuid.uuid4())

    options = ProcessingOptions(
        scope=request.scope,
        document_ids=request.document_ids,
        generate_titles=request.generate_titles,
        suggest_tags=request.suggest_tags,
        suggest_document_type=request.suggest_document_type,
        auto_apply=request.auto_apply,
    )

    # Get document count for response
    doc_count = len(request.document_ids) if request.document_ids else 0

    # Create and save the job BEFORE starting the background task
    # This prevents race conditions where the frontend polls before the job exists
    job = ProcessingJob(job_id=job_id, options=options)
    job.progress_total = doc_count
    await state_manager.save_job(job)
    # Commit immediately so the job is visible to other sessions (polling requests)
    await state_manager.session.commit()

    # Start background processing
    background_tasks.add_task(
        run_processing_job,
        job_id=job_id,
        options=options,
        settings=settings,
    )

    logger.info("Created processing job %s for %d documents", job_id, doc_count)
    return ProcessingResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        document_count=doc_count,
    )


@router.get("/jobs", response_model=List[JobStatusResponse])
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """List all processing jobs."""
    jobs = await state_manager.list_jobs(limit=limit)
    return [
        JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress_current=job.progress_current,
            progress_total=job.progress_total,
            current_document_title=job.current_document_title,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            errors=job.errors,
        )
        for job in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Get status of a processing job."""
    job = await state_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress_current=job.progress_current,
        progress_total=job.progress_total,
        current_document_title=job.current_document_title,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        errors=job.errors,
    )


# =============================================================================
# Suggestion Management Endpoints
# =============================================================================


@router.get("/suggestions", response_model=List[dict])
async def list_pending_suggestions(
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Get all pending suggestions awaiting approval."""
    suggestions = await state_manager.get_pending_suggestions()
    return [s.model_dump() for s in suggestions]


@router.get("/suggestions/{doc_id}")
async def get_document_suggestions(
    doc_id: int,
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Get suggestions for a specific document."""
    suggestion = await state_manager.get_suggestion(doc_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="No suggestions found for this document")

    return suggestion.model_dump()


@router.post("/suggestions/{doc_id}/approve")
async def approve_suggestion(
    doc_id: int,
    request: ApprovalRequest,
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Approve or reject suggestions for a document."""
    logger.debug(
        "Approving suggestion for doc %d: title=%s, tags=%s, doc_type=%s",
        doc_id, request.approve_title, request.approve_tags, request.approve_document_type
    )
    suggestion = await state_manager.get_suggestion(doc_id)
    if not suggestion:
        logger.warning("Cannot approve: no suggestion found for document %d", doc_id)
        raise HTTPException(status_code=404, detail="No suggestions found for this document")

    # Update statuses based on request
    if request.approve_title is not None:
        if request.approve_title:
            suggestion.title_status = SuggestionStatus.APPROVED
            if request.modified_title:
                suggestion.modified_title = request.modified_title
        else:
            suggestion.title_status = SuggestionStatus.REJECTED

    if request.approve_tags is not None:
        if request.approve_tags:
            suggestion.tags_status = SuggestionStatus.APPROVED
            if request.selected_tag_indices is not None:
                suggestion.selected_tag_indices = request.selected_tag_indices
            if request.additional_tag_ids is not None:
                suggestion.additional_tag_ids = request.additional_tag_ids
        else:
            suggestion.tags_status = SuggestionStatus.REJECTED

    # Store rejection notes if provided (for learning)
    if request.rejection_notes:
        suggestion.rejection_notes = request.rejection_notes

    if request.approve_document_type is not None:
        if request.approve_document_type:
            suggestion.doc_type_status = SuggestionStatus.APPROVED
        else:
            suggestion.doc_type_status = SuggestionStatus.REJECTED

    await state_manager.update_suggestion(doc_id, suggestion)

    logger.info(
        "Updated suggestion approval for doc %d: title=%s, tags=%s, doc_type=%s",
        doc_id, suggestion.title_status.value, suggestion.tags_status.value, suggestion.doc_type_status.value
    )
    return {"success": True, "suggestion": suggestion.model_dump()}


@router.post("/suggestions/{doc_id}/reject")
async def reject_suggestion(
    doc_id: int,
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Reject all suggestions for a document."""
    logger.debug("Rejecting all suggestions for document %d", doc_id)
    suggestion = await state_manager.get_suggestion(doc_id)
    if not suggestion:
        logger.warning("Cannot reject: no suggestion found for document %d", doc_id)
        raise HTTPException(status_code=404, detail="No suggestions found for this document")

    suggestion.title_status = SuggestionStatus.REJECTED
    suggestion.tags_status = SuggestionStatus.REJECTED
    suggestion.doc_type_status = SuggestionStatus.REJECTED

    await state_manager.update_suggestion(doc_id, suggestion)

    logger.info("Rejected all suggestions for document %d", doc_id)
    return {"success": True}


@router.post("/suggestions/{doc_id}/apply", response_model=ApplyResult)
async def apply_suggestion(
    doc_id: int,
    settings: Settings = Depends(get_settings),
    state_manager: AIStateManagerDB = Depends(get_state_manager),
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Apply approved suggestions to paperless-ngx.

    Also learns from user rejections to improve future suggestions.
    """
    logger.info("Applying suggestions for document %d", doc_id)
    suggestion = await state_manager.get_suggestion(doc_id)
    if not suggestion:
        logger.warning("Cannot apply: no suggestion found for document %d", doc_id)
        raise HTTPException(status_code=404, detail="No suggestions found for this document")

    if not suggestion.has_approved_suggestions():
        logger.warning("Cannot apply: no approved suggestions for document %d", doc_id)
        raise HTTPException(status_code=400, detail="No approved suggestions to apply")

    result = ApplyResult(document_id=doc_id, success=True)

    async with PaperlessClient(settings) as client:
        try:
            # Fetch the document (we need content for learning)
            doc = await client.get_document(doc_id)

            # Collect updates
            title = None
            tags = None
            document_type = None

            # Title
            if suggestion.title_status == SuggestionStatus.APPROVED:
                title = suggestion.modified_title or suggestion.suggested_title
                if title:
                    result.title_applied = True

            # Tags
            if suggestion.tags_status == SuggestionStatus.APPROVED:
                # Get which suggested tags to apply
                if suggestion.selected_tag_indices is not None and suggestion.suggested_tags:
                    selected_tags = [
                        suggestion.suggested_tags[i]
                        for i in suggestion.selected_tag_indices
                        if i < len(suggestion.suggested_tags)
                    ]
                    # Learn from rejected tags
                    rejected_indices = set(range(len(suggestion.suggested_tags))) - set(
                        suggestion.selected_tag_indices
                    )
                    rejected_tags = [
                        suggestion.suggested_tags[i]
                        for i in rejected_indices
                        if i < len(suggestion.suggested_tags)
                    ]
                    accepted_tag_names = [t.tag_name for t in selected_tags]

                    # Include additional tags in accepted names for learning
                    if suggestion.additional_tag_ids:
                        all_tags = client.get_all_tags()
                        tag_id_to_name = {t.id: t.name for t in all_tags}
                        for tag_id in suggestion.additional_tag_ids:
                            if tag_id in tag_id_to_name:
                                accepted_tag_names.append(tag_id_to_name[tag_id])

                    # Build reason string from user notes or auto-generate
                    reason = suggestion.rejection_notes or (
                        f"User rejected suggested tags and chose: {', '.join(accepted_tag_names)}"
                    )

                    # Learn from each rejection
                    for rejected in rejected_tags:
                        if accepted_tag_names:  # Only learn if there are accepted alternatives
                            await preferences.add_correction(
                                rejected_tag=rejected.tag_name,
                                preferred_tags=accepted_tag_names,
                                document_id=doc_id,
                                document_snippet=(doc.content or "")[:500],  # More context for AI
                                reason=reason,  # User's notes - AI will reason about this
                            )
                            logger.info(
                                "=== LEARNED CORRECTION ===\n"
                                "  Document: %d ('%s')\n"
                                "  Rejected tag: '%s'\n"
                                "  Preferred tags: %s\n"
                                "  User reason: %s\n"
                                "  Doc snippet: %s...",
                                doc_id,
                                doc.title[:40],
                                rejected.tag_name,
                                accepted_tag_names,
                                reason[:100] if reason else "(auto-generated)",
                                (doc.content or "")[:100],
                            )
                elif suggestion.suggested_tags:
                    selected_tags = suggestion.suggested_tags
                else:
                    selected_tags = []

                tag_ids = []
                for tag_suggestion in selected_tags:
                    if tag_suggestion.is_new:
                        # Create the new tag
                        new_tag = await client.create_tag(tag_suggestion.tag_name)
                        tag_ids.append(new_tag.id)
                        result.tags_created.append(tag_suggestion.tag_name)
                    else:
                        tag_ids.append(tag_suggestion.tag_id)

                # Add additional tags (user-selected beyond suggestions)
                if suggestion.additional_tag_ids:
                    tag_ids.extend(suggestion.additional_tag_ids)

                if tag_ids:
                    # Get current tags and merge
                    current_tag_ids = [t.id for t in doc.tags]
                    # Add new tags to existing (don't replace)
                    tags = list(set(current_tag_ids + tag_ids))
                    result.tags_applied = True

            # Document type
            if (
                suggestion.doc_type_status == SuggestionStatus.APPROVED
                and suggestion.suggested_document_type
            ):
                dt = suggestion.suggested_document_type
                if dt.is_new:
                    # Create the new document type
                    new_dt = await client.create_document_type(dt.doc_type_name)
                    document_type = new_dt.id
                    result.document_type_created = dt.doc_type_name
                else:
                    document_type = dt.doc_type_id
                result.document_type_applied = True

            # Apply updates
            if title or tags or document_type:
                await client.update_document(
                    doc_id=doc_id,
                    title=title,
                    tags=tags,
                    document_type=document_type,
                )

            # Mark as applied
            if result.title_applied:
                suggestion.title_status = SuggestionStatus.APPLIED
            if result.tags_applied:
                suggestion.tags_status = SuggestionStatus.APPLIED
            if result.document_type_applied:
                suggestion.doc_type_status = SuggestionStatus.APPLIED

            await state_manager.update_suggestion(doc_id, suggestion)

            # Learn from approval - track positive patterns
            if result.tags_applied and tags:
                # Get tag names for the applied tags
                all_tags_list = client.get_all_tags()
                tag_id_to_name = {t.id: t.name for t in all_tags_list}
                applied_tag_names = [tag_id_to_name.get(tid, "") for tid in tags if tid in tag_id_to_name]
                applied_tag_names = [n for n in applied_tag_names if n]  # Filter empty

                if applied_tag_names:
                    correspondent_name = doc.correspondent.name if doc.correspondent else None
                    doc_type_name = doc.document_type.name if doc.document_type else None
                    await preferences.learn_from_tag_approval(
                        correspondent=correspondent_name,
                        document_type=doc_type_name,
                        approved_tags=applied_tag_names,
                        document_snippet=(doc.content or "")[:200],
                    )

            logger.info(
                "Applied suggestions for doc %d: title=%s, tags=%s, doc_type=%s",
                doc_id, result.title_applied, result.tags_applied, result.document_type_applied
            )

        except Exception as e:
            logger.error("Failed to apply suggestions for doc %d: %s", doc_id, e)
            result.success = False
            result.error = str(e)

    return result


@router.post("/suggestions/apply-all", response_model=BulkApplyResponse)
async def apply_all_approved(
    settings: Settings = Depends(get_settings),
    state_manager: AIStateManagerDB = Depends(get_state_manager),
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Apply all approved suggestions."""
    logger.info("Applying all approved suggestions")
    suggestions = await state_manager.get_pending_suggestions()
    approved = [s for s in suggestions if s.has_approved_suggestions()]
    logger.info("Found %d approved suggestions to apply", len(approved))

    results = []
    successful = 0
    failed = 0

    for suggestion in approved:
        try:
            # Reuse the single apply logic
            result = await apply_suggestion(
                doc_id=suggestion.document_id,
                settings=settings,
                state_manager=state_manager,
                preferences=preferences,
            )
            results.append(result)
            if result.success:
                successful += 1
            else:
                failed += 1
        except Exception as e:
            results.append(
                ApplyResult(
                    document_id=suggestion.document_id,
                    success=False,
                    error=str(e),
                )
            )
            failed += 1

    logger.info("Bulk apply completed: %d successful, %d failed out of %d", successful, failed, len(approved))
    return BulkApplyResponse(
        total=len(approved),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.post("/suggestions/bulk-approve")
async def bulk_approve(
    request: BulkApprovalRequest,
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Approve suggestions for multiple documents at once."""
    approved_count = 0

    for doc_id in request.document_ids:
        suggestion = await state_manager.get_suggestion(doc_id)
        if not suggestion:
            continue

        if request.approve_titles and suggestion.suggested_title:
            suggestion.title_status = SuggestionStatus.APPROVED
        if request.approve_tags and suggestion.suggested_tags:
            suggestion.tags_status = SuggestionStatus.APPROVED
        if request.approve_document_types and suggestion.suggested_document_type:
            suggestion.doc_type_status = SuggestionStatus.APPROVED

        await state_manager.update_suggestion(doc_id, suggestion)
        approved_count += 1

    return {"success": True, "approved_count": approved_count}


# =============================================================================
# Utility Endpoints
# =============================================================================


@router.get("/stats")
async def get_ai_stats(
    settings: Settings = Depends(get_settings),
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Get AI processing statistics."""
    pending = await state_manager.get_pending_suggestions()
    jobs = await state_manager.list_jobs(limit=100)
    processed_count = await state_manager.get_processed_document_count()

    processing_jobs = [j for j in jobs if j.status == JobStatus.PROCESSING]
    completed_jobs = [j for j in jobs if j.status == JobStatus.COMPLETED]

    return {
        "pending_suggestions": len(pending),
        "processed_documents": processed_count,
        "active_jobs": len(processing_jobs),
        "completed_jobs": len(completed_jobs),
        "total_jobs": len(jobs),
    }


@router.delete("/suggestions/{doc_id}")
async def delete_suggestion(
    doc_id: int,
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Delete suggestions for a document."""
    removed = await state_manager.remove_suggestion(doc_id)
    if not removed:
        raise HTTPException(status_code=404, detail="No suggestions found for this document")

    return {"success": True}


@router.post("/documents/{doc_id}/reprocess")
async def mark_for_reprocess(
    doc_id: int,
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Clear a document's processed status so it can be reprocessed.

    This removes any existing suggestions and marks the document as unprocessed.
    """
    cleared = await state_manager.clear_document_processed(doc_id)
    return {"success": True, "was_processed": cleared}


@router.post("/suggestions/{doc_id}/reset")
async def reset_suggestion(
    doc_id: int,
    state_manager: AIStateManagerDB = Depends(get_state_manager),
):
    """Reset approved suggestions back to pending status.

    Use this to "unapprove" suggestions before they're applied to Paperless.
    """
    suggestion = await state_manager.get_suggestion(doc_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="No suggestions found for this document")

    # Reset any approved statuses back to pending
    if suggestion.title_status == SuggestionStatus.APPROVED:
        suggestion.title_status = SuggestionStatus.PENDING
    if suggestion.tags_status == SuggestionStatus.APPROVED:
        suggestion.tags_status = SuggestionStatus.PENDING
    if suggestion.doc_type_status == SuggestionStatus.APPROVED:
        suggestion.doc_type_status = SuggestionStatus.PENDING

    # Clear user modifications
    suggestion.modified_title = None
    suggestion.selected_tag_indices = None
    suggestion.additional_tag_ids = None
    suggestion.rejection_notes = None

    await state_manager.update_suggestion(doc_id, suggestion)

    return {"success": True, "suggestion": suggestion.model_dump()}


# =============================================================================
# Preferences Management Endpoints
# =============================================================================


@router.get("/preferences/settings")
async def get_preference_settings(
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Get AI preference settings."""
    settings = await preferences.get_settings()
    return settings.model_dump()


@router.put("/preferences/settings")
async def update_preference_settings(
    request: PreferenceSettingsRequest,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Update AI preference settings."""
    updated = await preferences.update_settings(**request.model_dump(exclude_none=True))
    return updated.model_dump()


# Tag Definitions
@router.get("/preferences/tags")
async def list_tag_definitions(
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """List all tag definitions."""
    definitions = await preferences.get_all_tag_definitions()
    return [d.model_dump() for d in definitions]


@router.get("/preferences/tags/{tag_name}")
async def get_tag_definition(
    tag_name: str,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Get a specific tag definition."""
    definition = await preferences.get_tag_definition(tag_name)
    if not definition:
        raise HTTPException(status_code=404, detail="Tag definition not found")
    return definition.model_dump()


@router.put("/preferences/tags")
async def set_tag_definition(
    request: TagDefinitionRequest,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Create or update a tag definition."""
    definition = await preferences.set_tag_definition(request)
    return definition.model_dump()


@router.delete("/preferences/tags/{tag_name}")
async def delete_tag_definition(
    tag_name: str,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Delete a tag definition."""
    deleted = await preferences.delete_tag_definition(tag_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tag definition not found")
    return {"success": True}


# Document Type Definitions
@router.get("/preferences/doc-types")
async def list_doc_type_definitions(
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """List all document type definitions."""
    definitions = await preferences.get_all_doc_type_definitions()
    return [d.model_dump() for d in definitions]


@router.get("/preferences/doc-types/{doc_type_name}")
async def get_doc_type_definition(
    doc_type_name: str,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Get a specific document type definition."""
    definition = await preferences.get_doc_type_definition(doc_type_name)
    if not definition:
        raise HTTPException(status_code=404, detail="Document type definition not found")
    return definition.model_dump()


@router.put("/preferences/doc-types")
async def set_doc_type_definition(
    request: DocTypeDefinitionRequest,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Create or update a document type definition."""
    definition = await preferences.set_doc_type_definition(request)
    return definition.model_dump()


@router.delete("/preferences/doc-types/{doc_type_name}")
async def delete_doc_type_definition(
    doc_type_name: str,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Delete a document type definition."""
    deleted = await preferences.delete_doc_type_definition(doc_type_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document type definition not found")
    return {"success": True}


# Correspondent Definitions
@router.get("/preferences/correspondents")
async def list_correspondent_definitions(
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """List all correspondent definitions."""
    definitions = await preferences.get_all_correspondent_definitions()
    return [d.model_dump() for d in definitions]


@router.get("/preferences/correspondents/{correspondent_name:path}")
async def get_correspondent_definition(
    correspondent_name: str,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Get a specific correspondent definition."""
    definition = await preferences.get_correspondent_definition(correspondent_name)
    if not definition:
        raise HTTPException(status_code=404, detail="Correspondent definition not found")
    return definition.model_dump()


@router.put("/preferences/correspondents")
async def set_correspondent_definition(
    request: CorrespondentDefinitionRequest,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Create or update a correspondent definition."""
    definition = await preferences.set_correspondent_definition(request)
    return definition.model_dump()


@router.delete("/preferences/correspondents/{correspondent_name:path}")
async def delete_correspondent_definition(
    correspondent_name: str,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Delete a correspondent definition."""
    deleted = await preferences.delete_correspondent_definition(correspondent_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Correspondent definition not found")
    return {"success": True}


# Corrections (Learned Rules)
@router.get("/preferences/corrections")
async def list_corrections(
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """List all learned tag corrections."""
    corrections = await preferences.get_corrections()
    return [c.model_dump() for c in corrections]


@router.delete("/preferences/corrections/{correction_id}")
async def delete_correction(
    correction_id: str,
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Delete a correction."""
    deleted = await preferences.delete_correction(correction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Correction not found")
    return {"success": True}


# Preferences Summary
@router.get("/preferences")
async def get_preferences_summary(
    preferences: AIPreferencesManagerDB = Depends(get_preferences_manager),
):
    """Get a summary of all AI preferences."""
    logger.debug("Fetching AI preferences summary")
    settings = await preferences.get_settings()
    tag_defs = await preferences.get_all_tag_definitions()
    doc_type_defs = await preferences.get_all_doc_type_definitions()
    correspondent_defs = await preferences.get_all_correspondent_definitions()
    corrections = await preferences.get_corrections()
    updated_at = await preferences.get_settings_updated_at()

    logger.info(
        "AI preferences summary: %d tag defs, %d doc type defs, %d correspondent defs, %d corrections",
        len(tag_defs), len(doc_type_defs), len(correspondent_defs), len(corrections)
    )

    return {
        "settings": settings.model_dump(),
        "tag_definitions_count": len(tag_defs),
        "doc_type_definitions_count": len(doc_type_defs),
        "correspondent_definitions_count": len(correspondent_defs),
        "corrections_count": len(corrections),
        "updated_at": updated_at,
    }


# =============================================================================
# Migration Endpoints
# =============================================================================


@router.post("/migrate")
async def migrate_json_to_database(
    session: AsyncSession = Depends(get_db),
):
    """Migrate AI data from JSON files to database.

    This endpoint reads the old JSON-based storage files and imports
    them into the database. It's safe to run multiple times - existing
    records will be skipped.

    Returns:
        Migration results summary with counts of migrated items
    """
    from app.services.ai_migration import run_migration

    logger.info("Starting JSON to database migration")
    data_dir = _get_data_dir()
    results = await run_migration(session, data_dir)

    logger.info("Migration completed: %s", results)
    return {
        "success": True,
        "migrated": results,
        "message": "Migration completed. Existing records were skipped.",
    }
