# Notes & Ideas MCP Server

A FastMCP server for capturing and organizing notes and ideas.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Folder Management

| Tool | Description |
|------|-------------|
| `create_folder` | Create a folder for organizing notes |
| `list_folders` | List folders |
| `delete_folder` | Delete a folder |

### Note Management

| Tool | Description |
|------|-------------|
| `create_note` | Create a new note |
| `get_note` | Get note by ID |
| `update_note` | Update a note |
| `delete_note` | Delete a note |
| `quick_note` | Quickly create a note |
| `quick_idea` | Quickly capture an idea |
| `list_notes` | List notes with filters |

### Search and Filter

| Tool | Description |
|------|-------------|
| `search_notes` | Search notes by content/title/tags |
| `get_notes_by_folder` | Get notes in a folder |
| `get_notes_by_tag` | Get notes with a tag |
| `get_all_tags` | Get all tags with counts |
| `get_pinned_notes` | Get all pinned notes |
| `get_ideas` | Get all ideas |

## Note Properties

- `is_idea` - Mark as an idea instead of regular note
- `pinned` - Pin important notes
- `archived` - Archive old notes
- `priority` - Set priority (low, medium, high)

## Tagging

Use `#tag` syntax in note content:

```markdown
This is a note about Python #programming #python

New feature idea for the app #idea #feature
```

## Resources

| Resource | Description |
|----------|-------------|
| `notes://recent` | Recent notes |
| `notes://ideas` | All ideas by priority |
| `notes://tags` | All tags with counts |

## Example Usage

```python
# Create folders
work = create_folder(name="Work", color="#3498db")
personal = create_folder(name="Personal", color="#e74c3c")

# Quick capture
note = quick_note("Remember to call John about the project")

# Quick idea
idea = quick_idea("Build a mobile app for the service", priority="high")

# Create full note
note = create_note(
    title="Project Notes",
    content="Meeting notes from today #work #project\n\n- Discussed timeline\n- Assigned tasks",
    folder_id=1,
    tags=["work", "project"],
    is_idea=False,
    priority="medium"
)

# Pin important note
update_note(note_id=1, pinned=True)

# Archive old note
update_note(note_id=2, archived=True)

# Search notes
results = search_notes(query="project", folder_id=1)

# Get ideas by priority
high_priority = get_ideas(priority="high")
```

## Storage

This server uses in-memory storage. Data is not persisted between restarts.