"""Service for finding similar documents using embeddings."""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
import numpy as np

from app.config import Settings
from app.models.ai_preferences import SimilarDocumentExample

logger = logging.getLogger(__name__)

# Module-level cache for embeddings (shared across all SimilarDocumentFinder instances)
_EMBEDDINGS_CACHE: Dict[str, dict] = {}  # path -> embeddings dict
_TEXT_UNITS_CACHE: Dict[str, list] = {}  # path -> text units list
_CACHE_MTIME: Dict[str, float] = {}  # path -> last modified time


class SimilarDocumentFinder:
    """Finds similar documents using embeddings.

    Uses either:
    1. Existing GraphRAG embeddings (if available)
    2. On-the-fly embeddings via LiteLLM

    Returns similar documents with their current tags for few-shot learning.
    """

    def __init__(self, settings: Settings, graphrag_output_dir: Optional[Path] = None):
        """Initialize the similar document finder.

        Args:
            settings: Application settings
            graphrag_output_dir: Path to GraphRAG output directory (optional)
        """
        self.settings = settings
        self.graphrag_output_dir = graphrag_output_dir
        self._embeddings_cache: Optional[dict] = None
        self._text_units_cache: Optional[list] = None

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using LiteLLM.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        if not self.settings.litellm_base_url or not self.settings.litellm_api_key:
            logger.warning("LiteLLM not configured for embeddings")
            return None

        # Truncate text to avoid token limits
        # Most embedding models have 512-8192 token limits
        # Use conservative 2000 chars (~500 tokens) to be safe across models
        max_chars = 2000
        original_len = len(text)
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.debug(
                "Truncated embedding text from %d to %d chars",
                original_len, max_chars
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.settings.litellm_base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.settings.litellm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.settings.embedding_model,
                        "input": text,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]
                else:
                    logger.error(
                        "Embedding call failed: %s - %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return None

        except Exception as e:
            logger.error("Embedding call error: %s", e)
            return None

    def _load_graphrag_embeddings(self) -> bool:
        """Load embeddings from GraphRAG parquet files.

        Uses module-level caching to avoid reloading on each request.
        Cache is invalidated if parquet files are modified.

        Returns:
            True if successfully loaded, False otherwise
        """
        global _EMBEDDINGS_CACHE, _TEXT_UNITS_CACHE, _CACHE_MTIME

        if self._embeddings_cache is not None:
            return True

        if not self.graphrag_output_dir:
            return False

        try:
            import pandas as pd

            # Load text units
            text_units_path = self.graphrag_output_dir / "text_units.parquet"
            embeddings_path = self.graphrag_output_dir / "embeddings.text_unit.text.parquet"

            if not text_units_path.exists() or not embeddings_path.exists():
                logger.warning("GraphRAG embedding files not found")
                return False

            cache_key = str(self.graphrag_output_dir)

            # Check if files have been modified since last cache
            current_mtime = max(
                text_units_path.stat().st_mtime,
                embeddings_path.stat().st_mtime
            )
            cached_mtime = _CACHE_MTIME.get(cache_key, 0)

            # Use cached data if available and not stale
            if (
                cache_key in _EMBEDDINGS_CACHE
                and cache_key in _TEXT_UNITS_CACHE
                and current_mtime <= cached_mtime
            ):
                self._embeddings_cache = _EMBEDDINGS_CACHE[cache_key]
                self._text_units_cache = _TEXT_UNITS_CACHE[cache_key]
                logger.info(
                    "Using cached embeddings: %d text units, %d embeddings",
                    len(self._text_units_cache),
                    len(self._embeddings_cache),
                )
                return True

            # Load fresh data
            logger.info("Loading embeddings from GraphRAG parquet files...")
            text_units_df = pd.read_parquet(text_units_path)
            embeddings_df = pd.read_parquet(embeddings_path)

            # Build mapping from text unit ID to embedding
            embeddings_cache = {}
            text_units_cache = []

            for _, row in text_units_df.iterrows():
                unit_id = row.get("id", "")
                text = row.get("text", "")
                doc_ids = row.get("document_ids", [])

                text_units_cache.append({
                    "id": unit_id,
                    "text": text,
                    "document_ids": doc_ids,
                })

            # Load embeddings
            for _, row in embeddings_df.iterrows():
                unit_id = row.get("id", "")
                embedding = row.get("vector", row.get("embedding", None))
                if embedding is not None:
                    if hasattr(embedding, "tolist"):
                        embedding = embedding.tolist()
                    embeddings_cache[unit_id] = embedding

            # Store in module-level cache
            _EMBEDDINGS_CACHE[cache_key] = embeddings_cache
            _TEXT_UNITS_CACHE[cache_key] = text_units_cache
            _CACHE_MTIME[cache_key] = current_mtime

            # Also store in instance for this request
            self._embeddings_cache = embeddings_cache
            self._text_units_cache = text_units_cache

            logger.info(
                "Loaded and cached %d text units and %d embeddings from GraphRAG",
                len(self._text_units_cache),
                len(self._embeddings_cache),
            )

            return True

        except ImportError:
            logger.warning("pandas not available for loading GraphRAG embeddings")
            return False
        except Exception as e:
            logger.error("Failed to load GraphRAG embeddings: %s", e)
            return False

    def _extract_paperless_id(self, text: str, document_ids: Optional[List] = None) -> Optional[int]:
        """Extract Paperless document ID from text unit content or document_ids field.

        Args:
            text: The text content of the unit
            document_ids: GraphRAG document_ids field (may contain file references)

        Returns:
            Paperless document ID or None
        """
        # Method 1 (primary): Extract from text content (YAML frontmatter style)
        # This is the most reliable source as the input files have "document_id: 123" format
        match = re.search(r"document_id:\s*(\d+)", text)
        if match:
            return int(match.group(1))

        # Method 2 (fallback): Try to extract from document_ids field
        # Only if it looks like a filename pattern (not a hash)
        if document_ids:
            for doc_ref in document_ids:
                doc_ref_str = str(doc_ref)
                # Skip long hash strings (GraphRAG uses hex hashes as document IDs)
                if len(doc_ref_str) > 20:
                    continue
                # Look for patterns like "paperless_123.txt" or "doc_123.md"
                match = re.search(r'(?:paperless_|doc_)?(\d+)\.(?:txt|md|pdf)$', doc_ref_str)
                if match:
                    return int(match.group(1))

        return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    async def find_similar_documents(
        self,
        content: str,
        existing_doc_tags: dict,  # {doc_id: {"tags": [...], "document_type": ..., "title": ..., "correspondent": ...}}
        exclude_doc_id: Optional[int] = None,
        top_k: int = 5,
        min_similarity: float = 0.5,
        correspondent: Optional[str] = None,
    ) -> List[SimilarDocumentExample]:
        """Find documents similar to the given content.

        Args:
            content: Document content to find similar documents for
            existing_doc_tags: Dict mapping doc IDs to their current metadata
            exclude_doc_id: Document ID to exclude from results (the current document)
            top_k: Number of similar documents to return
            min_similarity: Minimum similarity threshold
            correspondent: Optional correspondent name to boost docs from same sender

        Returns:
            List of similar document examples with their tags
        """
        similar_docs = []

        # Method 1: Try using GraphRAG embeddings
        if self._load_graphrag_embeddings():
            similar_docs = await self._find_similar_via_graphrag(
                content, existing_doc_tags, exclude_doc_id, top_k, min_similarity,
                correspondent=correspondent,
            )

        # Method 2: Fall back to on-the-fly embeddings if GraphRAG didn't work or found few results
        if len(similar_docs) < top_k:
            # For now, we rely on GraphRAG embeddings
            # On-the-fly would require embedding all documents which is expensive
            pass

        return similar_docs

    async def _find_similar_via_graphrag(
        self,
        content: str,
        existing_doc_tags: dict,
        exclude_doc_id: Optional[int],
        top_k: int,
        min_similarity: float,
        correspondent: Optional[str] = None,
    ) -> List[SimilarDocumentExample]:
        """Find similar documents using GraphRAG embeddings.

        Uses aggregated similarity across all text units per document for more
        accurate matching. Also boosts documents from the same correspondent.
        """
        if not self._text_units_cache or not self._embeddings_cache:
            logger.warning("GraphRAG caches not loaded, cannot find similar docs")
            return []

        # Get embedding for query content
        logger.info("Generating embedding for document content (%d chars)", len(content))
        query_embedding = await self._get_embedding(content)
        if not query_embedding:
            logger.warning("Failed to generate embedding for document content")
            return []

        logger.info("Searching %d text units for similar documents", len(self._text_units_cache))

        # Aggregate similarities per document (max similarity across all text units)
        doc_similarities: dict = {}  # {paperless_id: {"max_sim": float, "sum_sim": float, "count": int}}
        units_with_paperless_id = 0
        units_without_paperless_id = 0

        for unit in self._text_units_cache:
            unit_id = unit["id"]
            unit_embedding = self._embeddings_cache.get(unit_id)

            if unit_embedding is None:
                continue

            # Extract paperless doc ID from document_ids field or text content
            paperless_id = self._extract_paperless_id(
                unit["text"],
                unit.get("document_ids")
            )
            if paperless_id is None:
                units_without_paperless_id += 1
                continue

            units_with_paperless_id += 1

            if exclude_doc_id and paperless_id == exclude_doc_id:
                continue

            # Calculate similarity
            similarity = self._cosine_similarity(query_embedding, unit_embedding)

            # Aggregate per document - track max, sum, and count for averaging
            if paperless_id not in doc_similarities:
                doc_similarities[paperless_id] = {"max_sim": 0.0, "sum_sim": 0.0, "count": 0}

            doc_similarities[paperless_id]["max_sim"] = max(
                doc_similarities[paperless_id]["max_sim"], similarity
            )
            doc_similarities[paperless_id]["sum_sim"] += similarity
            doc_similarities[paperless_id]["count"] += 1

        # Log coverage statistics
        logger.info(
            "Paperless ID extraction: %d units matched, %d units unmatched (%.1f%% coverage)",
            units_with_paperless_id,
            units_without_paperless_id,
            (units_with_paperless_id / max(1, units_with_paperless_id + units_without_paperless_id)) * 100
        )

        # Calculate final similarity score per document
        # Use weighted combination of max and average similarity
        similarities: List[Tuple[int, float]] = []
        for paperless_id, stats in doc_similarities.items():
            avg_sim = stats["sum_sim"] / stats["count"]
            # Weighted: 70% max similarity, 30% average (rewards documents with consistently similar content)
            combined_sim = 0.7 * stats["max_sim"] + 0.3 * avg_sim

            # Boost documents from same correspondent (strong signal for similar tagging)
            if correspondent:
                doc_meta = existing_doc_tags.get(paperless_id, {})
                doc_correspondent = doc_meta.get("correspondent")
                if doc_correspondent and doc_correspondent.lower() == correspondent.lower():
                    combined_sim = min(0.99, combined_sim + 0.15)  # 15% boost, cap at 0.99
                    logger.debug(
                        "Boosted doc %d similarity by 15%% (same correspondent: %s)",
                        paperless_id, correspondent
                    )

            if combined_sim >= min_similarity:
                similarities.append((paperless_id, combined_sim))

        # Sort by similarity and take top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_similar = similarities[:top_k]

        logger.info(
            "Found %d unique documents above similarity threshold %.2f (showing top %d)",
            len(similarities), min_similarity, len(top_similar)
        )

        # Debug: log top similar docs and their cache status
        for doc_id, similarity in top_similar[:5]:
            in_cache = doc_id in existing_doc_tags
            doc_meta = existing_doc_tags.get(doc_id, {})
            has_tags = bool(doc_meta.get("tags", []))
            logger.debug(
                "  Similar doc %d: sim=%.2f, in_cache=%s, has_tags=%s, meta=%s",
                doc_id, similarity, in_cache, has_tags,
                {k: v for k, v in doc_meta.items() if k != 'correspondent'} if doc_meta else "N/A"
            )

        # Build result list with document metadata
        results = []
        skipped_no_cache = 0
        skipped_no_tags = 0
        for doc_id, similarity in top_similar:
            doc_meta = existing_doc_tags.get(doc_id, {})
            if not doc_meta:
                skipped_no_cache += 1
                continue

            tags = doc_meta.get("tags", [])

            # Only include documents that have tags (they can serve as examples)
            if not tags:
                skipped_no_tags += 1
                continue

            results.append(
                SimilarDocumentExample(
                    document_id=doc_id,
                    title=doc_meta.get("title", f"Document {doc_id}"),
                    similarity_score=similarity,
                    tags=tags,
                    document_type=doc_meta.get("document_type"),
                    correspondent=doc_meta.get("correspondent"),
                )
            )

        if results:
            logger.info("Returning %d similar documents for few-shot context:", len(results))
            for doc in results:
                logger.info(
                    "  - Doc %d '%s' (%.1f%% similar) tags=%s",
                    doc.document_id,
                    doc.title[:40],
                    doc.similarity_score * 100,
                    doc.tags
                )
        else:
            logger.info(
                "No similar documents with tags found for few-shot context "
                "(skipped: %d not in cache, %d have no tags)",
                skipped_no_cache, skipped_no_tags
            )

        return results

    def build_few_shot_context(
        self,
        similar_docs: List[SimilarDocumentExample],
        include_doc_types: bool = True,
    ) -> str:
        """Build a few-shot context string from similar documents.

        Args:
            similar_docs: List of similar document examples
            include_doc_types: Whether to include document type info

        Returns:
            Formatted context string for the AI prompt
        """
        if not similar_docs:
            return ""

        lines = [
            "SIMILAR DOCUMENTS (use these as examples for consistent tagging):",
            "The following documents have similar content and have been tagged by the user.",
            "Use these as guidance for which tags to apply to maintain consistency:",
            ""
        ]

        for i, doc in enumerate(similar_docs, 1):
            line = f"{i}. \"{doc.title}\""
            if doc.correspondent:
                line += f" (from {doc.correspondent})"
            line += f"\n   Tags: {', '.join(doc.tags)}"
            if include_doc_types and doc.document_type:
                line += f"\n   Document Type: {doc.document_type}"
            line += f"\n   Similarity: {doc.similarity_score:.0%}"
            lines.append(line)
            lines.append("")

        lines.append(
            "IMPORTANT: Prefer using tags that appear in multiple similar documents above. "
            "This ensures consistency across your document library."
        )

        return "\n".join(lines)

    def suggest_tags_from_similar(
        self,
        similar_docs: List[SimilarDocumentExample],
        min_occurrences: int = 1,
    ) -> List[Tuple[str, float]]:
        """Suggest tags based on frequency and similarity in similar documents.

        Args:
            similar_docs: List of similar documents
            min_occurrences: Minimum times a tag must appear

        Returns:
            List of (tag_name, confidence) tuples
        """
        if not similar_docs:
            return []

        # Count tag occurrences weighted by similarity
        tag_scores: dict = {}
        for doc in similar_docs:
            for tag in doc.tags:
                if tag not in tag_scores:
                    tag_scores[tag] = {"count": 0, "weighted_sum": 0.0, "max_sim": 0.0}
                tag_scores[tag]["count"] += 1
                tag_scores[tag]["weighted_sum"] += doc.similarity_score
                tag_scores[tag]["max_sim"] = max(tag_scores[tag]["max_sim"], doc.similarity_score)

        # Calculate confidence for each tag
        suggestions = []
        for tag, scores in tag_scores.items():
            if scores["count"] >= min_occurrences:
                avg_similarity = scores["weighted_sum"] / scores["count"]
                # Confidence factors:
                # - Higher similarity = more confidence
                # - More occurrences = more confidence
                # - Single occurrence but very high similarity (>0.7) still gets decent confidence
                occurrence_factor = min(1.0, scores["count"] / max(3, len(similar_docs)))
                confidence = avg_similarity * (0.5 + 0.5 * occurrence_factor)

                # Boost if tag appears in highly similar doc
                if scores["max_sim"] > 0.7:
                    confidence = min(0.95, confidence + 0.1)

                suggestions.append((tag, confidence))

        # Sort by confidence
        suggestions.sort(key=lambda x: x[1], reverse=True)

        if suggestions:
            logger.info(
                "Tag hints from similar docs: %s",
                [(tag, f"{conf:.0%}") for tag, conf in suggestions[:5]]
            )

        return suggestions

    def suggest_doc_type_from_similar(
        self,
        similar_docs: List[SimilarDocumentExample],
    ) -> Optional[Tuple[str, float]]:
        """Suggest document type based on similar documents.

        Args:
            similar_docs: List of similar documents

        Returns:
            Tuple of (doc_type_name, confidence) or None
        """
        if not similar_docs:
            return None

        # Count document type occurrences weighted by similarity
        type_scores: dict = {}
        for doc in similar_docs:
            if doc.document_type:
                if doc.document_type not in type_scores:
                    type_scores[doc.document_type] = {"count": 0, "weighted_sum": 0.0}
                type_scores[doc.document_type]["count"] += 1
                type_scores[doc.document_type]["weighted_sum"] += doc.similarity_score

        if not type_scores:
            return None

        # Find the most common/highest confidence document type
        best_type = None
        best_confidence = 0.0
        for doc_type, scores in type_scores.items():
            avg_similarity = scores["weighted_sum"] / scores["count"]
            # Confidence based on occurrence count and similarity
            confidence = avg_similarity * (scores["count"] / len(similar_docs))

            if confidence > best_confidence:
                best_confidence = confidence
                best_type = doc_type

        if best_type and best_confidence >= 0.3:  # Minimum threshold
            logger.info(
                "Doc type hint from similar docs: '%s' (%.0f%% confidence)",
                best_type, best_confidence * 100
            )
            return (best_type, best_confidence)

        return None
