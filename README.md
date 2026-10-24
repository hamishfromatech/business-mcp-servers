# MCP Servers for Business

![MCP Servers Poster](poster.png)

A collection of production-ready MCP (Model Context Protocol) server examples built with FastMCP, designed to teach you how to create servers that solve real business problems.

Created by **hamishfromatech** - [YouTube](https://youtube.com/@hamishfromatech)
<a href="https://buymeacoffee.com/hamishfromatech" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

## Contents

- [What This Repository Is](#what-this-repository-is)
- [Servers Overview](#servers-overview)
- [Quick Start](#quick-start)
- [Key Concepts Demonstrated](#key-concepts-demonstrated)
- [Architecture Patterns](#architecture-patterns)
- [Performance & Reliability](#performance--reliability)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Learning Path](#learning-path)
- [Why FastMCP?](#why-fastmcp)
- [Data Management](#data-management)
- [Contributing](#contributing)
- [License](#license)

## What This Repository Is

This repository contains **27 fully-functional MCP servers** that demonstrate patterns, tools, and resources you can use as reference when building your own MCP servers. Each server is self-contained, well-documented, and showcases different aspects of the MCP protocol.

**The key insight**: These servers don't need to connect to any external applications or services. They're designed to work standalone, proving that you can build powerful, business-valuable MCP servers without complex integrations.

**At a glance**

| | |
|---|---|
| Servers | 27, each independently runnable |
| External APIs required | None |
| Storage | Plain, human-readable JSON |
| Test suites | 6 pytest suites (64 tests) |
| Runtime | Python 3.10+ and FastMCP |

## Why This Matters

Many MCP tutorials focus on connecting to external APIs (Slack, GitHub, Google, etc.). But real business value often comes from:

- **Data organization** - Structuring information for AI to query
- **Workflow automation** - Creating repeatable processes
- **Knowledge management** - Building searchable systems
- **Tracking & analytics** - Monitoring habits, time, expenses, revenue, SLAs

This repository proves that MCP servers can deliver all of this without a single external API key.

## Servers Overview

### Contact & CRM

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Contact Book](./mcp-servers/contact-book) | Manage contacts with search and organization | CRUD operations, search | `contacts.json` |
| [CRM](./mcp-servers/crm) | Customer relationship management | Leads, deals, pipeline tracking, interactions | `crm.json` |

### Revenue & Customer Operations

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Invoice Manager](./mcp-servers/invoice-manager) | Invoicing and accounts receivable | Clients, line items, payments, recurring billing, aging report | `invoices.json` |
| [Support Desk](./mcp-servers/support-desk) | Customer support helpdesk | Tickets, SLA deadlines, escalations, CSAT | `support.json` |

### Procurement & Legal

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Contract Manager](./mcp-servers/contract-manager) | Contract lifecycle management | Expiry, renewal notice deadlines, obligations | `contracts.json` |
| [Vendor Manager](./mcp-servers/vendor-manager) | Vendor and procurement management | Suppliers, purchase orders, lead times, scorecards | `vendors.json` |

### Knowledge & Documentation

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Document Wiki](./mcp-servers/document-wiki) | Wiki with bi-directional linking | Wiki links `[[title]]`, categories, tags, backlinks | `wiki.json` |
| [Zettelkasten](./mcp-servers/zettelkasten) | Slip-box note-taking system | Note types, link graphs, hub detection, orphan finding | `zettelkasten.json` |
| [Notes & Ideas](./mcp-servers/notes-ideas) | Quick capture and organization | Folders, pinning, archiving, idea tracking | `notes.json` |

### Productivity & Planning

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Career Manager](./mcp-servers/career-manager) | Complete career management system | Resume builder, job applications, interview practice, skills inventory, networking | `~/.career-manager/*.json` |
| [Project Manager](./mcp-servers/project-manager) | Projects, tasks, milestones, teams | Task hierarchy, assignments, progress tracking | `projects.json` |
| [Kanban](./mcp-servers/kanban-mcp) | Kanban board with visual interface | Web UI, CLI tools, task management, board statistics, drag-and-drop ready | `kanban_data.json` |
| [Meeting Notes](./mcp-servers/meeting-notes) | Meetings, agendas, action items | Attendees, notes, action item tracking | `meetings.json` |
| [Task Automator](./mcp-servers/task-automator) | Workflows and templates | Triggers, template rendering, quick actions | `automator.json` |
| [OKR Tracker](./mcp-servers/okr-tracker) | Objectives and key results | Key results, check-ins, confidence, progress rollups | `okrs.json` |

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
| [Password Vault](./mcp-servers/password-vault) | Secure credential storage | AES/Fernet encryption, PBKDF2 key derivation, password generation, strength checking | `vault.json` |
| [Business Search](./mcp-servers/business-search) | Cross-server search hub | One query across every server's JSON data, incremental indexing | None (indexes other servers) |

### Developer Tools

| Server | Description | Key Features | Data File |
|--------|-------------|--------------|-----------|
| [Skills Server](./mcp-servers/skills-server) | Expose Claude Code skills as MCP resources | Skill discovery, dynamic loading, resource URIs | None (reads filesystem) |
| [Code Reviewer](./mcp-servers/code-reviewer) | Code review management | Review sessions, issue tracking, code standards | `code_reviewer.json` |
| [Design Audit](./mcp-servers/design-audit) | Web design auditing | UI/UX issues, design systems, accessibility checks | `design_audit.json` |
| [Tech Debt Tracker](./mcp-servers/tech-debt-tracker) | Technical debt management | Debt tracking, refactoring tasks, quality metrics | `tech_debt.json` |

## Quick Start

Each server is standalone and can be run independently:

```bash
# Install FastMCP (and any server-specific extras)
pip install fastmcp

# Or install a server's exact dependencies
pip install -r mcp-servers/invoice-manager/requirements.txt

# Navigate to any server and run it
cd mcp-servers/contact-book
python server.py
```

**Data Persistence**: Each server automatically creates a `data/` directory on first use. All your data is stored in JSON files and persists across server restarts. You can find your data at `mcp-servers/<server-name>/data/<server-name>.json`.

**Connecting to a client**: see the configuration examples in [mcp-servers/README.md](./mcp-servers/README.md) for Claude Desktop, Claude Code, and the FastMCP CLI.

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

All 23 `server.py` data servers use the same hardened JSON persistence helper:

```python
# Override the data directory for tests or deployments
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "contacts.json"

def _load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"contacts": {}, "next_id": 1}

def _save_data(data: dict) -> None:
    # Serialize once, skip identical writes, write atomically under a lock.
    payload = json.dumps(data, indent=2, default=str)
    with _write_lock:
        if payload == _last_payload:
            return
        _write_payload(payload)   # temp file + os.replace()
```

Properties shared by every data server:

- **Atomic writes** - temp file + `os.replace()`, so an interrupted write cannot corrupt your data
- **Thread-safe** - a module-level `threading.Lock()` serialises concurrent tool calls
- **Redundant-write skipping** - identical payloads are never rewritten
- **Single write per mutation** - ID allocation does not trigger a second save
- **Opt-in debouncing** - `MCP_WRITE_DEBOUNCE_MS` defers disk I/O; pending writes flush on exit and via `flush_data`
- **Built-in backups** - `backup_data`, `list_backups`, and `restore_backup` on every data server

Each server stores its data in a dedicated `data/` directory:

- **Automatic loading** - Data loads on server startup
- **Auto-save** - Changes persist immediately after each operation
- **Portable** - JSON files can be backed up, migrated, or inspected easily
- **No external dependencies** - Uses only Python's built-in `json` module

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

### 6. Pydantic Models

Records are validated with Pydantic models and returned as typed objects, so
clients get real JSON schemas instead of loose dicts.

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

### Business Logic Patterns

The business servers demonstrate reusable domain techniques:

| Pattern | Server | What it shows |
|---------|--------|---------------|
| Money math | Invoice Manager | Line-item totals, tax, discounts, rounding to cents |
| Aging buckets | Invoice Manager | `current / 1-30 / 31-60 / 61-90 / 90+` receivables |
| Recurring schedules | Invoice Manager, Contract Manager | Month-end-safe date advancement |
| SLA windows | Support Desk | Deadline derivation, at-risk vs breached, compliance % |
| Bidirectional targets | OKR Tracker | Progress works when the target is lower than the start |
| Hierarchy rollups | OKR Tracker | Objective progress = mean of key results |
| Notice deadlines | Contract Manager | `end_date - notice_days`, "notice passed" warnings |
| On-time scoring | Vendor Manager | `received_at` vs `expected_at` per order |
| Cross-file indexing | Business Search | Incremental mtime/size cache, nested record extraction |
| Bulk operations | Invoice / Support / OKR | One disk write for N records |

## Performance & Reliability

Recent hardening across every data server:

- **Atomic, locked writes** - no torn files, no lost updates under concurrent tool calls
- **Redundant-write skipping** - unchanged state never touches the disk
- **Optional debouncing** - `MCP_WRITE_DEBOUNCE_MS` trades a small durability window for fewer writes
- **Bulk endpoints** - `bulk_create_*` / `bulk_add_*` collapse N saves into 1
- **Backups** - snapshot, list, and restore from inside the MCP client
- **Incremental indexing** - Business Search re-parses only changed files
- **TTL skill scanning** - Skills Server stats only changed `SKILL.md` files
- **Secure vault** - AES/Fernet with PBKDF2-HMAC-SHA256 (600k iterations) and a random salt

## Environment Variables

All servers respect these where applicable:

| Variable | Used by | Purpose |
|----------|---------|---------|
| `MCP_DATA_DIR` | All 23 `server.py` data servers | Store data somewhere other than `<server>/data/` (career-manager and kanban-mcp manage their own storage) |
| `MCP_WRITE_DEBOUNCE_MS` | All 23 `server.py` data servers | Defer disk writes by N milliseconds (default `0` = write immediately) |
| `MCP_DATA_ROOTS` | Business Search | `os.pathsep`-separated roots to index instead of the default `mcp-servers/` directory |
| `SKILLS_REFRESH_TTL_SECONDS` | Skills Server | Minimum seconds between skill-directory change checks (default `30`) |
| `SKILLS_PATH` | Skills Server | Extra `os.pathsep`-separated skill directories to scan |

Examples:

```bash
# Keep all data in a shared volume
MCP_DATA_DIR=/srv/mcp-data python server.py

# Batch writes for high-throughput ingestion
MCP_WRITE_DEBOUNCE_MS=250 python server.py

# Point the search hub at multiple data roots
MCP_DATA_ROOTS=/srv/mcp-data:/backup/mcp-data python server.py
```

## Project Structure

```
mcp-servers/
├── README.md                     # Client configuration + per-server index
│
├── # Business servers
├── invoice-manager/              # server.py, README.md, requirements*.txt, tests/
├── support-desk/                 #   "
├── contract-manager/             #   "
├── vendor-manager/               #   "
├── crm/                          #   "
├── contact-book/                 #   "
├── okr-tracker/                  #   "
│
├── # Knowledge & productivity
├── document-wiki/
├── zettelkasten/
├── notes-ideas/
├── project-manager/
├── meeting-notes/
├── task-automator/
├── journal/
├── habit-tracker/
├── time-tracker/
├── expense-tracker/
│
├── # Utilities & dev tools
├── file-organizer/
├── inventory-manager/
├── password-vault/               # AES/Fernet + PBKDF2 encryption
├── business-search/              # Cross-server search hub
├── skills-server/                # No persistence (filesystem + TTL cache)
├── code-reviewer/
├── design-audit/
├── tech-debt-tracker/
│
├── # Special layouts
├── career-manager/               # src/career_manager/ package + pyproject.toml
└── kanban-mcp/                   # kanban_server.py, models.py, storage.py, cli.py, index.html
```

Per-server layout (the common case):

```
<server-name>/
├── server.py                 # FastMCP server
├── README.md                 # Tool reference and examples
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Test dependencies
├── tests/                    # pytest suite
│   └── test_<name>.py
└── data/                     # Auto-created on first write (gitignored)
    ├── <name>.json
    └── backups/              # Created by backup_data
```

## Testing

Six servers ship with pytest suites covering their core logic (money math,
payment allocation, aging, SLA windows, progress math, search indexing,
renewal deadlines, and procurement scoring):

```bash
pip install -r mcp-servers/invoice-manager/requirements-dev.txt

pytest mcp-servers/invoice-manager/tests \
       mcp-servers/support-desk/tests \
       mcp-servers/okr-tracker/tests \
       mcp-servers/business-search/tests \
       mcp-servers/contract-manager/tests \
       mcp-servers/vendor-manager/tests
```

Expected: `64 passed`.

Tests isolate themselves with `MCP_DATA_DIR` / `MCP_DATA_ROOTS`, so they never
touch your real data.

## Learning Path

**Beginner**: Start with these simple, focused servers:

1. Contact Book - Basic CRUD operations
2. Notes & Ideas - Simple note management
3. Habit Tracker - Daily tracking patterns

**Intermediate**: These introduce more complex relationships:

1. Project Manager - Hierarchical tasks, team management
2. CRM - Multi-entity relationships (leads, deals, customers)
3. Meeting Notes - Agendas, attendees, action items
4. Kanban - Web UI, CLI tools, board management

**Advanced**: Sophisticated patterns and algorithms:

1. Zettelkasten - Link graphs, pathfinding, hub detection
2. Document Wiki - Wiki link parsing, backlinks
3. Task Automator - Workflows, triggers, template rendering
4. Skills Server - File system scanning, resource templates, dynamic resource generation
5. Career Manager - Resume generation, job application tracking, interview practice, skill gap analysis
6. Code Reviewer - Review sessions, issue tracking with categories/severity, code standards
7. Design Audit - Design systems, accessibility compliance, WCAG tracking
8. Tech Debt Tracker - Interest tracking, snapshots, quality metrics
9. Invoice Manager - Money math, tax/discount totals, payment allocation, aging buckets, recurring schedules
10. Support Desk - Time-based SLA logic, breach detection, compliance metrics
11. OKR Tracker - Bidirectional progress math, hierarchical rollups, check-in history
12. Business Search - Cross-file indexing, incremental cache refresh, multi-source ranking
13. Contract Manager - Date-window logic, notice deadlines, recurring obligations
14. Vendor Manager - Procurement totals, lead-time forecasting, on-time delivery scoring

## Why FastMCP?

All servers use [FastMCP](https://github.com/jlowin/fastmcp) because it provides:

- **Simple decorators** - `@mcp.tool` and `@mcp.resource`
- **Automatic schema generation** - Type hints become JSON schemas
- **Built-in server** - No boilerplate code needed
- **Development mode** - Hot reload during development

## Data Management

### Backup

Every data server exposes backup tools your AI client can call:

| Tool | Purpose |
|------|---------|
| `backup_data` | Snapshot the current JSON into `data/backups/<name>-<timestamp>.json` |
| `list_backups` | List snapshots, newest first |
| `restore_backup(name)` | Replace current data from a snapshot (restart the server to load it) |

You can also copy the folder yourself:

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

## Contributing

This is an educational repository. Feel free to:

- Use these servers as starting points for your own projects
- Suggest improvements or new server ideas
- Report issues or documentation gaps

## License

MIT License - Use these examples freely for learning and building your own MCP servers.

---

**Learn more about MCP and AI development**: [YouTube - Hamish from a Tech](https://youtube.com/@hamishfromatech)
---

## Feedback & Community

Found this MCP server genuinely useful? I'd love to hear from you.

- **Email**: [hamish@atech.industries](mailto:hamish@atech.industries)
- **Join our free Open Source AI Builders Club on Skool**: [https://www.skool.com/open-source-ai-builders-club/about?ref=da946a67c5c646e991b96ea9ce7ad9e4](https://www.skool.com/open-source-ai-builders-club/about?ref=da946a67c5c646e991b96ea9ce7ad9e4)
