"""FastAPI routes for log streaming."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])

# Log file paths
LOG_DIR = Path("/app/data/graphrag/logs")
INDEXING_LOG = LOG_DIR / "indexing-engine.log"


class LogFileInfo(BaseModel):
    """Information about a log file."""
    name: str
    path: str
    size_bytes: int
    exists: bool


class LogFilesResponse(BaseModel):
    """Response listing available log files."""
    files: list[LogFileInfo]


@router.get("/files", response_model=LogFilesResponse)
async def list_log_files():
    """List available log files."""
    log_files = []

    # Check for indexing log
    if INDEXING_LOG.exists():
        log_files.append(LogFileInfo(
            name="indexing-engine.log",
            path=str(INDEXING_LOG),
            size_bytes=INDEXING_LOG.stat().st_size,
            exists=True,
        ))
    else:
        log_files.append(LogFileInfo(
            name="indexing-engine.log",
            path=str(INDEXING_LOG),
            size_bytes=0,
            exists=False,
        ))

    # Check for other log files in the directory
    if LOG_DIR.exists():
        for log_file in LOG_DIR.glob("*.log"):
            if log_file != INDEXING_LOG:
                log_files.append(LogFileInfo(
                    name=log_file.name,
                    path=str(log_file),
                    size_bytes=log_file.stat().st_size,
                    exists=True,
                ))

    return LogFilesResponse(files=log_files)


@router.get("/file/{filename}")
async def get_log_file(
    filename: str,
    tail: int = Query(default=500, ge=1, le=10000, description="Number of lines from end"),
):
    """Get the last N lines of a specific log file.

    Args:
        filename: Name of the log file (must end with .log)
        tail: Number of lines to return from end of file
    """
    # Validate filename to prevent path traversal
    if not filename.endswith(".log") or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid log filename")

    log_path = LOG_DIR / filename
    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"Log file '{filename}' not found")

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            tail_lines = lines[-tail:] if len(lines) > tail else lines
            return {
                "filename": filename,
                "content": "".join(tail_lines),
                "total_lines": len(lines),
                "returned_lines": len(tail_lines),
            }
    except Exception as e:
        logger.exception(f"Failed to read log file: {filename}")
        raise HTTPException(status_code=500, detail=f"Failed to read log: {str(e)}")


@router.get("/indexing")
async def get_indexing_log(
    tail: int = Query(default=500, ge=1, le=10000, description="Number of lines from end"),
):
    """Get the last N lines of the indexing engine log."""
    if not INDEXING_LOG.exists():
        raise HTTPException(status_code=404, detail="Indexing log file not found")

    try:
        # Read last N lines efficiently
        with open(INDEXING_LOG, "r", encoding="utf-8", errors="replace") as f:
            # For smaller files, just read all and take last N
            lines = f.readlines()
            tail_lines = lines[-tail:] if len(lines) > tail else lines
            return {
                "content": "".join(tail_lines),
                "total_lines": len(lines),
                "returned_lines": len(tail_lines),
            }
    except Exception as e:
        logger.exception("Failed to read indexing log")
        raise HTTPException(status_code=500, detail=f"Failed to read log: {str(e)}")


@router.get("/indexing/stream")
async def stream_indexing_log(
    tail: int = Query(default=100, ge=0, le=1000, description="Initial lines to show"),
):
    """Stream the indexing engine log file in real-time using Server-Sent Events.

    This endpoint will:
    1. Send the last N lines initially
    2. Then stream new lines as they are written to the file
    """

    async def log_generator():
        """Generate SSE events from log file."""
        last_position = 0
        last_size = 0

        # Send initial content (tail lines)
        if INDEXING_LOG.exists():
            try:
                with open(INDEXING_LOG, "r", encoding="utf-8", errors="replace") as f:
                    if tail > 0:
                        lines = f.readlines()
                        tail_lines = lines[-tail:] if len(lines) > tail else lines
                        for line in tail_lines:
                            yield f"data: {line.rstrip()}\n\n"

                    # Record position for streaming new content
                    f.seek(0, 2)  # Seek to end
                    last_position = f.tell()
                    last_size = INDEXING_LOG.stat().st_size
            except Exception as e:
                yield f"data: [Error reading log: {str(e)}]\n\n"
        else:
            yield f"data: [Log file not found, waiting for indexing to start...]\n\n"

        # Stream new content
        while True:
            try:
                await asyncio.sleep(1)  # Poll every second

                if not INDEXING_LOG.exists():
                    continue

                current_size = INDEXING_LOG.stat().st_size

                # Check if file was truncated/rotated
                if current_size < last_size:
                    last_position = 0
                    yield f"data: [Log file rotated, starting from beginning]\n\n"

                # Read new content if file grew
                if current_size > last_position:
                    with open(INDEXING_LOG, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(last_position)
                        new_content = f.read()
                        last_position = f.tell()

                        # Send each new line
                        for line in new_content.splitlines():
                            if line.strip():
                                yield f"data: {line}\n\n"

                last_size = current_size

            except asyncio.CancelledError:
                break
            except Exception as e:
                yield f"data: [Error: {str(e)}]\n\n"
                await asyncio.sleep(5)  # Wait longer on error

    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/indexing")
async def clear_indexing_log():
    """Clear the indexing engine log file."""
    if not INDEXING_LOG.exists():
        return {"message": "Log file does not exist", "cleared": False}

    try:
        # Truncate the file
        with open(INDEXING_LOG, "w") as f:
            f.write("")
        return {"message": "Log file cleared", "cleared": True}
    except Exception as e:
        logger.exception("Failed to clear indexing log")
        raise HTTPException(status_code=500, detail=f"Failed to clear log: {str(e)}")
