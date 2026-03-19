"""
Kanban MCP Server - A task management system with web UI.

This server provides:
- Tools for managing kanban boards and tasks
- Resources for viewing board state
- A web UI for interactive kanban management

Usage:
    # Run as stdio MCP server (for Claude Desktop, etc.)
    python kanban_server.py

    # Run as HTTP server with web UI
    python kanban_server.py --transport http --port 8000

    # Run as SSE server
    python kanban_server.py --transport sse --port 8000

When running with --webui flag, a web interface will be available at the specified port.
"""

import argparse
import json
import uuid
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig

from models import Board, Task, TaskStatus, TaskPriority, CreateTaskInput, UpdateTaskInput, CreateBoardInput
from storage import KanbanStorage

# Initialize FastMCP server
mcp = FastMCP(
    name="Kanban MCP",
    instructions="""
    This is a Kanban task management MCP server.

    Available operations:
    - Create, list, and delete boards
    - Create, update, move, and delete tasks
    - Search tasks and filter by status/assignee
    - View board statistics

    The default board is automatically created on first use.
    Use list_boards to see all available boards.
    """,
)

# Initialize storage
storage = KanbanStorage()


# =============================================================================
# TOOLS - Board Management
# =============================================================================

@mcp.tool
def create_board(
    name: str,
    description: Optional[str] = None,
    columns: Optional[list[str]] = None
) -> str:
    """
    Create a new kanban board.

    Args:
        name: Board name
        description: Optional board description
        columns: Optional custom columns (default: todo, in_progress, review, done)

    Returns:
        JSON string with created board details
    """
    parsed_columns = None
    if columns:
        try:
            parsed_columns = [TaskStatus(c) for c in columns]
        except ValueError as e:
            return json.dumps({"error": f"Invalid column: {e}"})

    board = storage.create_board(name, description, parsed_columns)
    return json.dumps({
        "success": True,
        "board": board.to_dict(),
        "message": f"Created board '{name}' with ID {board.id}"
    })


@mcp.tool
def list_boards() -> str:
    """
    List all available kanban boards.

    Returns:
        JSON string with list of boards
    """
    boards = storage.list_boards()
    data = storage._read_data() if hasattr(storage, '_read_data') else {}
    default_id = data.get("default_board_id")

    return json.dumps({
        "boards": [b.to_dict() for b in boards],
        "default_board_id": default_id,
        "count": len(boards)
    })


@mcp.tool
def get_board(board_id: Optional[str] = None) -> str:
    """
    Get details of a specific board or the default board.

    Args:
        board_id: Board ID (uses default board if not provided)

    Returns:
        JSON string with board details
    """
    if board_id:
        board = storage.get_board(board_id)
    else:
        board = storage.get_default_board()

    if not board:
        return json.dumps({"error": "Board not found"})

    return json.dumps({
        "board": board.to_dict(),
        "statistics": storage.get_statistics(board.id)
    })


@mcp.tool
def delete_board(board_id: str) -> str:
    """
    Delete a kanban board.

    Args:
        board_id: ID of board to delete

    Returns:
        JSON string with result
    """
    if storage.delete_board(board_id):
        return json.dumps({"success": True, "message": f"Deleted board {board_id}"})
    return json.dumps({"error": "Board not found"})


@mcp.tool
def set_default_board(board_id: str) -> str:
    """
    Set a board as the default board.

    Args:
        board_id: ID of board to set as default

    Returns:
        JSON string with result
    """
    if storage.set_default_board(board_id):
        return json.dumps({"success": True, "message": f"Set board {board_id} as default"})
    return json.dumps({"error": "Board not found"})


# =============================================================================
# TOOLS - Task Management
# =============================================================================

@mcp.tool
def create_task(
    title: str,
    board_id: Optional[str] = None,
    description: Optional[str] = None,
    status: str = "todo",
    priority: str = "medium",
    tags: Optional[list[str]] = None,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None
) -> str:
    """
    Create a new task on a kanban board.

    Args:
        title: Task title
        board_id: Board ID (uses default board if not provided)
        description: Task description
        status: Task status (todo, in_progress, review, done)
        priority: Task priority (low, medium, high, urgent)
        tags: List of tags
        assignee: Person assigned to task
        due_date: Due date in ISO format (e.g., "2024-12-31")

    Returns:
        JSON string with created task details
    """
    # Get or create board
    if board_id:
        board = storage.get_board(board_id)
    else:
        board = storage.get_default_board()
        if not board:
            board = storage.create_board("Default Board", "Default kanban board")

    # Validate status and priority
    try:
        task_status = TaskStatus(status)
    except ValueError:
        return json.dumps({"error": f"Invalid status: {status}. Must be one of: {[s.value for s in TaskStatus]}"})

    try:
        task_priority = TaskPriority(priority)
    except ValueError:
        return json.dumps({"error": f"Invalid priority: {priority}. Must be one of: {[p.value for p in TaskPriority]}"})

    # Parse due date
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except ValueError:
            return json.dumps({"error": f"Invalid due_date format: {due_date}. Use ISO format (e.g., 2024-12-31)"})

    # Create task
    task = Task(
        id=str(uuid.uuid4())[:8],
        title=title,
        description=description,
        status=task_status,
        priority=task_priority,
        tags=tags or [],
        assignee=assignee,
        due_date=parsed_due_date,
    )

    added_task = storage.add_task(board.id, task)
    if added_task:
        return json.dumps({
            "success": True,
            "task": added_task.to_dict(),
            "board_id": board.id,
            "message": f"Created task '{title}' with ID {added_task.id}"
        })

    return json.dumps({"error": "Failed to create task"})


@mcp.tool
def update_task(
    task_id: str,
    board_id: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[list[str]] = None,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None
) -> str:
    """
    Update an existing task.

    Args:
        task_id: ID of task to update
        board_id: Board ID (uses default board if not provided)
        title: New title
        description: New description
        status: New status (todo, in_progress, review, done)
        priority: New priority (low, medium, high, urgent)
        tags: New tags list
        assignee: New assignee
        due_date: New due date in ISO format

    Returns:
        JSON string with updated task details
    """
    # Get board
    if board_id:
        board = storage.get_board(board_id)
    else:
        board = storage.get_default_board()

    if not board:
        return json.dumps({"error": "Board not found"})

    # Build updates dict
    updates = {}
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description
    if status is not None:
        try:
            updates["status"] = TaskStatus(status)
        except ValueError:
            return json.dumps({"error": f"Invalid status: {status}"})
    if priority is not None:
        try:
            updates["priority"] = TaskPriority(priority)
        except ValueError:
            return json.dumps({"error": f"Invalid priority: {priority}"})
    if tags is not None:
        updates["tags"] = tags
    if assignee is not None:
        updates["assignee"] = assignee
    if due_date is not None:
        updates["due_date"] = due_date

    if not updates:
        return json.dumps({"error": "No updates provided"})

    updated_task = storage.update_task(board.id, task_id, **updates)
    if updated_task:
        return json.dumps({
            "success": True,
            "task": updated_task.to_dict(),
            "message": f"Updated task {task_id}"
        })

    return json.dumps({"error": "Task not found"})


@mcp.tool
def move_task(
    task_id: str,
    new_status: str,
    board_id: Optional[str] = None
) -> str:
    """
    Move a task to a different column/status.

    Args:
        task_id: ID of task to move
        new_status: Target status (todo, in_progress, review, done)
        board_id: Board ID (uses default board if not provided)

    Returns:
        JSON string with result
    """
    # Get board
    if board_id:
        board = storage.get_board(board_id)
    else:
        board = storage.get_default_board()

    if not board:
        return json.dumps({"error": "Board not found"})

    try:
        status = TaskStatus(new_status)
    except ValueError:
        return json.dumps({"error": f"Invalid status: {new_status}"})

    updated_task = storage.move_task(board.id, task_id, status)
    if updated_task:
        return json.dumps({
            "success": True,
            "task": updated_task.to_dict(),
            "message": f"Moved task {task_id} to {new_status}"
        })

    return json.dumps({"error": "Task not found"})


@mcp.tool
def delete_task(
    task_id: str,
    board_id: Optional[str] = None
) -> str:
    """
    Delete a task from a board.

    Args:
        task_id: ID of task to delete
        board_id: Board ID (uses default board if not provided)

    Returns:
        JSON string with result
    """
    if board_id:
        board = storage.get_board(board_id)
    else:
        board = storage.get_default_board()

    if not board:
        return json.dumps({"error": "Board not found"})

    if storage.delete_task(board.id, task_id):
        return json.dumps({"success": True, "message": f"Deleted task {task_id}"})

    return json.dumps({"error": "Task not found"})


@mcp.tool
def search_tasks(
    query: str,
    board_id: Optional[str] = None
) -> str:
    """
    Search tasks by title, description, or tags.

    Args:
        query: Search query
        board_id: Board ID to search (searches all boards if not provided)

    Returns:
        JSON string with matching tasks
    """
    results = storage.search_tasks(query, board_id)
    return json.dumps({
        "query": query,
        "count": len(results),
        "results": [{"board_id": bid, "task": task.to_dict()} for bid, task in results]
    })


@mcp.tool
def get_tasks_by_status(
    status: str,
    board_id: Optional[str] = None
) -> str:
    """
    Get all tasks with a specific status.

    Args:
        status: Task status to filter by (todo, in_progress, review, done)
        board_id: Board ID (uses default board if not provided)

    Returns:
        JSON string with tasks
    """
    if board_id:
        board = storage.get_board(board_id)
    else:
        board = storage.get_default_board()

    if not board:
        return json.dumps({"error": "Board not found"})

    try:
        task_status = TaskStatus(status)
    except ValueError:
        return json.dumps({"error": f"Invalid status: {status}"})

    tasks = storage.get_tasks_by_status(board.id, task_status)
    return json.dumps({
        "status": status,
        "count": len(tasks),
        "tasks": [t.to_dict() for t in tasks]
    })


@mcp.tool
def get_tasks_by_assignee(
    assignee: str,
    board_id: Optional[str] = None
) -> str:
    """
    Get all tasks assigned to a person.

    Args:
        assignee: Assignee name to filter by
        board_id: Board ID (uses default board if not provided)

    Returns:
        JSON string with tasks
    """
    if board_id:
        board = storage.get_board(board_id)
    else:
        board = storage.get_default_board()

    if not board:
        return json.dumps({"error": "Board not found"})

    tasks = storage.get_tasks_by_assignee(board.id, assignee)
    return json.dumps({
        "assignee": assignee,
        "count": len(tasks),
        "tasks": [t.to_dict() for t in tasks]
    })


@mcp.tool
def get_board_statistics(board_id: Optional[str] = None) -> str:
    """
    Get statistics for a board.

    Args:
        board_id: Board ID (uses default board if not provided)

    Returns:
        JSON string with statistics
    """
    if board_id:
        board = storage.get_board(board_id)
    else:
        board = storage.get_default_board()

    if not board:
        return json.dumps({"error": "Board not found"})

    stats = storage.get_statistics(board.id)
    return json.dumps({
        "board_id": board.id,
        "board_name": board.name,
        "statistics": stats
    })


# =============================================================================
# RESOURCES - Board State
# =============================================================================

@mcp.resource("kanban://boards")
def get_boards_resource() -> str:
    """Get all boards as a resource."""
    boards = storage.list_boards()
    return json.dumps([b.to_dict() for b in boards], indent=2)


@mcp.resource("kanban://board/{board_id}")
def get_board_resource(board_id: str) -> str:
    """Get a specific board as a resource."""
    board = storage.get_board(board_id)
    if board:
        return json.dumps(board.to_dict(), indent=2)
    return json.dumps({"error": "Board not found"})


@mcp.resource("kanban://default")
def get_default_board_resource() -> str:
    """Get the default board as a resource."""
    board = storage.get_default_board()
    if board:
        return json.dumps(board.to_dict(), indent=2)
    return json.dumps({"error": "No default board found"})


# =============================================================================
# CLI Helper Tools
# =============================================================================

@mcp.tool
def cli_overview() -> str:
    """Get a CLI-friendly overview of all boards and tasks."""
    boards = storage.list_boards()
    if not boards:
        return "No boards found. Use create_board to create one."

    output = ["=" * 60]
    output.append("KANBAN OVERVIEW")
    output.append("=" * 60)

    for board in boards:
        stats = storage.get_statistics(board.id)
        output.append(f"\n📋 {board.name} ({board.id})")
        if board.description:
            output.append(f"   {board.description}")
        output.append(f"   Tasks: {stats['total_tasks']} total")

        for status in ["todo", "in_progress", "review", "done"]:
            count = stats["by_status"].get(status, 0)
            status_icons = {"todo": "📋", "in_progress": "🔄", "review": "👀", "done": "✅"}
            if count > 0:
                output.append(f"     {status_icons.get(status, '•')} {status.replace('_', ' ').title()}: {count}")

    return "\n".join(output)


@mcp.tool
def cli_board_view(board_id: Optional[str] = None) -> str:
    """Get a CLI-friendly view of a board with all tasks organized by column."""
    if board_id:
        board = storage.get_board(board_id)
    else:
        board = storage.get_default_board()

    if not board:
        return "Board not found."

    output = ["=" * 60]
    output.append(f"📋 {board.name}")
    output.append("=" * 60)

    status_config = [
        ("todo", "📋 TO DO", "#6366f1"),
        ("in_progress", "🔄 IN PROGRESS", "#f59e0b"),
        ("review", "👀 REVIEW", "#8b5cf6"),
        ("done", "✅ DONE", "#10b981"),
    ]

    for status_value, status_label, _ in status_config:
        tasks = [t for t in board.tasks if t.status.value == status_value]
        output.append(f"\n{status_label} ({len(tasks)})")
        output.append("-" * 40)

        if not tasks:
            output.append("  (empty)")
        else:
            for task in tasks:
                priority_icons = {"low": "🟢", "medium": "🟡", "high": "🔴", "urgent": "⚡"}
                icon = priority_icons.get(task.priority.value, "•")
                output.append(f"  {icon} [{task.id}] {task.title}")
                if task.assignee:
                    output.append(f"      👤 {task.assignee}")
                if task.tags:
                    output.append(f"      🏷️ {', '.join(task.tags)}")

    return "\n".join(output)


# =============================================================================
# Web UI HTTP Server
# =============================================================================

# Global storage reference for web server
_web_storage = None
_UI_HTML_PATH = None


def _get_ui_html_content() -> str:
    """Load the UI HTML from the index.html file."""
    global _UI_HTML_PATH
    if _UI_HTML_PATH and Path(_UI_HTML_PATH).exists():
        with open(_UI_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    # Fallback: look for index.html in the same directory as this script
    script_dir = Path(__file__).parent
    index_path = script_dir / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<html><body><h1>UI not found</h1><p>Please ensure index.html exists.</p></body></html>"


class KanbanWebHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the Kanban web UI and REST API."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_ui()
        elif path == "/api/boards":
            self._get_boards()
        elif path.startswith("/api/board/"):
            board_id = path.split("/")[-1]
            self._get_board(board_id)
        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        if path == "/api/boards":
            self._create_board(data)
        elif path == "/api/tasks":
            self._create_task(data)
        elif path.startswith("/api/tasks/"):
            parts = path.split("/")
            task_id = parts[-1]
            self._update_task(task_id, data)
        elif path.startswith("/api/board/"):
            parts = path.split("/")
            board_id = parts[-1]
            self._set_default_board(board_id)
        else:
            self.send_error(404)

    def do_DELETE(self):
        """Handle DELETE requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/tasks/"):
            parts = path.split("/")
            task_id = parts[-1]
            query = urllib.parse.parse_qs(parsed.query)
            board_id = query.get("board_id", [None])[0]
            self._delete_task(task_id, board_id)
        elif path.startswith("/api/boards/"):
            parts = path.split("/")
            board_id = parts[-1]
            self._delete_board(board_id)
        else:
            self.send_error(404)

    def _serve_ui(self):
        """Serve the Kanban UI HTML from index.html file."""
        html = _get_ui_html_content()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode())

    def _get_boards(self):
        """Get all boards."""
        global _web_storage
        boards = _web_storage.list_boards()
        data = _web_storage._read_data() if hasattr(_web_storage, '_read_data') else {}
        default_id = data.get("default_board_id")
        self._send_json({
            "boards": [b.to_dict() for b in boards],
            "default_board_id": default_id,
            "count": len(boards)
        })

    def _get_board(self, board_id: str):
        """Get a specific board."""
        global _web_storage
        board = _web_storage.get_board(board_id) if board_id else _web_storage.get_default_board()
        if board:
            self._send_json({
                "board": board.to_dict(),
                "statistics": _web_storage.get_statistics(board.id)
            })
        else:
            self._send_json({"error": "Board not found"}, 404)

    def _create_board(self, data: dict):
        """Create a new board."""
        global _web_storage
        name = data.get("name", "New Board")
        description = data.get("description")
        board = _web_storage.create_board(name, description)
        self._send_json({
            "success": True,
            "board": board.to_dict(),
            "message": f"Created board '{name}'"
        })

    def _create_task(self, data: dict):
        """Create a new task."""
        global _web_storage
        board_id = data.get("board_id")
        if board_id:
            board = _web_storage.get_board(board_id)
        else:
            board = _web_storage.get_default_board()
            if not board:
                board = _web_storage.create_board("Default Board", "Default kanban board")

        try:
            task_status = TaskStatus(data.get("status", "todo"))
        except ValueError:
            task_status = TaskStatus.TODO

        try:
            task_priority = TaskPriority(data.get("priority", "medium"))
        except ValueError:
            task_priority = TaskPriority.MEDIUM

        task = Task(
            id=str(uuid.uuid4())[:8],
            title=data.get("title", "Untitled"),
            description=data.get("description"),
            status=task_status,
            priority=task_priority,
            tags=data.get("tags", []),
            assignee=data.get("assignee"),
        )

        added_task = _web_storage.add_task(board.id, task)
        if added_task:
            self._send_json({
                "success": True,
                "task": added_task.to_dict(),
                "board_id": board.id,
                "message": f"Created task '{task.title}'"
            })
        else:
            self._send_json({"error": "Failed to create task"}, 500)

    def _update_task(self, task_id: str, data: dict):
        """Update a task."""
        global _web_storage
        board_id = data.get("board_id")
        if board_id:
            board = _web_storage.get_board(board_id)
        else:
            board = _web_storage.get_default_board()

        if not board:
            self._send_json({"error": "Board not found"}, 404)
            return

        updates = {}
        if "title" in data:
            updates["title"] = data["title"]
        if "description" in data:
            updates["description"] = data["description"]
        if "status" in data:
            try:
                updates["status"] = TaskStatus(data["status"])
            except ValueError:
                pass
        if "priority" in data:
            try:
                updates["priority"] = TaskPriority(data["priority"])
            except ValueError:
                pass
        if "tags" in data:
            updates["tags"] = data["tags"]
        if "assignee" in data:
            updates["assignee"] = data["assignee"]

        updated_task = _web_storage.update_task(board.id, task_id, **updates)
        if updated_task:
            self._send_json({
                "success": True,
                "task": updated_task.to_dict(),
                "message": f"Updated task {task_id}"
            })
        else:
            self._send_json({"error": "Task not found"}, 404)

    def _delete_task(self, task_id: str, board_id: str = None):
        """Delete a task."""
        global _web_storage
        if board_id:
            board = _web_storage.get_board(board_id)
        else:
            board = _web_storage.get_default_board()

        if not board:
            self._send_json({"error": "Board not found"}, 404)
            return

        if _web_storage.delete_task(board.id, task_id):
            self._send_json({"success": True, "message": f"Deleted task {task_id}"})
        else:
            self._send_json({"error": "Task not found"}, 404)

    def _delete_board(self, board_id: str):
        """Delete a board."""
        global _web_storage
        if _web_storage.delete_board(board_id):
            self._send_json({"success": True, "message": f"Deleted board {board_id}"})
        else:
            self._send_json({"error": "Board not found"}, 404)

    def _set_default_board(self, board_id: str):
        """Set a board as default."""
        global _web_storage
        if _web_storage.set_default_board(board_id):
            self._send_json({"success": True, "message": f"Set board {board_id} as default"})
        else:
            self._send_json({"error": "Board not found"}, 404)


def run_web_server(host: str, port: int, storage_instance: KanbanStorage):
    """Run the web UI HTTP server."""
    global _web_storage
    _web_storage = storage_instance
    server = HTTPServer((host, port), KanbanWebHandler)
    server.serve_forever()


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for the Kanban MCP server."""
    parser = argparse.ArgumentParser(description="Kanban MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol to use"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for MCP HTTP/SSE transport"
    )
    parser.add_argument(
        "--webui-port",
        type=int,
        default=3000,
        help="Port for web UI (default: 3000)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP transport"
    )
    parser.add_argument(
        "--storage",
        default="kanban_data.json",
        help="Path to JSON storage file"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )

    args = parser.parse_args()

    # Update storage path if provided
    global storage
    if args.storage != "kanban_data.json":
        storage = KanbanStorage(args.storage)

    # For stdio mode, just run the MCP server
    if args.transport == "stdio":
        mcp.run()
    else:
        # For HTTP/SSE modes, start web UI server alongside MCP server
        webui_url = f"http://{args.host}:{args.webui_port}"

        # Start web UI server in a background thread
        web_thread = threading.Thread(
            target=run_web_server,
            args=(args.host, args.webui_port, storage),
            daemon=True
        )
        web_thread.start()

        print(f"\n{'='*60}")
        print(f"  Kanban MCP Server Started")
        print(f"{'='*60}")
        print(f"  MCP Transport: {args.transport}")
        print(f"  MCP Port: {args.port}")
        print(f"  Storage: {args.storage}")
        print(f"{'='*60}")
        print(f"  🌐 Web UI: {webui_url}")
        print(f"{'='*60}\n")

        # Open browser if not disabled
        if not args.no_browser:
            try:
                webbrowser.open(webui_url)
            except Exception:
                pass  # Browser might not be available

        # Run the MCP server
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()