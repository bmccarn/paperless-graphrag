"""Service for managing AI tagging preferences and learned rules."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.models.ai_preferences import (
    AIPreferences,
    AIPreferenceSettings,
    CorrespondentDefinition,
    CorrespondentDefinitionRequest,
    DocTypeDefinitionRequest,
    DocumentTypeDefinition,
    TagCorrection,
    TagDefinition,
    TagDefinitionRequest,
    VendorRuleRequest,
    VendorTagRule,
)

logger = logging.getLogger(__name__)


class AIPreferencesManager:
    """Manages AI tagging preferences with file-based persistence."""

    def __init__(self, state_path: Path):
        """Initialize the preferences manager.

        Args:
            state_path: Path to the JSON file for storing preferences
        """
        self.state_path = state_path
        self._preferences: Optional[AIPreferences] = None

    @property
    def preferences(self) -> AIPreferences:
        """Get preferences, loading from disk if needed."""
        if self._preferences is None:
            self._load()
        return self._preferences

    def _load(self) -> None:
        """Load preferences from disk."""
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                self._preferences = AIPreferences.model_validate(data)
                logger.info("Loaded AI preferences from %s", self.state_path)
            except Exception as e:
                logger.error("Failed to load preferences, starting fresh: %s", e)
                self._preferences = AIPreferences()
        else:
            logger.info("No preferences file found, starting fresh")
            self._preferences = AIPreferences()

    def _save(self) -> None:
        """Save preferences to disk."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(self.preferences.model_dump(mode="json"), f, indent=2, default=str)
        logger.debug("Saved AI preferences to %s", self.state_path)

    # =========================================================================
    # Tag Definitions
    # =========================================================================

    def get_tag_definition(self, tag_name: str) -> Optional[TagDefinition]:
        """Get definition for a specific tag."""
        return self.preferences.tag_definitions.get(tag_name.lower())

    def get_all_tag_definitions(self) -> List[TagDefinition]:
        """Get all tag definitions."""
        return list(self.preferences.tag_definitions.values())

    def set_tag_definition(self, request: TagDefinitionRequest) -> TagDefinition:
        """Create or update a tag definition."""
        tag_key = request.tag_name.lower()
        existing = self.preferences.tag_definitions.get(tag_key)

        if existing:
            # Update existing
            existing.definition = request.definition
            existing.examples = request.examples
            existing.exclude_contexts = request.exclude_contexts
            existing.include_contexts = request.include_contexts
            existing.updated_at = datetime.utcnow()
            definition = existing
        else:
            # Create new
            definition = TagDefinition(
                tag_name=request.tag_name,
                definition=request.definition,
                examples=request.examples,
                exclude_contexts=request.exclude_contexts,
                include_contexts=request.include_contexts,
            )
            self.preferences.tag_definitions[tag_key] = definition

        self.preferences.updated_at = datetime.utcnow()
        self._save()
        return definition

    def delete_tag_definition(self, tag_name: str) -> bool:
        """Delete a tag definition."""
        tag_key = tag_name.lower()
        if tag_key in self.preferences.tag_definitions:
            del self.preferences.tag_definitions[tag_key]
            self.preferences.updated_at = datetime.utcnow()
            self._save()
            return True
        return False

    # =========================================================================
    # Document Type Definitions
    # =========================================================================

    def get_doc_type_definition(self, doc_type_name: str) -> Optional[DocumentTypeDefinition]:
        """Get definition for a specific document type."""
        return self.preferences.doc_type_definitions.get(doc_type_name.lower())

    def get_all_doc_type_definitions(self) -> List[DocumentTypeDefinition]:
        """Get all document type definitions."""
        return list(self.preferences.doc_type_definitions.values())

    def set_doc_type_definition(self, request: DocTypeDefinitionRequest) -> DocumentTypeDefinition:
        """Create or update a document type definition."""
        type_key = request.doc_type_name.lower()
        existing = self.preferences.doc_type_definitions.get(type_key)

        if existing:
            existing.definition = request.definition
            existing.examples = request.examples
            existing.exclude_contexts = request.exclude_contexts
            existing.include_contexts = request.include_contexts
            existing.updated_at = datetime.utcnow()
            definition = existing
        else:
            definition = DocumentTypeDefinition(
                doc_type_name=request.doc_type_name,
                definition=request.definition,
                examples=request.examples,
                exclude_contexts=request.exclude_contexts,
                include_contexts=request.include_contexts,
            )
            self.preferences.doc_type_definitions[type_key] = definition

        self.preferences.updated_at = datetime.utcnow()
        self._save()
        return definition

    def delete_doc_type_definition(self, doc_type_name: str) -> bool:
        """Delete a document type definition."""
        type_key = doc_type_name.lower()
        if type_key in self.preferences.doc_type_definitions:
            del self.preferences.doc_type_definitions[type_key]
            self.preferences.updated_at = datetime.utcnow()
            self._save()
            return True
        return False

    # =========================================================================
    # Correspondent Definitions
    # =========================================================================

    def get_correspondent_definition(self, correspondent_name: str) -> Optional[CorrespondentDefinition]:
        """Get definition for a specific correspondent."""
        return self.preferences.correspondent_definitions.get(correspondent_name.lower())

    def get_all_correspondent_definitions(self) -> List[CorrespondentDefinition]:
        """Get all correspondent definitions."""
        return list(self.preferences.correspondent_definitions.values())

    def set_correspondent_definition(self, request: CorrespondentDefinitionRequest) -> CorrespondentDefinition:
        """Create or update a correspondent definition."""
        correspondent_key = request.correspondent_name.lower()
        existing = self.preferences.correspondent_definitions.get(correspondent_key)

        if existing:
            existing.definition = request.definition
            existing.standard_tags = request.standard_tags
            existing.standard_document_type = request.standard_document_type
            existing.notes = request.notes
            existing.updated_at = datetime.utcnow()
            definition = existing
        else:
            definition = CorrespondentDefinition(
                correspondent_name=request.correspondent_name,
                definition=request.definition,
                standard_tags=request.standard_tags,
                standard_document_type=request.standard_document_type,
                notes=request.notes,
            )
            self.preferences.correspondent_definitions[correspondent_key] = definition

        self.preferences.updated_at = datetime.utcnow()
        self._save()
        return definition

    def delete_correspondent_definition(self, correspondent_name: str) -> bool:
        """Delete a correspondent definition."""
        correspondent_key = correspondent_name.lower()
        if correspondent_key in self.preferences.correspondent_definitions:
            del self.preferences.correspondent_definitions[correspondent_key]
            self.preferences.updated_at = datetime.utcnow()
            self._save()
            return True
        return False

    # =========================================================================
    # Corrections
    # =========================================================================

    def add_correction(
        self,
        rejected_tag: str,
        preferred_tags: List[str],
        document_id: Optional[int] = None,
        document_snippet: Optional[str] = None,
        context_keywords: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> TagCorrection:
        """Add a learned correction from user feedback."""
        correction = TagCorrection(
            id=str(uuid.uuid4()),
            document_id=document_id,
            document_snippet=document_snippet,
            context_keywords=context_keywords or [],
            rejected_tag=rejected_tag,
            preferred_tags=preferred_tags,
            reason=reason,
        )
        self.preferences.corrections.append(correction)
        self.preferences.updated_at = datetime.utcnow()
        self._save()
        logger.info(
            "Added correction: %s -> %s (keywords: %s)",
            rejected_tag,
            preferred_tags,
            context_keywords,
        )
        return correction

    def get_corrections(self) -> List[TagCorrection]:
        """Get all corrections."""
        return self.preferences.corrections

    def get_relevant_corrections(self, content: str) -> List[TagCorrection]:
        """Get corrections relevant to the given content."""
        content_lower = content.lower()
        relevant = []

        for correction in self.preferences.corrections:
            # Check if any context keyword matches
            if correction.context_keywords:
                if any(kw.lower() in content_lower for kw in correction.context_keywords):
                    relevant.append(correction)
            # Also include corrections without keywords (global rules)
            elif not correction.context_keywords and correction.document_snippet:
                # Check if document snippet context matches
                if correction.document_snippet.lower() in content_lower:
                    relevant.append(correction)

        return relevant

    def delete_correction(self, correction_id: str) -> bool:
        """Delete a correction by ID."""
        for i, correction in enumerate(self.preferences.corrections):
            if correction.id == correction_id:
                del self.preferences.corrections[i]
                self.preferences.updated_at = datetime.utcnow()
                self._save()
                return True
        return False

    # =========================================================================
    # Vendor Rules
    # =========================================================================

    def get_vendor_rule(self, vendor_name: str) -> Optional[VendorTagRule]:
        """Get rule for a specific vendor."""
        return self.preferences.vendor_rules.get(vendor_name.lower())

    def get_all_vendor_rules(self) -> List[VendorTagRule]:
        """Get all vendor rules."""
        return list(self.preferences.vendor_rules.values())

    def set_vendor_rule(self, request: VendorRuleRequest) -> VendorTagRule:
        """Create or update a vendor rule."""
        vendor_key = request.vendor_name.lower()
        existing = self.preferences.vendor_rules.get(vendor_key)

        if existing:
            existing.standard_tags = request.standard_tags
            existing.standard_document_type = request.standard_document_type
            if request.correspondent_id:
                existing.correspondent_id = request.correspondent_id
            existing.updated_at = datetime.utcnow()
            rule = existing
        else:
            rule = VendorTagRule(
                vendor_name=request.vendor_name,
                correspondent_id=request.correspondent_id,
                standard_tags=request.standard_tags,
                standard_document_type=request.standard_document_type,
            )
            self.preferences.vendor_rules[vendor_key] = rule

        self.preferences.updated_at = datetime.utcnow()
        self._save()
        return rule

    def increment_vendor_rule_usage(self, vendor_name: str) -> None:
        """Increment the usage count for a vendor rule."""
        vendor_key = vendor_name.lower()
        if vendor_key in self.preferences.vendor_rules:
            self.preferences.vendor_rules[vendor_key].applied_count += 1
            self._save()

    def delete_vendor_rule(self, vendor_name: str) -> bool:
        """Delete a vendor rule."""
        vendor_key = vendor_name.lower()
        if vendor_key in self.preferences.vendor_rules:
            del self.preferences.vendor_rules[vendor_key]
            self.preferences.updated_at = datetime.utcnow()
            self._save()
            return True
        return False

    def find_vendor_rule_by_content(self, content: str, correspondent: Optional[str] = None) -> Optional[VendorTagRule]:
        """Find a matching vendor rule based on content or correspondent."""
        content_lower = content.lower()

        # First try exact correspondent match
        if correspondent:
            for rule in self.preferences.vendor_rules.values():
                if rule.vendor_name.lower() == correspondent.lower():
                    return rule

        # Then try content-based matching
        for rule in self.preferences.vendor_rules.values():
            vendor_lower = rule.vendor_name.lower()
            # Check if vendor name appears in content
            if vendor_lower in content_lower:
                return rule
            # Also check variations (e.g., "RapidRoute Solutions" vs "rapidroute-solutions")
            vendor_normalized = vendor_lower.replace(" ", "").replace("-", "").replace("_", "")
            content_normalized = content_lower.replace(" ", "").replace("-", "").replace("_", "")
            if vendor_normalized in content_normalized:
                return rule

        return None

    # =========================================================================
    # Settings
    # =========================================================================

    def get_settings(self) -> AIPreferenceSettings:
        """Get preference settings."""
        return self.preferences.settings

    def update_settings(self, **kwargs) -> AIPreferenceSettings:
        """Update preference settings."""
        for key, value in kwargs.items():
            if value is not None and hasattr(self.preferences.settings, key):
                setattr(self.preferences.settings, key, value)
        self.preferences.updated_at = datetime.utcnow()
        self._save()
        return self.preferences.settings

    # =========================================================================
    # Context Building for AI Prompts
    # =========================================================================

    def build_tag_context_for_prompt(self, content: str, existing_tags: List[str]) -> str:
        """Build context string for tag suggestion prompts.

        This includes relevant tag definitions, corrections, and rules.
        """
        sections = []

        # Add tag definitions that are relevant
        tag_defs = []
        for tag_name in existing_tags:
            definition = self.get_tag_definition(tag_name)
            if definition and definition.definition:
                def_text = f"- {definition.tag_name}: {definition.definition}"
                if definition.exclude_contexts:
                    def_text += f" (NOT for: {', '.join(definition.exclude_contexts)})"
                tag_defs.append(def_text)

        if tag_defs:
            sections.append("TAG DEFINITIONS (use these to understand what each tag means):\n" + "\n".join(tag_defs))

        # Add relevant corrections
        relevant_corrections = self.get_relevant_corrections(content)
        if relevant_corrections:
            corrections_text = []
            for corr in relevant_corrections[:5]:  # Limit to 5 most relevant
                corrections_text.append(
                    f"- Do NOT use '{corr.rejected_tag}' for this type of content. "
                    f"Use {', '.join(corr.preferred_tags)} instead."
                    + (f" Reason: {corr.reason}" if corr.reason else "")
                )
            sections.append(
                "LEARNED PREFERENCES (important - follow these rules):\n" + "\n".join(corrections_text)
            )

        # Add vendor rule if applicable
        vendor_rule = self.find_vendor_rule_by_content(content)
        if vendor_rule:
            rule_text = f"VENDOR RULE for '{vendor_rule.vendor_name}':\n"
            rule_text += f"- Standard tags to use: {', '.join(vendor_rule.standard_tags)}\n"
            if vendor_rule.standard_document_type:
                rule_text += f"- Standard document type: {vendor_rule.standard_document_type}\n"
            rule_text += "These tags should be consistently applied to all documents from this vendor."
            sections.append(rule_text)

        return "\n\n".join(sections) if sections else ""

    def build_doc_type_context_for_prompt(self, existing_doc_types: List[str]) -> str:
        """Build context string for document type suggestion prompts."""
        doc_type_defs = []
        for doc_type_name in existing_doc_types:
            definition = self.get_doc_type_definition(doc_type_name)
            if definition and definition.definition:
                def_text = f"- {definition.doc_type_name}: {definition.definition}"
                if definition.exclude_contexts:
                    def_text += f" (NOT for: {', '.join(definition.exclude_contexts)})"
                doc_type_defs.append(def_text)

        if doc_type_defs:
            return "DOCUMENT TYPE DEFINITIONS:\n" + "\n".join(doc_type_defs)
        return ""

    # =========================================================================
    # Auto-learning from user actions
    # =========================================================================

    def learn_from_tag_rejection(
        self,
        document_id: int,
        document_content: str,
        rejected_tag: str,
        accepted_tags: List[str],
    ) -> Optional[TagCorrection]:
        """Learn from user rejecting a tag and accepting others.

        Automatically extracts context keywords from the document.
        """
        if not self.preferences.settings.auto_learn_from_corrections:
            return None

        # Extract potential keywords from document (simple heuristic)
        content_lower = document_content.lower()
        keywords = []

        # Look for company/entity names (capitalized words)
        import re
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

        return self.add_correction(
            rejected_tag=rejected_tag,
            preferred_tags=accepted_tags,
            document_id=document_id,
            document_snippet=snippet,
            context_keywords=keywords,
            reason=f"User rejected '{rejected_tag}' and accepted {accepted_tags}",
        )

    def learn_vendor_rule_from_tagging(
        self,
        vendor_name: str,
        correspondent_id: Optional[int],
        tags: List[str],
        document_type: Optional[str],
    ) -> Optional[VendorTagRule]:
        """Learn vendor rule from consistent tagging patterns.

        Called after user applies tags to a document.
        """
        if not self.preferences.settings.auto_learn_vendor_rules:
            return None

        vendor_key = vendor_name.lower()
        existing_rule = self.preferences.vendor_rules.get(vendor_key)

        if existing_rule:
            # Update existing rule if tags are consistent
            existing_rule.applied_count += 1
            # Merge tags (keep common ones)
            if existing_rule.applied_count >= self.preferences.settings.min_vendor_occurrences_for_rule:
                # Find intersection of tags
                common_tags = set(existing_rule.standard_tags) & set(tags)
                if common_tags:
                    existing_rule.standard_tags = list(common_tags)
                else:
                    # Add new tags if no overlap
                    existing_rule.standard_tags = list(set(existing_rule.standard_tags + tags))
            existing_rule.updated_at = datetime.utcnow()
            self._save()
            return existing_rule
        else:
            # Create new rule
            rule = VendorTagRule(
                vendor_name=vendor_name,
                correspondent_id=correspondent_id,
                standard_tags=tags,
                standard_document_type=document_type,
                applied_count=1,
            )
            self.preferences.vendor_rules[vendor_key] = rule
            self.preferences.updated_at = datetime.utcnow()
            self._save()
            logger.info("Created vendor rule for %s: tags=%s", vendor_name, tags)
            return rule
