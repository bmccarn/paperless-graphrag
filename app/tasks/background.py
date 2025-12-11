"""Background task management for long-running operations."""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
    """Status of a background task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """Background task representation."""
    task_id: str
    task_type: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    # Progress tracking
    progress_percent: Optional[int] = None  # 0-100
    progress_message: Optional[str] = None  # Current step description
    progress_detail: Optional[str] = None  # Additional detail (e.g., file being processed)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None


class TaskManager:
    """Singleton manager for background tasks."""

    _instance: Optional["TaskManager"] = None
    _tasks: Dict[str, Task] = {}

    def __new__(cls) -> "TaskManager":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tasks = {}
        return cls._instance

    def create_task(self, task_type: str) -> str:
        """Create a new pending task.

        Args:
            task_type: Type/name of the task

        Returns:
            Unique task ID
        """
        task_id = str(uuid.uuid4())[:8]
        self._tasks[task_id] = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        return task_id

    def start_task(self, task_id: str) -> None:
        """Mark a task as running.

        Args:
            task_id: Task ID to start
        """
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.RUNNING
            self._tasks[task_id].started_at = datetime.utcnow()
            self._tasks[task_id].progress_percent = 0
            self._tasks[task_id].progress_message = "Starting..."

    def update_progress(
        self,
        task_id: str,
        percent: Optional[int] = None,
        message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Update task progress.

        Args:
            task_id: Task ID to update
            percent: Progress percentage (0-100)
            message: Current step description
            detail: Additional detail
        """
        if task_id in self._tasks:
            if percent is not None:
                self._tasks[task_id].progress_percent = min(100, max(0, percent))
            if message is not None:
                self._tasks[task_id].progress_message = message
            if detail is not None:
                self._tasks[task_id].progress_detail = detail

    def complete_task(self, task_id: str, result: Any) -> None:
        """Mark a task as completed with result.

        Args:
            task_id: Task ID to complete
            result: Task result data
        """
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.COMPLETED
            self._tasks[task_id].result = result
            self._tasks[task_id].completed_at = datetime.utcnow()
            self._tasks[task_id].progress_percent = 100
            self._tasks[task_id].progress_message = "Completed"

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark a task as failed with error.

        Args:
            task_id: Task ID that failed
            error: Error message
        """
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.FAILED
            self._tasks[task_id].error = error
            self._tasks[task_id].completed_at = datetime.utcnow()

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: Task ID to retrieve

        Returns:
            Task if found, None otherwise
        """
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
    ) -> list[Task]:
        """List tasks with optional filters.

        Args:
            status: Filter by status
            task_type: Filter by task type

        Returns:
            List of matching tasks
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]

        # Sort by created_at descending
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Remove tasks older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of tasks removed
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        old_count = len(self._tasks)

        self._tasks = {
            k: v for k, v in self._tasks.items() if v.created_at > cutoff
        }

        return old_count - len(self._tasks)

    def has_running_task(self, task_type: str) -> bool:
        """Check if there's a running task of given type.

        Args:
            task_type: Task type to check

        Returns:
            True if a task of this type is currently running
        """
        return any(
            t.task_type == task_type and t.status == TaskStatus.RUNNING
            for t in self._tasks.values()
        )


# Global task manager instance
task_manager = TaskManager()
