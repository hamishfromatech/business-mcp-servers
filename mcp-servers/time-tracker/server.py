"""
Time Tracker MCP Server
A FastMCP server for tracking time spent on activities and projects.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json
from fastmcp import FastMCP

mcp = FastMCP(
    name="Time Tracker",
    instructions="A time tracking server for logging time entries, managing projects, and analyzing time usage."
)

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "time.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Restore active timer datetime if exists
            if data.get("active_timer") and data["active_timer"].get("started_at"):
                # Keep as string, it's already ISO format
                pass
            return data
    return {"projects": {}, "time_entries": {}, "active_timer": None, "next_project_id": 1, "next_entry_id": 1}


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
projects: dict[int, dict] = {int(k): v for k, v in _data.get("projects", {}).items()}
time_entries: dict[int, dict] = {int(k): v for k, v in _data.get("time_entries", {}).items()}
active_timer: Optional[dict] = _data.get("active_timer")

_next_project_id = _data.get("next_project_id", 1)
_next_entry_id = _data.get("next_entry_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "projects": projects, "time_entries": time_entries,
        "active_timer": active_timer,
        "next_project_id": _next_project_id, "next_entry_id": _next_entry_id
    })


def _get_next_project_id() -> int:
    global _next_project_id
    id_ = _next_project_id
    _next_project_id += 1
    return id_


def _get_next_entry_id() -> int:
    global _next_entry_id
    id_ = _next_entry_id
    _next_entry_id += 1
    return id_


def _parse_duration(duration_str: str) -> int:
    """Parse duration string to minutes. Formats: '1h30m', '90m', '1.5h'"""
    duration_str = duration_str.lower().strip()
    total_minutes = 0

    # Handle hours
    if 'h' in duration_str:
        parts = duration_str.split('h')
        total_minutes += int(float(parts[0].strip()) * 60)
        if len(parts) > 1 and 'm' in parts[1]:
            total_minutes += int(parts[1].replace('m', '').strip())
    elif 'm' in duration_str:
        total_minutes = int(duration_str.replace('m', '').strip())
    else:
        # Assume minutes if no unit
        try:
            total_minutes = int(duration_str)
        except ValueError:
            try:
                total_minutes = int(float(duration_str) * 60)
            except ValueError:
                pass

    return total_minutes


def _format_duration(minutes: int) -> str:
    """Format minutes as human-readable duration."""
    hours = minutes // 60
    mins = minutes % 60
    if hours and mins:
        return f"{hours}h {mins}m"
    elif hours:
        return f"{hours}h"
    else:
        return f"{mins}m"


# Project Management
@mcp.tool
def create_project(
    name: str,
    client: Optional[str] = None,
    color: Optional[str] = None,
    billable_rate: Optional[float] = None,
    budget_hours: Optional[float] = None
) -> dict:
    """Create a new project.

    Args:
        name: Project name
        client: Client name
        color: Color for UI display
        billable_rate: Hourly rate for billing
        budget_hours: Budgeted hours

    Returns:
        The created project
    """
    project_id = _get_next_project_id()
    project = {
        "id": project_id,
        "name": name,
        "client": client,
        "color": color or "#3498db",
        "billable_rate": billable_rate,
        "budget_hours": budget_hours,
        "active": True,
        "created_at": datetime.now().isoformat()
    }
    projects[project_id] = project
    _save()
    return project


@mcp.tool
def get_project(project_id: int) -> Optional[dict]:
    """Get a project by ID.

    Args:
        project_id: The project ID

    Returns:
        Project details or None
    """
    return projects.get(project_id)


@mcp.tool
def update_project(
    project_id: int,
    name: Optional[str] = None,
    client: Optional[str] = None,
    color: Optional[str] = None,
    billable_rate: Optional[float] = None,
    budget_hours: Optional[float] = None,
    active: Optional[bool] = None
) -> Optional[dict]:
    """Update a project.

    Args:
        project_id: The project ID
        name: New name
        client: New client
        color: New color
        billable_rate: New hourly rate
        budget_hours: New budget
        active: Project active status

    Returns:
        Updated project or None
    """
    if project_id not in projects:
        return None

    project = projects[project_id]
    if name is not None:
        project["name"] = name
    if client is not None:
        project["client"] = client
    if color is not None:
        project["color"] = color
    if billable_rate is not None:
        project["billable_rate"] = billable_rate
    if budget_hours is not None:
        project["budget_hours"] = budget_hours
    if active is not None:
        project["active"] = active
    _save()

    return project


@mcp.tool
def list_projects(active_only: bool = True) -> list[dict]:
    """List all projects.

    Args:
        active_only: Only return active projects

    Returns:
        List of projects
    """
    result = list(projects.values())
    if active_only:
        result = [p for p in result if p.get("active")]
    return result


@mcp.tool
def delete_project(project_id: int) -> bool:
    """Delete a project.

    Args:
        project_id: The project ID

    Returns:
        True if deleted, False if not found
    """
    if project_id in projects:
        del projects[project_id]
        _save()
        return True
    return False


# Time Entry Management
@mcp.tool
def start_timer(
    project_id: Optional[int] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None
) -> dict:
    """Start a new time tracking timer.

    Args:
        project_id: Optional project ID
        description: Description of the activity
        tags: Optional tags for categorization

    Returns:
        The started timer
    """
    global active_timer

    # Stop existing timer if any
    if active_timer:
        stop_timer()

    active_timer = {
        "project_id": project_id,
        "description": description,
        "tags": tags or [],
        "started_at": datetime.now().isoformat()
    }
    _save()

    return active_timer


@mcp.tool
def stop_timer() -> Optional[dict]:
    """Stop the active timer and create a time entry.

    Returns:
        The created time entry or None if no timer active
    """
    global active_timer

    if not active_timer:
        return None

    started = datetime.fromisoformat(active_timer["started_at"])
    ended = datetime.now()
    duration_minutes = int((ended - started).total_seconds() / 60)

    entry = log_time(
        project_id=active_timer.get("project_id"),
        description=active_timer.get("description"),
        duration_minutes=duration_minutes,
        start_time=active_timer["started_at"],
        end_time=ended.isoformat(),
        tags=active_timer.get("tags")
    )

    active_timer = None
    _save()
    return entry


@mcp.tool
def get_active_timer() -> Optional[dict]:
    """Get the currently active timer.

    Returns:
        Active timer or None
    """
    if not active_timer:
        return None

    started = datetime.fromisoformat(active_timer["started_at"])
    elapsed = datetime.now() - started
    elapsed_minutes = int(elapsed.total_seconds() / 60)

    result = active_timer.copy()
    result["elapsed_minutes"] = elapsed_minutes
    result["elapsed_formatted"] = _format_duration(elapsed_minutes)
    return result


@mcp.tool
def log_time(
    duration_minutes: Optional[int] = None,
    duration: Optional[str] = None,
    project_id: Optional[int] = None,
    description: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    date: Optional[str] = None,
    tags: Optional[list[str]] = None,
    billable: bool = True
) -> dict:
    """Log a time entry manually.

    Args:
        duration_minutes: Duration in minutes
        duration: Duration string (e.g., '1h30m', '90m')
        project_id: Optional project ID
        description: Description of the activity
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        date: Date of the entry (YYYY-MM-DD)
        tags: Optional tags
        billable: Whether the time is billable

    Returns:
        The created time entry
    """
    # Parse duration
    if duration and not duration_minutes:
        duration_minutes = _parse_duration(duration)

    if not duration_minutes:
        raise ValueError("Duration must be specified")

    # Determine date
    entry_date = date
    if start_time:
        entry_date = start_time[:10]
    elif not entry_date:
        entry_date = datetime.now().strftime("%Y-%m-%d")

    entry_id = _get_next_entry_id()
    entry = {
        "id": entry_id,
        "project_id": project_id,
        "description": description,
        "duration_minutes": duration_minutes,
        "duration_formatted": _format_duration(duration_minutes),
        "start_time": start_time,
        "end_time": end_time,
        "date": entry_date,
        "tags": tags or [],
        "billable": billable,
        "created_at": datetime.now().isoformat()
    }
    time_entries[entry_id] = entry
    _save()
    return entry


@mcp.tool
def get_time_entry(entry_id: int) -> Optional[dict]:
    """Get a time entry by ID.

    Args:
        entry_id: The entry ID

    Returns:
        Time entry details or None
    """
    return time_entries.get(entry_id)


@mcp.tool
def update_time_entry(
    entry_id: int,
    project_id: Optional[int] = None,
    description: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    date: Optional[str] = None,
    tags: Optional[list[str]] = None,
    billable: Optional[bool] = None
) -> Optional[dict]:
    """Update a time entry.

    Args:
        entry_id: The entry ID
        project_id: New project
        description: New description
        duration_minutes: New duration
        date: New date
        tags: New tags
        billable: New billable status

    Returns:
        Updated entry or None
    """
    if entry_id not in time_entries:
        return None

    entry = time_entries[entry_id]
    if project_id is not None:
        entry["project_id"] = project_id
    if description is not None:
        entry["description"] = description
    if duration_minutes is not None:
        entry["duration_minutes"] = duration_minutes
        entry["duration_formatted"] = _format_duration(duration_minutes)
    if date is not None:
        entry["date"] = date
    if tags is not None:
        entry["tags"] = tags
    if billable is not None:
        entry["billable"] = billable
    _save()

    return entry


@mcp.tool
def delete_time_entry(entry_id: int) -> bool:
    """Delete a time entry.

    Args:
        entry_id: The entry ID

    Returns:
        True if deleted, False if not found
    """
    if entry_id in time_entries:
        del time_entries[entry_id]
        _save()
        return True
    return False


@mcp.tool
def list_time_entries(
    project_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """List time entries with filters.

    Args:
        project_id: Filter by project
        start_date: Start of date range
        end_date: End of date range
        limit: Maximum number of entries

    Returns:
        List of time entries
    """
    result = list(time_entries.values())

    if project_id is not None:
        result = [e for e in result if e.get("project_id") == project_id]
    if start_date:
        result = [e for e in result if e["date"] >= start_date]
    if end_date:
        result = [e for e in result if e["date"] <= end_date]

    result.sort(key=lambda x: x["date"], reverse=True)
    return result[:limit]


# Reporting
@mcp.tool
def get_time_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    project_id: Optional[int] = None
) -> dict:
    """Get a summary of time tracked.

    Args:
        start_date: Start of date range
        end_date: End of date range
        project_id: Filter by project

    Returns:
        Time summary with totals by project
    """
    result = list(time_entries.values())

    if project_id is not None:
        result = [e for e in result if e.get("project_id") == project_id]
    if start_date:
        result = [e for e in result if e["date"] >= start_date]
    if end_date:
        result = [e for e in result if e["date"] <= end_date]

    total_minutes = sum(e["duration_minutes"] for e in result)
    billable_minutes = sum(e["duration_minutes"] for e in result if e.get("billable"))

    # By project
    by_project: dict[int, dict] = {}
    for entry in result:
        pid = entry.get("project_id")
        if pid is None:
            pid = 0  # Uncategorized

        if pid not in by_project:
            project = projects.get(pid, {"name": "Uncategorized"})
            by_project[pid] = {
                "project_name": project.get("name", "Uncategorized"),
                "minutes": 0,
                "entries": 0
            }

        by_project[pid]["minutes"] += entry["duration_minutes"]
        by_project[pid]["entries"] += 1

    # Calculate earnings
    total_earnings = 0
    for pid, data in by_project.items():
        project = projects.get(pid, {})
        rate = project.get("billable_rate", 0)
        if rate:
            hours = data["minutes"] / 60
            data["earnings"] = round(hours * rate, 2)
            total_earnings += data["earnings"]

    return {
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "total_formatted": _format_duration(total_minutes),
        "billable_minutes": billable_minutes,
        "billable_hours": round(billable_minutes / 60, 2),
        "total_entries": len(result),
        "by_project": by_project,
        "total_earnings": total_earnings
    }


@mcp.tool
def get_daily_summary(date: Optional[str] = None) -> dict:
    """Get time summary for a specific day.

    Args:
        date: Date to summarize (YYYY-MM-DD), defaults to today

    Returns:
        Daily time summary
    """
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    entries = [e for e in time_entries.values() if e["date"] == target_date]

    total_minutes = sum(e["duration_minutes"] for e in entries)

    by_project: dict[int, dict] = {}
    for entry in entries:
        pid = entry.get("project_id", 0)
        if pid not in by_project:
            project = projects.get(pid, {"name": "Uncategorized"})
            by_project[pid] = {
                "project_name": project.get("name", "Uncategorized"),
                "minutes": 0,
                "entries": []
            }

        by_project[pid]["minutes"] += entry["duration_minutes"]
        by_project[pid]["entries"].append(entry)

    return {
        "date": target_date,
        "total_minutes": total_minutes,
        "total_formatted": _format_duration(total_minutes),
        "entry_count": len(entries),
        "by_project": by_project
    }


@mcp.tool
def get_weekly_summary(start_date: Optional[str] = None) -> dict:
    """Get time summary for a week.

    Args:
        start_date: Start of week (YYYY-MM-DD), defaults to this Monday

    Returns:
        Weekly time summary
    """
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        today = datetime.now()
        start = today - timedelta(days=today.weekday())

    days = []
    total_minutes = 0

    for i in range(7):
        day = start + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_entries = [e for e in time_entries.values() if e["date"] == day_str]
        day_minutes = sum(e["duration_minutes"] for e in day_entries)
        total_minutes += day_minutes

        days.append({
            "date": day_str,
            "day_name": day.strftime("%A"),
            "minutes": day_minutes,
            "formatted": _format_duration(day_minutes),
            "entries": len(day_entries)
        })

    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": (start + timedelta(days=6)).strftime("%Y-%m-%d"),
        "total_minutes": total_minutes,
        "total_formatted": _format_duration(total_minutes),
        "days": days
    }


# Resources
@mcp.resource("time://today")
def get_today_resource() -> str:
    """Resource showing today's time tracking."""
    summary = get_daily_summary()
    timer = get_active_timer()

    lines = [f"# Time Tracking - {summary['date']}\n"]

    if timer:
        lines.append(f"**Active Timer:** {timer.get('description', 'No description')}")
        lines.append(f"- Elapsed: {timer['elapsed_formatted']}")
        if timer.get('project_id'):
            project = projects.get(timer['project_id'], {})
            lines.append(f"- Project: {project.get('name', 'Unknown')}")
        lines.append("")

    lines.append(f"**Total Today:** {summary['total_formatted']}")
    lines.append(f"**Entries:** {summary['entry_count']}\n")

    if summary['by_project']:
        lines.append("## By Project")
        for pid, data in summary['by_project'].items():
            lines.append(f"- {data['project_name']}: {data['minutes']}m ({len(data['entries'])} entries)")

    return "\n".join(lines)


@mcp.resource("time://week")
def get_week_resource() -> str:
    """Resource showing this week's time tracking."""
    summary = get_weekly_summary()

    lines = ["# Weekly Time Summary\n"]
    lines.append(f"**Period:** {summary['start_date']} to {summary['end_date']}")
    lines.append(f"**Total:** {summary['total_formatted']}\n")

    lines.append("## Daily Breakdown")
    for day in summary['days']:
        lines.append(f"- **{day['day_name']}** ({day['date']}): {day['formatted']}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()