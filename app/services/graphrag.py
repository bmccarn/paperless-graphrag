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
                    # Use new LiteLLM config format (GraphRAG 2.6+)
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
                "default_embedding_model": {
                    # Use new LiteLLM config format (GraphRAG 2.6+)
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
            },
            "entity_extraction": {
                "entity_types": [
                    # Core entities
                    "person",
                    "organization",
                    "location",
                    # Document management specifics
                    "tax_form",           # IRS forms, state tax forms, schedules
                    "financial_transaction",  # payments, invoices, purchases, refunds
                    "account",            # bank accounts, policy numbers, member IDs
                    "insurance_policy",   # coverages, endorsements, claims
                    "medical_record",     # procedures, conditions, medications, test results
                    "subscription",       # services, memberships, recurring charges
                    "legal_document",     # contracts, agreements, court filings
                    "vehicle",            # cars, boats, property for insurance/DMV
                    "certification",      # training, licenses, credentials
                    "government_form",    # non-tax government documents
                ],
                "max_gleanings": 1,
            },
            "summarize_descriptions": {
                "max_length": 500,
            },
            "community_reports": {
                "max_length": 2000,
            },
            "local_search": {
                "text_unit_prop": 0.5,
                "community_prop": 0.1,
                "top_k_entities": 20,
                "top_k_relationships": 20,
                "max_tokens": 32000,
            },
            "global_search": {
                "max_tokens": 32000,
                "dynamic_community_selection": {
                    "enabled": True,
                    "max_communities": 50,
                },
                "concurrent_coroutines": 32,
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
            """Read stream line by line and process progress."""
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded:
                    lines_list.append(decoded)
                    # Log the output
                    if is_stderr:
                        logger.debug("GraphRAG stderr: %s", decoded)
                    else:
                        logger.debug("GraphRAG stdout: %s", decoded)

                    # Parse and report progress
                    if progress_callback:
                        progress = self._parse_progress(decoded)
                        if progress:
                            progress_callback(*progress)

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
            Dict with query, method, and response

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

        return {
            "query": query,
            "method": method,
            "response": result.get("response", ""),
        }

    def _parse_graphrag_log(self, line: str) -> Optional[dict]:
        """Parse a GraphRAG log line into a user-friendly event.

        Returns dict with 'message' and optional 'detail', or None to skip.
        """
        line_lower = line.lower()

        # Skip noise/debug lines
        skip_patterns = [
            "debug:",
            "warning:",
            "httpx",
            "asyncio",
            "charset_normalizer",
            "using default",
            "api_base",
            "api_version",
        ]
        if any(p in line_lower for p in skip_patterns):
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
            except asyncio.TimeoutError:
                # No event from GraphRAG, use time-based stage progression
                elapsed = asyncio.get_event_loop().time() - start_time

                # Progress through stages based on elapsed time
                while (current_stage < len(stages) - 1 and
                       current_stage < len(stage_times) and
                       elapsed >= stage_times[current_stage]):
                    current_stage += 1
                    msg, detail = stages[current_stage]
                    if msg != last_message:
                        last_message = msg
                        yield {"type": "thinking", "message": msg, "detail": detail}

        # Ensure both tasks complete
        await stderr_task
        await stdout_task
        await process.wait()

        stdout_text = '\n'.join(stdout_lines).strip()
        stderr_text = '\n'.join(stderr_lines).strip()

        if process.returncode != 0:
            logger.error("GraphRAG query failed: %s", stderr_text)
            yield {"type": "error", "message": f"Query failed: {stderr_text}"}
            return

        yield {
            "type": "complete",
            "response": stdout_text,
            "query": query,
            "method": method,
        }
