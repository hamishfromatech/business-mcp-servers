"""Data models for the Kanban MCP server."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status representing kanban columns."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(BaseModel):
    """A kanban task."""
    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: TaskStatus = Field(TaskStatus.TODO, description="Current status/column")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    tags: list[str] = Field(default_factory=list, description="Task tags")
    assignee: Optional[str] = Field(None, description="Person assigned to task")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    due_date: Optional[datetime] = Field(None, description="Task due date")

    def to_dict(self) -> dict:
        """Convert task to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "tags": self.tags,
            "assignee": self.assignee,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create task from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            status=TaskStatus(data.get("status", "todo")),
            priority=TaskPriority(data.get("priority", "medium")),
            tags=data.get("tags", []),
            assignee=data.get("assignee"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
        )


class Board(BaseModel):
    """A kanban board."""
    id: str = Field(..., description="Unique board identifier")
    name: str = Field(..., description="Board name")
    description: Optional[str] = Field(None, description="Board description")
    columns: list[TaskStatus] = Field(
        default_factory=lambda: [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW, TaskStatus.DONE],
        description="Board columns"
    )
    tasks: list[Task] = Field(default_factory=list, description="Board tasks")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert board to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "columns": [c.value for c in self.columns],
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Board":
        """Create board from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            columns=[TaskStatus(c) for c in data.get("columns", ["todo", "in_progress", "review", "done"])],
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )


class CreateTaskInput(BaseModel):
    """Input for creating a new task."""
    board_id: str = Field(..., description="Board ID to add task to")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: TaskStatus = Field(TaskStatus.TODO, description="Initial status")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    tags: list[str] = Field(default_factory=list, description="Task tags")
    assignee: Optional[str] = Field(None, description="Assignee")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")


class UpdateTaskInput(BaseModel):
    """Input for updating a task."""
    board_id: str = Field(..., description="Board ID")
    task_id: str = Field(..., description="Task ID to update")
    title: Optional[str] = Field(None, description="New title")
    description: Optional[str] = Field(None, description="New description")
    status: Optional[TaskStatus] = Field(None, description="New status")
    priority: Optional[TaskPriority] = Field(None, description="New priority")
    tags: Optional[list[str]] = Field(None, description="New tags")
    assignee: Optional[str] = Field(None, description="New assignee")
    due_date: Optional[str] = Field(None, description="New due date in ISO format")


class CreateBoardInput(BaseModel):
    """Input for creating a new board."""
    name: str = Field(..., description="Board name")
    description: Optional[str] = Field(None, description="Board description")
    columns: Optional[list[TaskStatus]] = Field(None, description="Custom columns")