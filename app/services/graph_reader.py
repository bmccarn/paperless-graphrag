"""Service for reading GraphRAG output parquet files."""

import logging
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

    def get_entities(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
        community_id: Optional[str] = None,
    ) -> dict:
        """Get paginated list of entities."""
        df = self._read_parquet("entities.parquet")
        if df is None:
            return {"items": [], "total": 0, "has_more": False}

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
            # Community might be stored differently depending on graphrag version
            if "community" in df.columns:
                df = df[df["community"].astype(str) == community_id]

        total = len(df)

        # Paginate
        df = df.iloc[offset:offset + limit]

        # Convert to dict
        entities = []
        for _, row in df.iterrows():
            entity = {
                "id": str(row.get("id", row.get("title", ""))),
                "name": str(row.get("title", row.get("name", "Unknown"))),
                "type": str(row.get("type", "unknown")),
                "description": str(row.get("description", "")),
            }
            if "community" in row:
                entity["community_id"] = str(row["community"])
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
    ) -> dict:
        """Get paginated list of relationships."""
        df = self._read_parquet("relationships.parquet")
        if df is None:
            return {"items": [], "total": 0, "has_more": False}

        # Apply filters
        if source_id:
            df = df[df["source"].astype(str) == source_id]

        if target_id:
            df = df[df["target"].astype(str) == target_id]

        if relationship_type:
            if "type" in df.columns:
                df = df[df["type"].str.lower() == relationship_type.lower()]

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
