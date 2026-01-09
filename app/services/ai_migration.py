"""Migration utility to import JSON-based AI state into the database."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AIProcessingJob,
    AISuggestion,
    AIProcessedDocument,
    AITagDefinition,
    AIDocTypeDefinition,
    AICorrespondentDefinition,
    AITagCorrection,
    AISettings,
)

logger = logging.getLogger(__name__)


async def migrate_ai_state_to_db(
    session: AsyncSession,
    state_file: Path,
) -> Tuple[int, int, int]:
    """Migrate AI processing state from JSON file to database.

    Args:
        session: Database session
        state_file: Path to ai_processing_state.json

    Returns:
        Tuple of (jobs_migrated, suggestions_migrated, processed_docs_migrated)
    """
    if not state_file.exists():
        logger.info("No state file found at %s, skipping migration", state_file)
        return (0, 0, 0)

    try:
        with open(state_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Failed to load state file: %s", e)
        return (0, 0, 0)

    jobs_migrated = 0
    suggestions_migrated = 0
    processed_docs_migrated = 0

    # Migrate jobs
    jobs_data = data.get("jobs", {})
    for job_id, job_data in jobs_data.items():
        # Check if job already exists
        existing = await session.get(AIProcessingJob, job_id)
        if existing:
            continue

        job = AIProcessingJob(
            job_id=job_id,
            status=job_data.get("status", "completed"),
            progress_current=job_data.get("progress_current", 0),
            progress_total=job_data.get("progress_total", 0),
            current_document_title=job_data.get("current_document_title"),
            options=job_data.get("options", {}),
            errors=job_data.get("errors", []),
            created_at=_parse_datetime(job_data.get("created_at")),
            started_at=_parse_datetime(job_data.get("started_at")),
            completed_at=_parse_datetime(job_data.get("completed_at")),
        )
        session.add(job)
        jobs_migrated += 1

    # Migrate suggestions
    suggestions_data = data.get("suggestions", {})
    for doc_id_str, sugg_data in suggestions_data.items():
        doc_id = int(doc_id_str)

        # Check if suggestion already exists
        from sqlalchemy import select
        result = await session.execute(
            select(AISuggestion).where(AISuggestion.document_id == doc_id)
        )
        if result.scalar_one_or_none():
            continue

        suggestion = AISuggestion(
            document_id=doc_id,
            job_id=sugg_data.get("job_id"),
            current_title=sugg_data.get("current_title", ""),
            current_tags=sugg_data.get("current_tags", []),
            current_document_type=sugg_data.get("current_document_type"),
            suggested_title=sugg_data.get("suggested_title"),
            suggested_tags=sugg_data.get("suggested_tags", []),
            suggested_document_type=sugg_data.get("suggested_document_type"),
            title_status=sugg_data.get("title_status", "pending"),
            tags_status=sugg_data.get("tags_status", "pending"),
            doc_type_status=sugg_data.get("doc_type_status", "pending"),
            modified_title=sugg_data.get("modified_title"),
            selected_tag_indices=sugg_data.get("selected_tag_indices"),
            additional_tag_ids=sugg_data.get("additional_tag_ids"),
            rejection_notes=sugg_data.get("rejection_notes"),
            created_at=_parse_datetime(sugg_data.get("created_at")),
            processed_at=_parse_datetime(sugg_data.get("processed_at")),
            error=sugg_data.get("error"),
        )
        session.add(suggestion)
        suggestions_migrated += 1

    # Migrate processed documents
    processed_docs = data.get("processed_documents", {})
    for doc_id_str, timestamp_str in processed_docs.items():
        doc_id = int(doc_id_str)

        # Check if already exists
        existing = await session.get(AIProcessedDocument, doc_id)
        if existing:
            continue

        processed_at = _parse_datetime(timestamp_str) or datetime.utcnow()
        doc = AIProcessedDocument(
            document_id=doc_id,
            processed_at=processed_at,
        )
        session.add(doc)
        processed_docs_migrated += 1

    await session.flush()
    logger.info(
        "Migrated AI state: %d jobs, %d suggestions, %d processed docs",
        jobs_migrated, suggestions_migrated, processed_docs_migrated,
    )

    return (jobs_migrated, suggestions_migrated, processed_docs_migrated)


async def migrate_ai_preferences_to_db(
    session: AsyncSession,
    preferences_file: Path,
) -> Tuple[int, int, int, int]:
    """Migrate AI preferences from JSON file to database.

    Args:
        session: Database session
        preferences_file: Path to ai_preferences.json

    Returns:
        Tuple of (tag_defs, doc_type_defs, correspondent_defs, corrections)
    """
    if not preferences_file.exists():
        logger.info("No preferences file found at %s, skipping migration", preferences_file)
        return (0, 0, 0, 0)

    try:
        with open(preferences_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Failed to load preferences file: %s", e)
        return (0, 0, 0, 0)

    tag_defs_migrated = 0
    doc_type_defs_migrated = 0
    correspondent_defs_migrated = 0
    corrections_migrated = 0

    # Migrate tag definitions
    tag_defs = data.get("tag_definitions", {})
    for tag_name, def_data in tag_defs.items():
        existing = await session.get(AITagDefinition, tag_name.lower())
        if existing:
            continue

        tag_def = AITagDefinition(
            tag_name=tag_name.lower(),
            definition=def_data.get("definition", ""),
            examples=def_data.get("examples", []),
            exclude_contexts=def_data.get("exclude_contexts", []),
            include_contexts=def_data.get("include_contexts", []),
        )
        session.add(tag_def)
        tag_defs_migrated += 1

    # Migrate document type definitions
    doc_type_defs = data.get("doc_type_definitions", {})
    for doc_type_name, def_data in doc_type_defs.items():
        existing = await session.get(AIDocTypeDefinition, doc_type_name.lower())
        if existing:
            continue

        doc_type_def = AIDocTypeDefinition(
            doc_type_name=doc_type_name.lower(),
            definition=def_data.get("definition", ""),
            examples=def_data.get("examples", []),
            exclude_contexts=def_data.get("exclude_contexts", []),
            include_contexts=def_data.get("include_contexts", []),
        )
        session.add(doc_type_def)
        doc_type_defs_migrated += 1

    # Migrate correspondent definitions
    correspondent_defs = data.get("correspondent_definitions", {})
    for correspondent_name, def_data in correspondent_defs.items():
        existing = await session.get(AICorrespondentDefinition, correspondent_name.lower())
        if existing:
            continue

        correspondent_def = AICorrespondentDefinition(
            correspondent_name=correspondent_name.lower(),
            definition=def_data.get("definition", ""),
            standard_tags=def_data.get("standard_tags", []),
            standard_document_type=def_data.get("standard_document_type"),
            notes=def_data.get("notes", ""),
        )
        session.add(correspondent_def)
        correspondent_defs_migrated += 1

    # Migrate corrections
    corrections = data.get("corrections", [])
    for corr_data in corrections:
        corr_id = corr_data.get("id")
        if not corr_id:
            continue

        existing = await session.get(AITagCorrection, corr_id)
        if existing:
            continue

        correction = AITagCorrection(
            id=corr_id,
            document_id=corr_data.get("document_id"),
            document_snippet=corr_data.get("document_snippet"),
            context_keywords=corr_data.get("context_keywords", []),
            rejected_tag=corr_data.get("rejected_tag", ""),
            preferred_tags=corr_data.get("preferred_tags", []),
            reason=corr_data.get("reason"),
            created_at=_parse_datetime(corr_data.get("created_at")),
        )
        session.add(correction)
        corrections_migrated += 1

    # Migrate settings
    settings_data = data.get("settings", {})
    if settings_data:
        existing_settings = await session.get(AISettings, 1)
        if not existing_settings:
            settings = AISettings(
                id=1,
                consistency_mode=settings_data.get("consistency_mode", True),
                prefer_existing_tags=settings_data.get("prefer_existing_tags", True),
                min_similar_docs_for_tag=settings_data.get("min_similar_docs_for_tag", 2),
                similar_doc_count=settings_data.get("similar_doc_count", 5),
                min_tag_confidence=settings_data.get("min_tag_confidence", 0.6),
                min_doc_type_confidence=settings_data.get("min_doc_type_confidence", 0.6),
                allow_new_tags=settings_data.get("allow_new_tags", True),
                allow_new_doc_types=settings_data.get("allow_new_doc_types", True),
                new_tag_confidence_boost=settings_data.get("new_tag_confidence_boost", -0.15),
                auto_learn_from_corrections=settings_data.get("auto_learn_from_corrections", True),
            )
            session.add(settings)

    await session.flush()
    logger.info(
        "Migrated AI preferences: %d tag defs, %d doc type defs, %d correspondent defs, %d corrections",
        tag_defs_migrated, doc_type_defs_migrated, correspondent_defs_migrated,
        corrections_migrated,
    )

    return (
        tag_defs_migrated,
        doc_type_defs_migrated,
        correspondent_defs_migrated,
        corrections_migrated,
    )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse datetime from ISO format string."""
    if not value:
        return None
    try:
        # Handle both with and without timezone
        if "+" in value or "Z" in value:
            value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value)
        return datetime.fromisoformat(value)
    except Exception:
        return None


async def run_migration(
    session: AsyncSession,
    data_dir: Path,
) -> dict:
    """Run full migration from JSON files to database.

    Args:
        session: Database session
        data_dir: Directory containing JSON files

    Returns:
        Migration results summary
    """
    state_file = data_dir / "ai_processing_state.json"
    preferences_file = data_dir / "ai_preferences.json"

    state_results = await migrate_ai_state_to_db(session, state_file)
    prefs_results = await migrate_ai_preferences_to_db(session, preferences_file)

    return {
        "state": {
            "jobs": state_results[0],
            "suggestions": state_results[1],
            "processed_documents": state_results[2],
        },
        "preferences": {
            "tag_definitions": prefs_results[0],
            "doc_type_definitions": prefs_results[1],
            "correspondent_definitions": prefs_results[2],
            "corrections": prefs_results[3],
        },
    }
