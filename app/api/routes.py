"""FastAPI routes for paperless-graphrag API."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.clients.paperless import PaperlessClient
from app.config import QueryMethod, Settings, get_settings
from app.api.dependencies import (
    get_graphrag_service,
    get_paperless_client,
    get_sync_service,
    get_task_manager,
)
from app.services.graphrag import GraphRAGService
from app.services.sync import SyncService
from app.tasks.background import Task, TaskManager, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class SyncRequest(BaseModel):
    """Request to trigger document sync."""
    full: bool = Field(
        default=False,
        description="Force full re-sync of all documents",
    )


class SyncResponse(BaseModel):
    """Response from sync trigger."""
    task_id: str
    status: str
    message: str


class QueryRequest(BaseModel):
    """Request to query documents."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The question to ask",
    )
    method: QueryMethod = Field(
        default=QueryMethod.LOCAL,
        description="Query method: local, global, drift, or basic",
    )
    community_level: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Community level for local search",
    )


class QueryResponse(BaseModel):
    """Response from document query."""
    query: str
    method: str
    response: str


class HealthResponse(BaseModel):
    """Response from health check."""
    status: str
    paperless_connected: bool
    graphrag_initialized: bool
    last_sync: Optional[str]
    document_count: int


class TaskStatusResponse(BaseModel):
    """Response with task status."""
    task_id: str
    status: TaskStatus
    task_type: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    # Progress tracking fields
    progress_percent: Optional[int] = None
    progress_message: Optional[str] = None
    progress_detail: Optional[str] = None


class StatsResponse(BaseModel):
    """Response with sync statistics."""
    total_documents: int
    index_version: int
    last_full_sync: Optional[str]
    last_incremental_sync: Optional[str]


# Routes
@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
):
    """Check service health and connectivity."""
    sync_service = get_sync_service(settings)
    graphrag_service = get_graphrag_service(settings)

    # Check paperless connectivity
    paperless_ok = False
    try:
        async with PaperlessClient(settings) as client:
            paperless_ok = await client.health_check()
    except Exception as e:
        logger.warning("Paperless health check failed: %s", e)

    # Load sync state
    sync_service.load_state()

    return HealthResponse(
        status="healthy" if paperless_ok else "degraded",
        paperless_connected=paperless_ok,
        graphrag_initialized=graphrag_service.has_index(),
        last_sync=(
            sync_service.state.last_incremental_sync.isoformat()
            if sync_service.state.last_incremental_sync
            else None
        ),
        document_count=len(sync_service.state.documents),
    )


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    task_mgr: TaskManager = Depends(get_task_manager),
):
    """Trigger document sync from paperless-ngx to GraphRAG.

    - **Incremental sync** (default): Only syncs changed documents
    - **Full sync** (full=true): Re-syncs all documents

    Returns a task_id for tracking progress via GET /tasks/{task_id}.
    """
    # Check if sync is already running
    if task_mgr.has_running_task("sync"):
        raise HTTPException(
            status_code=409,
            detail="A sync task is already running. Check /tasks for status.",
        )

    # Create task
    task_id = task_mgr.create_task("sync")

    # Define progress callback
    def progress_callback(percent: int, message: str, detail: Optional[str] = None):
        task_mgr.update_progress(task_id, percent, message, detail)

    # Define background sync function
    async def run_sync():
        try:
            task_mgr.start_task(task_id)
            logger.info("Starting sync task %s (full=%s)", task_id, request.full)

            sync_service = get_sync_service(settings)
            graphrag_service = get_graphrag_service(settings)

            async with PaperlessClient(settings) as paperless:
                result = await sync_service.sync_and_index(
                    paperless=paperless,
                    graphrag=graphrag_service,
                    full=request.full,
                    progress_callback=progress_callback,
                )

            task_mgr.complete_task(task_id, result)
            logger.info("Sync task %s completed", task_id)

        except Exception as e:
            logger.exception("Sync task %s failed", task_id)
            task_mgr.fail_task(task_id, str(e))

    # Queue the task
    background_tasks.add_task(run_sync)

    return SyncResponse(
        task_id=task_id,
        status="queued",
        message=f"Sync task queued. Check GET /tasks/{task_id} for status.",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    task_mgr: TaskManager = Depends(get_task_manager),
):
    """Get status of a background task."""
    task = task_mgr.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        task_type=task.task_type,
        result=task.result,
        error=task.error,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        duration_seconds=task.duration_seconds,
        progress_percent=task.progress_percent,
        progress_message=task.progress_message,
        progress_detail=task.progress_detail,
    )


@router.get("/tasks", response_model=list[TaskStatusResponse])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    task_mgr: TaskManager = Depends(get_task_manager),
):
    """List all background tasks."""
    tasks = task_mgr.list_tasks(status=status)

    return [
        TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            task_type=task.task_type,
            result=task.result,
            error=task.error,
            created_at=task.created_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            duration_seconds=task.duration_seconds,
            progress_percent=task.progress_percent,
            progress_message=task.progress_message,
            progress_detail=task.progress_detail,
        )
        for task in tasks
    ]


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    settings: Settings = Depends(get_settings),
):
    """Query indexed documents using GraphRAG.

    **Methods:**
    - **local**: Best for specific questions about entities/relationships
      (e.g., "Who sent me invoices in 2024?")
    - **global**: Best for broad summarization questions
      (e.g., "What are the main themes in my documents?")
    - **drift**: Experimental hybrid approach
    - **basic**: Simple vector search (fastest but less context-aware)
    """
    graphrag_service = get_graphrag_service(settings)
    sync_service = get_sync_service(settings)

    # Check if index exists
    if not graphrag_service.has_index():
        raise HTTPException(
            status_code=400,
            detail="No GraphRAG index found. Run POST /sync first to index documents.",
        )

    # Check if we have any documents
    sync_service.load_state()
    if sync_service.state.index_version == 0:
        raise HTTPException(
            status_code=400,
            detail="Index has not been built yet. Run POST /sync first.",
        )

    try:
        result = await graphrag_service.query(
            query=request.query,
            method=request.method.value,
            community_level=request.community_level,
        )
        return QueryResponse(**result)

    except Exception as e:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/query/stream")
async def query_documents_stream(
    request: QueryRequest,
    settings: Settings = Depends(get_settings),
):
    """Query indexed documents with streaming progress updates.

    Returns Server-Sent Events (SSE) with progress updates and final response.

    **Event types:**
    - `status`: Initial status message
    - `thinking`: Progress/reasoning updates
    - `complete`: Final response
    - `error`: Error message
    """
    graphrag_service = get_graphrag_service(settings)
    sync_service = get_sync_service(settings)

    # Check if index exists
    if not graphrag_service.has_index():
        raise HTTPException(
            status_code=400,
            detail="No GraphRAG index found. Run POST /sync first to index documents.",
        )

    # Check if we have any documents
    sync_service.load_state()
    if sync_service.state.index_version == 0:
        raise HTTPException(
            status_code=400,
            detail="Index has not been built yet. Run POST /sync first.",
        )

    async def event_generator():
        """Generate SSE events from query stream."""
        try:
            async for event in graphrag_service.query_stream(
                query=request.query,
                method=request.method.value,
                community_level=request.community_level,
            ):
                # Format as SSE
                event_data = json.dumps(event)
                yield f"data: {event_data}\n\n"

        except Exception as e:
            logger.exception("Query stream failed")
            error_event = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/documents/stats", response_model=StatsResponse)
async def get_document_stats(
    settings: Settings = Depends(get_settings),
):
    """Get statistics about synced documents."""
    sync_service = get_sync_service(settings)
    stats = sync_service.get_stats()

    return StatsResponse(
        total_documents=stats["total_documents"],
        index_version=stats["index_version"],
        last_full_sync=stats["last_full_sync"],
        last_incremental_sync=stats["last_incremental_sync"],
    )


@router.post("/tasks/cleanup")
async def cleanup_tasks(
    max_age_hours: int = Query(default=24, ge=1, le=168),
    task_mgr: TaskManager = Depends(get_task_manager),
):
    """Clean up old tasks from memory."""
    removed = task_mgr.cleanup_old_tasks(max_age_hours)
    return {"removed": removed, "max_age_hours": max_age_hours}
