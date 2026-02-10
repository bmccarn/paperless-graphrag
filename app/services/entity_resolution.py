"""Post-indexing entity resolution service.

Identifies and merges duplicate entities in GraphRAG output parquet files
using fuzzy matching heuristics with blocking keys for performance.
"""

import logging
import re
import shutil
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Known aliases (maiden names, etc.) ────────────────────────────────
# Maps alternate last names to canonical last names for specific people.
# Only used when first-name tokens overlap.
KNOWN_ALIASES: dict[str, str] = {
    "MCADAM": "MCCARN",  # Chelsea's maiden name
}


# ── Helpers ───────────────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Normalize a name for comparison: uppercase, strip punctuation/whitespace."""
    name = name.upper().strip()
    name = re.sub(r'[.,;:\-\'\"()&]', ' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def _tokenize_name(name: str) -> set[str]:
    """Split a normalized name into tokens."""
    return set(_normalize_name(name).split())


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def _is_proper_noun(name: str) -> bool:
    """Heuristic: does this look like a real person's name (not a generic role)?

    Real names usually have 2-4 capitalized tokens and no common role words.
    """
    ROLE_INDICATORS = {
        "EMPLOYEE", "EMPLOYER", "OFFICER", "MEMBER", "REPRESENTATIVE",
        "APPLICANT", "BENEFICIARY", "CLAIMANT", "VETERAN", "SPOUSE",
        "GUARDIAN", "CUSTODIAN", "ATTORNEY", "AGENT", "PROVIDER",
        "SUPERVISOR", "DIRECTOR", "MANAGER", "TENANT", "OWNER",
        "HOLDER", "SIGNER", "PATIENT", "CLIENT", "CUSTOMER",
        "INSURED", "SUBSCRIBER", "PURCHASER", "SELLER", "BUYER",
        "OCCUPANT", "RESIDENT", "PERSONNEL", "WORKER", "STAFF",
        "CAREGIVER", "DEPENDENT", "CHILD", "PARENT", "FAMILY",
        "HEIRS", "SUCCESSORS", "ASSIGNS", "PARTIES", "PERSON",
        "INDIVIDUALS", "TAXPAYER", "PAYER", "PAYEE", "DEBTOR",
    }
    tokens = _tokenize_name(name)
    if not tokens:
        return False
    # If any token is a role indicator, it's probably a generic entity
    if tokens & ROLE_INDICATORS:
        return False
    # Single-word "names" that are all caps and >10 chars are likely roles
    if len(tokens) == 1 and len(list(tokens)[0]) > 12:
        return False
    return True


def _is_joint_entity(name: str) -> bool:
    """Check if name represents multiple people (e.g., 'BLAKE T & CHELSEA J MCCARN')."""
    norm = _normalize_name(name)
    # Already stripped & to space in _normalize_name, so check for patterns like
    # "FIRSTNAME1 ... FIRSTNAME2 ... LASTNAME" which would have been "F1 & F2 LAST"
    # Better: check original name for & or "and" between name parts
    return bool(re.search(r'&|\bAND\b', name.upper()))


def _middle_initial_conflicts(name_a: str, name_b: str) -> bool:
    """Check if two names have conflicting middle initials.

    E.g., "LOWELL E LANDER" vs "LOWELL X LANDER" — E ≠ X, likely different people.
    Only applies when both names have the same structure with a single-char token.
    """
    tokens_a = _normalize_name(name_a).split()
    tokens_b = _normalize_name(name_b).split()

    if len(tokens_a) != len(tokens_b) or len(tokens_a) < 3:
        return False

    # Find single-character tokens (likely initials) at the same position
    for ta, tb in zip(tokens_a, tokens_b):
        if len(ta) == 1 and len(tb) == 1 and ta != tb:
            return True
    return False


def _apply_known_aliases(name: str) -> str:
    """Replace known alias last names with canonical versions for comparison."""
    tokens = _normalize_name(name).split()
    if not tokens:
        return name
    last = tokens[-1]
    if last in KNOWN_ALIASES:
        tokens[-1] = KNOWN_ALIASES[last]
        return " ".join(tokens)
    return _normalize_name(name)


# ── Main merge candidate finder ──────────────────────────────────────

def _find_merge_candidates(
    entities_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
) -> list[tuple[str, str]]:
    """Find pairs of entities that should be merged.

    Uses blocking keys for O(n) performance instead of O(n²) pairwise comparison.
    Returns list of (keep_id, merge_id) tuples.
    """
    merge_pairs = []
    name_col = "title" if "title" in entities_df.columns else "name"

    # Only process PERSON entities for now (other types rarely have duplicates
    # and the heuristics are tuned for person names)
    person_mask = entities_df["type"].str.upper() == "PERSON"
    persons = entities_df[person_mask].copy()

    if len(persons) < 2:
        return merge_pairs

    # Pre-compute normalized info
    records = []
    for _, row in persons.iterrows():
        name = str(row.get(name_col, ""))
        norm = _normalize_name(name)
        tokens = set(norm.split())
        alias_norm = _apply_known_aliases(name)
        alias_tokens = set(alias_norm.split())
        records.append({
            "id": str(row["id"]),
            "name": name,
            "norm": norm,
            "tokens": tokens,
            "alias_norm": alias_norm,
            "alias_tokens": alias_tokens,
            "is_proper": _is_proper_noun(name),
            "is_joint": _is_joint_entity(name),
        })

    # Build ambiguity set: last names shared by multiple distinct people
    last_name_people = defaultdict(set)
    for r in records:
        parts = r["norm"].split()
        if len(parts) >= 2:
            last = parts[-1]
            # Use frozenset of tokens as identity proxy
            last_name_people[last].add(frozenset(r["tokens"]))
        # Also check alias tokens
        alias_parts = r["alias_norm"].split()
        if len(alias_parts) >= 2:
            alias_last = alias_parts[-1]
            last_name_people[alias_last].add(frozenset(r["alias_tokens"]))

    ambiguous_lastnames = {
        ln for ln, people in last_name_people.items()
        if len(people) > 1
    }

    # Index by name for dedup
    seen_pairs = set()

    def _add_merge(keep_rec, merge_rec, reason):
        pair = (keep_rec["id"], merge_rec["id"])
        rev = (merge_rec["id"], keep_rec["id"])
        if pair not in seen_pairs and rev not in seen_pairs:
            seen_pairs.add(pair)
            merge_pairs.append(pair)
            logger.info(
                "Merge candidate: '%s' <- '%s' [%s]",
                keep_rec["name"], merge_rec["name"], reason,
            )

    def _pick_keep(a, b):
        """Pick the more complete name as canonical."""
        # Never use a joint entity as canonical
        if a["is_joint"] and not b["is_joint"]:
            return b, a
        if b["is_joint"] and not a["is_joint"]:
            return a, b
        # Prefer more tokens, then longer string
        if len(a["tokens"]) != len(b["tokens"]):
            return (a, b) if len(a["tokens"]) >= len(b["tokens"]) else (b, a)
        return (a, b) if len(a["name"]) >= len(b["name"]) else (b, a)

    # ── Strategy 1: Exact normalized match ────────────────────────────
    norm_groups = defaultdict(list)
    for r in records:
        norm_groups[r["norm"]].append(r)

    for norm_name, group in norm_groups.items():
        if len(group) < 2:
            continue
        keep = max(group, key=lambda r: len(r["name"]))
        for r in group:
            if r["id"] != keep["id"]:
                _add_merge(keep, r, "exact-norm")

    # ── Strategy 2: Token-set match (reordered names) ────────────────
    token_groups = defaultdict(list)
    for r in records:
        key = frozenset(r["tokens"])
        token_groups[key].append(r)

    for key, group in token_groups.items():
        if len(group) < 2:
            continue
        # Deduplicate by id, exclude joint entities
        unique = {r["id"]: r for r in group if not r["is_joint"]}
        if len(unique) < 2:
            continue
        recs = list(unique.values())
        keep = max(recs, key=lambda r: (len(r["tokens"]), len(r["name"])))
        for r in recs:
            if r["id"] != keep["id"]:
                _add_merge(keep, r, "token-reorder")

    # ── Strategy 2b: Token-set match with alias resolution ───────────
    alias_token_groups = defaultdict(list)
    for r in records:
        key = frozenset(r["alias_tokens"])
        alias_token_groups[key].append(r)

    for key, group in alias_token_groups.items():
        if len(group) < 2:
            continue
        unique = {r["id"]: r for r in group if not r["is_joint"]}
        if len(unique) < 2:
            continue
        recs = list(unique.values())
        keep = max(recs, key=lambda r: (len(r["tokens"]), len(r["name"])))
        for r in recs:
            if r["id"] != keep["id"]:
                _add_merge(keep, r, "alias-match")

    # ── Strategy 3: Subset match (all tokens of A in B) ──────────────
    # Index: token -> set of record indices
    token_index = defaultdict(set)
    for i, r in enumerate(records):
        for t in r["tokens"]:
            token_index[t].add(i)

    for i, r in enumerate(records):
        if len(r["tokens"]) < 2:
            continue
        if r["is_joint"]:
            continue  # Don't use joint entities as subset source

        # Find records that contain ALL tokens of r
        candidates = None
        for t in r["tokens"]:
            if candidates is None:
                candidates = set(token_index[t])
            else:
                candidates &= token_index[t]

        for j in candidates:
            if j == i:
                continue
            other = records[j]
            if other["is_joint"]:
                continue  # Don't merge into or from joint entities

            # r's tokens are a strict subset of other's tokens
            if r["tokens"] < other["tokens"]:
                # Check ambiguity: single-token names matching ambiguous last names
                if len(r["tokens"]) == 1:
                    token = list(r["tokens"])[0]
                    if token in ambiguous_lastnames:
                        continue
                    # Also skip single-token generic roles
                    if not r["is_proper"]:
                        continue

                keep, merge = _pick_keep(other, r)
                _add_merge(keep, merge, "subset")

    # ── Strategy 3b: Subset match with alias resolution ──────────────
    alias_token_index = defaultdict(set)
    for i, r in enumerate(records):
        for t in r["alias_tokens"]:
            alias_token_index[t].add(i)

    for i, r in enumerate(records):
        if len(r["alias_tokens"]) < 2 or r["is_joint"]:
            continue
        candidates = None
        for t in r["alias_tokens"]:
            if candidates is None:
                candidates = set(alias_token_index[t])
            else:
                candidates &= alias_token_index[t]

        for j in candidates:
            if j == i:
                continue
            other = records[j]
            if other["is_joint"]:
                continue
            if r["alias_tokens"] < other["alias_tokens"]:
                if len(r["alias_tokens"]) == 1:
                    continue
                keep, merge = _pick_keep(other, r)
                _add_merge(keep, merge, "alias-subset")

    # ── Strategy 4: OCR fuzzy (1-token diff, ≤2 edit distance) ───────
    # Blocking: group by (sorted tokens minus one)
    block_index = defaultdict(set)
    for i, r in enumerate(records):
        tlist = sorted(r["tokens"])
        if len(tlist) < 2:
            continue
        if not r["is_proper"]:
            continue  # Skip generic roles for fuzzy matching
        for k in range(len(tlist)):
            key = tuple(tlist[:k] + tlist[k + 1:])
            block_index[key].add(i)

    for key, indices in block_index.items():
        if len(indices) < 2:
            continue
        idx_list = sorted(indices)
        for ii in range(len(idx_list)):
            for jj in range(ii + 1, len(idx_list)):
                a, b = records[idx_list[ii]], records[idx_list[jj]]

                if a["is_joint"] or b["is_joint"]:
                    continue
                if a["tokens"] == b["tokens"]:
                    continue  # Already caught

                # Find differing tokens
                shared = a["tokens"] & b["tokens"]
                diff_a = a["tokens"] - shared
                diff_b = b["tokens"] - shared
                if len(diff_a) != 1 or len(diff_b) != 1:
                    continue

                da, db = list(diff_a)[0], list(diff_b)[0]
                dist = _levenshtein(da, db)
                if dist > 2:
                    continue

                # Reject middle-initial conflicts
                if _middle_initial_conflicts(a["name"], b["name"]):
                    logger.debug(
                        "Skipping middle-initial conflict: '%s' vs '%s'",
                        a["name"], b["name"],
                    )
                    continue

                # Reject if the differing tokens are clearly different words
                # (not OCR errors but genuinely different, e.g., GRANDFATHER/GRANDMOTHER)
                if dist == 2:
                    # Short tokens (≤3 chars): likely numbers/initials, too ambiguous
                    if len(da) <= 3 or len(db) <= 3:
                        continue
                    # For tokens ≥8 chars with edit distance 2: could be a real
                    # different word (GRANDFATHER vs GRANDMOTHER). Require that
                    # the edits are NOT substitutions at the same position
                    # (substitutions suggest different words; insertions/deletions
                    # suggest OCR errors like missing/extra chars).
                    if len(da) >= 8 and len(db) >= 8 and abs(len(da) - len(db)) == 0:
                        # Same length + dist 2 = two substitutions = likely different word
                        continue

                keep, merge = _pick_keep(a, b)
                _add_merge(keep, merge, f"ocr-fuzzy(lev={dist})")

    return merge_pairs


# ── Apply merges ──────────────────────────────────────────────────────

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
    - Deduplicate relationships (directional — does NOT sort edge keys)
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
        # Update any existing entries that pointed to keep_id or merge_id
        for k, v in list(merge_map.items()):
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

    id_to_name = {
        str(row["id"]): str(row.get(name_col, ""))
        for _, row in entities_df.iterrows()
    }

    # Build name redirect map
    merge_name_map = {}
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

            raw_keep = entities_df.at[keep_idx, "description"]
            raw_merge = entities_df.at[merge_idx, "description"]
            keep_desc = str(raw_keep) if pd.notna(raw_keep) else ""
            merge_desc = str(raw_merge) if pd.notna(raw_merge) else ""

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

    # Remove self-referential relationships
    if "source_id" in relationships_df.columns and "target_id" in relationships_df.columns:
        relationships_df = relationships_df[
            relationships_df["source_id"] != relationships_df["target_id"]
        ].reset_index(drop=True)
    elif "source" in relationships_df.columns and "target" in relationships_df.columns:
        relationships_df = relationships_df[
            relationships_df["source"] != relationships_df["target"]
        ].reset_index(drop=True)

    # Deduplicate relationships — directional: (source, target) NOT sorted
    if "source" in relationships_df.columns and "target" in relationships_df.columns:
        weight_col = "combined_degree" if "combined_degree" in relationships_df.columns else (
            "weight" if "weight" in relationships_df.columns else None
        )
        if weight_col:
            relationships_df = relationships_df.sort_values(weight_col, ascending=False)

        def edge_key(row):
            return (str(row.get("source", "")), str(row.get("target", "")))

        relationships_df["_edge_key"] = relationships_df.apply(edge_key, axis=1)
        relationships_df = relationships_df.drop_duplicates(
            subset=["_edge_key"], keep="first"
        ).drop(columns=["_edge_key"]).reset_index(drop=True)

    return entities_df, relationships_df


# ── Public API ────────────────────────────────────────────────────────

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
