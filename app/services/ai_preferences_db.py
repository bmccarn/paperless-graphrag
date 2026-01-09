"""Database-backed service for managing AI tagging preferences and learned rules."""

import logging
import re
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AITagDefinition,
    AIDocTypeDefinition,
    AICorrespondentDefinition,
    AITagCorrection,
    AITagApproval,
    AISettings,
)
from app.models.ai_preferences import (
    AIPreferenceSettings,
    CorrespondentDefinition,
    CorrespondentDefinitionRequest,
    DocTypeDefinitionRequest,
    DocumentTypeDefinition,
    TagApproval,
    TagCorrection,
    TagDefinition,
    TagDefinitionRequest,
)

logger = logging.getLogger(__name__)


class AIPreferencesManagerDB:
    """Database-backed manager for AI tagging preferences."""

    def __init__(self, session: AsyncSession):
        """Initialize with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # =========================================================================
    # Tag Definitions
    # =========================================================================

    async def get_tag_definition(self, tag_name: str) -> Optional[TagDefinition]:
        """Get definition for a specific tag."""
        db_def = await self.session.get(AITagDefinition, tag_name.lower())
        if db_def:
            return self._db_tag_def_to_model(db_def)
        return None

    async def get_all_tag_definitions(self) -> List[TagDefinition]:
        """Get all tag definitions."""
        logger.debug("Fetching all tag definitions")
        result = await self.session.execute(select(AITagDefinition))
        definitions = [self._db_tag_def_to_model(d) for d in result.scalars().all()]
        logger.debug("Found %d tag definitions", len(definitions))
        return definitions

    async def set_tag_definition(self, request: TagDefinitionRequest) -> TagDefinition:
        """Create or update a tag definition."""
        tag_key = request.tag_name.lower()
        existing = await self.session.get(AITagDefinition, tag_key)

        if existing:
            logger.debug("Updating existing tag definition for '%s'", tag_key)
            existing.definition = request.definition
            existing.examples = request.examples
            existing.exclude_contexts = request.exclude_contexts
            existing.include_contexts = request.include_contexts
            existing.updated_at = datetime.utcnow()
        else:
            logger.info("Creating new tag definition for '%s'", tag_key)
            existing = AITagDefinition(
                tag_name=tag_key,
                definition=request.definition,
                examples=request.examples,
                exclude_contexts=request.exclude_contexts,
                include_contexts=request.include_contexts,
            )
            self.session.add(existing)

        await self.session.flush()
        logger.debug("Tag definition for '%s' saved successfully", tag_key)
        return self._db_tag_def_to_model(existing)

    async def delete_tag_definition(self, tag_name: str) -> bool:
        """Delete a tag definition."""
        logger.debug("Attempting to delete tag definition for '%s'", tag_name)
        result = await self.session.execute(
            delete(AITagDefinition).where(AITagDefinition.tag_name == tag_name.lower())
        )
        await self.session.flush()
        if result.rowcount > 0:
            logger.info("Deleted tag definition for '%s'", tag_name)
            return True
        logger.debug("No tag definition found to delete for '%s'", tag_name)
        return False

    def _db_tag_def_to_model(self, db_def: AITagDefinition) -> TagDefinition:
        """Convert database tag definition to Pydantic model."""
        return TagDefinition(
            tag_name=db_def.tag_name,
            definition=db_def.definition,
            examples=db_def.examples or [],
            exclude_contexts=db_def.exclude_contexts or [],
            include_contexts=db_def.include_contexts or [],
            created_at=db_def.created_at,
            updated_at=db_def.updated_at,
        )

    # =========================================================================
    # Document Type Definitions
    # =========================================================================

    async def get_doc_type_definition(self, doc_type_name: str) -> Optional[DocumentTypeDefinition]:
        """Get definition for a specific document type."""
        db_def = await self.session.get(AIDocTypeDefinition, doc_type_name.lower())
        if db_def:
            return self._db_doc_type_def_to_model(db_def)
        return None

    async def get_all_doc_type_definitions(self) -> List[DocumentTypeDefinition]:
        """Get all document type definitions."""
        logger.debug("Fetching all document type definitions")
        result = await self.session.execute(select(AIDocTypeDefinition))
        definitions = [self._db_doc_type_def_to_model(d) for d in result.scalars().all()]
        logger.debug("Found %d document type definitions", len(definitions))
        return definitions

    async def set_doc_type_definition(self, request: DocTypeDefinitionRequest) -> DocumentTypeDefinition:
        """Create or update a document type definition."""
        type_key = request.doc_type_name.lower()
        existing = await self.session.get(AIDocTypeDefinition, type_key)

        if existing:
            logger.debug("Updating existing document type definition for '%s'", type_key)
            existing.definition = request.definition
            existing.examples = request.examples
            existing.exclude_contexts = request.exclude_contexts
            existing.include_contexts = request.include_contexts
            existing.updated_at = datetime.utcnow()
        else:
            logger.info("Creating new document type definition for '%s'", type_key)
            existing = AIDocTypeDefinition(
                doc_type_name=type_key,
                definition=request.definition,
                examples=request.examples,
                exclude_contexts=request.exclude_contexts,
                include_contexts=request.include_contexts,
            )
            self.session.add(existing)

        await self.session.flush()
        logger.debug("Document type definition for '%s' saved successfully", type_key)
        return self._db_doc_type_def_to_model(existing)

    async def delete_doc_type_definition(self, doc_type_name: str) -> bool:
        """Delete a document type definition."""
        logger.debug("Attempting to delete document type definition for '%s'", doc_type_name)
        result = await self.session.execute(
            delete(AIDocTypeDefinition).where(AIDocTypeDefinition.doc_type_name == doc_type_name.lower())
        )
        await self.session.flush()
        if result.rowcount > 0:
            logger.info("Deleted document type definition for '%s'", doc_type_name)
            return True
        logger.debug("No document type definition found to delete for '%s'", doc_type_name)
        return False

    def _db_doc_type_def_to_model(self, db_def: AIDocTypeDefinition) -> DocumentTypeDefinition:
        """Convert database doc type definition to Pydantic model."""
        return DocumentTypeDefinition(
            doc_type_name=db_def.doc_type_name,
            definition=db_def.definition,
            examples=db_def.examples or [],
            exclude_contexts=db_def.exclude_contexts or [],
            include_contexts=db_def.include_contexts or [],
            created_at=db_def.created_at,
            updated_at=db_def.updated_at,
        )

    # =========================================================================
    # Correspondent Definitions
    # =========================================================================

    async def get_correspondent_definition(self, correspondent_name: str) -> Optional[CorrespondentDefinition]:
        """Get definition for a specific correspondent."""
        db_def = await self.session.get(AICorrespondentDefinition, correspondent_name.lower())
        if db_def:
            return self._db_correspondent_def_to_model(db_def)
        return None

    async def get_all_correspondent_definitions(self) -> List[CorrespondentDefinition]:
        """Get all correspondent definitions."""
        logger.debug("Fetching all correspondent definitions")
        result = await self.session.execute(select(AICorrespondentDefinition))
        definitions = [self._db_correspondent_def_to_model(d) for d in result.scalars().all()]
        logger.debug("Found %d correspondent definitions", len(definitions))
        return definitions

    async def set_correspondent_definition(self, request: CorrespondentDefinitionRequest) -> CorrespondentDefinition:
        """Create or update a correspondent definition."""
        correspondent_key = request.correspondent_name.lower()
        existing = await self.session.get(AICorrespondentDefinition, correspondent_key)

        if existing:
            logger.debug("Updating existing correspondent definition for '%s'", correspondent_key)
            existing.definition = request.definition
            existing.standard_tags = request.standard_tags
            existing.standard_document_type = request.standard_document_type
            existing.notes = request.notes
            existing.updated_at = datetime.utcnow()
        else:
            logger.info("Creating new correspondent definition for '%s'", correspondent_key)
            existing = AICorrespondentDefinition(
                correspondent_name=correspondent_key,
                definition=request.definition,
                standard_tags=request.standard_tags,
                standard_document_type=request.standard_document_type,
                notes=request.notes,
            )
            self.session.add(existing)

        await self.session.flush()
        logger.debug("Correspondent definition for '%s' saved successfully", correspondent_key)
        return self._db_correspondent_def_to_model(existing)

    async def delete_correspondent_definition(self, correspondent_name: str) -> bool:
        """Delete a correspondent definition."""
        logger.debug("Attempting to delete correspondent definition for '%s'", correspondent_name)
        result = await self.session.execute(
            delete(AICorrespondentDefinition).where(
                AICorrespondentDefinition.correspondent_name == correspondent_name.lower()
            )
        )
        await self.session.flush()
        if result.rowcount > 0:
            logger.info("Deleted correspondent definition for '%s'", correspondent_name)
            return True
        logger.debug("No correspondent definition found to delete for '%s'", correspondent_name)
        return False

    def _db_correspondent_def_to_model(self, db_def: AICorrespondentDefinition) -> CorrespondentDefinition:
        """Convert database correspondent definition to Pydantic model."""
        return CorrespondentDefinition(
            correspondent_name=db_def.correspondent_name,
            definition=db_def.definition,
            standard_tags=db_def.standard_tags or [],
            standard_document_type=db_def.standard_document_type,
            notes=db_def.notes,
            created_at=db_def.created_at,
            updated_at=db_def.updated_at,
        )

    # =========================================================================
    # Corrections
    # =========================================================================

    async def add_correction(
        self,
        rejected_tag: str,
        preferred_tags: List[str],
        document_id: Optional[int] = None,
        document_snippet: Optional[str] = None,
        context_keywords: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> TagCorrection:
        """Add a learned correction from user feedback."""
        correction = AITagCorrection(
            id=str(uuid.uuid4()),
            document_id=document_id,
            document_snippet=document_snippet,
            context_keywords=context_keywords or [],
            rejected_tag=rejected_tag,
            preferred_tags=preferred_tags,
            reason=reason,
        )
        self.session.add(correction)
        await self.session.flush()

        logger.info(
            "Added correction: %s -> %s (keywords: %s)",
            rejected_tag,
            preferred_tags,
            context_keywords,
        )

        return self._db_correction_to_model(correction)

    async def get_corrections(self) -> List[TagCorrection]:
        """Get all corrections."""
        logger.debug("Fetching all corrections")
        result = await self.session.execute(select(AITagCorrection))
        corrections = [self._db_correction_to_model(c) for c in result.scalars().all()]
        logger.debug("Found %d corrections", len(corrections))
        return corrections

    async def get_relevant_corrections(self, content: str, limit: int = 10) -> List[TagCorrection]:
        """Get corrections to include in AI context.

        Returns recent corrections for the AI to semantically reason about.
        The AI will determine which corrections are relevant based on context and user notes.
        """
        logger.debug("Getting corrections for AI context (limit=%d)", limit)
        all_corrections = await self.get_corrections()

        # Return most recent corrections - let the AI reason about relevance
        # Sort by created_at descending and limit
        sorted_corrections = sorted(all_corrections, key=lambda c: c.created_at, reverse=True)
        relevant = sorted_corrections[:limit]

        # Log what corrections are being passed to AI for accountability
        if relevant:
            logger.info(
                "Passing %d corrections to AI for semantic reasoning:",
                len(relevant)
            )
            for i, corr in enumerate(relevant, 1):
                logger.info(
                    "  Correction %d: '%s' -> %s | reason: %s | snippet: %s",
                    i,
                    corr.rejected_tag,
                    corr.preferred_tags,
                    (corr.reason[:80] + "...") if corr.reason and len(corr.reason) > 80 else corr.reason,
                    (corr.document_snippet[:50] + "...") if corr.document_snippet and len(corr.document_snippet) > 50 else corr.document_snippet,
                )
        else:
            logger.debug("No corrections available to pass to AI")

        return relevant

    async def delete_correction(self, correction_id: str) -> bool:
        """Delete a correction by ID."""
        logger.debug("Attempting to delete correction %s", correction_id)
        result = await self.session.execute(
            delete(AITagCorrection).where(AITagCorrection.id == correction_id)
        )
        await self.session.flush()
        if result.rowcount > 0:
            logger.info("Deleted correction %s", correction_id)
            return True
        logger.debug("No correction found to delete with id %s", correction_id)
        return False

    def _db_correction_to_model(self, db_corr: AITagCorrection) -> TagCorrection:
        """Convert database correction to Pydantic model."""
        return TagCorrection(
            id=db_corr.id,
            created_at=db_corr.created_at,
            document_id=db_corr.document_id,
            document_snippet=db_corr.document_snippet,
            context_keywords=db_corr.context_keywords or [],
            rejected_tag=db_corr.rejected_tag,
            preferred_tags=db_corr.preferred_tags or [],
            reason=db_corr.reason,
        )

    # =========================================================================
    # Approvals (learned positive patterns)
    # =========================================================================

    async def add_approval(
        self,
        correspondent: Optional[str],
        document_type: Optional[str],
        approved_tags: List[str],
        document_snippet: Optional[str] = None,
    ) -> TagApproval:
        """Add or update a learned approval pattern.

        If a matching pattern exists (same correspondent + doc_type), increment count.
        Otherwise create a new pattern.
        """
        # Normalize keys
        corr_key = correspondent.lower() if correspondent else None
        doc_type_key = document_type.lower() if document_type else None

        # Look for existing pattern with same correspondent and doc_type
        result = await self.session.execute(
            select(AITagApproval).where(
                AITagApproval.correspondent == corr_key,
                AITagApproval.document_type == doc_type_key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Merge approved tags and increment count
            existing_tags = set(existing.approved_tags or [])
            existing_tags.update(approved_tags)
            existing.approved_tags = sorted(existing_tags)
            existing.approval_count += 1
            existing.updated_at = datetime.utcnow()
            logger.info(
                "Updated approval pattern: correspondent=%s, doc_type=%s, tags=%s (count=%d)",
                corr_key, doc_type_key, existing.approved_tags, existing.approval_count
            )
        else:
            existing = AITagApproval(
                id=str(uuid.uuid4()),
                correspondent=corr_key,
                document_type=doc_type_key,
                approved_tags=sorted(approved_tags),
                document_snippet=document_snippet,
            )
            self.session.add(existing)
            logger.info(
                "Created approval pattern: correspondent=%s, doc_type=%s, tags=%s",
                corr_key, doc_type_key, approved_tags
            )

        await self.session.flush()
        return self._db_approval_to_model(existing)

    async def get_approvals_for_context(
        self,
        correspondent: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[TagApproval]:
        """Get approval patterns relevant to a specific context."""
        corr_key = correspondent.lower() if correspondent else None
        doc_type_key = document_type.lower() if document_type else None

        # Find patterns matching correspondent OR document type
        result = await self.session.execute(
            select(AITagApproval).where(
                (AITagApproval.correspondent == corr_key) |
                (AITagApproval.document_type == doc_type_key)
            )
        )
        approvals = [self._db_approval_to_model(a) for a in result.scalars().all()]

        if approvals:
            logger.debug(
                "Found %d approval patterns for correspondent=%s, doc_type=%s",
                len(approvals), corr_key, doc_type_key
            )
        return approvals

    async def get_all_approvals(self) -> List[TagApproval]:
        """Get all approval patterns."""
        result = await self.session.execute(
            select(AITagApproval).order_by(AITagApproval.approval_count.desc())
        )
        return [self._db_approval_to_model(a) for a in result.scalars().all()]

    def _db_approval_to_model(self, db_approval: AITagApproval) -> TagApproval:
        """Convert database approval to Pydantic model."""
        return TagApproval(
            id=db_approval.id,
            correspondent=db_approval.correspondent,
            document_type=db_approval.document_type,
            approved_tags=db_approval.approved_tags or [],
            document_snippet=db_approval.document_snippet,
            approval_count=db_approval.approval_count,
            created_at=db_approval.created_at,
            updated_at=db_approval.updated_at,
        )

    # =========================================================================
    # Settings
    # =========================================================================

    async def get_settings(self) -> AIPreferenceSettings:
        """Get preference settings."""
        logger.debug("Fetching AI preference settings")
        db_settings = await self.session.get(AISettings, 1)
        if db_settings:
            logger.debug("Found existing AI preference settings")
            return self._db_settings_to_model(db_settings)
        # Return defaults if no settings exist
        logger.debug("No settings found, returning defaults")
        return AIPreferenceSettings()

    async def update_settings(self, **kwargs) -> AIPreferenceSettings:
        """Update preference settings."""
        logger.debug("Updating AI preference settings: %s", list(kwargs.keys()))
        db_settings = await self.session.get(AISettings, 1)
        if not db_settings:
            logger.info("Creating new AI settings record")
            db_settings = AISettings(id=1)
            self.session.add(db_settings)

        updated_fields = []
        for key, value in kwargs.items():
            if value is not None and hasattr(db_settings, key):
                setattr(db_settings, key, value)
                updated_fields.append(key)

        db_settings.updated_at = datetime.utcnow()
        await self.session.flush()
        logger.info("Updated AI preference settings: %s", updated_fields)
        return self._db_settings_to_model(db_settings)

    async def get_settings_updated_at(self) -> Optional[datetime]:
        """Get the timestamp when settings were last updated.

        Returns:
            Last updated timestamp, or None if no settings exist
        """
        db_settings = await self.session.get(AISettings, 1)
        return db_settings.updated_at if db_settings else None

    def _db_settings_to_model(self, db_settings: AISettings) -> AIPreferenceSettings:
        """Convert database settings to Pydantic model."""
        return AIPreferenceSettings(
            consistency_mode=db_settings.consistency_mode,
            prefer_existing_tags=db_settings.prefer_existing_tags,
            min_similar_docs_for_tag=db_settings.min_similar_docs_for_tag,
            similar_doc_count=db_settings.similar_doc_count,
            min_tag_confidence=db_settings.min_tag_confidence,
            min_doc_type_confidence=db_settings.min_doc_type_confidence,
            allow_new_tags=db_settings.allow_new_tags,
            allow_new_doc_types=db_settings.allow_new_doc_types,
            new_tag_confidence_boost=db_settings.new_tag_confidence_boost,
            auto_learn_from_corrections=db_settings.auto_learn_from_corrections,
        )

    # =========================================================================
    # Context Building for AI Prompts
    # =========================================================================

    async def build_tag_context_for_prompt(
        self,
        content: str,
        existing_tags: List[str],
        correspondent: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> str:
        """Build context string for tag suggestion prompts."""
        sections = []

        # Add tag definitions that are relevant (batch fetch to reduce DB calls)
        tag_defs = []
        tags_with_defs = []
        for tag_name in existing_tags:
            definition = await self.get_tag_definition(tag_name)
            if definition and definition.definition:
                def_text = f"- {definition.tag_name}: {definition.definition}"
                if definition.exclude_contexts:
                    def_text += f" (NOT for: {', '.join(definition.exclude_contexts)})"
                tag_defs.append(def_text)
                tags_with_defs.append(tag_name)

        if tag_defs:
            sections.append("TAG DEFINITIONS (use these to understand what each tag means):\n" + "\n".join(tag_defs))

        # Add correspondent-based rules from approval patterns
        if correspondent or document_type:
            approvals = await self.get_approvals_for_context(correspondent, document_type)
            if approvals:
                pattern_lines = []
                for approval in approvals:
                    if approval.approval_count >= 1:  # Only include patterns that have been confirmed
                        if approval.correspondent and approval.correspondent.lower() == (correspondent or "").lower():
                            pattern_lines.append(
                                f"- Documents from '{approval.correspondent}' typically use tags: {', '.join(approval.approved_tags)} "
                                f"(confirmed {approval.approval_count}x)"
                            )
                        elif approval.document_type and approval.document_type.lower() == (document_type or "").lower():
                            pattern_lines.append(
                                f"- Documents of type '{approval.document_type}' typically use tags: {', '.join(approval.approved_tags)} "
                                f"(confirmed {approval.approval_count}x)"
                            )
                if pattern_lines:
                    sections.append(
                        "LEARNED TAG PATTERNS (user has approved these tags for similar documents):\n"
                        + "\n".join(pattern_lines)
                    )
                    logger.info("Added %d learned patterns to AI context", len(pattern_lines))

        # Add corrections for AI to reason about
        relevant_corrections = await self.get_relevant_corrections(content)
        if relevant_corrections:
            corrections_text = []
            for corr in relevant_corrections:
                correction_entry = f"- Rejected: '{corr.rejected_tag}' → Preferred: {', '.join(corr.preferred_tags)}"
                if corr.reason:
                    correction_entry += f"\n  User's note: \"{corr.reason}\""
                if corr.document_snippet:
                    correction_entry += f"\n  Original context: \"{corr.document_snippet[:150]}...\""
                corrections_text.append(correction_entry)
            corrections_section = (
                "USER CORRECTIONS (review these and apply if semantically relevant to this document):\n"
                + "\n".join(corrections_text)
            )
            sections.append(corrections_section)
            logger.info(
                "Added %d user corrections to AI context (%d chars)",
                len(relevant_corrections),
                len(corrections_section)
            )

        context = "\n\n".join(sections) if sections else ""

        # Single consolidated log entry instead of per-tag logging
        if tag_defs or relevant_corrections:
            logger.info(
                "AI context: checked %d tags, found %d definitions%s, %d corrections",
                len(existing_tags),
                len(tag_defs),
                f" ({', '.join(tags_with_defs)})" if tags_with_defs else "",
                len(relevant_corrections) if relevant_corrections else 0
            )

        return context

    async def build_doc_type_context_for_prompt(self, existing_doc_types: List[str]) -> str:
        """Build context string for document type suggestion prompts."""
        logger.debug("Building document type context for %d existing types", len(existing_doc_types))
        doc_type_defs = []
        for doc_type_name in existing_doc_types:
            definition = await self.get_doc_type_definition(doc_type_name)
            if definition and definition.definition:
                def_text = f"- {definition.doc_type_name}: {definition.definition}"
                if definition.exclude_contexts:
                    def_text += f" (NOT for: {', '.join(definition.exclude_contexts)})"
                doc_type_defs.append(def_text)

        if doc_type_defs:
            context = "DOCUMENT TYPE DEFINITIONS:\n" + "\n".join(doc_type_defs)
            logger.debug("Built document type context with %d definitions", len(doc_type_defs))
            return context
        logger.debug("No document type definitions to include in context")
        return ""

    # =========================================================================
    # Auto-learning from user actions
    # =========================================================================

    async def learn_from_tag_rejection(
        self,
        document_id: int,
        document_content: str,
        rejected_tag: str,
        accepted_tags: List[str],
    ) -> Optional[TagCorrection]:
        """Learn from user rejecting a tag and accepting others."""
        logger.debug(
            "Learning from tag rejection: document=%d, rejected='%s', accepted=%s",
            document_id, rejected_tag, accepted_tags
        )
        settings = await self.get_settings()
        if not settings.auto_learn_from_corrections:
            logger.debug("Auto-learn from corrections is disabled, skipping")
            return None

        # Extract potential keywords from document
        content_lower = document_content.lower()
        keywords = []

        # Look for company/entity names
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', document_content[:1000])
        keywords.extend([w.lower() for w in capitalized[:5]])

        # Look for common document type indicators
        doc_type_indicators = [
            "invoice", "receipt", "statement", "bill", "policy",
            "veterinary", "vet", "pet", "animal", "medical", "doctor",
            "subscription", "recurring", "monthly", "annual"
        ]
        for indicator in doc_type_indicators:
            if indicator in content_lower:
                keywords.append(indicator)

        # Deduplicate and limit
        keywords = list(set(keywords))[:10]

        # Create snippet for context
        snippet = document_content[:200] if document_content else None

        return await self.add_correction(
            rejected_tag=rejected_tag,
            preferred_tags=accepted_tags,
            document_id=document_id,
            document_snippet=snippet,
            context_keywords=keywords,
            reason=f"User rejected '{rejected_tag}' and accepted {accepted_tags}",
        )

    async def learn_from_tag_approval(
        self,
        correspondent: Optional[str],
        document_type: Optional[str],
        approved_tags: List[str],
        document_snippet: Optional[str] = None,
    ) -> Optional[TagApproval]:
        """Learn from user approving tags - reinforces positive patterns.

        Tracks which tags are commonly approved for specific correspondents
        and document types to boost confidence in future suggestions.
        """
        if not approved_tags:
            return None

        settings = await self.get_settings()
        if not settings.auto_learn_from_corrections:
            logger.debug("Auto-learn is disabled, skipping approval learning")
            return None

        # Only learn if we have correspondent or doc_type context
        if not correspondent and not document_type:
            logger.debug("No correspondent or doc_type context, skipping approval learning")
            return None

        return await self.add_approval(
            correspondent=correspondent,
            document_type=document_type,
            approved_tags=approved_tags,
            document_snippet=document_snippet,
        )

    # =========================================================================
    # Summary / Stats
    # =========================================================================

    async def get_summary(self) -> dict:
        """Get a summary of all preferences."""
        logger.debug("Building AI preferences summary")
        tag_defs = await self.get_all_tag_definitions()
        doc_type_defs = await self.get_all_doc_type_definitions()
        correspondent_defs = await self.get_all_correspondent_definitions()
        corrections = await self.get_corrections()
        approvals = await self.get_all_approvals()
        settings = await self.get_settings()

        return {
            "settings": settings.model_dump(),
            "tag_definitions_count": len(tag_defs),
            "doc_type_definitions_count": len(doc_type_defs),
            "correspondent_definitions_count": len(correspondent_defs),
            "corrections_count": len(corrections),
            "approvals_count": len(approvals),
        }
