"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.graph_routes import router as graph_router
from app.api.settings_routes import router as settings_router
from app.api.logs_routes import router as logs_router
from app.api.chat_routes import router as chat_router
from app.config import get_settings, is_configured
from app.services.graphrag import GraphRAGService
from app.db.connection import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting paperless-graphrag service...")

    # Initialize database for chat history (if configured)
    db_initialized = await init_db()
    if db_initialized:
        logger.info("Chat history database initialized")
    else:
        logger.info("Chat history will use browser storage (no database configured)")

    if is_configured():
        settings = get_settings()
        logger.info("Configuration loaded:")
        logger.info("  Paperless URL: %s", settings.paperless_url)
        logger.info("  LiteLLM URL: %s", settings.litellm_base_url)
        logger.info("  GraphRAG root: %s", settings.graphrag_root)
        logger.info("  Indexing model: %s", settings.indexing_model)
        logger.info("  Query model: %s", settings.query_model)
        logger.info("  Embedding model: %s", settings.embedding_model)

        # Initialize GraphRAG project structure
        graphrag_service = GraphRAGService(settings)
        await graphrag_service.initialize()

        logger.info("Service ready")
    else:
        logger.warning("Service started but not fully configured!")
        logger.warning("Please configure required settings via /settings endpoint or environment variables")
        logger.warning("Required: PGRAPH_PAPERLESS_URL, PGRAPH_PAPERLESS_TOKEN, PGRAPH_LITELLM_API_KEY")

    yield

    # Shutdown
    logger.info("Shutting down paperless-graphrag service...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Paperless GraphRAG",
    description="""
    A GraphRAG integration for paperless-ngx document management.

    This service syncs documents from paperless-ngx and builds a knowledge graph
    for intelligent querying using GraphRAG.

    ## Features

    - **Document Sync**: Automatically sync documents from paperless-ngx
    - **Incremental Updates**: Only re-index changed documents
    - **Multiple Query Methods**: Local, global, drift, and basic search
    - **Background Processing**: Long-running tasks with status tracking

    ## Quick Start

    1. **Initial Sync**: `POST /sync` with `{"full": true}`
    2. **Check Status**: `GET /tasks/{task_id}`
    3. **Query**: `POST /query` with `{"query": "your question"}`

    ## Query Methods

    - **local**: Best for specific entity/relationship questions
    - **global**: Best for broad summarization
    - **drift**: Experimental hybrid approach
    - **basic**: Simple vector search (fastest)
    """,
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["api"])
app.include_router(graph_router, prefix="/api/v1", tags=["graph"])
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(logs_router, prefix="/api/v1", tags=["logs"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])

# Also mount at root for convenience
app.include_router(router, tags=["api"])
app.include_router(graph_router, tags=["graph"])
app.include_router(settings_router, tags=["settings"])
app.include_router(logs_router, tags=["logs"])
app.include_router(chat_router, tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "paperless-graphrag",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
