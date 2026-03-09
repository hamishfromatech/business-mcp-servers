#!/usr/bin/env python3
"""
CLI interface for the Kanban MCP server.

This provides a command-line interface for interacting with the kanban
system directly without an MCP client.
"""

import argparse
import json
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from storage import KanbanStorage
from models import TaskStatus, TaskPriority, Task
from datetime import datetime
import uuid

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
GREEN = "\033[32m"
RED = "\033[31m"

# Status configuration
STATUS_CONFIG = [
    ("todo", "TODO", "📋", BLUE),
    ("in_progress", "IN PROGRESS", "🔄", YELLOW),
    ("review", "REVIEW", "👁", MAGENTA),
    ("done", "DONE", "✅", GREEN),
]

# Priority styles
PRIORITY_STYLES = {
    "low": (GREEN, "○"),
    "medium": (YELLOW, "●"),
    "high": (RED, "●"),
    "urgent": (RED, "⚡"),
}


def get_storage(storage_path: str = "kanban_data.json") -> KanbanStorage:
    """Get storage instance."""
    return KanbanStorage(storage_path)


def get_terminal_width():
    """Get terminal width with fallback."""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except:
        return 100


def truncate(text, max_len):
    """Truncate text with ellipsis."""
    if len(text) > max_len:
        return text[:max_len-1] + "…"
    return text


def cmd_list_boards(args):
    """List all boards."""
    storage = get_storage(args.storage)
    boards = storage.list_boards()

    if not boards:
        print(f"\n  {DIM}No boards found. Create one with: kanban create-board <name>{RESET}\n")
        return

    data = storage._read_data()
    default_id = data.get("default_board_id")

    print(f"\n  {BOLD}{CYAN}Kanban Boards{RESET}\n")
    for board in boards:
        marker = f" {GREEN}(default){RESET}" if board.id == default_id else ""
        tasks_count = len(board.tasks)
        print(f"  {BOLD}[{board.id}]{RESET} {board.name}{marker}")
        if board.description:
            print(f"         {DIM}{board.description}{RESET}")
        print(f"         {DIM}{tasks_count} tasks{RESET}")
    print()


def cmd_create_board(args):
    """Create a new board."""
    storage = get_storage(args.storage)
    board = storage.create_board(args.name, args.description)
    print(f"\n  {GREEN}✓{RESET} Created board {BOLD}'{board.name}'{RESET} with ID: {CYAN}{board.id}{RESET}\n")


def cmd_delete_board(args):
    """Delete a board."""
    storage = get_storage(args.storage)
    if storage.delete_board(args.board_id):
        print(f"\n  {GREEN}✓{RESET} Deleted board: {args.board_id}\n")
    else:
        print(f"\n  {RED}✗{RESET} Board not found: {args.board_id}\n")


def cmd_view(args):
    """View a board with all tasks in a visual kanban layout."""
    storage = get_storage(args.storage)

    if args.board_id:
        board = storage.get_board(args.board_id)
    else:
        board = storage.get_default_board()

    if not board:
        print(f"\n  {RED}Board not found.{RESET}\n")
        return

    terminal_width = get_terminal_width()
    col_width = max(22, min(40, (terminal_width - 12) // 4))

    # Build columns
    columns = []
    max_tasks = 0
    for status_value, status_label, icon, color in STATUS_CONFIG:
        tasks = [t for t in board.tasks if t.status.value == status_value]
        columns.append({
            "status": status_value,
            "label": status_label,
            "icon": icon,
            "tasks": tasks,
            "color": color
        })
        max_tasks = max(max_tasks, len(tasks))

    # Print header
    print()
    print(f"  {BOLD}{CYAN}{'━' * (terminal_width - 4)}{RESET}")
    print(f"  {BOLD}📋 {board.name}{RESET}")
    if board.description:
        print(f"  {DIM}{board.description}{RESET}")
    print(f"  {BOLD}{CYAN}{'━' * (terminal_width - 4)}{RESET}")
    print()

    # Print column headers
    header_line = "  "
    for col in columns:
        count = len(col["tasks"])
        color = col["color"]
        header = f"{col['icon']} {col['label']} ({count})"
        header_line += f"{BOLD}{color}{header:<{col_width}}{RESET}"
    print(header_line)
    print(f"  {DIM}{'─' * (terminal_width - 4)}{RESET}")

    # Print tasks
    if max_tasks == 0:
        print(f"\n      {DIM}(no tasks - use 'kanban add \"task title\"' to add one){RESET}\n")
    else:
        for row_idx in range(max_tasks):
            # Task title row
            title_row = "  "
            for col in columns:
                tasks = col["tasks"]
                if row_idx < len(tasks):
                    task = tasks[row_idx]
                    p_color, p_icon = PRIORITY_STYLES.get(task.priority.value, ("", "○"))
                    title = truncate(task.title, col_width - 6)
                    title_row += f"  {p_color}{p_icon}{RESET} {title:<{col_width-6}}"
                else:
                    title_row += " " * col_width
            print(title_row)

            # ID and assignee row
            details_row = "  "
            for col in columns:
                tasks = col["tasks"]
                if row_idx < len(tasks):
                    task = tasks[row_idx]
                    details = f"[{task.id}]"
                    if task.assignee:
                        details += f" @{truncate(task.assignee, 8)}"
                    details = truncate(details, col_width - 4)
                    details_row += f"    {DIM}{details:<{col_width-6}}{RESET}"
                else:
                    details_row += " " * col_width
            print(details_row)

            # Tags row
            tags_row = "  "
            for col in columns:
                tasks = col["tasks"]
                if row_idx < len(tasks):
                    task = tasks[row_idx]
                    if task.tags:
                        tags = " ".join(f"#{t}" for t in task.tags[:2])
                        tags = truncate(tags, col_width - 4)
                        tags_row += f"    {DIM}{CYAN}{tags:<{col_width-6}}{RESET}"
                    else:
                        tags_row += " " * col_width
                else:
                    tags_row += " " * col_width
            print(tags_row)

            # Spacing between tasks
            if row_idx < max_tasks - 1:
                print()

    # Print footer with stats
    stats = storage.get_statistics(board.id)
    total = stats.get('total_tasks', 0)
    print()
    print(f"  {DIM}{'─' * (terminal_width - 4)}{RESET}")
    stats_line = f"  {BOLD}Total:{RESET} {total}   "
    stats_line += f"{GREEN}● {stats.get('by_status', {}).get('done', 0)} done{RESET}   "
    stats_line += f"{YELLOW}● {stats.get('by_status', {}).get('in_progress', 0)} active{RESET}   "
    stats_line += f"{MAGENTA}● {stats.get('by_status', {}).get('review', 0)} review{RESET}   "
    stats_line += f"{BLUE}● {stats.get('by_status', {}).get('todo', 0)} todo{RESET}"
    print(stats_line)
    print()

    # Legend and help
    print(f"  {DIM}Priority: ○ low   ● medium/high   ⚡ urgent{RESET}")
    print(f"  {DIM}Commands: add \"title\"  |  move <id> <status>  |  delete <id>{RESET}")
    print()


def cmd_add_task(args):
    """Add a new task."""
    storage = get_storage(args.storage)

    if args.board_id:
        board = storage.get_board(args.board_id)
    else:
        board = storage.get_default_board()
        if not board:
            board = storage.create_board("Default Board", "Default kanban board")

    try:
        status = TaskStatus(args.status)
    except ValueError:
        print(f"\n  {RED}✗{RESET} Invalid status: {args.status}")
        print(f"  Valid options: {[s.value for s in TaskStatus]}\n")
        return

    try:
        priority = TaskPriority(args.priority)
    except ValueError:
        print(f"\n  {RED}✗{RESET} Invalid priority: {args.priority}")
        print(f"  Valid options: {[p.value for p in TaskPriority]}\n")
        return

    task = Task(
        id=str(uuid.uuid4())[:8],
        title=args.title,
        description=args.description,
        status=status,
        priority=priority,
        tags=args.tags.split(",") if args.tags else [],
        assignee=args.assignee,
    )

    storage.add_task(board.id, task)
    print(f"\n  {GREEN}✓{RESET} Created task {BOLD}[{task.id}]{RESET} '{task.title}' in '{board.name}'\n")


def cmd_move_task(args):
    """Move a task to a different status."""
    storage = get_storage(args.storage)

    if args.board_id:
        board = storage.get_board(args.board_id)
    else:
        board = storage.get_default_board()

    if not board:
        print(f"\n  {RED}✗{RESET} Board not found\n")
        return

    try:
        status = TaskStatus(args.status)
    except ValueError:
        print(f"\n  {RED}✗{RESET} Invalid status: {args.status}")
        print(f"  Valid: todo, in_progress, review, done\n")
        return

    task = storage.move_task(board.id, args.task_id, status)
    if task:
        print(f"\n  {GREEN}✓{RESET} Moved task {BOLD}[{task.id}]{RESET} to {YELLOW}'{status.value}'{RESET}\n")
    else:
        print(f"\n  {RED}✗{RESET} Task not found: {args.task_id}\n")


def cmd_delete_task(args):
    """Delete a task."""
    storage = get_storage(args.storage)

    if args.board_id:
        board = storage.get_board(args.board_id)
    else:
        board = storage.get_default_board()

    if not board:
        print(f"\n  {RED}✗{RESET} Board not found\n")
        return

    if storage.delete_task(board.id, args.task_id):
        print(f"\n  {GREEN}✓{RESET} Deleted task: {args.task_id}\n")
    else:
        print(f"\n  {RED}✗{RESET} Task not found: {args.task_id}\n")


def cmd_search(args):
    """Search tasks."""
    storage = get_storage(args.storage)
    results = storage.search_tasks(args.query, args.board_id)

    if not results:
        print(f"\n  {DIM}No tasks found matching '{args.query}'{RESET}\n")
        return

    print(f"\n  {BOLD}Search results for '{args.query}'{RESET} ({len(results)} found)\n")
    for board_id, task in results:
        status_colors = {"todo": BLUE, "in_progress": YELLOW, "review": MAGENTA, "done": GREEN}
        color = status_colors.get(task.status.value, "")
        print(f"  {BOLD}[{task.id}]{RESET} {task.title} {color}({task.status.value}){RESET}")
        if task.description:
            desc = truncate(task.description, 60)
            print(f"      {DIM}{desc}{RESET}")
    print()


def cmd_stats(args):
    """Show board statistics."""
    storage = get_storage(args.storage)

    if args.board_id:
        board = storage.get_board(args.board_id)
    else:
        board = storage.get_default_board()

    if not board:
        print(f"\n  {RED}Board not found.{RESET}\n")
        return

    stats = storage.get_statistics(board.id)

    print(f"\n  {BOLD}{CYAN}Statistics for '{board.name}'{RESET}\n")
    print(f"  Total Tasks: {BOLD}{stats['total_tasks']}{RESET}")
    print()
    print(f"  {BOLD}By Status:{RESET}")
    for status, count in stats.get("by_status", {}).items():
        status_colors = {"todo": BLUE, "in_progress": YELLOW, "review": MAGENTA, "done": GREEN}
        color = status_colors.get(status, "")
        print(f"    {color}●{RESET} {status}: {count}")
    print()
    print(f"  {BOLD}By Priority:{RESET}")
    for priority, count in stats.get("by_priority", {}).items():
        p_color, p_icon = PRIORITY_STYLES.get(priority, ("", "●"))
        print(f"    {p_color}{p_icon}{RESET} {priority}: {count}")
    print()
    print(f"  {BOLD}By Assignee:{RESET}")
    for assignee, count in stats.get("by_assignee", {}).items():
        print(f"    👤 {assignee}: {count}")
    print()


def cmd_export(args):
    """Export board to JSON."""
    storage = get_storage(args.storage)

    if args.board_id:
        board = storage.get_board(args.board_id)
    else:
        board = storage.get_default_board()

    if not board:
        print(f"\n  {RED}Board not found.{RESET}\n")
        return

    output = json.dumps(board.to_dict(), indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(f"\n  {GREEN}✓{RESET} Exported to {args.output}\n")
    else:
        print(f"\n{output}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Kanban CLI - Task management from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kanban list                           List all boards
  kanban create-board "My Project"      Create a new board
  kanban view                           View default board (visual kanban)
  kanban add "Write docs" -p high       Add a high priority task
  kanban move abc123 in_progress        Move task to in progress
  kanban search "bug"                   Search for tasks
  kanban stats                          Show statistics
        """
    )
    parser.add_argument("--storage", "-s", default="kanban_data.json",
                        help="Path to JSON storage file")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list boards
    subparsers.add_parser("list", aliases=["ls"], help="List all boards")

    # create board
    create_board_parser = subparsers.add_parser("create-board", aliases=["cb"],
                                                 help="Create a new board")
    create_board_parser.add_argument("name", help="Board name")
    create_board_parser.add_argument("-d", "--description", help="Board description")

    # delete board
    delete_board_parser = subparsers.add_parser("delete-board", aliases=["db"],
                                                 help="Delete a board")
    delete_board_parser.add_argument("board_id", help="Board ID to delete")

    # view board
    view_parser = subparsers.add_parser("view", aliases=["v"], help="View a board (visual kanban)")
    view_parser.add_argument("board_id", nargs="?", help="Board ID (optional)")

    # add task
    add_parser = subparsers.add_parser("add", aliases=["a"], help="Add a new task")
    add_parser.add_argument("title", help="Task title")
    add_parser.add_argument("-b", "--board-id", help="Board ID")
    add_parser.add_argument("-d", "--description", help="Task description")
    add_parser.add_argument("-s", "--status", default="todo",
                            choices=["todo", "in_progress", "review", "done"],
                            help="Task status")
    add_parser.add_argument("-p", "--priority", default="medium",
                            choices=["low", "medium", "high", "urgent"],
                            help="Task priority")
    add_parser.add_argument("-t", "--tags", help="Comma-separated tags")
    add_parser.add_argument("-a", "--assignee", help="Assignee name")

    # move task
    move_parser = subparsers.add_parser("move", aliases=["m"], help="Move a task")
    move_parser.add_argument("task_id", help="Task ID to move")
    move_parser.add_argument("status", choices=["todo", "in_progress", "review", "done"],
                             help="Target status")
    move_parser.add_argument("-b", "--board-id", help="Board ID")

    # delete task
    delete_parser = subparsers.add_parser("delete", aliases=["del"], help="Delete a task")
    delete_parser.add_argument("task_id", help="Task ID to delete")
    delete_parser.add_argument("-b", "--board-id", help="Board ID")

    # search
    search_parser = subparsers.add_parser("search", aliases=["s"], help="Search tasks")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-b", "--board-id", help="Board ID")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show board statistics")
    stats_parser.add_argument("board_id", nargs="?", help="Board ID")

    # export
    export_parser = subparsers.add_parser("export", help="Export board to JSON")
    export_parser.add_argument("board_id", nargs="?", help="Board ID")
    export_parser.add_argument("-o", "--output", help="Output file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "list": cmd_list_boards,
        "ls": cmd_list_boards,
        "create-board": cmd_create_board,
        "cb": cmd_create_board,
        "delete-board": cmd_delete_board,
        "db": cmd_delete_board,
        "view": cmd_view,
        "v": cmd_view,
        "add": cmd_add_task,
        "a": cmd_add_task,
        "move": cmd_move_task,
        "m": cmd_move_task,
        "delete": cmd_delete_task,
        "del": cmd_delete_task,
        "search": cmd_search,
        "s": cmd_search,
        "stats": cmd_stats,
        "export": cmd_export,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()