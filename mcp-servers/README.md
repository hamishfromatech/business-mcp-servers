# MCP Servers

A collection of production-ready MCP (Model Context Protocol) servers built with FastMCP. Each server is self-contained and solves real business problems without requiring external API integrations.

## Quick Start

```bash
# Install FastMCP
pip install fastmcp

# Run any server
cd mcp-servers/<server-name>
python server.py
```

## Available Servers

### Contact & CRM

| Server | Description |
|--------|-------------|
| [contact-book](./contact-book) | Manage contacts with CRUD operations, search, and organization |
| [crm](./crm) | Customer relationship management with leads, deals, pipeline tracking |

### Knowledge & Documentation

| Server | Description |
|--------|-------------|
| [document-wiki](./document-wiki) | Wiki with bi-directional linking `[[title]]`, categories, and tags |
| [zettelkasten](./zettelkasten) | Slip-box note-taking with link graphs, hub detection, orphan finding |
| [notes-ideas](./notes-ideas) | Quick capture and organization with folders, pinning, and archiving |

### Productivity & Planning

| Server | Description |
|--------|-------------|
| [career-manager](./career-manager) | Career development with resume tracking, job applications, cover letters, and interview prep |
| [project-manager](./project-manager) | Projects, tasks, milestones, and team management |
| [kanban-mcp](./kanban-mcp) | Kanban board with web UI, CLI tools, task management, and board statistics |
| [meeting-notes](./meeting-notes) | Meetings with agendas, attendees, and action items |
| [task-automator](./task-automator) | Workflows, templates, triggers, and quick actions |

### Personal Tracking

| Server | Description |
|--------|-------------|
| [habit-tracker](./habit-tracker) | Daily habit tracking with streaks and leaderboards |
| [time-tracker](./time-tracker) | Time tracking with timers and billable rates |
| [expense-tracker](./expense-tracker) | Expense and budget management with categories |
| [journal](./journal) | Personal journal with mood tracking and tags |

### Utilities

| Server | Description |
|--------|-------------|
| [file-organizer](./file-organizer) | Organize and categorize files with duplicate detection |
| [inventory-manager](./inventory-manager) | Stock and product management with low-stock alerts |
| [password-vault](./password-vault) | Secure credential storage with password generation |

### Developer Tools

| Server | Description |
|--------|-------------|
| [skills-server](./skills-server) | Expose Claude Code skills as MCP resources |
| [code-reviewer](./code-reviewer) | Code review management with sessions, issues, and standards |
| [design-audit](./design-audit) | Web design auditing with UI/UX issues and accessibility checks |
| [tech-debt-tracker](./tech-debt-tracker) | Technical debt tracking with refactoring tasks and metrics |

## Configuration

### Claude Desktop

Add any server to your Claude Desktop config at:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "contact-book": {
      "command": "python",
      "args": ["/path/to/mcp-servers/contact-book/server.py"]
    },
    "project-manager": {
      "command": "python",
      "args": ["/path/to/mcp-servers/project-manager/server.py"]
    }
  }
}
```

### Claude Code

Add to your `.claude/settings.json`:

```json
{
  "mcpServers": {
    "contact-book": {
      "command": "python",
      "args": ["./mcp-servers/contact-book/server.py"]
    }
  }
}
```

### Using with FastMCP CLI

```bash
# Run with FastMCP CLI (enables hot reload)
cd mcp-servers/contact-book
fastmcp run server.py

# Development mode with auto-reload
fastmcp dev server.py
```

## Data Persistence

Each server automatically creates a `data/` directory on first use:

```
mcp-servers/
├── contact-book/
│   └── data/
│       └── contacts.json      # Your contact data
├── project-manager/
│   └── data/
│       └── projects.json      # Projects, tasks, milestones
...
```

- **Automatic loading** - Data loads on server startup
- **Auto-save** - Changes persist immediately
- **Portable** - JSON files can be backed up or migrated easily

### Backup & Reset

```bash
# Backup a server's data
cp -r mcp-servers/contact-book/data/ backup/contact-book/

# Reset a server (delete its data)
rm mcp-servers/contact-book/data/contacts.json
```

## Learning Path

**Beginner** - Simple, focused servers:
1. [contact-book](./contact-book) - Basic CRUD operations
2. [notes-ideas](./notes-ideas) - Simple note management
3. [habit-tracker](./habit-tracker) - Daily tracking patterns

**Intermediate** - Complex relationships:
1. [project-manager](./project-manager) - Hierarchical tasks, team management
2. [crm](./crm) - Multi-entity relationships
3. [meeting-notes](./meeting-notes) - Agendas, attendees, action items
4. [kanban-mcp](./kanban-mcp) - Web UI, CLI tools, board management

**Advanced** - Sophisticated patterns:
1. [zettelkasten](./zettelkasten) - Link graphs, pathfinding
2. [document-wiki](./document-wiki) - Wiki link parsing, backlinks
3. [task-automator](./task-automator) - Workflows, triggers, templates
4. [skills-server](./skills-server) - Dynamic resource generation
5. [code-reviewer](./code-reviewer) - Review sessions, issue tracking, code standards
6. [design-audit](./design-audit) - Design systems, accessibility compliance
7. [tech-debt-tracker](./tech-debt-tracker) - Debt tracking, snapshots, quality metrics

## Key Concepts

### Tools

Tools are functions AI assistants can call:

```python
@mcp.tool
def create_contact(name: str, email: str = None) -> dict:
    """Create a new contact."""
```

### Resources

Resources provide read-only data access:

```python
@mcp.resource("contacts://all")
def get_all_contacts() -> str:
    """All contacts as formatted list."""
```

### Type Safety

All tools use type hints for better AI understanding:

```python
def create_task(
    title: str,
    priority: str = "medium",  # low, medium, high, urgent
    due_date: Optional[str] = None
) -> dict:
```

## Common Patterns

### CRUD Operations

Most servers follow this pattern:
- `create_*` - Create new records
- `get_*` - Retrieve by ID
- `list_*` - List with filters
- `update_*` - Modify records
- `delete_*` - Remove records
- `search_*` - Full-text search

### Analytics

Many servers include analytics:
- `get_*_summary` - Aggregated statistics
- `get_*_history` - Historical data
- `get_*_stats` - Overall metrics

## Troubleshooting

**Server won't start:**
```bash
# Ensure FastMCP is installed
pip install fastmcp

# Check Python version (3.8+ required)
python --version
```

**Data not persisting:**
- Check that the server has write permissions to its directory
- Look for a `data/` folder inside the server directory

**MCP client not connecting:**
- Verify the path in your config is absolute
- Check that Python is in your PATH
- Try running the server directly first: `python server.py`

---

Created by **hamishfromatech** - [YouTube](https://youtube.com/@hamishfromatech)