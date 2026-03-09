# Kanban MCP Server

A fully-featured Kanban task management MCP server built with FastMCP, supporting:
- **Web UI** - Beautiful interactive kanban board interface
- **CLI Tools** - Command-line friendly views and commands
- **Native MCP** - Full MCP tool integration for AI assistants

## Features

- Create and manage multiple kanban boards
- Full task lifecycle management (create, update, move, delete)
- Task prioritization (low, medium, high, urgent)
- Task assignment and tagging
- Search and filter tasks
- Board statistics
- JSON-based persistence (no database required)
- Responsive web UI with drag-and-drop ready design

## Installation

```bash
# Install dependencies
pip install fastmcp pydantic

# Or using uv
uv pip install -e .
```

## Usage

### As an MCP Server (stdio)

For use with Claude Desktop, VS Code MCP, or other MCP clients:

```bash
python kanban_server.py
```

### As an HTTP Server

Run as an HTTP server with web UI access:

```bash
python kanban_server.py --transport http --port 8000
```

### As an SSE Server

For Server-Sent Events transport:

```bash
python kanban_server.py --transport sse --port 8000
```

### Custom Storage Location

```bash
python kanban_server.py --storage /path/to/kanban.json
```

## Available Tools

### Board Management

| Tool | Description |
|------|-------------|
| `create_board` | Create a new kanban board |
| `list_boards` | List all available boards |
| `get_board` | Get board details and statistics |
| `delete_board` | Delete a board |
| `set_default_board` | Set a board as default |

### Task Management

| Tool | Description |
|------|-------------|
| `create_task` | Create a new task |
| `update_task` | Update task properties |
| `move_task` | Move task to different column |
| `delete_task` | Delete a task |
| `search_tasks` | Search tasks by title/description/tags |
| `get_tasks_by_status` | Filter tasks by status |
| `get_tasks_by_assignee` | Filter tasks by assignee |
| `get_board_statistics` | Get task distribution stats |

### UI & CLI Tools

| Tool | Description |
|------|-------------|
| `open_kanban_ui` | Open the web-based kanban UI |
| `cli_overview` | Get CLI-friendly overview |
| `cli_board_view` | Get CLI-friendly board view |

## Task Properties

| Property | Type | Values |
|----------|------|--------|
| status | string | `todo`, `in_progress`, `review`, `done` |
| priority | string | `low`, `medium`, `high`, `urgent` |
| tags | array | Any string values |
| assignee | string | Person's name |
| due_date | string | ISO date format |

## Resources

The server exposes the following MCP resources:

- `kanban://boards` - List all boards
- `kanban://board/{board_id}` - Get specific board
- `kanban://default` - Get default board
- `ui://kanban/board` - Interactive web UI

## Example Usage

### Creating a Board and Tasks

```python
# Create a new board
create_board(name="Project Alpha", description="Main project tracking")

# Create tasks
create_task(
    title="Design mockups",
    description="Create UI mockups for the dashboard",
    status="todo",
    priority="high",
    tags=["design", "ui"],
    assignee="Alice"
)

# Move task to in progress
move_task(task_id="abc123", new_status="in_progress")

# Search tasks
search_tasks(query="design")

# Get board statistics
get_board_statistics()
```

### CLI Examples

```
# Overview of all boards
cli_overview()

# View specific board
cli_board_view()

# View with board ID
cli_board_view(board_id="abc12345")
```

## MCP Client Configuration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kanban": {
      "command": "python",
      "args": ["/path/to/kanban_server.py"]
    }
  }
}
```

### VS Code MCP

Add to your MCP settings:

```json
{
  "servers": {
    "kanban": {
      "command": "python",
      "args": ["/path/to/kanban_server.py"]
    }
  }
}
```

## Data Storage

All data is stored in a JSON file (`kanban_data.json` by default). The structure is:

```json
{
  "boards": {
    "board_id": {
      "id": "abc12345",
      "name": "My Board",
      "description": "Board description",
      "columns": ["todo", "in_progress", "review", "done"],
      "tasks": [...],
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  },
  "default_board_id": "abc12345"
}
```

## Web UI

The web UI provides:
- Visual kanban board with 4 columns
- Task creation with modal form
- Task details and editing
- Priority indicators
- Assignee display
- Tag support
- Board statistics
- Multiple board support
- Responsive design for mobile/desktop

Access the UI through the `open_kanban_ui` tool or via the `ui://kanban/board` resource when using an MCP client that supports UI rendering.

## License

MIT