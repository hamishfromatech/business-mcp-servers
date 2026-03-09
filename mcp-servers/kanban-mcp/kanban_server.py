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
"""

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    data = self._read_data() if hasattr(storage, '_read_data') else {}
    default_id = storage._read_data().get("default_board_id") if hasattr(storage, '_read_data') else None

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
# UI Resources - Web Interface
# =============================================================================

KANBAN_UI_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kanban Board</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            backdrop-filter: blur(10px);
        }

        h1 {
            font-size: 28px;
            font-weight: 600;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .board-selector {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        select, button, input {
            padding: 10px 16px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(255, 255, 255, 0.08);
            color: #e0e0e0;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }

        select:hover, button:hover {
            background: rgba(255, 255, 255, 0.12);
        }

        button.primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            font-weight: 500;
        }

        button.primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
        }

        .board {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }

        .column {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            padding: 20px;
            min-height: 500px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .column-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid;
        }

        .column-header h2 {
            font-size: 16px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .column-header .count {
            background: rgba(255, 255, 255, 0.1);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
        }

        .column.todo .column-header { border-color: #6366f1; }
        .column.in_progress .column-header { border-color: #f59e0b; }
        .column.review .column-header { border-color: #8b5cf6; }
        .column.done .column-header { border-color: #10b981; }

        .tasks {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .task {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .task:hover {
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .task-title {
            font-weight: 500;
            margin-bottom: 8px;
        }

        .task-description {
            font-size: 13px;
            color: #a0a0a0;
            margin-bottom: 12px;
        }

        .task-meta {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .tag {
            background: rgba(99, 102, 241, 0.2);
            color: #818cf8;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
        }

        .priority {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }

        .priority.low { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .priority.medium { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
        .priority.high { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        .priority.urgent { background: rgba(239, 68, 68, 0.4); color: #ef4444; }

        .assignee {
            font-size: 12px;
            color: #a0a0a0;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .assignee::before {
            content: "👤";
            font-size: 10px;
        }

        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s;
        }

        .modal-overlay.active {
            opacity: 1;
            visibility: visible;
        }

        .modal {
            background: #1e1e2e;
            border-radius: 16px;
            padding: 24px;
            width: 100%;
            max-width: 500px;
            transform: scale(0.9);
            transition: transform 0.3s;
        }

        .modal-overlay.active .modal {
            transform: scale(1);
        }

        .modal h2 {
            margin-bottom: 20px;
            font-size: 20px;
        }

        .form-group {
            margin-bottom: 16px;
        }

        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-size: 14px;
            color: #a0a0a0;
        }

        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #e0e0e0;
        }

        .form-group textarea {
            min-height: 100px;
            resize: vertical;
        }

        .modal-actions {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
            margin-top: 24px;
        }

        .stats-bar {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            padding: 16px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
        }

        .stat {
            text-align: center;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 600;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            font-size: 12px;
            color: #a0a0a0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #666;
        }

        .empty-state p {
            margin-bottom: 16px;
        }

        @media (max-width: 1200px) {
            .board {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 768px) {
            .board {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📋 Kanban Board</h1>
            <div class="board-selector">
                <select id="boardSelect">
                    <option value="">Loading boards...</option>
                </select>
                <button class="primary" onclick="openCreateTaskModal()">+ New Task</button>
                <button onclick="openCreateBoardModal()">+ New Board</button>
            </div>
        </header>

        <div class="stats-bar" id="statsBar">
            <div class="stat">
                <div class="stat-value" id="totalTasks">0</div>
                <div class="stat-label">Total Tasks</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="todoCount">0</div>
                <div class="stat-label">To Do</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="inProgressCount">0</div>
                <div class="stat-label">In Progress</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="reviewCount">0</div>
                <div class="stat-label">Review</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="doneCount">0</div>
                <div class="stat-label">Done</div>
            </div>
        </div>

        <div class="board" id="board">
            <div class="column todo">
                <div class="column-header">
                    <h2>📋 To Do</h2>
                    <span class="count" id="todoCountBadge">0</span>
                </div>
                <div class="tasks" id="todoTasks"></div>
            </div>

            <div class="column in_progress">
                <div class="column-header">
                    <h2>🔄 In Progress</h2>
                    <span class="count" id="inProgressCountBadge">0</span>
                </div>
                <div class="tasks" id="inProgressTasks"></div>
            </div>

            <div class="column review">
                <div class="column-header">
                    <h2>👀 Review</h2>
                    <span class="count" id="reviewCountBadge">0</span>
                </div>
                <div class="tasks" id="reviewTasks"></div>
            </div>

            <div class="column done">
                <div class="column-header">
                    <h2>✅ Done</h2>
                    <span class="count" id="doneCountBadge">0</span>
                </div>
                <div class="tasks" id="doneTasks"></div>
            </div>
        </div>
    </div>

    <!-- Create Task Modal -->
    <div class="modal-overlay" id="createTaskModal">
        <div class="modal">
            <h2>Create New Task</h2>
            <form id="createTaskForm">
                <div class="form-group">
                    <label>Title *</label>
                    <input type="text" id="taskTitle" required placeholder="Enter task title">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="taskDescription" placeholder="Enter task description"></textarea>
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select id="taskStatus">
                        <option value="todo">To Do</option>
                        <option value="in_progress">In Progress</option>
                        <option value="review">Review</option>
                        <option value="done">Done</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Priority</label>
                    <select id="taskPriority">
                        <option value="low">Low</option>
                        <option value="medium" selected>Medium</option>
                        <option value="high">High</option>
                        <option value="urgent">Urgent</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Assignee</label>
                    <input type="text" id="taskAssignee" placeholder="Assignee name">
                </div>
                <div class="form-group">
                    <label>Tags (comma-separated)</label>
                    <input type="text" id="taskTags" placeholder="tag1, tag2, tag3">
                </div>
                <div class="modal-actions">
                    <button type="button" onclick="closeCreateTaskModal()">Cancel</button>
                    <button type="submit" class="primary">Create Task</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Create Board Modal -->
    <div class="modal-overlay" id="createBoardModal">
        <div class="modal">
            <h2>Create New Board</h2>
            <form id="createBoardForm">
                <div class="form-group">
                    <label>Board Name *</label>
                    <input type="text" id="boardName" required placeholder="Enter board name">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="boardDescription" placeholder="Enter board description"></textarea>
                </div>
                <div class="modal-actions">
                    <button type="button" onclick="closeCreateBoardModal()">Cancel</button>
                    <button type="submit" class="primary">Create Board</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Task Detail Modal -->
    <div class="modal-overlay" id="taskDetailModal">
        <div class="modal">
            <h2 id="taskDetailTitle">Task Details</h2>
            <div id="taskDetailContent"></div>
            <div class="modal-actions">
                <button onclick="closeTaskDetailModal()">Close</button>
                <button id="deleteTaskBtn" class="primary" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);">Delete Task</button>
            </div>
        </div>
    </div>

    <script>
        let currentBoardId = null;
        let boards = [];
        let currentTaskId = null;

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadBoards();

            // Form handlers
            document.getElementById('createTaskForm').addEventListener('submit', handleCreateTask);
            document.getElementById('createBoardForm').addEventListener('submit', handleCreateBoard);
        });

        async function loadBoards() {
            try {
                const response = await window.mcp.callTool('list_boards', {});
                const data = JSON.parse(response.content[0].text);
                boards = data.boards || [];

                const select = document.getElementById('boardSelect');
                select.innerHTML = '';

                if (boards.length === 0) {
                    // Create default board
                    await createDefaultBoard();
                    return;
                }

                boards.forEach(board => {
                    const option = document.createElement('option');
                    option.value = board.id;
                    option.textContent = board.name;
                    if (board.id === data.default_board_id) {
                        option.selected = true;
                        currentBoardId = board.id;
                    }
                    select.appendChild(option);
                });

                loadBoardData();
            } catch (error) {
                console.error('Error loading boards:', error);
            }
        }

        async function createDefaultBoard() {
            try {
                const response = await window.mcp.callTool('create_board', {
                    name: 'My Kanban Board',
                    description: 'Default kanban board'
                });
                loadBoards();
            } catch (error) {
                console.error('Error creating default board:', error);
            }
        }

        async function loadBoardData() {
            if (!currentBoardId) return;

            try {
                const response = await window.mcp.callTool('get_board', { board_id: currentBoardId });
                const data = JSON.parse(response.content[0].text);

                if (data.board) {
                    renderBoard(data.board, data.statistics);
                }
            } catch (error) {
                console.error('Error loading board:', error);
            }
        }

        function renderBoard(board, stats) {
            // Update stats
            document.getElementById('totalTasks').textContent = stats?.total_tasks || 0;
            document.getElementById('todoCount').textContent = stats?.by_status?.todo || 0;
            document.getElementById('inProgressCount').textContent = stats?.by_status?.in_progress || 0;
            document.getElementById('reviewCount').textContent = stats?.by_status?.review || 0;
            document.getElementById('doneCount').textContent = stats?.by_status?.done || 0;

            // Group tasks by status
            const tasksByStatus = {
                todo: [],
                in_progress: [],
                review: [],
                done: []
            };

            board.tasks.forEach(task => {
                if (tasksByStatus[task.status]) {
                    tasksByStatus[task.status].push(task);
                }
            });

            // Render each column
            renderColumn('todoTasks', tasksByStatus.todo, 'todoCountBadge');
            renderColumn('inProgressTasks', tasksByStatus.in_progress, 'inProgressCountBadge');
            renderColumn('reviewTasks', tasksByStatus.review, 'reviewCountBadge');
            renderColumn('doneTasks', tasksByStatus.done, 'doneCountBadge');
        }

        function renderColumn(containerId, tasks, badgeId) {
            const container = document.getElementById(containerId);
            const badge = document.getElementById(badgeId);

            badge.textContent = tasks.length;

            if (tasks.length === 0) {
                container.innerHTML = '<div class="empty-state"><p>No tasks yet</p></div>';
                return;
            }

            container.innerHTML = tasks.map(task => `
                <div class="task" onclick="openTaskDetail('${task.id}')">
                    <div class="task-title">${escapeHtml(task.title)}</div>
                    ${task.description ? `<div class="task-description">${escapeHtml(task.description.substring(0, 100))}${task.description.length > 100 ? '...' : ''}</div>` : ''}
                    <div class="task-meta">
                        <span class="priority ${task.priority}">${task.priority}</span>
                        ${task.tags?.slice(0, 2).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('') || ''}
                    </div>
                    ${task.assignee ? `<div class="assignee">${escapeHtml(task.assignee)}</div>` : ''}
                </div>
            `).join('');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Modal handlers
        function openCreateTaskModal() {
            document.getElementById('createTaskModal').classList.add('active');
            document.getElementById('createTaskForm').reset();
        }

        function closeCreateTaskModal() {
            document.getElementById('createTaskModal').classList.remove('active');
        }

        function openCreateBoardModal() {
            document.getElementById('createBoardModal').classList.add('active');
            document.getElementById('createBoardForm').reset();
        }

        function closeCreateBoardModal() {
            document.getElementById('createBoardModal').classList.remove('active');
        }

        async function openTaskDetail(taskId) {
            currentTaskId = taskId;
            try {
                const response = await window.mcp.callTool('get_board', { board_id: currentBoardId });
                const data = JSON.parse(response.content[0].text);
                const task = data.board.tasks.find(t => t.id === taskId);

                if (task) {
                    document.getElementById('taskDetailTitle').textContent = task.title;
                    document.getElementById('taskDetailContent').innerHTML = `
                        <div class="form-group">
                            <label>Status</label>
                            <select id="detailStatus">
                                <option value="todo" ${task.status === 'todo' ? 'selected' : ''}>To Do</option>
                                <option value="in_progress" ${task.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                                <option value="review" ${task.status === 'review' ? 'selected' : ''}>Review</option>
                                <option value="done" ${task.status === 'done' ? 'selected' : ''}>Done</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Description</label>
                            <p>${task.description || 'No description'}</p>
                        </div>
                        <div class="form-group">
                            <label>Priority</label>
                            <select id="detailPriority">
                                <option value="low" ${task.priority === 'low' ? 'selected' : ''}>Low</option>
                                <option value="medium" ${task.priority === 'medium' ? 'selected' : ''}>Medium</option>
                                <option value="high" ${task.priority === 'high' ? 'selected' : ''}>High</option>
                                <option value="urgent" ${task.priority === 'urgent' ? 'selected' : ''}>Urgent</option>
                            </select>
                        </div>
                        ${task.assignee ? `<div class="form-group"><label>Assignee</label><p>${task.assignee}</p></div>` : ''}
                        ${task.tags?.length ? `<div class="form-group"><label>Tags</label><p>${task.tags.join(', ')}</p></div>` : ''}
                    `;

                    document.getElementById('taskDetailModal').classList.add('active');
                }
            } catch (error) {
                console.error('Error loading task:', error);
            }
        }

        function closeTaskDetailModal() {
            document.getElementById('taskDetailModal').classList.remove('active');
            currentTaskId = null;
        }

        // Form handlers
        async function handleCreateTask(e) {
            e.preventDefault();

            const title = document.getElementById('taskTitle').value;
            const description = document.getElementById('taskDescription').value;
            const status = document.getElementById('taskStatus').value;
            const priority = document.getElementById('taskPriority').value;
            const assignee = document.getElementById('taskAssignee').value;
            const tagsInput = document.getElementById('taskTags').value;
            const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];

            try {
                await window.mcp.callTool('create_task', {
                    title,
                    description: description || null,
                    board_id: currentBoardId,
                    status,
                    priority,
                    assignee: assignee || null,
                    tags
                });

                closeCreateTaskModal();
                loadBoardData();
            } catch (error) {
                console.error('Error creating task:', error);
                alert('Failed to create task');
            }
        }

        async function handleCreateBoard(e) {
            e.preventDefault();

            const name = document.getElementById('boardName').value;
            const description = document.getElementById('boardDescription').value;

            try {
                const response = await window.mcp.callTool('create_board', {
                    name,
                    description: description || null
                });

                closeCreateBoardModal();
                loadBoards();
            } catch (error) {
                console.error('Error creating board:', error);
                alert('Failed to create board');
            }
        }

        // Delete task handler
        document.getElementById('deleteTaskBtn').addEventListener('click', async () => {
            if (!currentTaskId) return;

            if (confirm('Are you sure you want to delete this task?')) {
                try {
                    await window.mcp.callTool('delete_task', {
                        task_id: currentTaskId,
                        board_id: currentBoardId
                    });

                    closeTaskDetailModal();
                    loadBoardData();
                } catch (error) {
                    console.error('Error deleting task:', error);
                    alert('Failed to delete task');
                }
            }
        });

        // Board selector handler
        document.getElementById('boardSelect').addEventListener('change', (e) => {
            currentBoardId = e.target.value;
            loadBoardData();
        });
    </script>
</body>
</html>'''


@mcp.resource("ui://kanban/board")
def kanban_ui() -> str:
    """Serve the Kanban UI HTML page."""
    return KANBAN_UI_HTML


@mcp.tool(app=AppConfig(resource_uri="ui://kanban/board"))
def open_kanban_ui() -> str:
    """Open the Kanban Board UI for interactive task management."""
    return json.dumps({
        "success": True,
        "message": "Opening Kanban Board UI",
        "ui_resource": "ui://kanban/board"
    })


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
        help="Port for HTTP/SSE transport"
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

    args = parser.parse_args()

    # Update storage path if provided
    if args.storage != "kanban_data.json":
        global storage
        storage = KanbanStorage(args.storage)

    # Run the server
    if args.transport == "stdio":
        mcp.run()
    elif args.transport in ["http", "sse", "streamable-http"]:
        print(f"Starting Kanban MCP Server on {args.host}:{args.port}")
        print(f"Transport: {args.transport}")
        print(f"Storage: {args.storage}")
        print(f"UI available at: ui://kanban/board")
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()