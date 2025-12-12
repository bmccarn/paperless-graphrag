"""Configuration management using Pydantic Settings."""

import json
import logging
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Path to persisted runtime settings
RUNTIME_SETTINGS_PATH = Path("/app/data/runtime_settings.json")


def load_runtime_settings() -> Dict[str, Any]:
    """Load runtime settings from JSON file."""
    if RUNTIME_SETTINGS_PATH.exists():
        try:
            with open(RUNTIME_SETTINGS_PATH) as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load runtime settings: %s", e)
    return {}


class IndexingMethod(str, Enum):
    """GraphRAG indexing methods."""
    STANDARD = "standard"
    FAST = "fast"


class QueryMethod(str, Enum):
    """GraphRAG query methods."""
    LOCAL = "local"
    GLOBAL = "global"
    DRIFT = "drift"
    BASIC = "basic"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and runtime config."""

    # Paperless-ngx settings (optional - can be set via UI)
    paperless_url: Optional[str] = Field(
        default=None,
        description="Paperless-ngx base URL (e.g., http://paperless:8000)"
    )
    paperless_token: Optional[str] = Field(
        default=None,
        description="API token for paperless-ngx authentication"
    )
    paperless_api_version: int = Field(
        default=9,
        ge=1,
        le=9,
        description="Paperless-ngx API version"
    )

    # LiteLLM settings (optional - can be set via UI)
    litellm_base_url: Optional[str] = Field(
        default="http://litellm:4000",
        description="LiteLLM proxy base URL"
    )
    litellm_api_key: Optional[str] = Field(
        default=None,
        description="API key for LiteLLM authentication"
    )

    # Model selection
    indexing_model: str = Field(
        default="gpt-5-mini",
        description="Model for GraphRAG indexing (entity extraction)"
    )
    query_model: str = Field(
        default="gpt-5-mini",
        description="Model for GraphRAG queries (user-facing)"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Model for text embeddings"
    )

    # GraphRAG settings
    graphrag_root: str = Field(
        default="/app/data/graphrag",
        description="Root directory for GraphRAG project"
    )
    indexing_method: IndexingMethod = Field(
        default=IndexingMethod.STANDARD,
        description="GraphRAG indexing method"
    )
    default_query_method: QueryMethod = Field(
        default=QueryMethod.LOCAL,
        description="Default query method"
    )
    community_level: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Community level for queries"
    )

    # Sync settings
    sync_state_path: str = Field(
        default="/app/data/sync_state.json",
        description="Path to sync state file"
    )

    # Chunking settings
    chunk_size: int = Field(
        default=1200,
        ge=100,
        le=4000,
        description="Chunk size for text splitting"
    )
    chunk_overlap: int = Field(
        default=100,
        ge=0,
        le=500,
        description="Chunk overlap for text splitting"
    )

    # Search settings
    top_k_entities: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Max entities in search context"
    )
    top_k_relationships: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Max relationships in search context"
    )
    text_unit_prop: float = Field(
        default=0.6,
        ge=0.1,
        le=0.9,
        description="Proportion of context for source text"
    )
    max_tokens: int = Field(
        default=128000,
        ge=4000,
        le=200000,
        description="Max tokens for search context"
    )

    # Rate limiting settings
    concurrent_requests: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Max concurrent LLM requests"
    )
    requests_per_minute: int = Field(
        default=500,
        ge=1,
        description="Max requests per minute to LLM"
    )
    tokens_per_minute: int = Field(
        default=2000000,
        ge=1000,
        description="Max tokens per minute to LLM"
    )

    # Database settings (for persistent chat history)
    database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection string for persistent chat history"
    )

    model_config = {
        "env_prefix": "PGRAPH_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v: int, info) -> int:
        """Ensure chunk_overlap is less than chunk_size."""
        chunk_size = info.data.get("chunk_size", 1200)
        if v >= chunk_size:
            raise ValueError(f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})")
        return v

    @field_validator("paperless_url", "litellm_base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        """Remove trailing slash from URLs."""
        return v.rstrip("/")


def get_settings() -> Settings:
    """Get settings instance merged with runtime config.

    Priority (highest to lowest):
    1. Environment variables
    2. Runtime settings (from JSON file)
    3. Default values
    """
    # Load runtime settings from file
    runtime = load_runtime_settings()

    # Create settings - Pydantic will use env vars first, then we merge runtime
    # We need to pass runtime settings as kwargs for fields not set by env
    import os

    merged = {}
    for key, value in runtime.items():
        # Only use runtime value if env var is not set
        env_key = f"PGRAPH_{key.upper()}"
        if not os.environ.get(env_key) and value is not None:
            merged[key] = value

    return Settings(**merged)


def is_configured() -> bool:
    """Check if required settings are configured.

    Returns:
        True if all required settings have values
    """
    try:
        settings = get_settings()
        return all([
            settings.paperless_url,
            settings.paperless_token,
            settings.litellm_api_key,
        ])
    except Exception:
        return False
