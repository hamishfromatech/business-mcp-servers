"""
Notes & Ideas MCP Server
A FastMCP server for capturing and organizing notes and ideas.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import re
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Notes & Ideas",
    instructions="A notes server for capturing ideas, quick notes, and organizing thoughts with tags and folders."
)


class Folder(BaseModel):
    """A folder for organizing notes."""
    id: int
    name: str
    parent_id: Optional[int] = None
    color: str
    created_at: str


class Note(BaseModel):
    """A note or idea."""
    id: int
    title: str
    content: str
    folder_id: Optional[int] = None
    tags: list[str] = []
    is_idea: bool = False
    priority: Optional[str] = None
    pinned: bool = False
    archived: bool = False
    created_at: str
    updated_at: str

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "notes.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"notes": {}, "folders": {}, "next_note_id": 1, "next_folder_id": 1}


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
notes: dict[int, dict] = {int(k): v for k, v in _data.get("notes", {}).items()}
folders: dict[int, dict] = {int(k): v for k, v in _data.get("folders", {}).items()}
_next_note_id = _data.get("next_note_id", 1)
_next_folder_id = _data.get("next_folder_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "notes": notes, "folders": folders,
        "next_note_id": _next_note_id, "next_folder_id": _next_folder_id
    })


def _get_next_note_id() -> int:
    global _next_note_id
    id_ = _next_note_id
    _next_note_id += 1
    return id_


def _get_next_folder_id() -> int:
    global _next_folder_id
    id_ = _next_folder_id
    _next_folder_id += 1
    return id_


def _extract_tags(content: str) -> list[str]:
    """Extract #tags from content."""
    return re.findall(r'#(\w+)', content)


# Folder Management
@mcp.tool
def create_folder(name: str, parent_id: Optional[int] = None, color: Optional[str] = None) -> Folder:
    """Create a folder for organizing notes.

    Args:
        name: Folder name
        parent_id: Optional parent folder ID for nesting
        color: Optional color for UI display

    Returns:
        The created folder
    """
    folder_id = _get_next_folder_id()
    folder = Folder(
        id=folder_id,
        name=name,
        parent_id=parent_id,
        color=color or "#3498db",
        created_at=datetime.now().isoformat()
    )
    folders[folder_id] = folder.model_dump()
    _save()
    return folder


@mcp.tool
def list_folders(parent_id: Optional[int] = None) -> list[Folder]:
    """List folders, optionally filtered by parent.

    Args:
        parent_id: Optional parent folder ID to list subfolders

    Returns:
        List of folders
    """
    if parent_id is not None:
        return [Folder(**f) for f in folders.values() if f.get("parent_id") == parent_id]
    return [Folder(**f) for f in folders.values()]


@mcp.tool
def delete_folder(folder_id: int, move_notes_to: Optional[int] = None) -> bool:
    """Delete a folder.

    Args:
        folder_id: The folder ID
        move_notes_to: Optional folder ID to move notes to

    Returns:
        True if deleted, False if not found
    """
    if folder_id not in folders:
        return False

    # Move or unfile notes in this folder
    for note in notes.values():
        if note.get("folder_id") == folder_id:
            note["folder_id"] = move_notes_to

    del folders[folder_id]
    _save()
    return True


# Note Management
@mcp.tool
def create_note(
    title: str,
    content: str,
    folder_id: Optional[int] = None,
    tags: Optional[list[str]] = None,
    is_idea: bool = False,
    priority: Optional[str] = None
) -> Note:
    """Create a new note or idea.

    Args:
        title: Note title
        content: Note content (supports markdown and #tags)
        folder_id: Optional folder ID
        tags: Optional list of tags (extracted from content if not provided)
        is_idea: Mark as an idea instead of a regular note
        priority: Optional priority (low, medium, high)

    Returns:
        The created note
    """
    note_id = _get_next_note_id()
    extracted_tags = tags or _extract_tags(content)

    note = Note(
        id=note_id,
        title=title,
        content=content,
        folder_id=folder_id,
        tags=extracted_tags,
        is_idea=is_idea,
        priority=priority,
        pinned=False,
        archived=False,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    notes[note_id] = note.model_dump()
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
def update_note(
    note_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    folder_id: Optional[int] = None,
    tags: Optional[list[str]] = None,
    is_idea: Optional[bool] = None,
    priority: Optional[str] = None,
    pinned: Optional[bool] = None,
    archived: Optional[bool] = None
) -> Optional[Note]:
    """Update a note.

    Args:
        note_id: The note ID
        title: New title
        content: New content
        folder_id: New folder
        tags: New tags
        is_idea: Mark as idea
        priority: New priority
        pinned: Pin/unpin
        archived: Archive/unarchive

    Returns:
        Updated note or None
    """
    if note_id not in notes:
        return None

    note = notes[note_id]
    if title is not None:
        note["title"] = title
    if content is not None:
        note["content"] = content
        note["tags"] = tags or _extract_tags(content)
    if folder_id is not None:
        note["folder_id"] = folder_id
    if tags is not None:
        note["tags"] = tags
    if is_idea is not None:
        note["is_idea"] = is_idea
    if priority is not None:
        note["priority"] = priority
    if pinned is not None:
        note["pinned"] = pinned
    if archived is not None:
        note["archived"] = archived

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
    if note_id in notes:
        del notes[note_id]
        _save()
        return True
    return False


@mcp.tool
def quick_idea(content: str, priority: Optional[str] = None) -> Note:
    """Quickly capture an idea.

    Args:
        content: The idea content
        priority: Optional priority

    Returns:
        The created idea note
    """
    return create_note(
        title=content[:50] + ("..." if len(content) > 50 else ""),
        content=content,
        is_idea=True,
        priority=priority
    )


@mcp.tool
def quick_note(content: str, folder_id: Optional[int] = None) -> Note:
    """Quickly create a note.

    Args:
        content: The note content
        folder_id: Optional folder ID

    Returns:
        The created note
    """
    return create_note(
        title=content[:50] + ("..." if len(content) > 50 else ""),
        content=content,
        folder_id=folder_id
    )


# Search and Filter
@mcp.tool
def search_notes(
    query: str,
    folder_id: Optional[int] = None,
    tags: Optional[list[str]] = None,
    is_idea: Optional[bool] = None,
    include_archived: bool = False
) -> list[Note]:
    """Search notes by content, title, or tags.

    Args:
        query: Search term
        folder_id: Filter by folder
        tags: Filter by tags
        is_idea: Filter by idea status
        include_archived: Include archived notes

    Returns:
        List of matching notes
    """
    query_lower = query.lower()
    result = []

    for note in notes.values():
        # Skip archived unless included
        if note.get("archived") and not include_archived:
            continue

        # Filter by folder
        if folder_id is not None and note.get("folder_id") != folder_id:
            continue

        # Filter by idea status
        if is_idea is not None and note.get("is_idea") != is_idea:
            continue

        # Filter by tags
        if tags:
            note_tags_lower = [t.lower() for t in note.get("tags", [])]
            if not any(t.lower() in note_tags_lower for t in tags):
                continue

        # Search in title and content
        if (query_lower in note["title"].lower() or
            query_lower in note["content"].lower()):
            result.append(Note(**note))

    return result


@mcp.tool
def get_notes_by_folder(folder_id: int, include_archived: bool = False) -> list[Note]:
    """Get all notes in a folder.

    Args:
        folder_id: The folder ID
        include_archived: Include archived notes

    Returns:
        List of notes in the folder
    """
    return [
        Note(**n) for n in notes.values()
        if n.get("folder_id") == folder_id and (include_archived or not n.get("archived"))
    ]


@mcp.tool
def get_notes_by_tag(tag: str, include_archived: bool = False) -> list[Note]:
    """Get all notes with a specific tag.

    Args:
        tag: The tag to search for
        include_archived: Include archived notes

    Returns:
        List of notes with the tag
    """
    tag_lower = tag.lower()
    return [
        Note(**n) for n in notes.values()
        if tag_lower in [t.lower() for t in n.get("tags", [])]
        and (include_archived or not n.get("archived"))
    ]


@mcp.tool
def get_all_tags() -> list[dict]:
    """Get all tags with usage counts.

    Returns:
        List of tags with counts
    """
    tag_counts: dict[str, int] = {}
    for note in notes.values():
        for tag in note.get("tags", []):
            tag_lower = tag.lower()
            tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

    return [
        {"tag": tag, "count": count}
        for tag, count in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
    ]


@mcp.tool
def get_pinned_notes() -> list[Note]:
    """Get all pinned notes.

    Returns:
        List of pinned notes
    """
    return [Note(**n) for n in notes.values() if n.get("pinned") and not n.get("archived")]


@mcp.tool
def get_ideas(priority: Optional[str] = None) -> list[Note]:
    """Get all ideas, optionally filtered by priority.

    Args:
        priority: Filter by priority (low, medium, high)

    Returns:
        List of ideas
    """
    result = [Note(**n) for n in notes.values() if n.get("is_idea") and not n.get("archived")]

    if priority:
        result = [n for n in result if n.priority == priority]

    return result


@mcp.tool
def list_notes(
    folder_id: Optional[int] = None,
    include_archived: bool = False,
    limit: int = 50
) -> list[Note]:
    """List notes with optional filters.

    Args:
        folder_id: Filter by folder
        include_archived: Include archived notes
        limit: Maximum number of notes

    Returns:
        List of notes
    """
    result = list(notes.values())

    if not include_archived:
        result = [n for n in result if not n.get("archived")]
    if folder_id is not None:
        result = [n for n in result if n.get("folder_id") == folder_id]

    # Sort: pinned first, then by updated_at
    result.sort(key=lambda x: (not x.get("pinned", False), x["updated_at"]), reverse=True)
    return [Note(**n) for n in result[:limit]]


# Resources
@mcp.resource("notes://recent")
def get_recent_notes_resource() -> str:
    """Resource showing recent notes."""
    recent = list_notes(limit=10)

    if not recent:
        return "# Recent Notes\n\nNo notes yet. Create your first note!"

    lines = ["# Recent Notes\n"]
    for note in recent:
        icon = "💡" if note.get("is_idea") else "📝"
        pin = " [PINNED]" if note.get("pinned") else ""
        lines.append(f"## {icon} {note['title']}{pin}")
        lines.append(f"*Updated: {note['updated_at'][:10]}*")
        preview = note["content"][:100]
        if len(note["content"]) > 100:
            preview += "..."
        lines.append(f"{preview}\n")

    return "\n".join(lines)


@mcp.resource("notes://ideas")
def get_ideas_resource() -> str:
    """Resource showing all ideas."""
    ideas = get_ideas()

    if not ideas:
        return "# Ideas\n\nNo ideas captured yet. Use quick_idea to capture one!"

    lines = ["# Ideas\n"]

    # Group by priority
    high = [i for i in ideas if i.get("priority") == "high"]
    medium = [i for i in ideas if i.get("priority") == "medium"]
    low = [i for i in ideas if i.get("priority") == "low" or not i.get("priority")]

    if high:
        lines.append("## High Priority")
        for idea in high:
            lines.append(f"- {idea['title']}")
        lines.append("")

    if medium:
        lines.append("## Medium Priority")
        for idea in medium:
            lines.append(f"- {idea['title']}")
        lines.append("")

    if low:
        lines.append("## Other Ideas")
        for idea in low:
            lines.append(f"- {idea['title']}")

    return "\n".join(lines)


@mcp.resource("notes://tags")
def get_tags_resource() -> str:
    """Resource showing all tags."""
    all_tags = get_all_tags()

    if not all_tags:
        return "# Tags\n\nNo tags used yet. Add #tags to your notes!"

    lines = ["# Tags\n"]
    for tag_info in all_tags:
        lines.append(f"- **#{tag_info['tag']}** ({tag_info['count']} notes)")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()