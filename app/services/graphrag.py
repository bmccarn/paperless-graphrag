"""GraphRAG service for indexing and querying documents."""

import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Callable, List, Optional

import yaml

from app.config import Settings
from app.models.document import GraphRAGDocument
from app.services.graph_reader import GraphReaderService

logger = logging.getLogger(__name__)

# GraphRAG indexing workflow steps and their approximate progress percentages
GRAPHRAG_STEPS = [
    ("create_base_text_units", 5, "Creating text units"),
    ("create_base_extracted_entities", 15, "Extracting entities"),
    ("create_summarized_entities", 25, "Summarizing entities"),
    ("create_base_entity_graph", 35, "Building entity graph"),
    ("create_final_entities", 40, "Finalizing entities"),
    ("create_final_nodes", 45, "Creating nodes"),
    ("create_final_communities", 50, "Creating communities"),
    ("create_final_community_reports", 60, "Generating community reports"),
    ("create_final_text_units", 70, "Finalizing text units"),
    ("create_base_documents", 75, "Processing documents"),
    ("create_final_documents", 80, "Finalizing documents"),
    ("create_final_relationships", 85, "Creating relationships"),
    ("create_final_covariates", 90, "Creating covariates"),
    ("generate_text_embeddings", 95, "Generating embeddings"),
]

# Type for progress callback: (percent, message, detail)
ProgressCallback = Callable[[int, str, Optional[str]], None]


def _extract_source_ids_from_response(response: str) -> tuple[list[str], list[str]]:
    """Extract source and entity IDs from GraphRAG response text.

    Parses patterns like [Data: Sources (291, 292); Entities (1780, 3514)]
    and extracts both source IDs and entity IDs.

    Args:
        response: The GraphRAG response text

    Returns:
        Tuple of (source_ids, entity_ids)
    """
    source_ids = []
    entity_ids = []

    # Match patterns like [Data: Sources (291, 292); ...] or [Data: Sources (291)]
    source_matches = re.findall(r'\[Data:[^\]]*Sources\s*\(([^)]+)\)[^\]]*\]', response)
    for match in source_matches:
        ids = [s.strip() for s in match.split(',')]
        source_ids.extend(ids)

    # Match patterns like [Data: Entities (1780, 3514)] or [Data: ... Entities (1780)]
    entity_matches = re.findall(r'\[Data:[^\]]*Entities\s*\(([^)]+)\)[^\]]*\]', response)
    for match in entity_matches:
        ids = [s.strip() for s in match.split(',')]
        entity_ids.extend(ids)

    return list(set(source_ids)), list(set(entity_ids))  # Deduplicate


class GraphRAGService:
    """Service for GraphRAG operations including indexing and querying."""

    def __init__(self, settings: Settings):
        """Initialize GraphRAG service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.root = Path(settings.graphrag_root)
        self.input_dir = self.root / "input"
        self.output_dir = self.root / "output"
        self.cache_dir = self.root / "cache"

    async def initialize(self) -> None:
        """Initialize GraphRAG project structure and configuration."""
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Generate settings.yaml if it doesn't exist or needs update
        settings_path = self.root / "settings.yaml"
        await self._generate_settings(settings_path)

        # Generate .env file
        env_path = self.root / ".env"
        await self._generate_env(env_path)

        logger.info("GraphRAG project initialized at %s", self.root)

    async def _generate_settings(self, settings_path: Path) -> None:
        """Generate GraphRAG settings.yaml with LiteLLM configuration."""
        settings_config = {
            "models": {
                "default_chat_model": {
                    # Used for indexing (entity extraction, summarization, etc.)
                    "type": "chat",
                    "auth_type": "api_key",
                    "api_key": "${GRAPHRAG_API_KEY}",
                    "model_provider": "openai",
                    "model": self.settings.indexing_model,
                    "api_base": self.settings.litellm_base_url,
                    "requests_per_minute": self.settings.requests_per_minute,
                    "tokens_per_minute": self.settings.tokens_per_minute,
                    "concurrent_requests": self.settings.concurrent_requests,
                    "request_timeout": 600,  # 10 minutes for large text units
                },
                "query_chat_model": {
                    # Used for search queries (local, global, drift)
                    "type": "chat",
                    "auth_type": "api_key",
                    "api_key": "${GRAPHRAG_API_KEY}",
                    "model_provider": "openai",
                    "model": self.settings.query_model,
                    "api_base": self.settings.litellm_base_url,
                    "requests_per_minute": self.settings.requests_per_minute,
                    "tokens_per_minute": self.settings.tokens_per_minute,
                    "concurrent_requests": self.settings.concurrent_requests,
                    "request_timeout": 600,
                },
                "default_embedding_model": {
                    # Used for embeddings (both indexing and queries)
                    "type": "embedding",
                    "auth_type": "api_key",
                    "api_key": "${GRAPHRAG_API_KEY}",
                    "model_provider": "openai",
                    "model": self.settings.embedding_model,
                    "api_base": self.settings.litellm_base_url,
                },
            },
            "input": {
                "type": "file",
                "file_type": "text",
                "base_dir": "input",
                "file_pattern": ".*\\.txt$$",  # $$ escapes $ for GraphRAG's Template parser
            },
            "storage": {
                "type": "file",
                "base_dir": "output",
            },
            "cache": {
                "type": "file",
                "base_dir": "cache",
            },
            "chunks": {
                "size": self.settings.chunk_size,
                "overlap": self.settings.chunk_overlap,
                "group_by_columns": ["id"],
                "prepend_metadata": True,
                "chunk_size_includes_metadata": True,
            },
            "extract_graph": {
                "prompt": "prompts/extract_graph.txt",
                "entity_types": [
                    "organization",
                    "person",
                    "tax preparer",
                    "tax form",
                    "tax identification number",
                    "financial account",
                    "transaction",
                    "monetary amount",
                    "certification",
                    "insurance policy",
                    "insurance claim",
                    "medical benefit",
                    "healthcare service",
                    "government benefits program",
                    "statute or regulation",
                    "appraisal",
                    "address",
                    "date/event",
                ],
                "max_gleanings": 2,
            },
            "summarize_descriptions": {
                "prompt": "prompts/summarize_descriptions.txt",
                "max_length": 500,
            },
            "community_reports": {
                "prompt": "prompts/community_report_graph.txt",
                "max_length": 2000,
            },
            "local_search": {
                "chat_model_id": "query_chat_model",
                "text_unit_prop": self.settings.text_unit_prop,
                "community_prop": 0.1,
                "top_k_entities": self.settings.top_k_entities,
                "top_k_relationships": self.settings.top_k_relationships,
                "max_tokens": self.settings.max_tokens,
            },
            "global_search": {
                "chat_model_id": "query_chat_model",
                "max_tokens": self.settings.max_tokens,
                "dynamic_community_selection": {
                    "enabled": True,
                    "max_communities": 50,
                },
                "concurrent_coroutines": 32,
            },
            "drift_search": {
                "chat_model_id": "query_chat_model",
                "data_max_tokens": min(64000, self.settings.max_tokens // 2),
                "concurrency": 10,
                "drift_k_followups": 5,
                "primer_folds": 3,
                "n_depth": 2,
                "local_search_text_unit_prop": self.settings.text_unit_prop,
                "local_search_community_prop": 0.1,
                "local_search_top_k_mapped_entities": self.settings.top_k_entities,
                "local_search_top_k_relationships": self.settings.top_k_relationships,
                "local_search_max_data_tokens": min(64000, self.settings.max_tokens // 2),
            },
            "extract_claims": {
                "enabled": True,
                "description": "Claims about financial obligations, policy coverages, insurance benefits, legal agreements, tax liabilities, medical coverage, certification requirements, or regulatory compliance",
                "max_gleanings": 2,
            },
            "embed_graph": {
                "enabled": True,
                "dimensions": 384,
                "num_walks": 10,
                "walk_length": 40,
                "window_size": 2,
                "iterations": 3,
            },
            "umap": {
                "enabled": True,
            },
            "prune_graph": {
                "min_node_freq": 2,
                "min_node_degree": 1,
            },
            "snapshots": {
                "graphml": True,
                "embeddings": True,
            },
        }

        with open(settings_path, "w") as f:
            yaml.dump(settings_config, f, default_flow_style=False, sort_keys=False)

        logger.info("Generated GraphRAG settings at %s", settings_path)

    async def _generate_env(self, env_path: Path) -> None:
        """Generate .env file for GraphRAG."""
        env_content = f"GRAPHRAG_API_KEY={self.settings.litellm_api_key}\n"
        with open(env_path, "w") as f:
            f.write(env_content)
        logger.debug("Generated GraphRAG .env at %s", env_path)

    async def write_documents(self, documents: List[GraphRAGDocument]) -> int:
        """Write documents to GraphRAG input directory.

        Uses asyncio.to_thread for non-blocking file I/O.

        Args:
            documents: List of GraphRAG documents to write

        Returns:
            Number of documents written
        """
        def _write_sync():
            count = 0
            for doc in documents:
                doc_path = self.input_dir / f"{doc.id}.txt"
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(doc.text)
                count += 1
            return count

        count = await asyncio.to_thread(_write_sync)
        logger.info("Wrote %d documents to GraphRAG input", count)
        return count

    async def remove_documents(self, doc_ids: List[str]) -> int:
        """Remove documents from GraphRAG input directory.

        Uses asyncio.to_thread for non-blocking file I/O.

        Args:
            doc_ids: List of document IDs to remove

        Returns:
            Number of documents removed
        """
        def _remove_sync():
            count = 0
            for doc_id in doc_ids:
                doc_path = self.input_dir / f"{doc_id}.txt"
                if doc_path.exists():
                    doc_path.unlink()
                    count += 1
            return count

        count = await asyncio.to_thread(_remove_sync)
        logger.info("Removed %d documents from GraphRAG input", count)
        return count

    def get_input_document_count(self) -> int:
        """Get count of documents in input directory."""
        return len(list(self.input_dir.glob("*.txt")))

    def has_index(self) -> bool:
        """Check if GraphRAG index exists."""
        # Check for key output files that indicate successful indexing
        # GraphRAG 2.x outputs directly to the output directory
        required_files = ["entities.parquet", "relationships.parquet", "text_units.parquet"]
        return all((self.output_dir / f).exists() for f in required_files)

    def _parse_progress(self, line: str) -> Optional[tuple[int, str, Optional[str]]]:
        """Parse a line of GraphRAG output to extract progress info.

        Args:
            line: Output line from GraphRAG

        Returns:
            Tuple of (percent, message, detail) if progress detected, None otherwise
        """
        # Look for workflow step indicators (e.g., "🚀 create_base_text_units")
        for step_name, percent, message in GRAPHRAG_STEPS:
            if step_name in line:
                return (percent, message, step_name)

        # Look for completion indicators
        if "completed successfully" in line.lower() or "indexing completed" in line.lower():
            return (100, "Completed", None)

        # Look for progress patterns like "Processing X of Y" or percentages
        progress_match = re.search(r'(\d+)\s*[%/]\s*(\d+)?', line)
        if progress_match:
            if progress_match.group(2):
                # X/Y format
                current = int(progress_match.group(1))
                total = int(progress_match.group(2))
                percent = min(99, int((current / total) * 100))
            else:
                # Direct percentage
                percent = min(99, int(progress_match.group(1)))
            return (percent, "Processing...", line.strip()[:100])

        return None

    async def run_index(
        self,
        update: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> dict:
        """Run GraphRAG indexing pipeline with non-blocking execution.

        Args:
            update: If True, run incremental update instead of full index
            progress_callback: Optional callback for progress updates (percent, message, detail)

        Returns:
            Dict with status and output

        Raises:
            RuntimeError: If indexing fails
        """
        await self.initialize()

        # Build command using Python module invocation
        root_abs = str(self.root.resolve())

        if update and self.has_index():
            cmd = [
                sys.executable, "-m", "graphrag",
                "update",
                "--root",
                root_abs,
            ]
            operation = "update"
        else:
            cmd = [
                sys.executable, "-m", "graphrag",
                "index",
                "--root",
                root_abs,
            ]
            operation = "index"

        logger.info("Starting GraphRAG %s (non-blocking)...", operation)

        # Prepare environment
        env = os.environ.copy()
        env["GRAPHRAG_API_KEY"] = self.settings.litellm_api_key
        # Prevent buffering issues that can cause BrokenPipeError
        env["PYTHONUNBUFFERED"] = "1"
        # Use dumb terminal to avoid carriage return progress bars that can break pipes
        env["TERM"] = "dumb"
        # Disable rich console output that can interfere with subprocess pipes
        env["NO_COLOR"] = "1"

        # Use asyncio subprocess for true non-blocking execution
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=root_abs,
            env=env,
        )

        stdout_lines = []
        stderr_lines = []

        async def read_stream(stream, lines_list, is_stderr=False):
            """Read stream and process progress.

            Uses chunked reading to handle very long lines that exceed
            asyncio's default readline buffer limit (64KB).
            """
            buffer = ""
            while True:
                try:
                    # Read chunks instead of lines to handle very long output
                    chunk = await stream.read(8192)  # 8KB chunks
                    if not chunk:
                        # Process any remaining buffer content
                        if buffer.strip():
                            lines_list.append(buffer.strip())
                            if is_stderr:
                                logger.debug("GraphRAG stderr: %s", buffer.strip()[:500])
                            else:
                                logger.debug("GraphRAG stdout: %s", buffer.strip()[:500])
                        break

                    buffer += chunk.decode('utf-8', errors='replace')

                    # Process complete lines from buffer
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        decoded = line.strip()
                        if decoded:
                            lines_list.append(decoded)
                            # Log the output (truncate very long lines)
                            log_line = decoded[:500] + "..." if len(decoded) > 500 else decoded
                            if is_stderr:
                                logger.debug("GraphRAG stderr: %s", log_line)
                            else:
                                logger.debug("GraphRAG stdout: %s", log_line)

                            # Parse and report progress
                            if progress_callback:
                                progress = self._parse_progress(decoded)
                                if progress:
                                    progress_callback(*progress)
                except Exception as e:
                    logger.warning("Error reading stream: %s", e)
                    break

        # Read both streams concurrently
        await asyncio.gather(
            read_stream(process.stdout, stdout_lines, is_stderr=False),
            read_stream(process.stderr, stderr_lines, is_stderr=True),
        )

        # Wait for process to complete
        return_code = await process.wait()

        stdout_text = '\n'.join(stdout_lines)
        stderr_text = '\n'.join(stderr_lines)

        if return_code != 0:
            logger.error("GraphRAG %s failed (code %d): %s", operation, return_code, stderr_text)
            raise RuntimeError(f"GraphRAG {operation} failed: {stderr_text}")

        logger.info("GraphRAG %s completed successfully", operation)

        if progress_callback:
            progress_callback(100, "Completed", None)

        return {
            "status": "completed",
            "operation": operation,
            "output": stdout_text,
        }

    async def query(
        self,
        query: str,
        method: str = "local",
        community_level: Optional[int] = None,
    ) -> dict:
        """Execute a GraphRAG query with non-blocking execution.

        Args:
            query: The query string
            method: Query method (local, global, drift, basic)
            community_level: Community level for local search

        Returns:
            Dict with query, method, response, and source_documents

        Raises:
            RuntimeError: If query fails
        """
        result = None
        async for event in self.query_stream(query, method, community_level):
            if event.get("type") == "complete":
                result = event
            elif event.get("type") == "error":
                raise RuntimeError(event.get("message", "Query failed"))

        if not result:
            raise RuntimeError("Query completed without result")

        response_text = result.get("response", "")

        # Extract source documents from response
        source_ids, entity_ids = _extract_source_ids_from_response(response_text)
        source_documents = []
        graph_reader = GraphReaderService(self.output_dir)
        paperless_base_url = self.settings.paperless_url

        if source_ids:
            source_documents = graph_reader.get_documents_from_source_ids(
                source_ids, paperless_base_url
            )

        # If no source documents from Sources, try getting them from entity IDs
        if not source_documents and entity_ids:
            source_documents = graph_reader.get_documents_from_entity_ids(
                entity_ids, paperless_base_url
            )

        return {
            "query": query,
            "method": method,
            "response": response_text,
            "source_documents": source_documents,
        }

    def _parse_graphrag_log(self, line: str) -> Optional[dict]:
        """Parse a GraphRAG log line into a user-friendly event.

        Returns dict with 'message' and optional 'detail', or None to skip.
        """
        line_lower = line.lower()

        # Skip noise/debug lines and Python traceback patterns
        skip_patterns = [
            "debug:",
            "warning:",
            "httpx",
            "asyncio",
            "charset_normalizer",
            "using default",
            "api_base",
            "api_version",
            # Python traceback patterns
            "traceback",
            "exception",
            "error:",
            "file \"",  # Python traceback file references
            # Pydantic serialization warnings (don't show in UI but they're logged)
            "pydantic",
            "serialization",
            "unexpected",
            "expected `",
        ]
        if any(p in line_lower for p in skip_patterns):
            return None

        # Skip Python traceback lines (return statements, raise statements, etc.)
        # These look like: "return bound(*args, **kwds)" or "raise SomeError"
        traceback_indicators = [
            line.strip().startswith("return "),
            line.strip().startswith("raise "),
            line.strip().startswith("File "),
            line.strip().startswith("^"),
            "bound(*args" in line,
            "**kwds)" in line,
        ]
        if any(traceback_indicators):
            return None

        # Parse specific GraphRAG operations
        if "loading" in line_lower and "parquet" in line_lower:
            return {"message": "Loading graph data", "detail": line}

        if "reading" in line_lower and ("entities" in line_lower or "relationships" in line_lower):
            return {"message": "Reading graph structure", "detail": line}

        if "search" in line_lower:
            if "local" in line_lower:
                return {"message": "Executing local search", "detail": line}
            if "global" in line_lower:
                return {"message": "Executing global search", "detail": line}
            return {"message": "Searching", "detail": line}

        if "community" in line_lower or "communities" in line_lower:
            return {"message": "Analyzing communities", "detail": line}

        if "context" in line_lower:
            return {"message": "Building context", "detail": line}

        if "embedding" in line_lower or "embeddings" in line_lower:
            return {"message": "Computing embeddings", "detail": line}

        if "llm" in line_lower or "generating" in line_lower or "response" in line_lower:
            return {"message": "Generating response", "detail": line}

        if "extract" in line_lower:
            return {"message": "Extracting information", "detail": line}

        if "rank" in line_lower or "scoring" in line_lower:
            return {"message": "Ranking results", "detail": line}

        if "map" in line_lower and "reduce" in line_lower:
            return {"message": "Map-reduce processing", "detail": line}

        if "chunk" in line_lower:
            return {"message": "Processing text chunks", "detail": line}

        # For INFO level logs, extract the actual message
        if "info:" in line_lower or line.startswith("INFO"):
            # Extract message after INFO marker
            parts = line.split("INFO", 1)
            if len(parts) > 1:
                msg = parts[1].strip().lstrip(":").strip()
                if msg and len(msg) > 5:
                    return {"message": "Processing", "detail": msg[:200]}

        # Generic processing for other meaningful lines
        if len(line) > 10 and not line.startswith(" ") and "=" not in line[:20]:
            # Truncate very long lines
            detail = line[:200] + "..." if len(line) > 200 else line
            return {"message": "Processing", "detail": detail}

        return None

    async def query_stream(
        self,
        query: str,
        method: str = "local",
        community_level: Optional[int] = None,
    ):
        """Execute a GraphRAG query with streaming progress updates.

        Streams actual GraphRAG output instead of fake time-based stages.

        Args:
            query: The query string
            method: Query method (local, global, drift, basic)
            community_level: Community level for local search

        Yields:
            Dict events with type and data (status, thinking, complete, error)
        """
        if not self.has_index():
            yield {"type": "error", "message": "No GraphRAG index found. Run indexing first."}
            return

        community_level = community_level or self.settings.community_level

        # Use absolute path for --root
        root_abs = str(self.root.resolve())

        cmd = [
            sys.executable, "-m", "graphrag",
            "query",
            "--root",
            root_abs,
            "--method",
            method,
            "--community-level",
            str(community_level),
            "--query",
            query,
        ]

        # Yield initial status
        method_descriptions = {
            "local": "Searching entities and relationships in your documents",
            "global": "Analyzing community summaries across all documents",
            "drift": "Running hybrid local + global search with drift",
            "basic": "Performing vector similarity search",
        }

        yield {
            "type": "status",
            "message": f"Starting {method} search",
            "detail": method_descriptions.get(method, "Processing query"),
        }

        logger.info("Executing GraphRAG query with method=%s", method)

        # Prepare environment
        env = os.environ.copy()
        env["GRAPHRAG_API_KEY"] = self.settings.litellm_api_key
        # Enable verbose logging from GraphRAG
        env["GRAPHRAG_LOG_LEVEL"] = "INFO"
        # Prevent buffering issues that can cause BrokenPipeError
        env["PYTHONUNBUFFERED"] = "1"
        # Use dumb terminal to avoid carriage return progress bars that can break pipes
        env["TERM"] = "dumb"
        # Disable rich console output that can interfere with subprocess pipes
        env["NO_COLOR"] = "1"

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=root_abs,
            env=env,
        )

        stdout_lines = []
        stderr_lines = []

        # Use a queue to pass stderr events back to main generator
        event_queue: asyncio.Queue = asyncio.Queue()

        async def read_stderr():
            """Read stderr and queue thinking/progress events."""
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded:
                    stderr_lines.append(decoded)
                    # Log errors/warnings at INFO level for visibility
                    if any(p in decoded.lower() for p in ['error', 'exception', 'unexpected', 'pydantic', 'failed']):
                        logger.warning("GraphRAG stderr (potential issue): %s", decoded[:500])
                    else:
                        logger.debug("GraphRAG stderr: %s", decoded)
                    # Parse and queue meaningful events
                    parsed = self._parse_graphrag_log(decoded)
                    if parsed:
                        await event_queue.put(parsed)

        async def read_stdout():
            """Read stdout (the actual response)."""
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded:
                    stdout_lines.append(decoded)

        # Start reading streams
        stderr_task = asyncio.create_task(read_stderr())
        stdout_task = asyncio.create_task(read_stdout())

        # Method-specific search descriptions
        method_details = {
            "local": [
                ("Loading knowledge graph", "Reading entities, relationships, and text chunks"),
                ("Computing query embeddings", "Converting your question to vector representation"),
                ("Searching entity index", f"Finding entities related to: {query[:50]}{'...' if len(query) > 50 else ''}"),
                ("Building search context", "Gathering relevant entities and their relationships"),
                ("Generating response", "Synthesizing answer from retrieved context"),
            ],
            "global": [
                ("Loading community reports", "Reading pre-computed community summaries"),
                ("Analyzing communities", f"Searching summaries for: {query[:50]}{'...' if len(query) > 50 else ''}"),
                ("Map-reduce processing", "Aggregating insights from multiple community reports"),
                ("Generating response", "Synthesizing comprehensive answer"),
            ],
            "drift": [
                ("Loading knowledge graph", "Preparing hybrid search"),
                ("Local entity search", f"Finding entities related to: {query[:50]}{'...' if len(query) > 50 else ''}"),
                ("Global community search", "Analyzing community summaries"),
                ("Merging results", "Combining local and global search results"),
                ("Generating response", "Synthesizing answer from combined context"),
            ],
            "basic": [
                ("Computing embeddings", "Converting query to vector representation"),
                ("Vector similarity search", f"Searching for: {query[:50]}{'...' if len(query) > 50 else ''}"),
                ("Retrieving text chunks", "Gathering relevant document sections"),
                ("Generating response", "Synthesizing answer from retrieved text"),
            ],
        }

        stages = method_details.get(method, method_details["local"])
        current_stage = 0
        stage_times = [0.3, 1.0, 2.5, 4.0, 6.0]  # Approximate times for each stage

        yield {
            "type": "thinking",
            "message": stages[0][0],
            "detail": stages[0][1],
        }

        # Track last message to avoid duplicates
        last_message = stages[0][0]
        start_time = asyncio.get_event_loop().time()

        # Poll for events and completion
        # Send heartbeats every 15 seconds to keep Cloudflare/proxies alive
        last_heartbeat = start_time
        heartbeat_interval = 15.0  # seconds

        while not (stdout_task.done() and stderr_task.done() and event_queue.empty()):
            try:
                # Try to get an event with a short timeout
                event = await asyncio.wait_for(event_queue.get(), timeout=0.3)
                # Skip deprecation warnings and other noise
                if "deprecated" in event.get("detail", "").lower():
                    continue
                # Only yield if message changed (avoid spam)
                if event["message"] != last_message:
                    last_message = event["message"]
                    yield {"type": "thinking", **event}
                    last_heartbeat = asyncio.get_event_loop().time()
            except asyncio.TimeoutError:
                # No event from GraphRAG, use time-based stage progression
                elapsed = asyncio.get_event_loop().time() - start_time
                current_time = asyncio.get_event_loop().time()

                # Progress through stages based on elapsed time
                stage_changed = False
                while (current_stage < len(stages) - 1 and
                       current_stage < len(stage_times) and
                       elapsed >= stage_times[current_stage]):
                    current_stage += 1
                    msg, detail = stages[current_stage]
                    if msg != last_message:
                        last_message = msg
                        yield {"type": "thinking", "message": msg, "detail": detail}
                        last_heartbeat = current_time
                        stage_changed = True

                # Send heartbeat if no event was sent recently (keeps proxy connections alive)
                if not stage_changed and (current_time - last_heartbeat) >= heartbeat_interval:
                    yield {"type": "heartbeat"}
                    last_heartbeat = current_time

        # Ensure both tasks complete
        await stderr_task
        await stdout_task
        await process.wait()

        stdout_text = '\n'.join(stdout_lines).strip()
        stderr_text = '\n'.join(stderr_lines).strip()

        # Log stderr even on success for debugging
        if stderr_text:
            logger.debug("GraphRAG stderr output: %s", stderr_text[:2000])

        if process.returncode != 0:
            logger.error("GraphRAG query failed with return code %d: %s", process.returncode, stderr_text)
            yield {"type": "error", "message": f"Query failed: {stderr_text}"}
            return

        # Log successful response length
        logger.info("GraphRAG query completed, response length: %d chars", len(stdout_text))

        try:
            # Extract source documents from response
            source_ids, entity_ids = _extract_source_ids_from_response(stdout_text)
            source_documents = []
            graph_reader = GraphReaderService(self.output_dir)
            paperless_base_url = self.settings.paperless_url

            if source_ids:
                source_documents = graph_reader.get_documents_from_source_ids(
                    source_ids, paperless_base_url
                )

            # If no source documents from Sources, try getting them from entity IDs
            if not source_documents and entity_ids:
                source_documents = graph_reader.get_documents_from_entity_ids(
                    entity_ids, paperless_base_url
                )

            logger.debug("Extracted %d source documents", len(source_documents))

            yield {
                "type": "complete",
                "response": stdout_text,
                "query": query,
                "method": method,
                "source_documents": source_documents,
            }
        except Exception as e:
            logger.exception("Error processing GraphRAG response: %s", str(e))
            # Still return the response even if source extraction failed
            yield {
                "type": "complete",
                "response": stdout_text,
                "query": query,
                "method": method,
                "source_documents": [],
                "warning": f"Source extraction failed: {str(e)}",
            }
