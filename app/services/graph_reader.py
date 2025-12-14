"""Service for reading GraphRAG output parquet files."""

import json
import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class GraphReaderService:
    """Service to read and query GraphRAG parquet output files."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def _read_parquet(self, filename: str) -> Optional[pd.DataFrame]:
        """Read a parquet file from the output directory."""
        filepath = self.output_dir / filename
        if not filepath.exists():
            logger.warning("Parquet file not found: %s", filepath)
            return None
        try:
            return pd.read_parquet(filepath)
        except Exception as e:
            logger.error("Failed to read parquet file %s: %s", filepath, e)
            return None

    def get_overview(self) -> dict:
        """Get overview statistics of the graph."""
        entities_df = self._read_parquet("entities.parquet")
        relationships_df = self._read_parquet("relationships.parquet")
        communities_df = self._read_parquet("communities.parquet")

        entity_count = len(entities_df) if entities_df is not None else 0
        relationship_count = len(relationships_df) if relationships_df is not None else 0
        community_count = len(communities_df) if communities_df is not None else 0

        # Count entity types
        entity_types = []
        if entities_df is not None and "type" in entities_df.columns:
            type_counts = entities_df["type"].value_counts()
            entity_types = [
                {"type": str(t), "count": int(c)}
                for t, c in type_counts.items()
            ]

        # Count relationship types
        relationship_types = []
        if relationships_df is not None and "type" in relationships_df.columns:
            rel_counts = relationships_df["type"].value_counts()
            relationship_types = [
                {"type": str(t), "count": int(c)}
                for t, c in rel_counts.items()
            ]

        return {
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "community_count": community_count,
            "entity_types": entity_types,
            "relationship_types": relationship_types,
        }

    def _compute_entity_degrees(self) -> dict:
        """Compute the degree (number of connections) for each entity."""
        relationships_df = self._read_parquet("relationships.parquet")
        if relationships_df is None:
            return {}

        degree_counts = {}

        # Count occurrences in source and target columns
        for _, row in relationships_df.iterrows():
            source = str(row.get("source", ""))
            target = str(row.get("target", ""))

            if source:
                degree_counts[source] = degree_counts.get(source, 0) + 1
            if target:
                degree_counts[target] = degree_counts.get(target, 0) + 1

        return degree_counts

    def _build_entity_community_map(self, level: int = 0) -> dict:
        """Build a mapping from entity ID to community ID at a given level."""
        communities_df = self._read_parquet("communities.parquet")
        if communities_df is None:
            return {}

        entity_to_community = {}

        # Filter by level if the column exists
        if "level" in communities_df.columns:
            communities_df = communities_df[communities_df["level"] == level]

        for _, row in communities_df.iterrows():
            community_id = str(row.get("community", row.get("id", "")))
            entity_ids = row.get("entity_ids", [])

            # entity_ids might be a numpy array or list
            if hasattr(entity_ids, 'tolist'):
                entity_ids = entity_ids.tolist()

            for entity_id in entity_ids:
                entity_to_community[str(entity_id)] = community_id

        return entity_to_community

    def get_entities(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
        community_id: Optional[str] = None,
        include_degree: bool = True,
        community_level: int = 0,
        sort_by_degree: bool = True,
    ) -> dict:
        """Get paginated list of entities.

        Args:
            sort_by_degree: If True, sort entities by degree (most connected first)
        """
        df = self._read_parquet("entities.parquet")
        if df is None:
            return {"items": [], "total": 0, "has_more": False}

        # Compute degree counts if requested (use parquet degree if available)
        use_parquet_degree = "degree" in df.columns
        degree_counts = {} if use_parquet_degree else (self._compute_entity_degrees() if (include_degree or sort_by_degree) else {})

        # Build entity-to-community mapping from communities parquet
        entity_community_map = self._build_entity_community_map(level=community_level)

        # Apply filters
        if entity_type:
            df = df[df["type"].str.lower() == entity_type.lower()]

        if search:
            search_lower = search.lower()
            mask = (
                df["title"].str.lower().str.contains(search_lower, na=False) |
                df["description"].str.lower().str.contains(search_lower, na=False)
            )
            df = df[mask]

        if community_id:
            # Filter by community - check both direct column and lookup
            if "community" in df.columns:
                df = df[df["community"].astype(str) == community_id]
            else:
                # Filter using entity_community_map
                entity_ids_in_community = [
                    eid for eid, cid in entity_community_map.items()
                    if cid == community_id
                ]
                df = df[df["id"].astype(str).isin(entity_ids_in_community)]

        # Sort by degree (most connected first) if requested
        if sort_by_degree:
            if use_parquet_degree:
                df = df.sort_values("degree", ascending=False)
            elif degree_counts:
                # Sort using computed degree counts
                df = df.copy()
                df["_computed_degree"] = df.apply(
                    lambda row: degree_counts.get(str(row.get("title", row.get("name", ""))), 0),
                    axis=1
                )
                df = df.sort_values("_computed_degree", ascending=False)
                df = df.drop(columns=["_computed_degree"])

        total = len(df)

        # Paginate
        df = df.iloc[offset:offset + limit]

        # Convert to dict
        entities = []
        for _, row in df.iterrows():
            entity_id = str(row.get("id", row.get("title", "")))
            entity_name = str(row.get("title", row.get("name", "Unknown")))

            # Get degree from parquet or computed
            if use_parquet_degree:
                degree = int(row.get("degree", 0))
            else:
                degree = degree_counts.get(entity_name, 0)

            entity = {
                "id": entity_id,
                "name": entity_name,
                "type": str(row.get("type", "unknown")),
                "description": str(row.get("description", "")),
                "degree": degree,
            }

            # Add community_id from mapping or direct column
            if "community" in df.columns:
                entity["community_id"] = str(row["community"])
            elif entity_id in entity_community_map:
                entity["community_id"] = entity_community_map[entity_id]

            entities.append(entity)

        return {
            "items": entities,
            "total": total,
            "has_more": offset + limit < total,
        }

    def get_entity(self, entity_id: str) -> Optional[dict]:
        """Get a single entity with its relationships.

        Supports lookup by:
        - UUID (actual entity id)
        - Entity title/name
        - Row index (numeric string like "4130" from GraphRAG data references)
        """
        entities_df = self._read_parquet("entities.parquet")
        relationships_df = self._read_parquet("relationships.parquet")

        if entities_df is None:
            return None

        entity_row = None

        # Try lookup by row index first (for GraphRAG data references like "4130")
        if entity_id.isdigit():
            row_idx = int(entity_id)
            if 0 <= row_idx < len(entities_df):
                entity_row = entities_df.iloc[row_idx]

        # Find entity by id (UUID)
        if entity_row is None and "id" in entities_df.columns:
            matches = entities_df[entities_df["id"].astype(str) == entity_id]
            if not matches.empty:
                entity_row = matches.iloc[0]

        # Find entity by title
        if entity_row is None and "title" in entities_df.columns:
            matches = entities_df[entities_df["title"].astype(str) == entity_id]
            if not matches.empty:
                entity_row = matches.iloc[0]

        if entity_row is None:
            return None

        entity = {
            "id": str(entity_row.get("id", entity_row.get("title", ""))),
            "name": str(entity_row.get("title", entity_row.get("name", "Unknown"))),
            "type": str(entity_row.get("type", "unknown")),
            "description": str(entity_row.get("description", "")),
            "relationships": [],
        }

        # Get relationships
        if relationships_df is not None:
            entity_name = entity["name"]
            related = relationships_df[
                (relationships_df["source"].astype(str) == entity_name) |
                (relationships_df["target"].astype(str) == entity_name)
            ]

            for _, row in related.iterrows():
                entity["relationships"].append({
                    "id": str(row.get("id", f"{row['source']}-{row['target']}")),
                    "source": str(row["source"]),
                    "target": str(row["target"]),
                    "type": str(row.get("type", row.get("description", "related"))),
                    "description": str(row.get("description", "")),
                    "weight": float(row.get("weight", row.get("rank", 1.0))),
                })

        return entity

    def get_relationships(
        self,
        limit: int = 100,
        offset: int = 0,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        sort_by_combined_degree: bool = True,
        entity_names: Optional[list] = None,
    ) -> dict:
        """Get paginated list of relationships.

        Args:
            sort_by_combined_degree: If True, sort by combined_degree (relationships
                between high-degree entities first)
            entity_names: If provided, only return relationships where BOTH source
                and target are in this list
        """
        df = self._read_parquet("relationships.parquet")
        if df is None:
            return {"items": [], "total": 0, "has_more": False}

        # Filter by entity names if provided (only relationships connecting loaded entities)
        if entity_names:
            entity_set = set(entity_names)
            df = df[
                df["source"].astype(str).isin(entity_set) &
                df["target"].astype(str).isin(entity_set)
            ]

        # Apply filters
        if source_id:
            df = df[df["source"].astype(str) == source_id]

        if target_id:
            df = df[df["target"].astype(str) == target_id]

        if relationship_type:
            if "type" in df.columns:
                df = df[df["type"].str.lower() == relationship_type.lower()]

        # Sort by combined_degree (relationships between high-degree entities first)
        if sort_by_combined_degree and "combined_degree" in df.columns:
            df = df.sort_values("combined_degree", ascending=False)

        total = len(df)

        # Paginate
        df = df.iloc[offset:offset + limit]

        # Convert to dict
        relationships = []
        for _, row in df.iterrows():
            relationships.append({
                "id": str(row.get("id", f"{row['source']}-{row['target']}")),
                "source": str(row["source"]),
                "target": str(row["target"]),
                "type": str(row.get("type", "")),
                "description": str(row.get("description", "")),
                "weight": float(row.get("weight", row.get("rank", 1.0))),
            })

        return {
            "items": relationships,
            "total": total,
            "has_more": offset + limit < total,
        }

    def get_communities(self, level: Optional[int] = None) -> dict:
        """Get list of communities."""
        df = self._read_parquet("communities.parquet")
        if df is None:
            return {"items": [], "total": 0, "has_more": False}

        # Apply level filter
        if level is not None and "level" in df.columns:
            df = df[df["level"] == level]

        total = len(df)

        # Convert to dict
        communities = []
        for _, row in df.iterrows():
            communities.append({
                "id": str(row.get("id", row.get("community", ""))),
                "level": int(row.get("level", 0)),
                "title": str(row.get("title", f"Community {row.get('id', '')}")),
                "summary": str(row.get("summary", row.get("full_content", ""))),
                "entity_count": int(row.get("size", 0)),
            })

        return {
            "items": communities,
            "total": total,
            "has_more": False,
        }

    def get_community(self, community_id: str) -> Optional[dict]:
        """Get a single community with its entities."""
        communities_df = self._read_parquet("communities.parquet")
        entities_df = self._read_parquet("entities.parquet")

        if communities_df is None:
            return None

        # Find community
        community_row = None
        if "id" in communities_df.columns:
            matches = communities_df[communities_df["id"].astype(str) == community_id]
            if not matches.empty:
                community_row = matches.iloc[0]

        if community_row is None and "community" in communities_df.columns:
            matches = communities_df[communities_df["community"].astype(str) == community_id]
            if not matches.empty:
                community_row = matches.iloc[0]

        if community_row is None:
            return None

        community = {
            "id": str(community_row.get("id", community_row.get("community", ""))),
            "level": int(community_row.get("level", 0)),
            "title": str(community_row.get("title", f"Community {community_id}")),
            "summary": str(community_row.get("summary", community_row.get("full_content", ""))),
            "entity_count": int(community_row.get("size", 0)),
            "entities": [],
        }

        # Get entities in this community
        if entities_df is not None and "community" in entities_df.columns:
            community_entities = entities_df[
                entities_df["community"].astype(str) == community_id
            ]
            for _, row in community_entities.iterrows():
                community["entities"].append({
                    "id": str(row.get("id", row.get("title", ""))),
                    "name": str(row.get("title", row.get("name", "Unknown"))),
                    "type": str(row.get("type", "unknown")),
                    "description": str(row.get("description", "")),
                })

        return community

    def _load_sync_state(self) -> dict:
        """Load the sync state file that maps Paperless IDs to GraphRAG doc IDs."""
        # sync_state.json is in the parent of output_dir (data/ not data/graphrag/output/)
        sync_state_path = self.output_dir.parent.parent / "sync_state.json"
        if not sync_state_path.exists():
            logger.warning("Sync state file not found: %s", sync_state_path)
            return {}
        try:
            with open(sync_state_path, "r") as f:
                data = json.load(f)
                return data.get("documents", {})
        except Exception as e:
            logger.error("Failed to load sync state: %s", e)
            return {}

    def _extract_paperless_id_from_text(self, text: str) -> Optional[int]:
        """Extract Paperless document ID from chunk text YAML frontmatter."""
        # Look for "document_id: NNN" in the YAML frontmatter
        match = re.search(r"document_id:\s*(\d+)", text)
        if match:
            return int(match.group(1))
        return None

    def get_source_documents_for_entity(self, entity_name: str, paperless_base_url: str = "") -> list:
        """Find Paperless documents that contain mentions of this entity.

        Args:
            entity_name: The name of the entity to search for
            paperless_base_url: Base URL of the Paperless instance for constructing full URLs

        Returns:
            List of dicts with paperless_id, title, and view_url
        """
        text_units_df = self._read_parquet("text_units.parquet")
        documents_df = self._read_parquet("documents.parquet")

        if text_units_df is None:
            return []

        # Find text units that mention the entity (case-insensitive)
        entity_lower = entity_name.lower()
        mask = text_units_df["text"].str.lower().str.contains(entity_lower, na=False)
        matching_chunks = text_units_df[mask]

        if matching_chunks.empty:
            return []

        # Extract unique Paperless document IDs from matching chunks
        paperless_ids = set()
        for _, row in matching_chunks.iterrows():
            text = row.get("text", "")
            doc_id = self._extract_paperless_id_from_text(text)
            if doc_id:
                paperless_ids.add(doc_id)

        # Load sync state for title lookup
        sync_state = self._load_sync_state()

        # Also try to get titles from documents.parquet
        doc_titles = {}
        if documents_df is not None:
            for _, row in documents_df.iterrows():
                text = str(row.get("text", ""))
                doc_id = self._extract_paperless_id_from_text(text)
                if doc_id:
                    # Extract title from frontmatter
                    title_match = re.search(r"title:\s*(.+?)(?:\n|$)", text)
                    if title_match:
                        doc_titles[doc_id] = title_match.group(1).strip()

        results = []
        # Clean the base URL (remove trailing slash)
        base_url = paperless_base_url.rstrip("/") if paperless_base_url else ""

        for paperless_id in sorted(paperless_ids):
            # Get title from sync state or documents parquet
            sync_record = sync_state.get(str(paperless_id), {})
            title = doc_titles.get(paperless_id) or f"Document {paperless_id}"

            results.append({
                "paperless_id": paperless_id,
                "graphrag_doc_id": sync_record.get("graphrag_doc_id", f"paperless_{paperless_id}"),
                "title": title,
                "view_url": f"{base_url}/documents/{paperless_id}/",
            })

        return results

    def _build_doc_hash_to_paperless_map(self, documents_df) -> dict[str, int]:
        """Build a mapping from document hash IDs to paperless IDs.

        Documents in GraphRAG have titles like 'paperless_384.txt' which contain
        the paperless document ID.
        """
        doc_hash_map = {}
        if documents_df is not None:
            for _, row in documents_df.iterrows():
                doc_hash = row.get("id", "")
                title = row.get("title", "")
                # Extract paperless ID from title like 'paperless_384.txt'
                match = re.search(r"paperless_(\d+)\.txt", title)
                if match and doc_hash:
                    doc_hash_map[doc_hash] = int(match.group(1))
        return doc_hash_map

    def get_documents_from_source_ids(
        self, source_ids: list[str], paperless_base_url: str = ""
    ) -> list[dict]:
        """Get Paperless documents from GraphRAG source/text_unit IDs.

        Source IDs in GraphRAG responses (from [Data: Sources (...)]) are row indices
        into the text_units.parquet file. This method resolves them to Paperless documents.

        Args:
            source_ids: List of source IDs (row indices in text_units.parquet)
            paperless_base_url: Base URL of the Paperless instance

        Returns:
            List of dicts with paperless_id, title, and view_url
        """
        text_units_df = self._read_parquet("text_units.parquet")
        if text_units_df is None:
            return []

        # Load documents.parquet for hash-to-paperless mapping
        documents_df = self._read_parquet("documents.parquet")
        doc_hash_map = self._build_doc_hash_to_paperless_map(documents_df)

        paperless_ids = set()

        for source_id in source_ids:
            if source_id.isdigit():
                row_idx = int(source_id)
                if 0 <= row_idx < len(text_units_df):
                    row = text_units_df.iloc[row_idx]
                    text = str(row.get("text", ""))

                    # Method 1: Try extracting document_id from YAML frontmatter in text
                    doc_id = self._extract_paperless_id_from_text(text)
                    if doc_id:
                        paperless_ids.add(doc_id)
                        continue

                    # Method 2: Use document_ids field to look up via documents.parquet
                    doc_hashes = row.get("document_ids", [])
                    if doc_hashes:
                        for doc_hash in doc_hashes:
                            paperless_id = doc_hash_map.get(doc_hash)
                            if paperless_id:
                                paperless_ids.add(paperless_id)

        if not paperless_ids:
            return []

        # Load sync state for titles
        sync_state = self._load_sync_state()

        # Also try to get titles from documents.parquet text content
        doc_titles = {}
        if documents_df is not None:
            for _, row in documents_df.iterrows():
                text = str(row.get("text", ""))
                doc_id = self._extract_paperless_id_from_text(text)
                if doc_id:
                    title_match = re.search(r"title:\s*(.+?)(?:\n|$)", text)
                    if title_match:
                        doc_titles[doc_id] = title_match.group(1).strip()

        # Clean the base URL
        base_url = paperless_base_url.rstrip("/") if paperless_base_url else ""

        results = []
        for paperless_id in sorted(paperless_ids):
            sync_record = sync_state.get(str(paperless_id), {})
            title = doc_titles.get(paperless_id) or sync_record.get("title") or f"Document {paperless_id}"

            results.append({
                "paperless_id": paperless_id,
                "title": title,
                "view_url": f"{base_url}/documents/{paperless_id}/",
            })

        return results

    def get_documents_from_entity_ids(
        self, entity_ids: list[str], paperless_base_url: str = ""
    ) -> list[dict]:
        """Get Paperless documents from GraphRAG entity IDs.

        Entity IDs in GraphRAG responses (from [Data: Entities (...)]) are row indices
        into the entities.parquet file. This method resolves them to source documents
        by looking up which text units mention those entities.

        Args:
            entity_ids: List of entity IDs (row indices in entities.parquet)
            paperless_base_url: Base URL of the Paperless instance

        Returns:
            List of dicts with paperless_id, title, and view_url
        """
        entities_df = self._read_parquet("entities.parquet")
        text_units_df = self._read_parquet("text_units.parquet")
        documents_df = self._read_parquet("documents.parquet")

        if entities_df is None or text_units_df is None:
            return []

        # Build hash-to-paperless mapping for fallback lookup
        doc_hash_map = self._build_doc_hash_to_paperless_map(documents_df)

        # Get entity names from IDs (row indices)
        entity_names = set()
        for entity_id in entity_ids:
            if entity_id.isdigit():
                row_idx = int(entity_id)
                if 0 <= row_idx < len(entities_df):
                    name = str(entities_df.iloc[row_idx].get("title", ""))
                    if name:
                        entity_names.add(name.lower())

        if not entity_names:
            return []

        # Find text units that mention these entities
        paperless_ids = set()
        for _, row in text_units_df.iterrows():
            text = str(row.get("text", "")).lower()
            # Check if any entity name appears in this text unit
            if any(name in text for name in entity_names):
                # Method 1: Try extracting document_id from YAML frontmatter
                doc_id = self._extract_paperless_id_from_text(str(row.get("text", "")))
                if doc_id:
                    paperless_ids.add(doc_id)
                    continue

                # Method 2: Use document_ids field to look up via documents.parquet
                doc_hashes = row.get("document_ids", [])
                if doc_hashes:
                    for doc_hash in doc_hashes:
                        paperless_id = doc_hash_map.get(doc_hash)
                        if paperless_id:
                            paperless_ids.add(paperless_id)

        if not paperless_ids:
            return []

        # Load sync state for titles
        sync_state = self._load_sync_state()

        # Also try to get titles from documents.parquet text content
        doc_titles = {}
        if documents_df is not None:
            for _, row in documents_df.iterrows():
                text = str(row.get("text", ""))
                doc_id = self._extract_paperless_id_from_text(text)
                if doc_id:
                    title_match = re.search(r"title:\s*(.+?)(?:\n|$)", text)
                    if title_match:
                        doc_titles[doc_id] = title_match.group(1).strip()

        # Clean the base URL
        base_url = paperless_base_url.rstrip("/") if paperless_base_url else ""

        results = []
        for paperless_id in sorted(paperless_ids)[:10]:  # Limit to 10 documents
            sync_record = sync_state.get(str(paperless_id), {})
            title = doc_titles.get(paperless_id) or sync_record.get("title") or f"Document {paperless_id}"

            results.append({
                "paperless_id": paperless_id,
                "title": title,
                "view_url": f"{base_url}/documents/{paperless_id}/",
            })

        return results
