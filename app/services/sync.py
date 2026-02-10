"""Sync service for orchestrating paperless to GraphRAG synchronization."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from app.clients.paperless import PaperlessClient
from app.config import Settings
from app.models.document import GraphRAGDocument
from app.models.sync_state import SyncState, DocumentSyncRecord, compute_content_hash
from app.services.entity_resolution import resolve_entities
from app.services.graphrag import GraphRAGService, ProgressCallback

logger = logging.getLogger(__name__)


class SyncService:
    """Service for synchronizing paperless documents to GraphRAG."""

    def __init__(self, settings: Settings):
        """Initialize sync service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.state_path = Path(settings.sync_state_path)
        self._state: Optional[SyncState] = None

    @property
    def state(self) -> SyncState:
        """Get current sync state, loading from disk if needed."""
        if self._state is None:
            self.load_state()
        return self._state

    def load_state(self) -> SyncState:
        """Load sync state from disk.

        Returns:
            Loaded or new SyncState
        """
        if self.state_path.exists():
            try:
                with open(self.state_path) as f:
                    data = json.load(f)
                self._state = SyncState(**data)
                logger.info(
                    "Loaded sync state: %d documents, version %d",
                    len(self._state.documents),
                    self._state.index_version,
                )
            except Exception as e:
                logger.warning("Failed to load sync state: %s. Starting fresh.", e)
                self._state = SyncState()
        else:
            self._state = SyncState()

        return self._state

    async def save_state(self) -> None:
        """Save sync state to disk (non-blocking)."""
        if self._state is None:
            return

        def _save_sync():
            # Ensure parent directory exists
            self.state_path.parent.mkdir(parents=True, exist_ok=True)

            # Custom serializer for datetime
            def serialize(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")

            with open(self.state_path, "w") as f:
                json.dump(self._state.model_dump(), f, default=serialize, indent=2)

        await asyncio.to_thread(_save_sync)
        logger.debug("Saved sync state to %s", self.state_path)

    async def _get_graphrag_input_ids(self, graphrag: GraphRAGService) -> set[int]:
        """Get document IDs currently in GraphRAG input directory (non-blocking).

        Returns:
            Set of paperless document IDs that have files in GraphRAG input
        """
        def _scan_sync():
            input_ids = set()
            for txt_file in graphrag.input_dir.glob("paperless_*.txt"):
                # Extract ID from filename like "paperless_123.txt"
                try:
                    doc_id = int(txt_file.stem.replace("paperless_", ""))
                    input_ids.add(doc_id)
                except ValueError:
                    continue
            return input_ids

        return await asyncio.to_thread(_scan_sync)

    async def sync(
        self,
        paperless: PaperlessClient,
        graphrag: GraphRAGService,
        full: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> dict:
        """Synchronize paperless documents to GraphRAG.

        This performs a proper diff between paperless and GraphRAG:
        - Detects new documents in paperless that aren't in GraphRAG
        - Detects documents deleted from paperless
        - Detects documents missing from GraphRAG input (re-syncs them)
        - Detects modified documents via content hash

        Args:
            paperless: Initialized paperless client
            graphrag: GraphRAG service instance
            full: If True, re-sync all documents regardless of state
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with sync statistics
        """
        self.load_state()

        stats = {
            "added": 0,
            "updated": 0,
            "deleted": 0,
            "unchanged": 0,
            "recovered": 0,  # Files missing from GraphRAG but in state
            "errors": 0,
        }

        # Get current document IDs from paperless
        if progress_callback:
            progress_callback(0, "Fetching documents", "Connecting to Paperless-ngx...")

        logger.info("Fetching document IDs from paperless...")
        paperless_ids = set(await paperless.get_all_document_ids())
        logger.info("Found %d documents in paperless", len(paperless_ids))

        # Get current document IDs in GraphRAG input
        graphrag_ids = await self._get_graphrag_input_ids(graphrag)
        logger.info("Found %d documents in GraphRAG input", len(graphrag_ids))

        # Report the diff to user
        if progress_callback:
            progress_callback(
                1,
                "Comparing documents",
                f"Found {len(paperless_ids)} in Paperless, {len(graphrag_ids)} in GraphRAG"
            )

        # Detect documents that exist in paperless but not in GraphRAG input
        missing_from_graphrag = paperless_ids - graphrag_ids
        if missing_from_graphrag:
            logger.info("Found %d documents in paperless missing from GraphRAG", len(missing_from_graphrag))

        # Detect documents deleted from paperless (in state but not in paperless)
        deleted_ids = self.state.get_deleted_ids(paperless_ids)
        if deleted_ids:
            graphrag_doc_ids = [f"paperless_{did}" for did in deleted_ids]
            await graphrag.remove_documents(graphrag_doc_ids)
            for did in deleted_ids:
                del self.state.documents[did]
            stats["deleted"] = len(deleted_ids)
            logger.info("Removed %d deleted documents", len(deleted_ids))

        # Also remove any orphaned files in GraphRAG that aren't in paperless
        orphaned_in_graphrag = graphrag_ids - paperless_ids
        if orphaned_in_graphrag:
            orphan_ids = [f"paperless_{oid}" for oid in orphaned_in_graphrag]
            await graphrag.remove_documents(orphan_ids)
            logger.info("Removed %d orphaned documents from GraphRAG input", len(orphaned_in_graphrag))

        # Report diff summary
        if progress_callback:
            diff_parts = []
            if missing_from_graphrag:
                diff_parts.append(f"{len(missing_from_graphrag)} new")
            if deleted_ids:
                diff_parts.append(f"{len(deleted_ids)} deleted")
            if orphaned_in_graphrag:
                diff_parts.append(f"{len(orphaned_in_graphrag)} orphaned")
            diff_summary = ", ".join(diff_parts) if diff_parts else "No changes detected"
            progress_callback(2, "Diff complete", diff_summary)

        # Determine documents to process
        # For incremental sync: process new docs + modified docs (by timestamp)
        # For full sync: process all docs
        if full:
            logger.info("Full sync: processing all %d documents", len(paperless_ids))
            modified_after = None
            docs_to_recover = set()
        else:
            # Documents missing from GraphRAG need to be recovered
            docs_to_recover = missing_from_graphrag.copy()
            modified_after = self.state.last_incremental_sync
            if modified_after:
                logger.info("Incremental sync from %s", modified_after)
                logger.info("Documents to recover: %d, checking for modifications...", len(docs_to_recover))
            else:
                logger.info("First incremental sync")

        # Process documents
        documents_to_write = []
        docs_checked = 0

        # First, recover any missing documents by fetching them directly
        if docs_to_recover:
            logger.info("Recovering %d missing documents...", len(docs_to_recover))
            if progress_callback:
                progress_callback(3, "Recovering documents", f"Fetching {len(docs_to_recover)} missing documents from Paperless...")
            for i, doc_id in enumerate(docs_to_recover):
                try:
                    doc = await paperless.get_document(doc_id)
                    if doc:
                        content_hash = compute_content_hash(doc.content, doc.title, doc.tag_names)
                        graphrag_doc = GraphRAGDocument.from_paperless(doc)
                        documents_to_write.append(graphrag_doc)

                        is_new = doc_id not in self.state.documents
                        self.state.documents[doc_id] = DocumentSyncRecord(
                            paperless_id=doc_id,
                            content_hash=content_hash,
                            last_modified=doc.modified,
                            last_synced=datetime.utcnow(),
                            graphrag_doc_id=graphrag_doc.id,
                        )

                        if is_new:
                            stats["added"] += 1
                        else:
                            stats["recovered"] += 1
                        docs_checked += 1

                        # Progress update every 10 docs or on last doc
                        if progress_callback and (i % 10 == 0 or i == len(docs_to_recover) - 1):
                            progress_callback(
                                3,
                                "Recovering documents",
                                f"Recovered {i + 1}/{len(docs_to_recover)}: {doc.title[:40]}..."
                            )
                except Exception as e:
                    logger.error("Failed to recover document %d: %s", doc_id, e)
                    stats["errors"] += 1

        # Then process modified documents using the efficient modified_after filter
        if progress_callback:
            progress_callback(4, "Checking for modifications", "Scanning for changed documents...")

        async for doc in paperless.iter_documents(modified_after=modified_after):
            # Skip if already recovered
            if doc.id in docs_to_recover:
                continue

            docs_checked += 1
            content_hash = compute_content_hash(
                doc.content,
                doc.title,
                doc.tag_names,
            )

            # Check if this document needs syncing
            needs_update = self.state.needs_sync(doc.id, content_hash, doc.modified)

            # For full sync, also check hash match
            if full and doc.id in self.state.documents:
                if self.state.documents[doc.id].content_hash == content_hash:
                    stats["unchanged"] += 1
                    continue
            elif not full and not needs_update:
                stats["unchanged"] += 1
                continue

            try:
                # Convert to GraphRAG format
                graphrag_doc = GraphRAGDocument.from_paperless(doc)
                documents_to_write.append(graphrag_doc)

                # Track what type of sync this is
                is_new = doc.id not in self.state.documents

                # Update sync record
                self.state.documents[doc.id] = DocumentSyncRecord(
                    paperless_id=doc.id,
                    content_hash=content_hash,
                    last_modified=doc.modified,
                    last_synced=datetime.utcnow(),
                    graphrag_doc_id=graphrag_doc.id,
                )

                if is_new:
                    stats["added"] += 1
                else:
                    stats["updated"] += 1

            except Exception as e:
                logger.error("Failed to process document %d: %s", doc.id, e)
                stats["errors"] += 1

        logger.info("Checked %d documents", docs_checked)

        # Write documents to GraphRAG input
        if documents_to_write:
            await graphrag.write_documents(documents_to_write)

        # Update sync timestamps
        now = datetime.utcnow()
        if full:
            self.state.last_full_sync = now
        self.state.last_incremental_sync = now

        await self.save_state()

        logger.info(
            "Sync completed: added=%d, updated=%d, deleted=%d, recovered=%d, unchanged=%d, errors=%d",
            stats["added"],
            stats["updated"],
            stats["deleted"],
            stats["recovered"],
            stats["unchanged"],
            stats["errors"],
        )

        return stats

    async def sync_and_index(
        self,
        paperless: PaperlessClient,
        graphrag: GraphRAGService,
        full: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> dict:
        """Sync documents and run GraphRAG indexing.

        Args:
            paperless: Initialized paperless client
            graphrag: GraphRAG service instance
            full: If True, full sync and reindex
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with sync stats and index result
        """
        # Run sync first (with progress callback for diff reporting)
        sync_stats = await self.sync(
            paperless=paperless,
            graphrag=graphrag,
            full=full,
            progress_callback=progress_callback,
        )

        # Report sync summary
        if progress_callback:
            sync_parts = []
            if sync_stats['added']:
                sync_parts.append(f"+{sync_stats['added']} added")
            if sync_stats['updated']:
                sync_parts.append(f"{sync_stats['updated']} updated")
            if sync_stats['deleted']:
                sync_parts.append(f"{sync_stats['deleted']} deleted")
            if sync_stats['recovered']:
                sync_parts.append(f"{sync_stats['recovered']} recovered")
            if sync_stats['unchanged']:
                sync_parts.append(f"{sync_stats['unchanged']} unchanged")
            sync_summary = ", ".join(sync_parts) if sync_parts else "No changes"
            progress_callback(5, "Sync complete", sync_summary)

        # Determine if indexing is needed
        is_first_run = self.state.index_version == 0
        has_changes = (
            sync_stats["added"] > 0
            or sync_stats["updated"] > 0
            or sync_stats["deleted"] > 0
            or sync_stats["recovered"] > 0
        )
        needs_indexing = has_changes or is_first_run

        if not needs_indexing:
            logger.info("No changes detected, skipping indexing")
            if progress_callback:
                progress_callback(100, "Completed", "No changes detected")
            return {
                "sync": sync_stats,
                "index": {"status": "skipped", "reason": "no changes"},
            }

        if is_first_run and not has_changes:
            logger.info("First run - indexing existing documents")

        # Run indexing with progress tracking
        is_first_run = self.state.index_version == 0
        use_update = not full and not is_first_run

        if progress_callback:
            progress_callback(10, "Starting indexing", "Initializing GraphRAG...")

        try:
            index_result = await graphrag.run_index(
                update=use_update,
                progress_callback=progress_callback,
            )

            # Run post-indexing entity resolution
            if progress_callback:
                progress_callback(97, "Resolving entities", "Deduplicating similar entities...")

            try:
                resolution_result = await asyncio.to_thread(
                    resolve_entities, graphrag.output_dir
                )
                index_result["entity_resolution"] = resolution_result
                if resolution_result.get("merges", 0) > 0:
                    logger.info(
                        "Entity resolution merged %d entities",
                        resolution_result["merges"],
                    )
                    if progress_callback:
                        progress_callback(
                            99,
                            "Entity resolution complete",
                            f"Merged {resolution_result['merges']} duplicate entities",
                        )
            except Exception as e:
                logger.warning("Entity resolution failed (non-fatal): %s", e)
                index_result["entity_resolution"] = {
                    "status": "failed",
                    "error": str(e),
                }

            self.state.index_version += 1
            await self.save_state()
        except Exception as e:
            import traceback
            logger.error("Indexing failed: %s", e)
            logger.error("Full traceback:\n%s", traceback.format_exc())
            return {
                "sync": sync_stats,
                "index": {"status": "failed", "error": str(e)},
            }

        return {
            "sync": sync_stats,
            "index": index_result,
        }

    async def force_reindex(
        self,
        graphrag: GraphRAGService,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> dict:
        """Force a full GraphRAG re-index without syncing documents.

        Useful when the extraction prompt or GraphRAG settings have changed
        but the source documents haven't.

        Args:
            graphrag: GraphRAG service instance
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with index result
        """
        self.load_state()

        if progress_callback:
            progress_callback(5, "Skipping sync", "Force re-index requested")

        if progress_callback:
            progress_callback(10, "Starting indexing", "Running full GraphRAG index...")

        try:
            index_result = await graphrag.run_index(
                update=False,  # Always full index
                progress_callback=progress_callback,
            )

            # Run post-indexing entity resolution
            if progress_callback:
                progress_callback(97, "Resolving entities", "Deduplicating similar entities...")

            try:
                resolution_result = await asyncio.to_thread(
                    resolve_entities, graphrag.output_dir
                )
                index_result["entity_resolution"] = resolution_result
                if resolution_result.get("merges", 0) > 0:
                    logger.info(
                        "Entity resolution merged %d entities",
                        resolution_result["merges"],
                    )
                    if progress_callback:
                        progress_callback(
                            99,
                            "Entity resolution complete",
                            f"Merged {resolution_result['merges']} duplicate entities",
                        )
            except Exception as e:
                logger.warning("Entity resolution failed (non-fatal): %s", e)
                index_result["entity_resolution"] = {
                    "status": "failed",
                    "error": str(e),
                }

            self.state.index_version += 1
            await self.save_state()

            return {
                "sync": {"status": "skipped", "reason": "force reindex"},
                "index": index_result,
            }

        except Exception as e:
            import traceback
            logger.error("Reindex failed: %s", e)
            logger.error("Full traceback:\n%s", traceback.format_exc())
            return {
                "sync": {"status": "skipped", "reason": "force reindex"},
                "index": {"status": "failed", "error": str(e)},
            }

    def get_stats(self) -> dict:
        """Get sync statistics.

        Returns:
            Dict with sync state statistics
        """
        self.load_state()
        return {
            "total_documents": len(self.state.documents),
            "index_version": self.state.index_version,
            "last_full_sync": (
                self.state.last_full_sync.isoformat()
                if self.state.last_full_sync
                else None
            ),
            "last_incremental_sync": (
                self.state.last_incremental_sync.isoformat()
                if self.state.last_incremental_sync
                else None
            ),
        }
