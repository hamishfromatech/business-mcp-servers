"""
Zettelkasten MCP Server
A FastMCP server for managing a slip-box note-taking system with linked notes.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import re
from collections import deque
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Zettelkasten",
    instructions="A Zettelkasten (slip-box) server for creating and linking atomic notes with bi-directional references."
)


class Note(BaseModel):
    """A Zettelkasten note."""
    id: int
    title: str
    content: str
    tags: list[str] = []
    links_to: list[int] = []
    created_at: str
    updated_at: str


class Tag(BaseModel):
    """A tag with note count."""
    tag: str
    count: int


class HubNote(BaseModel):
    """A hub note with backlink count."""
    id: int
    title: str
    content: str
    tags: list[str] = []
    links_to: list[int] = []
    created_at: str
    updated_at: str
    backlink_count: int


class NoteWithBacklinks(BaseModel):
    """A note with its backlinks."""
    id: int
    title: str
    content: str
    tags: list[str] = []
    links_to: list[int] = []
    created_at: str
    updated_at: str
    backlinks: list[Note]
    backlink_count: int


class RelatedNote(BaseModel):
    """A related note with relationship info."""
    id: int
    title: str
    content: str
    tags: list[str] = []
    links_to: list[int] = []
    created_at: str
    updated_at: str
    relationship: str
    distance: int

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "zettelkasten.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"notes": {}, "tags": {}, "links": {}, "next_note_id": 1}


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
notes: dict[int, dict] = {int(k): v for k, v in _data.get("notes", {}).items()}
# Convert tag sets back from lists
tags: dict[str, set] = {k: set(v) for k, v in _data.get("tags", {}).items()}
# Convert link sets back from lists
links: dict[int, set] = {int(k): set(v) for k, v in _data.get("links", {}).items()}
_next_note_id = _data.get("next_note_id", 1)


def _save() -> None:
    """Save current state to disk."""
    # Convert sets to lists for JSON serialization
    _save_data({
        "notes": notes,
        "tags": {k: list(v) for k, v in tags.items()},
        "links": {k: list(v) for k, v in links.items()},
        "next_note_id": _next_note_id
    })


def _get_next_note_id() -> int:
    global _next_note_id
    id_ = _next_note_id
    _next_note_id += 1
    return id_


def _extract_wikilinks(content: str) -> list[int]:
    """Extract [[note_id]] references from content."""
    matches = re.findall(r'\[\[(\d+)\]\]', content)
    return [int(m) for m in matches]


def _extract_tags(content: str) -> list[str]:
    """Extract #tags from content."""
    return re.findall(r'#(\w+)', content)


def _update_links(note_id: int, linked_ids: list[int]) -> None:
    """Update the links index for a note."""
    # Remove old links
    if note_id in links:
        for old_linked_id in links[note_id]:
            if old_linked_id in links:
                links[old_linked_id].discard(note_id)

    # Add new links
    new_links = set()
    for linked_id in linked_ids:
        if linked_id in notes:  # Only link to existing notes
            new_links.add(linked_id)
            if linked_id not in links:
                links[linked_id] = set()
            links[linked_id].add(note_id)

    links[note_id] = new_links


def _update_tags(note_id: int, old_tags: list[str], new_tags: list[str]) -> None:
    """Update the tags index for a note."""
    # Remove old tags
    for tag in old_tags:
        if tag in tags:
            tags[tag].discard(note_id)
            if not tags[tag]:
                del tags[tag]

    # Add new tags
    for tag in new_tags:
        if tag not in tags:
            tags[tag] = set()
        tags[tag].add(note_id)


# Note Management
@mcp.tool
def create_note(
    title: str,
    content: str,
    source: Optional[str] = None,
    note_type: str = "permanent"
) -> Note:
    """Create a new Zettelkasten note.

    Args:
        title: Note title (should be a complete thought)
        content: Note content (supports [[note_id]] links and #tags)
        source: Optional source/reference
        note_type: Type of note (fleeting, literature, permanent, structure)

    Returns:
        The created note
    """
    note_id = _get_next_note_id()
    extracted_tags = _extract_tags(content)
    linked_ids = _extract_wikilinks(content)

    note = Note(
        id=note_id,
        title=title,
        content=content,
        tags=extracted_tags,
        links_to=linked_ids,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    notes[note_id] = note.model_dump()

    # Update indices
    _update_links(note_id, linked_ids)
    _update_tags(note_id, [], extracted_tags)
    _save()

    return note


@mcp.tool
def get_note(note_id: int) -> Optional[Note]:
    """Get a note by ID.

    Args:
        note_id: The note ID

    Returns:
        Note details or None
    """
    if note_id in notes:
        return Note(**notes[note_id])
    return None


@mcp.tool
def get_note_with_backlinks(note_id: int) -> Optional[NoteWithBacklinks]:
    """Get a note with its backlinks (notes that link to it).

    Args:
        note_id: The note ID

    Returns:
        Note details with backlinks or None
    """
    if note_id not in notes:
        return None

    note = notes[note_id]
    backlinks = get_backlinks(note_id)
    return NoteWithBacklinks(
        id=note["id"],
        title=note["title"],
        content=note["content"],
        tags=note.get("tags", []),
        links_to=note.get("links_to", []),
        created_at=note["created_at"],
        updated_at=note["updated_at"],
        backlinks=backlinks,
        backlink_count=len(backlinks)
    )


@mcp.tool
def update_note(
    note_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    source: Optional[str] = None,
    note_type: Optional[str] = None
) -> Optional[Note]:
    """Update a note.

    Args:
        note_id: The note ID
        title: New title
        content: New content
        source: New source
        note_type: New note type

    Returns:
        Updated note or None
    """
    if note_id not in notes:
        return None

    note = notes[note_id]
    old_tags = note.get("tags", [])

    if title is not None:
        note["title"] = title
    if content is not None:
        note["content"] = content
        note["tags"] = _extract_tags(content)
        new_linked_ids = _extract_wikilinks(content)
        note["links_to"] = new_linked_ids
        _update_links(note_id, new_linked_ids)
        _update_tags(note_id, old_tags, note["tags"])
    if source is not None:
        note["source"] = source
    if note_type is not None:
        note["note_type"] = note_type

    note["updated_at"] = datetime.now().isoformat()
    _save()
    return Note(**note)


@mcp.tool
def delete_note(note_id: int) -> bool:
    """Delete a note.

    Args:
        note_id: The note ID

    Returns:
        True if deleted, False if not found
    """
    if note_id not in notes:
        return False

    note = notes[note_id]

    # Remove from tags index
    _update_tags(note_id, note.get("tags", []), [])

    # Remove from links index
    if note_id in links:
        for linked_id in links[note_id]:
            if linked_id in notes:
                notes[linked_id]["links_to"] = [
                    lid for lid in notes[linked_id].get("links_to", [])
                    if lid != note_id
                ]
        del links[note_id]

    # Remove from other notes' backlinks
    for other_id, backlinks in links.items():
        backlinks.discard(note_id)

    del notes[note_id]
    _save()
    return True


@mcp.tool
def list_notes(
    note_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> list[Note]:
    """List notes with optional filter.

    Args:
        note_type: Filter by note type
        limit: Maximum notes to return
        offset: Number of notes to skip

    Returns:
        List of notes
    """
    result = list(notes.values())

    if note_type:
        result = [n for n in result if n.get("note_type") == note_type]

    result.sort(key=lambda x: x["updated_at"], reverse=True)
    return [Note(**n) for n in result[offset:offset + limit]]


# Linking
@mcp.tool
def link_notes(from_note_id: int, to_note_id: int) -> Optional[Note]:
    """Create a link between two notes.

    Args:
        from_note_id: Source note ID
        to_note_id: Target note ID

    Returns:
        Updated source note or None
    """
    if from_note_id not in notes or to_note_id not in notes:
        return None

    note = notes[from_note_id]
    if to_note_id not in note.get("links_to", []):
        note["links_to"].append(to_note_id)
        _update_links(from_note_id, note["links_to"])
        note["updated_at"] = datetime.now().isoformat()
        _save()

    return Note(**note)


@mcp.tool
def unlink_notes(from_note_id: int, to_note_id: int) -> Optional[Note]:
    """Remove a link between two notes.

    Args:
        from_note_id: Source note ID
        to_note_id: Target note ID

    Returns:
        Updated source note or None
    """
    if from_note_id not in notes:
        return None

    note = notes[from_note_id]
    if to_note_id in note.get("links_to", []):
        note["links_to"].remove(to_note_id)
        _update_links(from_note_id, note["links_to"])
        note["updated_at"] = datetime.now().isoformat()
        _save()

    return Note(**note)


@mcp.tool
def get_backlinks(note_id: int) -> list[Note]:
    """Get all notes that link to this note.

    Args:
        note_id: The note ID

    Returns:
        List of notes with backlinks
    """
    if note_id not in links:
        return []

    return [Note(**notes[nid]) for nid in links[note_id] if nid in notes]


@mcp.tool
def get_outgoing_links(note_id: int) -> list[Note]:
    """Get all notes this note links to.

    Args:
        note_id: The note ID

    Returns:
        List of linked notes
    """
    if note_id not in notes:
        return []

    return [Note(**notes[nid]) for nid in notes[note_id].get("links_to", []) if nid in notes]


# Search and Discovery
@mcp.tool
def search_notes(query: str) -> list[Note]:
    """Search notes by title or content.

    Args:
        query: Search term

    Returns:
        List of matching notes
    """
    query_lower = query.lower()
    return [
        Note(**n) for n in notes.values()
        if query_lower in n["title"].lower() or query_lower in n["content"].lower()
    ]


@mcp.tool
def get_notes_by_tag(tag: str) -> list[Note]:
    """Get all notes with a specific tag.

    Args:
        tag: The tag to search for (without #)

    Returns:
        List of notes with the tag
    """
    tag_lower = tag.lower()
    if tag_lower not in tags:
        return []

    return [Note(**notes[nid]) for nid in tags[tag_lower] if nid in notes]


@mcp.tool
def get_all_tags() -> list[Tag]:
    """Get all tags with note counts.

    Returns:
        List of tags with counts
    """
    return [
        Tag(tag=tag, count=len(note_ids))
        for tag, note_ids in sorted(tags.items(), key=lambda x: (-len(x[1]), x[0]))
    ]


@mcp.tool
def get_hub_notes(min_backlinks: int = 3) -> list[HubNote]:
    """Get notes that are highly linked (hub notes).

    Args:
        min_backlinks: Minimum number of backlinks to be considered a hub

    Returns:
        List of hub notes
    """
    hubs = []
    for note_id, backlink_ids in links.items():
        if len(backlink_ids) >= min_backlinks and note_id in notes:
            note = notes[note_id]
            hubs.append(HubNote(
                id=note["id"],
                title=note["title"],
                content=note["content"],
                tags=note.get("tags", []),
                links_to=note.get("links_to", []),
                created_at=note["created_at"],
                updated_at=note["updated_at"],
                backlink_count=len(backlink_ids)
            ))

    return sorted(hubs, key=lambda x: x.backlink_count, reverse=True)


@mcp.tool
def get_orphan_notes() -> list[Note]:
    """Get notes with no incoming or outgoing links.

    Returns:
        List of orphan notes
    """
    orphans = []
    for note_id, note in notes.items():
        has_outgoing = bool(note.get("links_to"))
        has_incoming = note_id in links and bool(links[note_id])

        if not has_outgoing and not has_incoming:
            orphans.append(Note(**note))

    return orphans


@mcp.tool
def get_note_path(from_note_id: int, to_note_id: int, max_depth: int = 5) -> Optional[list[int]]:
    """Find a path between two notes using BFS.

    Args:
        from_note_id: Starting note ID
        to_note_id: Target note ID
        max_depth: Maximum search depth

    Returns:
        List of note IDs representing the path, or None if no path found
    """
    if from_note_id not in notes or to_note_id not in notes:
        return None

    if from_note_id == to_note_id:
        return [from_note_id]

    # BFS
    queue = deque([(from_note_id, [from_note_id])])
    visited = {from_note_id}

    while queue:
        current, path = queue.popleft()

        if len(path) > max_depth:
            continue

        # Get neighbors (both outgoing and incoming)
        neighbors = set()
        if current in notes:
            neighbors.update(notes[current].get("links_to", []))
        if current in links:
            neighbors.update(links[current])

        for neighbor in neighbors:
            if neighbor == to_note_id:
                return path + [neighbor]

            if neighbor not in visited and neighbor in notes:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None


@mcp.tool
def get_related_notes(note_id: int, max_distance: int = 2) -> list[RelatedNote]:
    """Get notes related to this note through shared links.

    Args:
        note_id: The note ID
        max_distance: Maximum link distance

    Returns:
        List of related notes with relationship info
    """
    if note_id not in notes:
        return []

    related = {}  # note_id -> relationship info

    # Direct connections
    direct_outgoing = notes[note_id].get("links_to", [])
    direct_incoming = links.get(note_id, set())

    for nid in direct_outgoing:
        if nid in notes:
            related[nid] = {"relationship": "outgoing", "distance": 1}

    for nid in direct_incoming:
        if nid in notes and nid not in related:
            related[nid] = {"relationship": "incoming", "distance": 1}

    # Second-degree connections
    if max_distance >= 2:
        for nid in list(related.keys()):
            if related[nid]["distance"] == 1:
                # Get connections of this connection
                if nid in notes:
                    for nnid in notes[nid].get("links_to", []):
                        if nnid != note_id and nnid in notes and nnid not in related:
                            related[nnid] = {"relationship": "second_degree", "distance": 2}

    return [
        RelatedNote(
            id=notes[nid]["id"],
            title=notes[nid]["title"],
            content=notes[nid]["content"],
            tags=notes[nid].get("tags", []),
            links_to=notes[nid].get("links_to", []),
            created_at=notes[nid]["created_at"],
            updated_at=notes[nid]["updated_at"],
            relationship=info["relationship"],
            distance=info["distance"]
        )
        for nid, info in related.items()
        if nid in notes
    ]


# Statistics
@mcp.tool
def get_zettelkasten_stats() -> dict:
    """Get statistics about the Zettelkasten.

    Returns:
        Statistics about notes, links, and tags
    """
    total_links = sum(len(n.get("links_to", [])) for n in notes.values())

    return {
        "total_notes": len(notes),
        "total_links": total_links,
        "total_tags": len(tags),
        "notes_by_type": {
            note_type: len([n for n in notes.values() if n.get("note_type") == note_type])
            for note_type in ["fleeting", "literature", "permanent", "structure"]
        },
        "hub_count": len(get_hub_notes()),
        "orphan_count": len(get_orphan_notes()),
        "average_links_per_note": round(total_links / len(notes), 2) if notes else 0
    }


# Resources
@mcp.resource("zettelkasten://index")
def get_index_resource() -> str:
    """Resource showing the Zettelkasten index."""
    stats = get_zettelkasten_stats()

    lines = ["# Zettelkasten Index\n"]
    lines.append(f"**Total Notes:** {stats['total_notes']}")
    lines.append(f"**Total Links:** {stats['total_links']}")
    lines.append(f"**Total Tags:** {stats['total_tags']}")
    lines.append(f"**Hub Notes:** {stats['hub_count']}")
    lines.append(f"**Orphan Notes:** {stats['orphan_count']}\n")

    # Notes by type
    lines.append("## Notes by Type")
    for note_type, count in stats['notes_by_type'].items():
        if count > 0:
            lines.append(f"- {note_type.title()}: {count}")
    lines.append("")

    # Recent notes
    recent = sorted(notes.values(), key=lambda x: x["updated_at"], reverse=True)[:5]
    if recent:
        lines.append("## Recent Notes")
        for note in recent:
            links_count = len(note.get("links_to", []))
            lines.append(f"- [[{note['id']}]] {note['title']} ({links_count} links)")

    return "\n".join(lines)


@mcp.resource("zettelkasten://hubs")
def get_hubs_resource() -> str:
    """Resource showing hub notes."""
    hubs = get_hub_notes()

    if not hubs:
        return "# Hub Notes\n\nNo hub notes yet. Hub notes are notes with 3+ backlinks."

    lines = ["# Hub Notes\n"]
    lines.append("These notes are highly connected and serve as central ideas.\n")

    for hub in hubs:
        lines.append(f"## [[{hub.id}]] {hub.title}")
        lines.append(f"- **Backlinks:** {hub.backlink_count}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("zettelkasten://orphans")
def get_orphans_resource() -> str:
    """Resource showing orphan notes."""
    orphans = get_orphan_notes()

    if not orphans:
        return "# Orphan Notes\n\nNo orphan notes! All notes are connected."

    lines = ["# Orphan Notes\n"]
    lines.append("These notes have no connections. Consider linking them to related ideas.\n")

    for note in orphans:
        lines.append(f"- [[{note.id}]] {note.title}")

    return "\n".join(lines)


@mcp.resource("zettelkasten://tags")
def get_tags_resource() -> str:
    """Resource showing all tags."""
    all_tags = get_all_tags()

    if not all_tags:
        return "# Tags\n\nNo tags used yet. Add #tags to your notes!"

    lines = ["# Tags\n"]
    for tag_info in all_tags:
        lines.append(f"- **#{tag_info.tag}** ({tag_info.count} notes)")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()