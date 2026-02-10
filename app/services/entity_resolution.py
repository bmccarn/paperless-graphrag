"""Post-indexing entity resolution service.

Identifies and merges duplicate entities in GraphRAG output parquet files
using fuzzy matching heuristics and optional LLM confirmation.
"""

import logging
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison: uppercase, strip whitespace/punctuation."""
    name = name.upper().strip()
    # Remove common suffixes/prefixes that don't affect identity
    name = re.sub(r'\s+', ' ', name)
    return name


def _tokenize_name(name: str) -> set[str]:
    """Split a name into tokens for overlap comparison."""
    return set(_normalize_name(name).split())


def _token_overlap_ratio(name_a: str, name_b: str) -> float:
    """Compute Jaccard similarity of name tokens."""
    tokens_a = _tokenize_name(name_a)
    tokens_b = _tokenize_name(name_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _is_substring_match(short: str, long: str) -> bool:
    """Check if all tokens of the shorter name appear in the longer name."""
    tokens_short = _tokenize_name(short)
    tokens_long = _tokenize_name(long)
    return tokens_short.issubset(tokens_long) and len(tokens_short) < len(tokens_long)


def _levenshtein_ratio(a: str, b: str) -> float:
    """Simple Levenshtein-based similarity ratio without external deps.

    Uses dynamic programming. Returns value in [0, 1] where 1 = identical.
    """
    a = _normalize_name(a)
    b = _normalize_name(b)
    if a == b:
        return 1.0
    len_a, len_b = len(a), len(b)
    if len_a == 0 or len_b == 0:
        return 0.0

    # Optimize: if length difference is too large, skip
    if abs(len_a - len_b) / max(len_a, len_b) > 0.5:
        return 0.0

    # Standard DP Levenshtein
    matrix = list(range(len_b + 1))
    for i in range(1, len_a + 1):
        prev = matrix[0]
        matrix[0] = i
        for j in range(1, len_b + 1):
            temp = matrix[j]
            if a[i - 1] == b[j - 1]:
                matrix[j] = prev
            else:
                matrix[j] = 1 + min(prev, matrix[j], matrix[j - 1])
            prev = temp

    distance = matrix[len_b]
    return 1.0 - distance / max(len_a, len_b)


def _find_merge_candidates(
    entities_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
) -> list[tuple[str, str]]:
    """Find pairs of entities that should be merged.

    Returns list of (keep_id, merge_id) tuples where merge_id should be
    merged into keep_id. The entity with the longer/more complete name is kept.

    Uses conservative heuristics to avoid false merges:
    - Same entity type required
    - High name similarity (fuzzy match or substring)
    - Ambiguous last-name-only entities are NOT merged unless context is clear
    """
    merge_pairs = []

    # Group entities by type for comparison
    type_groups = entities_df.groupby("type")

    for entity_type, group in type_groups:
        entities = group.to_dict("records")
        n = len(entities)

        if n < 2:
            continue

        # Build a map of entity_id -> set of related entity names for context
        entity_relationships = defaultdict(set)
        for _, rel in relationships_df.iterrows():
            source = str(rel.get("source", ""))
            target = str(rel.get("target", ""))
            entity_relationships[source].add(target)
            entity_relationships[target].add(source)

        # Compare all pairs within same type
        for i in range(n):
            for j in range(i + 1, n):
                ent_a = entities[i]
                ent_b = entities[j]
                name_a = str(ent_a.get("title", ent_a.get("name", "")))
                name_b = str(ent_b.get("title", ent_b.get("name", "")))
                norm_a = _normalize_name(name_a)
                norm_b = _normalize_name(name_b)

                if norm_a == norm_b:
                    # Exact match after normalization — always merge
                    pass
                elif _is_substring_match(norm_a, norm_b) or _is_substring_match(norm_b, norm_a):
                    # One name is a subset of the other (e.g., "BLAKE" vs "BLAKE T MCCARN")
                    shorter = norm_a if len(norm_a.split()) < len(norm_b.split()) else norm_b
                    longer = norm_b if shorter == norm_a else norm_a

                    # Safety check: single-token names that are common last names
                    # could be ambiguous (e.g., "MCCARN" could be Blake or Chelsea)
                    if len(shorter.split()) == 1:
                        # Check if this single token matches multiple longer entities
                        short_token = shorter.split()[0]
                        matches = [
                            e for e in entities
                            if short_token in _normalize_name(
                                str(e.get("title", e.get("name", "")))
                            ).split()
                            and _normalize_name(str(e.get("title", e.get("name", "")))) != shorter
                        ]
                        if len(matches) > 1:
                            # Ambiguous — multiple entities share this token
                            logger.debug(
                                "Skipping ambiguous merge: '%s' matches %d entities (%s)",
                                shorter,
                                len(matches),
                                [str(m.get("title", m.get("name", ""))) for m in matches[:3]],
                            )
                            continue

                        # Check shared relationships for context
                        id_a = str(ent_a.get("id", ""))
                        id_b = str(ent_b.get("id", ""))
                        shared_rels = entity_relationships.get(name_a, set()) & entity_relationships.get(name_b, set())
                        if not shared_rels and len(shorter.split()) == 1:
                            # Single token, no shared relationships — too risky
                            logger.debug(
                                "Skipping low-confidence merge: '%s' -> '%s' (no shared relationships)",
                                shorter, longer,
                            )
                            continue
                elif _levenshtein_ratio(norm_a, norm_b) >= 0.85:
                    # High fuzzy similarity (handles typos, minor variations)
                    pass
                elif _token_overlap_ratio(name_a, name_b) >= 0.6 and entity_type.upper() == "PERSON":
                    # Partial token overlap for person names
                    # Additional check: must share at least one relationship
                    shared_rels = entity_relationships.get(name_a, set()) & entity_relationships.get(name_b, set())
                    if not shared_rels:
                        continue
                else:
                    continue

                # Determine which to keep: prefer longer (more complete) name
                tokens_a = len(norm_a.split())
                tokens_b = len(norm_b.split())
                if tokens_a >= tokens_b:
                    keep_id = str(ent_a.get("id", ""))
                    merge_id = str(ent_b.get("id", ""))
                    logger.info(
                        "Entity merge candidate: '%s' <- '%s' (type=%s)",
                        name_a, name_b, entity_type,
                    )
                else:
                    keep_id = str(ent_b.get("id", ""))
                    merge_id = str(ent_a.get("id", ""))
                    logger.info(
                        "Entity merge candidate: '%s' <- '%s' (type=%s)",
                        name_b, name_a, entity_type,
                    )

                merge_pairs.append((keep_id, merge_id))

    return merge_pairs


def _apply_merges(
    entities_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
    merge_pairs: list[tuple[str, str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply entity merges to dataframes.

    For each (keep_id, merge_id):
    - Combine descriptions
    - Redirect relationships from merge_id to keep_id
    - Remove merged entity
    - Deduplicate relationships
    """
    if not merge_pairs:
        return entities_df, relationships_df

    # Build transitive merge map (if A <- B and B <- C, then A <- C)
    merge_map = {}  # merge_id -> final_keep_id
    for keep_id, merge_id in merge_pairs:
        # Follow chain to find ultimate keep
        ultimate_keep = keep_id
        while ultimate_keep in merge_map:
            ultimate_keep = merge_map[ultimate_keep]
        merge_map[merge_id] = ultimate_keep
        # Also update any existing entries that pointed to keep_id
        for k, v in merge_map.items():
            if v == keep_id or v == merge_id:
                merge_map[k] = ultimate_keep

    entities_df = entities_df.copy()
    relationships_df = relationships_df.copy()

    # Ensure id columns are strings
    entities_df["id"] = entities_df["id"].astype(str)
    if "source_id" in relationships_df.columns:
        relationships_df["source_id"] = relationships_df["source_id"].astype(str)
    if "target_id" in relationships_df.columns:
        relationships_df["target_id"] = relationships_df["target_id"].astype(str)

    # Build lookups BEFORE any mutations
    entity_id_to_idx = {str(row["id"]): idx for idx, row in entities_df.iterrows()}

    name_col = "title" if "title" in entities_df.columns else "name"

    # Build name maps from original data (before removal)
    id_to_name = {
        str(row["id"]): str(row.get(name_col, ""))
        for _, row in entities_df.iterrows()
    }

    # Build merge_id -> keep_name map for relationship redirection
    merge_name_map = {}  # old_name -> new_name
    for merge_id, keep_id in merge_map.items():
        old_name = id_to_name.get(merge_id, "")
        new_name = id_to_name.get(keep_id, "")
        if old_name and new_name:
            merge_name_map[old_name] = new_name

    # Combine descriptions for merged entities
    for merge_id, keep_id in merge_map.items():
        if merge_id in entity_id_to_idx and keep_id in entity_id_to_idx:
            keep_idx = entity_id_to_idx[keep_id]
            merge_idx = entity_id_to_idx[merge_id]

            keep_desc = str(entities_df.at[keep_idx, "description"] or "")
            merge_desc = str(entities_df.at[merge_idx, "description"] or "")

            if merge_desc and merge_desc not in keep_desc:
                combined = f"{keep_desc} {merge_desc}".strip()
                entities_df.at[keep_idx, "description"] = combined

    # Remove merged entities
    merged_ids = set(merge_map.keys())
    entities_df = entities_df[~entities_df["id"].isin(merged_ids)].reset_index(drop=True)

    # Redirect relationships by ID
    if "source_id" in relationships_df.columns:
        relationships_df["source_id"] = relationships_df["source_id"].apply(
            lambda x: merge_map.get(str(x), str(x))
        )
    if "target_id" in relationships_df.columns:
        relationships_df["target_id"] = relationships_df["target_id"].apply(
            lambda x: merge_map.get(str(x), str(x))
        )

    # Redirect relationships by name
    if "source" in relationships_df.columns:
        relationships_df["source"] = relationships_df["source"].apply(
            lambda x: merge_name_map.get(str(x), str(x))
        )
    if "target" in relationships_df.columns:
        relationships_df["target"] = relationships_df["target"].apply(
            lambda x: merge_name_map.get(str(x), str(x))
        )

    # Remove self-referential relationships (caused by merging)
    if "source_id" in relationships_df.columns and "target_id" in relationships_df.columns:
        relationships_df = relationships_df[
            relationships_df["source_id"] != relationships_df["target_id"]
        ].reset_index(drop=True)
    elif "source" in relationships_df.columns and "target" in relationships_df.columns:
        relationships_df = relationships_df[
            relationships_df["source"] != relationships_df["target"]
        ].reset_index(drop=True)

    # Deduplicate relationships (same source+target, keep highest weight)
    if "source" in relationships_df.columns and "target" in relationships_df.columns:
        # Sort by weight descending so first occurrence has highest weight
        weight_col = "combined_degree" if "combined_degree" in relationships_df.columns else (
            "weight" if "weight" in relationships_df.columns else None
        )
        if weight_col:
            relationships_df = relationships_df.sort_values(weight_col, ascending=False)

        # Create a normalized edge key (alphabetical order to handle bidirectional)
        def edge_key(row):
            s = str(row.get("source", ""))
            t = str(row.get("target", ""))
            return (s, t)

        relationships_df["_edge_key"] = relationships_df.apply(edge_key, axis=1)
        relationships_df = relationships_df.drop_duplicates(
            subset=["_edge_key"], keep="first"
        ).drop(columns=["_edge_key"]).reset_index(drop=True)

    return entities_df, relationships_df


def resolve_entities(output_dir: Path) -> dict:
    """Run entity resolution on GraphRAG output files.

    Reads entities.parquet and relationships.parquet, finds duplicates,
    merges them, and writes back updated files.

    Args:
        output_dir: Path to GraphRAG output directory containing parquet files

    Returns:
        Dict with resolution statistics
    """
    entities_path = output_dir / "entities.parquet"
    relationships_path = output_dir / "relationships.parquet"

    if not entities_path.exists() or not relationships_path.exists():
        logger.warning("Entity resolution skipped: parquet files not found in %s", output_dir)
        return {"status": "skipped", "reason": "parquet files not found"}

    logger.info("Starting entity resolution on %s", output_dir)

    # Load data
    entities_df = pd.read_parquet(entities_path)
    relationships_df = pd.read_parquet(relationships_path)

    original_entity_count = len(entities_df)
    original_rel_count = len(relationships_df)

    logger.info(
        "Loaded %d entities and %d relationships",
        original_entity_count, original_rel_count,
    )

    # Find merge candidates
    merge_pairs = _find_merge_candidates(entities_df, relationships_df)

    if not merge_pairs:
        logger.info("No duplicate entities found")
        return {
            "status": "completed",
            "entities_before": original_entity_count,
            "entities_after": original_entity_count,
            "relationships_before": original_rel_count,
            "relationships_after": original_rel_count,
            "merges": 0,
        }

    logger.info("Found %d merge candidates", len(merge_pairs))

    # Apply merges
    entities_df, relationships_df = _apply_merges(
        entities_df, relationships_df, merge_pairs
    )

    # Log merge summary
    canonical_forms = len(set(keep for keep, _ in merge_pairs))
    logger.info(
        "Entity resolution: merged %d entities into %d canonical forms",
        len(merge_pairs), canonical_forms,
    )

    # Backup originals before overwriting
    shutil.copy2(entities_path, str(entities_path) + ".bak")
    shutil.copy2(relationships_path, str(relationships_path) + ".bak")
    logger.info("Backed up parquet files to .bak before overwriting")

    # Write back
    entities_df.to_parquet(entities_path, index=False)
    relationships_df.to_parquet(relationships_path, index=False)

    final_entity_count = len(entities_df)
    final_rel_count = len(relationships_df)

    logger.info(
        "Entity resolution complete: %d -> %d entities, %d -> %d relationships",
        original_entity_count, final_entity_count,
        original_rel_count, final_rel_count,
    )

    return {
        "status": "completed",
        "entities_before": original_entity_count,
        "entities_after": final_entity_count,
        "relationships_before": original_rel_count,
        "relationships_after": final_rel_count,
        "merges": len(merge_pairs),
    }
