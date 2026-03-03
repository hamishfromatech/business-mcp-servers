# Zettelkasten MCP Server

A FastMCP server for managing a slip-box (Zettelkasten) note-taking system with bi-directional linking.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Note Management

| Tool | Description |
|------|-------------|
| `create_note` | Create a new note |
| `get_note` | Get note by ID |
| `get_note_with_backlinks` | Get note with backlinks |
| `update_note` | Update a note |
| `delete_note` | Delete a note |
| `list_notes` | List notes with filters |

### Linking

| Tool | Description |
|------|-------------|
| `link_notes` | Create link between notes |
| `unlink_notes` | Remove link between notes |
| `get_backlinks` | Get notes linking to a note |
| `get_outgoing_links` | Get notes linked from a note |

### Search and Discovery

| Tool | Description |
|------|-------------|
| `search_notes` | Search by title or content |
| `get_notes_by_tag` | Get notes with a tag |
| `get_all_tags` | Get all tags |
| `get_hub_notes` | Get highly linked notes |
| `get_orphan_notes` | Get notes with no links |
| `get_note_path` | Find path between notes |
| `get_related_notes` | Get related notes |

### Statistics

| Tool | Description |
|------|-------------|
| `get_zettelkasten_stats` | Get overall statistics |

## Note Types

- `fleeting` - Temporary notes, quick captures
- `literature` - Notes from reading/research
- `permanent` - Refined, atomic notes
- `structure` - Index/overview notes

## Wiki Links

Use `[[note_id]]` to link to other notes:

```markdown
# My Note

This idea connects to [[42]] and builds on [[15]].

Related concepts: #philosophy #knowledge-management
```

## Resources

| Resource | Description |
|----------|-------------|
| `zettelkasten://index` | Zettelkasten index and stats |
| `zettelkasten://hubs` | Hub notes (highly linked) |
| `zettelkasten://orphans` | Orphan notes (no links) |
| `zettelkasten://tags` | All tags with counts |

## Example Usage

```python
# Create notes
note1 = create_note(
    title="Atomic notes are self-contained",
    content="Each note should contain one idea. This connects to [[2]]. #principle",
    note_type="permanent"
)

note2 = create_note(
    title="Notes should be linked",
    content="Links create a knowledge network. See [[1]] for principles. #principle",
    note_type="permanent"
)

# Get with backlinks
note = get_note_with_backlinks(note_id=1)
# Returns note + backlinks from note 2

# Find path between notes
path = get_note_path(from_note_id=1, to_note_id=5, max_depth=3)
# Returns: [1, 3, 5] or None if no path

# Get related notes
related = get_related_notes(note_id=1, max_distance=2)

# Find hub notes (3+ backlinks)
hubs = get_hub_notes(min_backlinks=3)

# Find orphan notes
orphans = get_orphan_notes()

# Search
results = search_notes("knowledge management")

# Get by tag
notes = get_notes_by_tag("principle")

# Get statistics
stats = get_zettelkasten_stats()
# Returns: total_notes, total_links, total_tags, hub_count, orphan_count
```

## Zettelkasten Principles

1. **Atomic**: Each note contains one idea
2. **Autonomous**: Notes make sense on their own
3. **Linked**: Notes connect to related ideas
4. **Tagged**: Notes have relevant tags
5. **Referenced**: Notes cite sources

## Link Graph

The server maintains bi-directional links:
- `links_to` - Notes this note links to
- `backlinks` - Notes linking to this note

This enables:
- Finding related concepts
- Discovering connections
- Building knowledge graphs

## Storage

This server uses in-memory storage. Data is not persisted between restarts.