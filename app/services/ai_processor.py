"""AI-powered document processing service using LiteLLM."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import httpx

from app.clients.paperless import PaperlessClient
from app.config import Settings
from app.models.ai_processing import (
    DocumentSuggestion,
    DocumentTypeSuggestion,
    JobStatus,
    ProcessingJob,
    ProcessingOptions,
    SuggestionStatus,
    TagSuggestion,
)
from app.models.ai_preferences import SimilarDocumentExample
from app.models.document import (
    PaperlessDocument,
    PaperlessDocumentType,
    PaperlessTag,
)

logger = logging.getLogger(__name__)


class AIProcessorService:
    """Service for AI-powered document analysis using LiteLLM."""

    # Maximum content length to send to LLM (to avoid token limits)
    MAX_CONTENT_LENGTH = 4000

    def __init__(self, settings: Settings):
        """Initialize the AI processor service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.llm_base_url = settings.litellm_base_url
        self.llm_api_key = settings.litellm_api_key
        self.model = settings.query_model

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
    ) -> Optional[str]:
        """Make a call to LiteLLM.

        Args:
            system_prompt: System message for the LLM
            user_prompt: User message (the actual query)
            max_tokens: Maximum tokens in response
            temperature: Temperature for sampling (lower = more deterministic)

        Returns:
            LLM response text, or None if call fails
        """
        if not self.llm_base_url or not self.llm_api_key:
            logger.warning("LiteLLM not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.llm_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error("LLM call failed: %s - %s", response.status_code, response.text)
                    return None

        except Exception as e:
            logger.error("LLM call error: %s", e)
            return None

    def _truncate_content(self, content: str) -> str:
        """Truncate content to fit within token limits."""
        if len(content) > self.MAX_CONTENT_LENGTH:
            return content[: self.MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"
        return content

    async def generate_title(self, doc: PaperlessDocument) -> Optional[str]:
        """Generate an improved title for a document.

        Args:
            doc: The document to analyze

        Returns:
            Suggested title, or None if generation fails or current title is good
        """
        system_prompt = """You are a document organization assistant. Your task is to generate clear, descriptive titles for documents.

A good title should:
- Be concise (under 80 characters)
- Identify the document type (invoice, receipt, letter, statement, contract, etc.)
- Include key identifying information (company name, date, account number, etc.)
- Be human-readable and scannable

Examples of good titles:
- "Chase Bank Statement - December 2024"
- "Amazon Invoice #123-456-789 - $52.99"
- "State Farm Auto Insurance Policy Renewal"
- "IRS Form W-2 - 2024 Tax Year - Employer XYZ"
- "Lease Agreement - 123 Main St - 2024-2025"

If the current title is already descriptive and well-formatted, respond with exactly "NO_CHANGE".
Otherwise, respond with ONLY the new title (no quotes, no explanation)."""

        content = self._truncate_content(doc.content or "")

        user_prompt = f"""Current title: {doc.title}

Document content:
{content}

Generate an improved title or respond "NO_CHANGE" if the current title is good."""

        response = await self._call_llm(system_prompt, user_prompt, max_tokens=100)

        if not response:
            return None

        response = response.strip().strip('"\'')

        if response.upper() == "NO_CHANGE":
            return None

        # Limit length
        if len(response) > 100:
            response = response[:97] + "..."

        return response

    async def suggest_tags(
        self,
        doc: PaperlessDocument,
        existing_tags: List[PaperlessTag],
        preferences_context: str = "",
        similar_docs_context: str = "",
        similar_doc_tag_hints: Optional[List[tuple]] = None,
    ) -> List[TagSuggestion]:
        """Suggest relevant tags for a document.

        Args:
            doc: The document to analyze
            existing_tags: List of existing tags in paperless-ngx
            preferences_context: Context from user preferences (definitions, corrections)
            similar_docs_context: Context from similar already-tagged documents
            similar_doc_tag_hints: Tags from similar docs [(tag_name, confidence), ...]

        Returns:
            List of tag suggestions (preferring existing tags)
        """
        # Build list of existing tag names
        tag_names = sorted([tag.name for tag in existing_tags])
        tags_list = ", ".join(tag_names) if tag_names else "(no existing tags)"

        # Current tags on the document
        current_tags = ", ".join(doc.tag_names) if doc.tag_names else "(none)"

        # Build enhanced system prompt with context
        system_prompt = """You are a document tagging assistant. Your task is to suggest relevant tags for organizing documents.

CRITICAL GUIDELINES FOR CONSISTENCY:
1. STRONGLY prefer existing tags from the provided list - reuse them across similar documents
2. If similar documents are provided below, USE THE SAME TAGS for consistency
3. Only suggest a NEW tag if no existing tag fits AND the tag would be useful for multiple documents
4. Suggest 1-5 relevant tags
5. Tags should be specific enough to be useful but general enough to apply to multiple documents
6. Pay close attention to any USER PREFERENCES or LEARNED RULES below - these are mandatory

IMPORTANT SEMANTIC RULES:
- "medical" typically means HUMAN health records (doctor visits, prescriptions, health insurance)
- For pet/veterinary documents, use tags like "pets", "veterinary", or the pet's name
- Be consistent: if similar documents use certain tags, prefer those same tags

"""
        # Add preferences context if available
        if preferences_context:
            system_prompt += f"""
{preferences_context}

"""
            logger.info(
                "Including preferences context in tag suggestion (%d chars)",
                len(preferences_context)
            )

        # Add similar documents context if available
        if similar_docs_context:
            system_prompt += f"""
{similar_docs_context}

"""
            logger.info(
                "Including similar docs context in tag suggestion (%d chars)",
                len(similar_docs_context)
            )

        system_prompt += """Respond in JSON format:
{
  "tags": [
    {"name": "existing-tag-name", "is_new": false, "confidence": 0.95},
    {"name": "new-tag-suggestion", "is_new": true, "confidence": 0.7}
  ]
}

Only include tags you're confident about (confidence > 0.6).
Prioritize tags that appear in similar documents for consistency."""

        content = self._truncate_content(doc.content or "")

        user_prompt = f"""Existing tags in the system: {tags_list}

Current tags on this document: {current_tags}

Document title: {doc.title}
"""
        if doc.correspondent:
            user_prompt += f"Correspondent/Vendor: {doc.correspondent.name}\n"

        user_prompt += f"""
Document content:
{content}

Suggest appropriate tags in JSON format. Remember to prioritize consistency with similar documents."""

        logger.info(
            "Requesting tag suggestions for doc '%s' (content: %d chars, system prompt: %d chars)",
            doc.title[:50],
            len(content),
            len(system_prompt)
        )

        response = await self._call_llm(system_prompt, user_prompt, max_tokens=400)

        if not response:
            logger.warning("No response from LLM for tag suggestions")
            return []

        logger.info("LLM tag suggestion response: %s", response[:500] if len(response) > 500 else response)

        # Parse JSON response
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning("No JSON found in tag suggestion response")
                return []

            suggestions = []
            existing_tag_names = {tag.name.lower(): tag for tag in existing_tags}
            seen_tags = set()

            # First, add tags from similar documents if they're highly confident
            if similar_doc_tag_hints:
                for tag_name, hint_confidence in similar_doc_tag_hints:
                    if hint_confidence >= 0.7 and tag_name.lower() not in seen_tags:
                        existing_tag = existing_tag_names.get(tag_name.lower())
                        if existing_tag:
                            suggestions.append(
                                TagSuggestion(
                                    tag_id=existing_tag.id,
                                    tag_name=existing_tag.name,
                                    is_new=False,
                                    confidence=hint_confidence,
                                )
                            )
                            seen_tags.add(tag_name.lower())

            # Then add LLM suggestions
            for tag_data in data.get("tags", []):
                tag_name = tag_data.get("name", "").strip()
                if not tag_name or tag_name.lower() in seen_tags:
                    continue

                is_new = tag_data.get("is_new", True)
                confidence = float(tag_data.get("confidence", 0.5))

                # Check if tag actually exists (LLM might be wrong about is_new)
                existing_tag = existing_tag_names.get(tag_name.lower())
                if existing_tag:
                    suggestions.append(
                        TagSuggestion(
                            tag_id=existing_tag.id,
                            tag_name=existing_tag.name,
                            is_new=False,
                            confidence=confidence,
                        )
                    )
                else:
                    # Apply penalty for new tags
                    adjusted_confidence = max(0.0, confidence - 0.15)
                    if adjusted_confidence >= 0.6:
                        suggestions.append(
                            TagSuggestion(
                                tag_id=None,
                                tag_name=tag_name,
                                is_new=True,
                                confidence=adjusted_confidence,
                            )
                        )
                seen_tags.add(tag_name.lower())

            # Sort by confidence
            suggestions.sort(key=lambda s: s.confidence, reverse=True)
            final_suggestions = suggestions[:7]  # Limit to top 7 suggestions

            # Log final suggestions for accountability
            logger.info(
                "Final tag suggestions for doc '%s': %s",
                doc.title[:30],
                [(s.tag_name, s.confidence, "NEW" if s.is_new else "existing") for s in final_suggestions]
            )

            return final_suggestions

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse tag suggestion JSON: %s", e)
            return []

    async def suggest_document_type(
        self,
        doc: PaperlessDocument,
        existing_types: List[PaperlessDocumentType],
        similar_doc_type_hint: Optional[tuple] = None,
    ) -> Optional[DocumentTypeSuggestion]:
        """Suggest a document type for a document.

        Args:
            doc: The document to analyze
            existing_types: List of existing document types in paperless-ngx
            similar_doc_type_hint: Optional (type_name, confidence) from similar docs

        Returns:
            Document type suggestion, or None if uncertain
        """
        # Build list of existing type names
        type_names = sorted([dt.name for dt in existing_types])
        types_list = ", ".join(type_names) if type_names else "(no existing document types)"

        current_type = doc.document_type.name if doc.document_type else "(none)"

        system_prompt = """You are a document classification assistant. Your task is to classify documents into appropriate types.

Guidelines:
1. STRONGLY prefer existing document types from the provided list
2. Only suggest a NEW type if no existing type fits AND it would be commonly used
3. Common document types: Invoice, Receipt, Bank Statement, Insurance Policy, Tax Document,
   Contract, Letter, Medical Record, Utility Bill, Pay Stub, etc.
4. If a hint from similar documents is provided, consider it strongly as it indicates
   how the user has classified similar content before.

Respond in JSON format:
{
  "document_type": {"name": "Type Name", "is_new": false, "confidence": 0.9}
}

If you cannot confidently classify the document (confidence < 0.6), respond:
{
  "document_type": null
}"""

        content = self._truncate_content(doc.content or "")

        user_prompt = f"""Existing document types in the system: {types_list}

Current document type: {current_type}

Document title: {doc.title}
"""
        # Add hint from similar documents if available
        if similar_doc_type_hint:
            hint_type, hint_confidence = similar_doc_type_hint
            user_prompt += f"""
HINT FROM SIMILAR DOCUMENTS: Similar documents have been classified as "{hint_type}"
(confidence: {hint_confidence:.0%}). Consider using this type for consistency.
"""

        user_prompt += f"""
Document content:
{content}

Classify this document in JSON format."""

        response = await self._call_llm(system_prompt, user_prompt, max_tokens=150)

        if not response:
            return None

        # Parse JSON response
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                return None

            type_data = data.get("document_type")
            if not type_data:
                return None

            type_name = type_data.get("name", "").strip()
            if not type_name:
                return None

            is_new = type_data.get("is_new", True)
            confidence = float(type_data.get("confidence", 0.5))

            if confidence < 0.6:
                return None

            # Check if type actually exists
            existing_type_names = {dt.name.lower(): dt for dt in existing_types}
            existing_type = existing_type_names.get(type_name.lower())

            if existing_type:
                return DocumentTypeSuggestion(
                    doc_type_id=existing_type.id,
                    doc_type_name=existing_type.name,
                    is_new=False,
                    confidence=confidence,
                )
            else:
                return DocumentTypeSuggestion(
                    doc_type_id=None,
                    doc_type_name=type_name,
                    is_new=True,
                    confidence=confidence,
                )

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse document type JSON: %s", e)
            return None

    async def analyze_document(
        self,
        doc: PaperlessDocument,
        existing_tags: List[PaperlessTag],
        existing_doc_types: List[PaperlessDocumentType],
        generate_title: bool = True,
        suggest_tags: bool = True,
        suggest_doc_type: bool = True,
        preferences_context: str = "",
        similar_docs_context: str = "",
        similar_doc_tag_hints: Optional[List[tuple]] = None,
        similar_doc_type_hint: Optional[tuple] = None,
    ) -> DocumentSuggestion:
        """Analyze a single document and generate all suggestions.

        Args:
            doc: Document to analyze
            existing_tags: Available tags in paperless-ngx
            existing_doc_types: Available document types in paperless-ngx
            generate_title: Whether to suggest a title
            suggest_tags: Whether to suggest tags
            suggest_doc_type: Whether to suggest a document type
            preferences_context: Context from user preferences
            similar_docs_context: Context from similar documents
            similar_doc_tag_hints: Tag hints from similar docs

        Returns:
            DocumentSuggestion with all generated suggestions
        """
        logger.info(
            "=== Analyzing document %d: '%s' ===",
            doc.id,
            doc.title[:60]
        )
        logger.info(
            "  Current state: tags=%s, doc_type=%s, correspondent=%s",
            doc.tag_names,
            doc.document_type.name if doc.document_type else None,
            doc.correspondent.name if doc.correspondent else None
        )
        logger.info(
            "  Analysis options: title=%s, tags=%s, doc_type=%s",
            generate_title, suggest_tags, suggest_doc_type
        )
        logger.info(
            "  Context available: preferences=%d chars, similar_docs=%d chars, tag_hints=%s",
            len(preferences_context),
            len(similar_docs_context),
            len(similar_doc_tag_hints) if similar_doc_tag_hints else 0
        )

        suggestion = DocumentSuggestion(
            document_id=doc.id,
            current_title=doc.title,
            current_tags=doc.tag_names,
            current_document_type=doc.document_type.name if doc.document_type else None,
        )

        # Generate title suggestion
        if generate_title:
            try:
                title = await self.generate_title(doc)
                suggestion.suggested_title = title
                if title:
                    suggestion.title_status = SuggestionStatus.PENDING
                else:
                    suggestion.title_status = SuggestionStatus.REJECTED  # No change needed
            except Exception as e:
                logger.error("Title generation failed for doc %d: %s", doc.id, e)
                suggestion.title_status = SuggestionStatus.FAILED

        # Generate tag suggestions with context
        if suggest_tags:
            try:
                tags = await self.suggest_tags(
                    doc,
                    existing_tags,
                    preferences_context=preferences_context,
                    similar_docs_context=similar_docs_context,
                    similar_doc_tag_hints=similar_doc_tag_hints,
                )
                suggestion.suggested_tags = tags
                if tags:
                    suggestion.tags_status = SuggestionStatus.PENDING
                else:
                    suggestion.tags_status = SuggestionStatus.REJECTED
            except Exception as e:
                logger.error("Tag suggestion failed for doc %d: %s", doc.id, e)
                suggestion.tags_status = SuggestionStatus.FAILED

        # Generate document type suggestion
        if suggest_doc_type:
            try:
                doc_type = await self.suggest_document_type(
                    doc, existing_doc_types, similar_doc_type_hint
                )
                suggestion.suggested_document_type = doc_type
                if doc_type:
                    suggestion.doc_type_status = SuggestionStatus.PENDING
                else:
                    suggestion.doc_type_status = SuggestionStatus.REJECTED
            except Exception as e:
                logger.error("Document type suggestion failed for doc %d: %s", doc.id, e)
                suggestion.doc_type_status = SuggestionStatus.FAILED

        suggestion.processed_at = datetime.utcnow()

        # Log summary of analysis results
        logger.info(
            "=== Analysis complete for doc %d ===",
            doc.id
        )
        logger.info(
            "  Title: '%s' -> '%s' (status: %s)",
            doc.title[:30],
            (suggestion.suggested_title or "NO CHANGE")[:30] if suggestion.suggested_title else "NO CHANGE",
            suggestion.title_status.value
        )
        logger.info(
            "  Tags: %s (status: %s)",
            [t.tag_name for t in suggestion.suggested_tags] if suggestion.suggested_tags else "NONE",
            suggestion.tags_status.value
        )
        logger.info(
            "  Doc Type: %s (status: %s)",
            suggestion.suggested_document_type.doc_type_name if suggestion.suggested_document_type else "NONE",
            suggestion.doc_type_status.value
        )

        return suggestion

    async def process_batch(
        self,
        paperless: PaperlessClient,
        job: ProcessingJob,
        progress_callback=None,
        preferences_manager=None,
        similar_doc_finder=None,
    ) -> ProcessingJob:
        """Process a batch of documents.

        Args:
            paperless: Paperless client instance
            job: Processing job with options and document IDs
            progress_callback: Optional callback(current, total, doc_title) for progress.
                Can be sync or async callable.
            preferences_manager: Optional AIPreferencesManager for context
            similar_doc_finder: Optional SimilarDocumentFinder for RAG

        Returns:
            Updated ProcessingJob with suggestions
        """
        import asyncio

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()

        options = job.options
        document_ids = options.document_ids

        # Get existing taxonomy
        existing_tags = paperless.get_all_tags()
        existing_doc_types = paperless.get_all_document_types()

        job.progress_total = len(document_ids)
        job.progress_current = 0

        # Build document metadata cache for similar doc lookup
        doc_metadata_cache: Dict[int, dict] = {}
        if similar_doc_finder:
            logger.info("Building document metadata cache for similar document lookup...")
            async for doc in paperless.iter_documents():
                doc_metadata_cache[doc.id] = {
                    "title": doc.title,
                    "tags": doc.tag_names,
                    "document_type": doc.document_type.name if doc.document_type else None,
                    "correspondent": doc.correspondent.name if doc.correspondent else None,
                }
            cache_ids = sorted(doc_metadata_cache.keys())
            docs_with_tags = sum(1 for m in doc_metadata_cache.values() if m.get("tags"))
            logger.info(
                "Cached metadata for %d documents (IDs %d-%d), %d have tags",
                len(doc_metadata_cache),
                min(cache_ids) if cache_ids else 0,
                max(cache_ids) if cache_ids else 0,
                docs_with_tags
            )

        for doc_id in document_ids:
            try:
                # Fetch document
                doc = await paperless.get_document(doc_id)
                job.current_document_title = doc.title

                if progress_callback:
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(job.progress_current, job.progress_total, doc.title)
                    else:
                        progress_callback(job.progress_current, job.progress_total, doc.title)

                # Build context from preferences (includes correspondent-based rules)
                preferences_context = ""
                if preferences_manager:
                    tag_names = [t.name for t in existing_tags]
                    correspondent_name = doc.correspondent.name if doc.correspondent else None
                    doc_type_name = doc.document_type.name if doc.document_type else None
                    preferences_context = await preferences_manager.build_tag_context_for_prompt(
                        doc.content or "",
                        tag_names,
                        correspondent=correspondent_name,
                        document_type=doc_type_name,
                    )

                # Find similar documents for few-shot examples
                similar_docs_context = ""
                similar_doc_tag_hints = None
                similar_doc_type_hint = None
                if similar_doc_finder and doc.content:
                    try:
                        similar_docs = await similar_doc_finder.find_similar_documents(
                            content=doc.content,
                            existing_doc_tags=doc_metadata_cache,
                            exclude_doc_id=doc.id,
                            top_k=10,  # More similar docs for better context
                            min_similarity=0.4,  # Lower threshold to find more matches
                            correspondent=doc.correspondent.name if doc.correspondent else None,
                        )
                        if similar_docs:
                            similar_docs_context = similar_doc_finder.build_few_shot_context(
                                similar_docs, include_doc_types=options.suggest_document_type
                            )
                            # Get tag hints from similar docs
                            similar_doc_tag_hints = similar_doc_finder.suggest_tags_from_similar(
                                similar_docs, min_occurrences=1
                            )
                            # Get document type hint from similar docs
                            similar_doc_type_hint = similar_doc_finder.suggest_doc_type_from_similar(
                                similar_docs
                            )
                            logger.info(
                                "Similar doc analysis for doc %d: %d docs, %d tag hints, doc_type_hint=%s",
                                doc_id,
                                len(similar_docs),
                                len(similar_doc_tag_hints) if similar_doc_tag_hints else 0,
                                similar_doc_type_hint[0] if similar_doc_type_hint else None,
                            )
                    except Exception as e:
                        logger.warning("Similar doc lookup failed for doc %d: %s", doc_id, e)

                # Analyze document with context
                suggestion = await self.analyze_document(
                    doc=doc,
                    existing_tags=existing_tags,
                    existing_doc_types=existing_doc_types,
                    generate_title=options.generate_titles,
                    suggest_tags=options.suggest_tags,
                    suggest_doc_type=options.suggest_document_type,
                    preferences_context=preferences_context,
                    similar_docs_context=similar_docs_context,
                    similar_doc_tag_hints=similar_doc_tag_hints,
                    similar_doc_type_hint=similar_doc_type_hint,
                )

                job.suggestions[doc_id] = suggestion

                # Auto-apply if enabled
                if options.auto_apply and suggestion.has_pending_suggestions():
                    # Mark all pending as approved
                    if suggestion.title_status == SuggestionStatus.PENDING:
                        suggestion.title_status = SuggestionStatus.APPROVED
                    if suggestion.tags_status == SuggestionStatus.PENDING:
                        suggestion.tags_status = SuggestionStatus.APPROVED
                    if suggestion.doc_type_status == SuggestionStatus.PENDING:
                        suggestion.doc_type_status = SuggestionStatus.APPROVED

                    # TODO: Apply immediately (would need applier service)

            except Exception as e:
                logger.error("Failed to process document %d: %s", doc_id, e)
                job.errors.append(f"Document {doc_id}: {str(e)}")

            job.progress_current += 1

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.current_document_title = None

        return job
