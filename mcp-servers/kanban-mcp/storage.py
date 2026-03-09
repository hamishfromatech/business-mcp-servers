"""JSON-based storage for the Kanban MCP server."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime
import uuid

from models import Board, Task, TaskStatus


class KanbanStorage:
    """JSON file-based storage for kanban boards and tasks."""

    def __init__(self, storage_path: str = "kanban_data.json"):
        """Initialize storage with a JSON file path."""
        self.storage_path = Path(storage_path)
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure storage file exists with valid structure."""
        if not self.storage_path.exists():
            self._write_data({"boards": {}, "default_board_id": None})
        else:
            try:
                data = self._read_data()
                if "boards" not in data:
                    data["boards"] = {}
                if "default_board_id" not in data:
                    data["default_board_id"] = None
                self._write_data(data)
            except json.JSONDecodeError:
                self._write_data({"boards": {}, "default_board_id": None})

    def _read_data(self) -> dict:
        """Read data from JSON file."""
        with open(self.storage_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_data(self, data: dict) -> None:
        """Write data to JSON file."""
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Board operations
    def create_board(self, name: str, description: Optional[str] = None,
                     columns: Optional[list[TaskStatus]] = None) -> Board:
        """Create a new kanban board."""
        data = self._read_data()
        board_id = str(uuid.uuid4())[:8]

        board = Board(
            id=board_id,
            name=name,
            description=description,
            columns=columns or [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW, TaskStatus.DONE],
        )

        data["boards"][board_id] = board.to_dict()

        # Set as default if first board
        if data["default_board_id"] is None:
            data["default_board_id"] = board_id

        self._write_data(data)
        return board

    def get_board(self, board_id: str) -> Optional[Board]:
        """Get a board by ID."""
        data = self._read_data()
        board_data = data["boards"].get(board_id)
        if board_data:
            return Board.from_dict(board_data)
        return None

    def get_default_board(self) -> Optional[Board]:
        """Get the default board."""
        data = self._read_data()
        default_id = data.get("default_board_id")
        if default_id:
            return self.get_board(default_id)
        # If no default, return first board or None
        boards = list(data["boards"].values())
        if boards:
            return Board.from_dict(boards[0])
        return None

    def list_boards(self) -> list[Board]:
        """List all boards."""
        data = self._read_data()
        return [Board.from_dict(b) for b in data["boards"].values()]

    def delete_board(self, board_id: str) -> bool:
        """Delete a board by ID."""
        data = self._read_data()
        if board_id in data["boards"]:
            del data["boards"][board_id]
            if data["default_board_id"] == board_id:
                boards = list(data["boards"].keys())
                data["default_board_id"] = boards[0] if boards else None
            self._write_data(data)
            return True
        return False

    def set_default_board(self, board_id: str) -> bool:
        """Set a board as the default."""
        data = self._read_data()
        if board_id in data["boards"]:
            data["default_board_id"] = board_id
            self._write_data(data)
            return True
        return False

    # Task operations
    def add_task(self, board_id: str, task: Task) -> Optional[Task]:
        """Add a task to a board."""
        data = self._read_data()
        if board_id not in data["boards"]:
            return None

        board_data = data["boards"][board_id]
        board_data["tasks"].append(task.to_dict())
        board_data["updated_at"] = datetime.now().isoformat()
        self._write_data(data)
        return task

    def get_task(self, board_id: str, task_id: str) -> Optional[Task]:
        """Get a specific task from a board."""
        board = self.get_board(board_id)
        if board:
            for task in board.tasks:
                if task.id == task_id:
                    return task
        return None

    def update_task(self, board_id: str, task_id: str, **updates) -> Optional[Task]:
        """Update a task on a board."""
        data = self._read_data()
        if board_id not in data["boards"]:
            return None

        board_data = data["boards"][board_id]
        for i, task_data in enumerate(board_data["tasks"]):
            if task_data["id"] == task_id:
                # Apply updates
                for key, value in updates.items():
                    if value is not None:
                        if key == "status" and isinstance(value, TaskStatus):
                            task_data[key] = value.value
                        elif key == "priority" and isinstance(value, TaskPriority):
                            task_data[key] = value.value
                        elif key == "due_date" and isinstance(value, str):
                            task_data[key] = value
                        else:
                            task_data[key] = value

                task_data["updated_at"] = datetime.now().isoformat()
                board_data["updated_at"] = datetime.now().isoformat()
                self._write_data(data)
                return Task.from_dict(task_data)

        return None

    def delete_task(self, board_id: str, task_id: str) -> bool:
        """Delete a task from a board."""
        data = self._read_data()
        if board_id not in data["boards"]:
            return False

        board_data = data["boards"][board_id]
        original_count = len(board_data["tasks"])
        board_data["tasks"] = [t for t in board_data["tasks"] if t["id"] != task_id]

        if len(board_data["tasks"]) < original_count:
            board_data["updated_at"] = datetime.now().isoformat()
            self._write_data(data)
            return True
        return False

    def move_task(self, board_id: str, task_id: str, new_status: TaskStatus) -> Optional[Task]:
        """Move a task to a different column/status."""
        return self.update_task(board_id, task_id, status=new_status)

    def search_tasks(self, query: str, board_id: Optional[str] = None) -> list[tuple[str, Task]]:
        """Search tasks by title, description, or tags."""
        results = []
        data = self._read_data()
        query_lower = query.lower()

        boards_to_search = [board_id] if board_id else list(data["boards"].keys())

        for bid in boards_to_search:
            if bid not in data["boards"]:
                continue
            board_data = data["boards"][bid]
            for task_data in board_data["tasks"]:
                # Search in title, description, and tags
                if (query_lower in task_data["title"].lower() or
                    (task_data.get("description") and query_lower in task_data["description"].lower()) or
                    any(query_lower in tag.lower() for tag in task_data.get("tags", []))):
                    results.append((bid, Task.from_dict(task_data)))

        return results

    def get_tasks_by_status(self, board_id: str, status: TaskStatus) -> list[Task]:
        """Get all tasks with a specific status."""
        board = self.get_board(board_id)
        if board:
            return [t for t in board.tasks if t.status == status]
        return []

    def get_tasks_by_assignee(self, board_id: str, assignee: str) -> list[Task]:
        """Get all tasks assigned to a person."""
        board = self.get_board(board_id)
        if board:
            return [t for t in board.tasks if t.assignee == assignee]
        return []

    def get_statistics(self, board_id: str) -> dict:
        """Get statistics for a board."""
        board = self.get_board(board_id)
        if not board:
            return {}

        stats = {
            "total_tasks": len(board.tasks),
            "by_status": {},
            "by_priority": {},
            "by_assignee": {},
        }

        for task in board.tasks:
            # By status
            status = task.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # By priority
            priority = task.priority.value
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

            # By assignee
            assignee = task.assignee or "unassigned"
            stats["by_assignee"][assignee] = stats["by_assignee"].get(assignee, 0) + 1

        return stats


# Import TaskPriority for update_task
from models import TaskPriority