"""Async client for paperless-ngx REST API."""

import logging
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.config import Settings
from app.models.document import (
    PaperlessCorrespondent,
    PaperlessDocument,
    PaperlessDocumentType,
    PaperlessTag,
)

logger = logging.getLogger(__name__)


class PaperlessClient:
    """Async client for interacting with paperless-ngx API."""

    def __init__(self, settings: Settings):
        """Initialize the client with settings.

        Args:
            settings: Application settings containing paperless URL and token
        """
        self.base_url = settings.paperless_url
        self.headers = {
            "Authorization": f"Token {settings.paperless_token}",
            "Accept": f"application/json; version={settings.paperless_api_version}",
        }
        self._client: Optional[httpx.AsyncClient] = None

        # Caches for lookups (populated on enter)
        self._tags_cache: Dict[int, PaperlessTag] = {}
        self._correspondents_cache: Dict[int, PaperlessCorrespondent] = {}
        self._doc_types_cache: Dict[int, PaperlessDocumentType] = {}

    async def __aenter__(self) -> "PaperlessClient":
        """Enter async context and initialize HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        await self._load_caches()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context and close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _load_caches(self) -> None:
        """Pre-load tags, correspondents, and document types for efficient lookups."""
        logger.info("Loading paperless metadata caches...")

        # Load tags
        async for item in self._paginate("/api/tags/"):
            self._tags_cache[item["id"]] = PaperlessTag(**item)

        # Load correspondents
        async for item in self._paginate("/api/correspondents/"):
            self._correspondents_cache[item["id"]] = PaperlessCorrespondent(**item)

        # Load document types
        async for item in self._paginate("/api/document_types/"):
            self._doc_types_cache[item["id"]] = PaperlessDocumentType(**item)

        logger.info(
            "Loaded caches: %d tags, %d correspondents, %d document types",
            len(self._tags_cache),
            len(self._correspondents_cache),
            len(self._doc_types_cache),
        )

    async def _paginate(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
    ) -> AsyncIterator[dict]:
        """Generic paginator for paperless API endpoints.

        Args:
            endpoint: API endpoint path (e.g., "/api/documents/")
            params: Optional query parameters

        Yields:
            Individual items from paginated results
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        params = params.copy() if params else {}

        # First request uses the endpoint with params
        response = await self._client.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()

        for item in data.get("results", []):
            yield item

        # Follow pagination using absolute URLs
        next_url = data.get("next")
        while next_url:
            # Use httpx directly with absolute URL (not the client with base_url)
            async with httpx.AsyncClient(headers=self._client.headers, timeout=30.0) as temp_client:
                response = await temp_client.get(next_url)
            response.raise_for_status()
            data = response.json()

            for item in data.get("results", []):
                yield item

            next_url = data.get("next")

    async def health_check(self) -> bool:
        """Check if paperless-ngx is reachable.

        Returns:
            True if paperless API is accessible, False otherwise
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        try:
            # Use /api/tags/ as it's a simple endpoint that returns 200
            response = await self._client.get("/api/tags/?page_size=1")
            return response.status_code == 200
        except Exception as e:
            logger.warning("Paperless health check failed: %s", e)
            return False

    async def get_all_document_ids(self) -> List[int]:
        """Get all document IDs (lightweight check for deletions).

        Returns:
            List of all document IDs in paperless
        """
        ids = []
        async for doc in self._paginate("/api/documents/", {"fields": "id"}):
            ids.append(doc["id"])
        return ids

    async def get_document_count(self) -> int:
        """Get total count of documents.

        Returns:
            Total number of documents in paperless
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.get("/api/documents/", params={"page_size": 1})
        response.raise_for_status()
        return response.json().get("count", 0)

    async def iter_documents(
        self,
        modified_after: Optional[datetime] = None,
        page_size: int = 50,
    ) -> AsyncIterator[PaperlessDocument]:
        """Iterate through documents, optionally filtered by modification date.

        Args:
            modified_after: Only return documents modified after this datetime
            page_size: Number of documents per API request

        Yields:
            PaperlessDocument objects with resolved foreign keys
        """
        params = {
            "ordering": "-modified",
            "page_size": page_size,
        }

        if modified_after:
            params["modified__gt"] = modified_after.isoformat()

        async for doc_data in self._paginate("/api/documents/", params):
            # Resolve foreign keys from cache
            correspondent_id = doc_data.get("correspondent")
            doctype_id = doc_data.get("document_type")
            tag_ids = doc_data.get("tags", [])

            doc_data["correspondent"] = (
                self._correspondents_cache.get(correspondent_id)
                if correspondent_id
                else None
            )
            doc_data["document_type"] = (
                self._doc_types_cache.get(doctype_id) if doctype_id else None
            )
            doc_data["tags"] = [
                self._tags_cache[tid] for tid in tag_ids if tid in self._tags_cache
            ]

            yield PaperlessDocument(**doc_data)

    async def get_document(self, doc_id: int) -> PaperlessDocument:
        """Get a single document by ID.

        Args:
            doc_id: Document ID in paperless

        Returns:
            PaperlessDocument with resolved foreign keys

        Raises:
            httpx.HTTPStatusError: If document not found or other HTTP error
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        response = await self._client.get(f"/api/documents/{doc_id}/")
        response.raise_for_status()
        doc_data = response.json()

        # Resolve foreign keys
        correspondent_id = doc_data.get("correspondent")
        doctype_id = doc_data.get("document_type")
        tag_ids = doc_data.get("tags", [])

        doc_data["correspondent"] = (
            self._correspondents_cache.get(correspondent_id)
            if correspondent_id
            else None
        )
        doc_data["document_type"] = (
            self._doc_types_cache.get(doctype_id) if doctype_id else None
        )
        doc_data["tags"] = [
            self._tags_cache[tid] for tid in tag_ids if tid in self._tags_cache
        ]

        return PaperlessDocument(**doc_data)

    def get_tag(self, tag_id: int) -> Optional[PaperlessTag]:
        """Get a tag from cache by ID."""
        return self._tags_cache.get(tag_id)

    def get_correspondent(self, corr_id: int) -> Optional[PaperlessCorrespondent]:
        """Get a correspondent from cache by ID."""
        return self._correspondents_cache.get(corr_id)

    def get_document_type(self, dt_id: int) -> Optional[PaperlessDocumentType]:
        """Get a document type from cache by ID."""
        return self._doc_types_cache.get(dt_id)
