# Time Tracker MCP Server

A FastMCP server for tracking time spent on activities and projects.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Project Management

| Tool | Description |
|------|-------------|
| `create_project` | Create a new project |
| `get_project` | Get project by ID |
| `update_project` | Update project details |
| `list_projects` | List projects |
| `delete_project` | Delete a project |

### Timer Operations

| Tool | Description |
|------|-------------|
| `start_timer` | Start a new timer |
| `stop_timer` | Stop active timer and create entry |
| `get_active_timer` | Get currently active timer |

### Time Entry Management

| Tool | Description |
|------|-------------|
| `log_time` | Log time manually |
| `get_time_entry` | Get entry by ID |
| `update_time_entry` | Update entry |
| `delete_time_entry` | Delete entry |
| `list_time_entries` | List entries with filters |

### Reporting

| Tool | Description |
|------|-------------|
| `get_time_summary` | Get time summary with totals |
| `get_daily_summary` | Get summary for a day |
| `get_weekly_summary` | Get summary for a week |

## Duration Formats

The `log_time` function accepts duration in multiple formats:

- Minutes as integer: `90`
- Duration string: `"1h30m"`, `"90m"`, `"1.5h"`

## Resources

| Resource | Description |
|----------|-------------|
| `time://today` | Today's time tracking |
| `time://week` | Weekly time summary |

## Example Usage

```python
# Create projects
work = create_project(
    name="Client Project",
    client="Acme Corp",
    billable_rate=100.00,
    budget_hours=50
)

personal = create_project(
    name="Side Project",
    color="#2ecc71"
)

# Start timer
timer = start_timer(
    project_id=1,
    description="Working on API integration",
    tags=["development", "api"]
)

# Check active timer
active = get_active_timer()
# Returns: elapsed_minutes, elapsed_formatted, description, project_id

# Stop timer
entry = stop_timer()

# Log time manually
entry = log_time(
    project_id=1,
    duration="2h30m",  # or duration_minutes=150
    description="Code review",
    date="2024-01-15",
    billable=True
)

# Get daily summary
daily = get_daily_summary(date="2024-01-15")
# Returns: date, total_minutes, total_formatted, by_project

# Get weekly summary
weekly = get_weekly_summary()
# Returns: start_date, end_date, total_minutes, days[]

# Get time summary
summary = get_time_summary(
    start_date="2024-01-01",
    end_date="2024-01-31",
    project_id=1
)
# Returns: total_hours, billable_hours, by_project, total_earnings
```

## Timer Behavior

- Only one timer can be active at a time
- Starting a new timer stops the previous one
- Timer calculates elapsed time on each call to `get_active_timer`

## Storage

This server uses in-memory storage. Data is not persisted between restarts.