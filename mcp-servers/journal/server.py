"""
Journal MCP Server
A FastMCP server for managing personal journal entries and reflections.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import re
from fastmcp import FastMCP

mcp = FastMCP(
    name="Journal",
    instructions="A personal journal server for creating, organizing, and reflecting on daily entries."
)

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "journal.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"entries": {}, "tags": {}, "next_entry_id": 1}


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
entries: dict[int, dict] = {int(k): v for k, v in _data.get("entries", {}).items()}
tags: dict[str, int] = _data.get("tags", {})
_next_entry_id = _data.get("next_entry_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "entries": entries,
        "tags": tags,
        "next_entry_id": _next_entry_id
    })


def _get_next_entry_id() -> int:
    global _next_entry_id
    id_ = _next_entry_id
    _next_entry_id += 1
    return id_


def _extract_tags(content: str) -> list[str]:
    """Extract #tags from content."""
    return re.findall(r'#(\w+)', content)


def _update_tag_counts(old_tags: list[str], new_tags: list[str]) -> None:
    """Update tag counts when entry is modified."""
    for tag in old_tags:
        if tag in tags:
            tags[tag] -= 1
            if tags[tag] <= 0:
                del tags[tag]
    for tag in new_tags:
        tags[tag] = tags.get(tag, 0) + 1


# Entry Management
@mcp.tool
def create_entry(
    content: str,
    title: Optional[str] = None,
    mood: Optional[str] = None,
    date: Optional[str] = None
) -> dict:
    """Create a new journal entry.

    Args:
        content: The journal entry content (supports #tags)
        title: Optional title for the entry
        mood: Optional mood indicator (happy, sad, neutral, anxious, etc.)
        date: Optional date for the entry (YYYY-MM-DD), defaults to today

    Returns:
        The created entry
    """
    entry_id = _get_next_entry_id()
    extracted_tags = _extract_tags(content)

    entry = {
        "id": entry_id,
        "title": title or datetime.now().strftime("%A, %B %d, %Y"),
        "content": content,
        "mood": mood,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "tags": extracted_tags,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    entries[entry_id] = entry

    # Update tag counts
    for tag in extracted_tags:
        tags[tag] = tags.get(tag, 0) + 1

    _save()
    return entry


@mcp.tool
def get_entry(entry_id: int) -> Optional[dict]:
    """Get a journal entry by ID.

    Args:
        entry_id: The entry ID

    Returns:
        Entry details or None
    """
    return entries.get(entry_id)


@mcp.tool
def get_entry_by_date(date: str) -> Optional[dict]:
    """Get the journal entry for a specific date.

    Args:
        date: The date (YYYY-MM-DD)

    Returns:
        Entry for that date or None
    """
    for entry in entries.values():
        if entry["date"] == date:
            return entry
    return None


@mcp.tool
def update_entry(
    entry_id: int,
    content: Optional[str] = None,
    title: Optional[str] = None,
    mood: Optional[str] = None
) -> Optional[dict]:
    """Update a journal entry.

    Args:
        entry_id: The entry ID
        content: New content
        title: New title
        mood: New mood

    Returns:
        Updated entry or None
    """
    if entry_id not in entries:
        return None

    entry = entries[entry_id]
    old_tags = entry.get("tags", [])

    if content is not None:
        entry["content"] = content
        entry["tags"] = _extract_tags(content)
    if title is not None:
        entry["title"] = title
    if mood is not None:
        entry["mood"] = mood

    entry["updated_at"] = datetime.now().isoformat()

    # Update tag counts
    _update_tag_counts(old_tags, entry["tags"])
    _save()

    return entry


@mcp.tool
def delete_entry(entry_id: int) -> bool:
    """Delete a journal entry.

    Args:
        entry_id: The entry ID

    Returns:
        True if deleted, False if not found
    """
    if entry_id not in entries:
        return False

    entry = entries[entry_id]
    _update_tag_counts(entry.get("tags", []), [])
    del entries[entry_id]
    _save()
    return True


@mcp.tool
def list_entries(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """List journal entries with optional date filter.

    Args:
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        limit: Maximum number of entries to return

    Returns:
        List of entries
    """
    result = list(entries.values())

    if start_date:
        result = [e for e in result if e["date"] >= start_date]
    if end_date:
        result = [e for e in result if e["date"] <= end_date]

    result.sort(key=lambda x: x["date"], reverse=True)
    return result[:limit]


@mcp.tool
def search_entries(query: str) -> list[dict]:
    """Search journal entries by content or title.

    Args:
        query: Search term

    Returns:
        List of matching entries
    """
    query_lower = query.lower()
    return [
        e for e in entries.values()
        if (query_lower in e["content"].lower() or
            query_lower in e.get("title", "").lower())
    ]


@mcp.tool
def get_entries_by_tag(tag: str) -> list[dict]:
    """Get all entries with a specific tag.

    Args:
        tag: The tag to search for (without #)

    Returns:
        List of entries with the tag
    """
    tag_lower = tag.lower()
    return [
        e for e in entries.values()
        if tag_lower in [t.lower() for t in e.get("tags", [])]
    ]


@mcp.tool
def get_entries_by_mood(mood: str) -> list[dict]:
    """Get all entries with a specific mood.

    Args:
        mood: The mood to search for

    Returns:
        List of entries with the mood
    """
    mood_lower = mood.lower()
    return [
        e for e in entries.values()
        if e.get("mood", "").lower() == mood_lower
    ]


@mcp.tool
def get_all_tags() -> list[dict]:
    """Get all tags with their usage counts.

    Returns:
        List of tags with counts
    """
    return [
        {"tag": tag, "count": count}
        for tag, count in sorted(tags.items(), key=lambda x: (-x[1], x[0]))
    ]


# Analytics
@mcp.tool
def get_mood_summary(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """Get a summary of moods over a period.

    Args:
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        Mood distribution summary
    """
    result = list(entries.values())

    if start_date:
        result = [e for e in result if e["date"] >= start_date]
    if end_date:
        result = [e for e in result if e["date"] <= end_date]

    mood_counts: dict[str, int] = {}
    for entry in result:
        mood = entry.get("mood")
        if mood:
            mood_counts[mood] = mood_counts.get(mood, 0) + 1

    return {
        "total_entries": len(result),
        "mood_distribution": mood_counts,
        "entries_with_mood": sum(mood_counts.values())
    }


@mcp.tool
def get_entry_calendar(year: int, month: int) -> dict:
    """Get a calendar view of entries for a month.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        Calendar with entries per day
    """
    from calendar import monthrange

    days_in_month = monthrange(year, month)[1]
    calendar = {}

    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        day_entries = [e for e in entries.values() if e["date"] == date_str]
        calendar[day] = {
            "date": date_str,
            "entry_count": len(day_entries),
            "moods": [e.get("mood") for e in day_entries if e.get("mood")]
        }

    return {
        "year": year,
        "month": month,
        "calendar": calendar,
        "total_entries": sum(d["entry_count"] for d in calendar.values())
    }


@mcp.tool
def get_writing_stats() -> dict:
    """Get writing statistics.

    Returns:
        Statistics about journal entries
    """
    if not entries:
        return {
            "total_entries": 0,
            "total_words": 0,
            "average_words": 0,
            "total_tags": 0,
            "entries_this_month": 0
        }

    total_words = sum(len(e["content"].split()) for e in entries.values())
    this_month = datetime.now().strftime("%Y-%m")
    entries_this_month = len([e for e in entries.values() if e["date"].startswith(this_month)])

    return {
        "total_entries": len(entries),
        "total_words": total_words,
        "average_words": total_words // len(entries),
        "total_tags": len(tags),
        "entries_this_month": entries_this_month
    }


# Resources
@mcp.resource("journal://today")
def get_today_entry_resource() -> str:
    """Resource showing today's journal entry."""
    today = datetime.now().strftime("%Y-%m-%d")
    entry = get_entry_by_date(today)

    if not entry:
        return f"# Journal Entry - {today}\n\nNo entry yet for today. Start writing!"

    lines = [f"# {entry['title']}\n"]
    lines.append(f"**Date:** {entry['date']}")
    if entry.get("mood"):
        lines.append(f"**Mood:** {entry['mood']}")
    lines.append(f"\n{entry['content']}\n")
    if entry.get("tags"):
        lines.append(f"\nTags: {' '.join(f'#{t}' for t in entry['tags'])}")

    return "\n".join(lines)


@mcp.resource("journal://recent")
def get_recent_entries_resource() -> str:
    """Resource showing recent journal entries."""
    recent = list_entries(limit=7)

    if not recent:
        return "# Recent Journal Entries\n\nNo entries yet. Start journaling!"

    lines = ["# Recent Journal Entries\n"]
    for entry in recent:
        mood_str = f" [{entry['mood']}]" if entry.get("mood") else ""
        lines.append(f"## {entry['date']}{mood_str}")
        lines.append(f"**{entry['title']}**")
        # Show first 150 chars of content
        preview = entry["content"][:150]
        if len(entry["content"]) > 150:
            preview += "..."
        lines.append(f"{preview}\n")

    return "\n".join(lines)


@mcp.resource("journal://tags")
def get_tags_resource() -> str:
    """Resource showing all tags."""
    all_tags = get_all_tags()

    if not all_tags:
        return "# Tags\n\nNo tags used yet. Add #tags to your entries!"

    lines = ["# Tags\n"]
    for tag_info in all_tags:
        lines.append(f"- **#{tag_info['tag']}** ({tag_info['count']} entries)")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()