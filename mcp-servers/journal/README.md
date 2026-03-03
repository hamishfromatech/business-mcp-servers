# Journal MCP Server

A FastMCP server for managing personal journal entries and reflections.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Entry Management

| Tool | Description |
|------|-------------|
| `create_entry` | Create a new journal entry |
| `get_entry` | Get an entry by ID |
| `get_entry_by_date` | Get entry for a specific date |
| `update_entry` | Update an existing entry |
| `delete_entry` | Delete an entry |
| `list_entries` | List entries with date filter |

### Search and Filter

| Tool | Description |
|------|-------------|
| `search_entries` | Search entries by content or title |
| `get_entries_by_tag` | Get entries with a specific tag |
| `get_entries_by_mood` | Get entries with a specific mood |
| `get_all_tags` | Get all tags with usage counts |

### Analytics

| Tool | Description |
|------|-------------|
| `get_mood_summary` | Get mood distribution summary |
| `get_entry_calendar` | Get calendar view for a month |
| `get_writing_stats` | Get writing statistics |

## Tagging

Use `#tag` syntax in entry content to create tags:

```markdown
Today was a great day! #gratitude #personal

Had a productive meeting with the team. #work #project
```

## Resources

| Resource | Description |
|----------|-------------|
| `journal://today` | Today's journal entry |
| `journal://recent` | Recent journal entries |
| `journal://tags` | All tags with counts |

## Example Usage

```python
# Create an entry
entry = create_entry(
    content="Today was productive. Finished the project proposal. #work #success",
    mood="happy",
    date="2024-01-15"
)

# Create with custom title
entry = create_entry(
    title="Project Milestone",
    content="Completed the first phase of development. #milestone",
    mood="accomplished"
)

# Update an entry
update_entry(entry_id=1, mood="excited")

# Search entries
results = search_entries("project")

# Get entries by tag
gratitude_entries = get_entries_by_tag("gratitude")

# Get mood summary
summary = get_mood_summary(start_date="2024-01-01", end_date="2024-01-31")

# Get calendar view
calendar = get_entry_calendar(year=2024, month=1)

# Get writing stats
stats = get_writing_stats()
# Returns: total_entries, total_words, average_words, total_tags
```

## Storage

This server uses in-memory storage. Data is not persisted between restarts.