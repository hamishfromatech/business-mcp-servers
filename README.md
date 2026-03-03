# MCP Servers for Business


![MCP Servers Poster](poster.png)



A collection of production-ready MCP (Model Context Protocol) server examples built with FastMCP, designed to teach you how to create servers that solve real business problems.

Created by **hamishfromatech** - [YouTube](https://youtube.com/@hamishfromatech)

## What This Repository Is

This repository contains **15 fully-functional MCP servers** that demonstrate patterns, tools, and resources you can use as reference when building your own MCP servers. Each server is self-contained, well-documented, and showcases different aspects of the MCP protocol.

**The key insight**: These servers don't need to connect to any external applications or services. They're designed to work standalone, proving that you can build powerful, business-valuable MCP servers without complex integrations.

## Why This Matters

Many MCP tutorials focus on connecting to external APIs (Slack, GitHub, Google, etc.). But real business value often comes from:

- **Data organization** - Structuring information for AI to query
- **Workflow automation** - Creating repeatable processes
- **Knowledge management** - Building searchable systems
- **Tracking & analytics** - Monitoring habits, time, expenses

This repository proves that MCP servers can deliver all of this without a single external API key.

## Servers Overview

### Contact & CRM

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Contact Book](./mcp-servers/contact-book) | Manage contacts with search and organization | CRUD operations, search | `contacts.json` |
| [CRM](./mcp-servers/crm) | Customer relationship management | Leads, deals, pipeline tracking, interactions | `crm.json` |

### Knowledge & Documentation

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Document Wiki](./mcp-servers/document-wiki) | Wiki with bi-directional linking | Wiki links `[[title]]`, categories, tags, backlinks | `wiki.json` |
| [Zettelkasten](./mcp-servers/zettelkasten) | Slip-box note-taking system | Note types, link graphs, hub detection, orphan finding | `zettelkasten.json` |
| [Notes & Ideas](./mcp-servers/notes-ideas) | Quick capture and organization | Folders, pinning, archiving, idea tracking | `notes.json` |

### Productivity & Planning

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Project Manager](./mcp-servers/project-manager) | Projects, tasks, milestones, teams | Task hierarchy, assignments, progress tracking | `projects.json` |
| [Meeting Notes](./mcp-servers/meeting-notes) | Meetings, agendas, action items | Attendees, notes, action item tracking | `meetings.json` |
| [Task Automator](./mcp-servers/task-automator) | Workflows and templates | Triggers, template rendering, quick actions | `automator.json` |

### Personal Tracking

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Habit Tracker](./mcp-servers/habit-tracker) | Daily habit tracking with streaks | Check-ins, streaks, leaderboards, weekly overviews | `habits.json` |
| [Time Tracker](./mcp-servers/time-tracker) | Time tracking with timers | Start/stop timer, manual logging, billable rates | `time.json` |
| [Expense Tracker](./mcp-servers/expense-tracker) | Expense and budget management | Categories, budgets, spending analysis | `expenses.json` |
| [Journal](./mcp-servers/journal) | Personal journal entries | Mood tracking, tags, calendar view, writing stats | `journal.json` |

### Utilities

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [File Organizer](./mcp-servers/file-organizer) | Organize and categorize files | File analysis, duplicate detection, organization rules | `organizer.json` |
| [Inventory Manager](./mcp-servers/inventory-manager) | Stock and product management | Stock in/out, transfers, low-stock alerts | `inventory.json` |
| [Password Vault](./mcp-servers/password-vault) | Secure credential storage | Encryption, password generation, strength checking | `vault.json` |

### Developer Tools

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Skills Server](./mcp-servers/skills-server) | Expose Claude Code skills as MCP resources | Skill discovery, dynamic loading, resource URIs | None (reads filesystem) |

## Quick Start

Each server is standalone and can be run independently:

```bash
# Install FastMCP
pip install fastmcp

# Navigate to any server
cd mcp-servers/contact-book

# Run the server
python server.py
```

**Data Persistence**: Each server automatically creates a `data/` directory on first use. All your data is stored in JSON files and persists across server restarts. You can find your data at `mcp-servers/<server-name>/data/<server-name>.json`.

## Key Concepts Demonstrated

### 1. Tools
Every server exposes tools that AI assistants can call:

```python
@mcp.tool
def create_contact(name: str, email: str = None) -> dict:
    """Create a new contact."""
    # Implementation
```

### 2. Resources
Resources provide read-only data access:

```python
@mcp.resource("contacts://all")
def get_all_contacts() -> str:
    """Resource providing all contacts as formatted list."""
    return formatted_contact_list
```

### 3. Persistent Storage
All servers feature JSON-based persistent storage - data survives server restarts:

```python
# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "contacts.json"

def _load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"contacts": {}, "next_id": 1}

def _save_data(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
```

Each server stores its data in a dedicated `data/` directory:
- **Automatic loading** - Data loads on server startup
- **Auto-save** - Changes persist immediately after each operation
- **Portable** - JSON files can be backed up, migrated, or inspected easily
- **No external dependencies** - Uses only Python's built-in `json` module

**Backing up your data**: Simply copy the `data/` folder from any server. To reset a server, delete its `data/` folder.

### 4. Type Safety
All tools use proper type hints for better AI understanding:

```python
def create_task(
    title: str,
    priority: str = "medium",  # low, medium, high, urgent
    due_date: Optional[str] = None
) -> dict:
```

### 5. Enums for Controlled Values
Status values and categories use Enums:

```python
class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
```

## Architecture Patterns

### CRUD Pattern
Most servers follow a consistent CRUD pattern:
- `create_*` - Create new records
- `get_*` - Retrieve by ID
- `list_*` - List with filters
- `update_*` - Modify records
- `delete_*` - Remove records
- `search_*` - Full-text search

### Analytics Pattern
Many servers include analytics tools:
- `get_*_summary` - Aggregated statistics
- `get_*_history` - Historical data
- `get_*_stats` - Overall metrics

### Linking Pattern
Knowledge systems use bi-directional linking:
- Track outgoing links in content
- Calculate backlinks
- Find paths between notes
- Identify hub and orphan notes

## Project Structure

```
mcp-servers/
├── contact-book/
│   ├── server.py              # Main server implementation
│   ├── README.md              # Server-specific documentation
│   └── data/                  # Persistent storage (auto-created)
│       └── contacts.json      # Contact data
├── crm/
│   ├── server.py
│   └── data/
│       └── crm.json           # Leads, deals, customers, interactions
├── document-wiki/
│   ├── server.py
│   └── data/
│       └── wiki.json          # Documents, categories
├── expense-tracker/
│   ├── server.py
│   └── data/
│       └── expenses.json      # Expenses, budgets, categories
├── file-organizer/
│   ├── server.py
│   └── data/
│       └── organizer.json     # Rules, file registry
├── habit-tracker/
│   ├── server.py
│   └── data/
│       └── habits.json        # Habits, check-ins
├── inventory-manager/
│   ├── server.py
│   └── data/
│       └── inventory.json     # Products, stock, movements
├── journal/
│   ├── server.py
│   └── data/
│       └── journal.json       # Entries, tags
├── meeting-notes/
│   ├── server.py
│   └── data/
│       └── meetings.json      # Meetings, action items
├── notes-ideas/
│   ├── server.py
│   └── data/
│       └── notes.json         # Notes, folders
├── password-vault/
│   ├── server.py
│   └── data/
│       └── vault.json         # Encrypted credentials
├── project-manager/
│   ├── server.py
│   └── data/
│       └── projects.json      # Projects, tasks, milestones
├── task-automator/
│   ├── server.py
│   └── data/
│       └── automator.json     # Workflows, templates
├── time-tracker/
│   ├── server.py
│   └── data/
│       └── time.json          # Time entries, projects
├── zettelkasten/
│   ├── server.py
│   └── data/
│       └── zettelkasten.json  # Notes, links, tags
└── skills-server/
    └── server.py              # No persistence (reads from filesystem)
```

## Learning Path

**Beginner**: Start with these simple, focused servers:
1. Contact Book - Basic CRUD operations
2. Notes & Ideas - Simple note management
3. Habit Tracker - Daily tracking patterns

**Intermediate**: These introduce more complex relationships:
1. Project Manager - Hierarchical tasks, team management
2. CRM - Multi-entity relationships (leads, deals, customers)
3. Meeting Notes - Agendas, attendees, action items

**Advanced**: Sophisticated patterns and algorithms:
1. Zettelkasten - Link graphs, pathfinding, hub detection
2. Document Wiki - Wiki link parsing, backlinks
3. Task Automator - Workflows, triggers, template rendering
4. Skills Server - File system scanning, resource templates, dynamic resource generation

## Why FastMCP?

All servers use [FastMCP](https://github.com/jlowin/fastmcp) because it provides:

- **Simple decorators** - `@mcp.tool` and `@mcp.resource`
- **Automatic schema generation** - Type hints become JSON schemas
- **Built-in server** - No boilerplate code needed
- **Development mode** - Hot reload during development

## Contributing

This is an educational repository. Feel free to:
- Use these servers as starting points for your own projects
- Suggest improvements or new server ideas
- Report issues or documentation gaps

## Data Management

### Backup
Simply copy the `data/` directory from any server:
```bash
cp -r mcp-servers/contact-book/data/ backup/contact-book/
```

### Migration
Data files are plain JSON - you can:
- Edit them directly with any text editor
- Import/export to other systems
- Version control your data with git

### Reset
To reset a server's data, delete its JSON file:
```bash
rm mcp-servers/contact-book/data/contacts.json
```
The server will start fresh on next run.

## License

MIT License - Use these examples freely for learning and building your own MCP servers.

---

**Learn more about MCP and AI development**: [YouTube - Hamish from a Tech](https://youtube.com/@hamishfromatech)