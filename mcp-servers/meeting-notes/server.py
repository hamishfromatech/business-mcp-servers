"""
Meeting Notes MCP Server
A FastMCP server for managing meeting notes, agendas, and action items.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
from enum import Enum
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Meeting Notes",
    instructions="A meeting notes server for organizing meetings, agendas, notes, and action items."
)


class MeetingStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ActionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Attendee(BaseModel):
    """A meeting attendee."""
    id: int
    name: str
    email: Optional[str] = None
    role: Optional[str] = None
    created_at: str


class Meeting(BaseModel):
    """A meeting."""
    id: int
    title: str
    scheduled_at: str
    duration_minutes: int = 60
    location: Optional[str] = None
    description: Optional[str] = None
    status: str
    attendee_ids: list[int] = []
    agenda: list = []
    notes: str = ""
    created_at: str
    updated_at: str


class ActionItem(BaseModel):
    """An action item from a meeting."""
    id: int
    meeting_id: int
    description: str
    assignee_id: Optional[int] = None
    due_date: Optional[str] = None
    priority: str
    status: str
    created_at: str
    updated_at: str

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "meetings.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "meetings": {}, "action_items": {}, "attendees": {},
        "next_meeting_id": 1, "next_action_id": 1, "next_attendee_id": 1
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
meetings: dict[int, dict] = {int(k): v for k, v in _data.get("meetings", {}).items()}
action_items: dict[int, dict] = {int(k): v for k, v in _data.get("action_items", {}).items()}
attendees: dict[int, dict] = {int(k): v for k, v in _data.get("attendees", {}).items()}

_next_meeting_id = _data.get("next_meeting_id", 1)
_next_action_id = _data.get("next_action_id", 1)
_next_attendee_id = _data.get("next_attendee_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "meetings": meetings, "action_items": action_items, "attendees": attendees,
        "next_meeting_id": _next_meeting_id, "next_action_id": _next_action_id,
        "next_attendee_id": _next_attendee_id
    })


def _get_next_meeting_id() -> int:
    global _next_meeting_id
    id_ = _next_meeting_id
    _next_meeting_id += 1
    return id_


def _get_next_action_id() -> int:
    global _next_action_id
    id_ = _next_action_id
    _next_action_id += 1
    return id_


def _get_next_attendee_id() -> int:
    global _next_attendee_id
    id_ = _next_attendee_id
    _next_attendee_id += 1
    return id_


# Attendee Management
@mcp.tool
def create_attendee(name: str, email: Optional[str] = None, role: Optional[str] = None) -> Attendee:
    """Create an attendee profile.

    Args:
        name: Attendee name
        email: Attendee email
        role: Attendee role/title

    Returns:
        The created attendee
    """
    attendee_id = _get_next_attendee_id()
    attendee = Attendee(
        id=attendee_id,
        name=name,
        email=email,
        role=role,
        created_at=datetime.now().isoformat()
    )
    attendees[attendee_id] = attendee.model_dump()
    _save()
    return attendee


@mcp.tool
def list_attendees() -> list[Attendee]:
    """List all attendees.

    Returns:
        List of attendees
    """
    return [Attendee(**a) for a in attendees.values()]


# Meeting Management
@mcp.tool
def create_meeting(
    title: str,
    scheduled_at: str,
    duration_minutes: int = 60,
    location: Optional[str] = None,
    description: Optional[str] = None,
    attendee_ids: Optional[list[int]] = None
) -> Meeting:
    """Create a new meeting.

    Args:
        title: Meeting title
        scheduled_at: Scheduled date and time (ISO format)
        duration_minutes: Meeting duration in minutes
        location: Meeting location or link
        description: Meeting description
        attendee_ids: List of attendee IDs

    Returns:
        The created meeting
    """
    meeting_id = _get_next_meeting_id()
    meeting = Meeting(
        id=meeting_id,
        title=title,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        location=location,
        description=description,
        status=MeetingStatus.SCHEDULED.value,
        attendee_ids=attendee_ids or [],
        agenda=[],
        notes="",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    meetings[meeting_id] = meeting.model_dump()
    _save()
    return meeting


@mcp.tool
def get_meeting(meeting_id: int) -> Optional[Meeting]:
    """Get a meeting by ID.

    Args:
        meeting_id: The meeting ID

    Returns:
        Meeting details or None
    """
    if meeting_id in meetings:
        return Meeting(**meetings[meeting_id])
    return None


@mcp.tool
def update_meeting(
    meeting_id: int,
    title: Optional[str] = None,
    scheduled_at: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None
) -> Optional[Meeting]:
    """Update a meeting.

    Args:
        meeting_id: The meeting ID
        title: New title
        scheduled_at: New scheduled time
        duration_minutes: New duration
        location: New location
        description: New description
        status: New status

    Returns:
        Updated meeting or None
    """
    if meeting_id not in meetings:
        return None

    meeting = meetings[meeting_id]
    if title is not None:
        meeting["title"] = title
    if scheduled_at is not None:
        meeting["scheduled_at"] = scheduled_at
    if duration_minutes is not None:
        meeting["duration_minutes"] = duration_minutes
    if location is not None:
        meeting["location"] = location
    if description is not None:
        meeting["description"] = description
    if status is not None:
        valid_statuses = [s.value for s in MeetingStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        meeting["status"] = status

    meeting["updated_at"] = datetime.now().isoformat()
    _save()
    return Meeting(**meeting)


@mcp.tool
def delete_meeting(meeting_id: int) -> bool:
    """Delete a meeting.

    Args:
        meeting_id: The meeting ID

    Returns:
        True if deleted, False if not found
    """
    if meeting_id in meetings:
        del meetings[meeting_id]
        # Also delete associated action items
        actions_to_delete = [aid for aid, a in action_items.items() if a.get("meeting_id") == meeting_id]
        for aid in actions_to_delete:
            del action_items[aid]
        _save()
        return True
    return False


@mcp.tool
def add_attendee_to_meeting(meeting_id: int, attendee_id: int) -> Optional[Meeting]:
    """Add an attendee to a meeting.

    Args:
        meeting_id: The meeting ID
        attendee_id: The attendee ID

    Returns:
        Updated meeting or None
    """
    if meeting_id not in meetings:
        return None
    if attendee_id not in attendees:
        raise ValueError(f"Attendee {attendee_id} not found")

    meeting = meetings[meeting_id]
    if attendee_id not in meeting["attendee_ids"]:
        meeting["attendee_ids"].append(attendee_id)
        meeting["updated_at"] = datetime.now().isoformat()
        _save()

    return Meeting(**meeting)


@mcp.tool
def remove_attendee_from_meeting(meeting_id: int, attendee_id: int) -> Optional[Meeting]:
    """Remove an attendee from a meeting.

    Args:
        meeting_id: The meeting ID
        attendee_id: The attendee ID

    Returns:
        Updated meeting or None
    """
    if meeting_id not in meetings:
        return None

    meeting = meetings[meeting_id]
    if attendee_id in meeting["attendee_ids"]:
        meeting["attendee_ids"].remove(attendee_id)
        meeting["updated_at"] = datetime.now().isoformat()
        _save()

    return Meeting(**meeting)


# Agenda Management
@mcp.tool
def set_agenda(meeting_id: int, agenda_items: list[str]) -> Optional[Meeting]:
    """Set the agenda for a meeting.

    Args:
        meeting_id: The meeting ID
        agenda_items: List of agenda items

    Returns:
        Updated meeting or None
    """
    if meeting_id not in meetings:
        return None

    meeting = meetings[meeting_id]
    meeting["agenda"] = [{"item": item, "completed": False} for item in agenda_items]
    meeting["updated_at"] = datetime.now().isoformat()
    _save()
    return Meeting(**meeting)


@mcp.tool
def add_agenda_item(meeting_id: int, item: str) -> Optional[Meeting]:
    """Add an agenda item to a meeting.

    Args:
        meeting_id: The meeting ID
        item: The agenda item

    Returns:
        Updated meeting or None
    """
    if meeting_id not in meetings:
        return None

    meeting = meetings[meeting_id]
    meeting["agenda"].append({"item": item, "completed": False})
    meeting["updated_at"] = datetime.now().isoformat()
    _save()
    return Meeting(**meeting)


# Notes Management
@mcp.tool
def set_meeting_notes(meeting_id: int, notes: str) -> Optional[Meeting]:
    """Set the notes for a meeting.

    Args:
        meeting_id: The meeting ID
        notes: The meeting notes

    Returns:
        Updated meeting or None
    """
    if meeting_id not in meetings:
        return None

    meeting = meetings[meeting_id]
    meeting["notes"] = notes
    meeting["updated_at"] = datetime.now().isoformat()
    _save()
    return Meeting(**meeting)


@mcp.tool
def append_meeting_notes(meeting_id: int, notes: str) -> Optional[Meeting]:
    """Append notes to a meeting.

    Args:
        meeting_id: The meeting ID
        notes: Notes to append

    Returns:
        Updated meeting or None
    """
    if meeting_id not in meetings:
        return None

    meeting = meetings[meeting_id]
    if meeting["notes"]:
        meeting["notes"] += "\n\n" + notes
    else:
        meeting["notes"] = notes
    meeting["updated_at"] = datetime.now().isoformat()
    _save()
    return Meeting(**meeting)


# Action Items
@mcp.tool
def create_action_item(
    meeting_id: int,
    description: str,
    assignee_id: Optional[int] = None,
    due_date: Optional[str] = None,
    priority: str = "medium"
) -> ActionItem:
    """Create an action item from a meeting.

    Args:
        meeting_id: The meeting ID
        description: Action item description
        assignee_id: ID of the assigned attendee
        due_date: Due date (YYYY-MM-DD)
        priority: Priority (low, medium, high)

    Returns:
        The created action item
    """
    if meeting_id not in meetings:
        raise ValueError(f"Meeting {meeting_id} not found")

    valid_priorities = [p.value for p in ActionPriority]
    if priority not in valid_priorities:
        raise ValueError(f"Invalid priority. Must be one of: {valid_priorities}")

    action_id = _get_next_action_id()
    action = ActionItem(
        id=action_id,
        meeting_id=meeting_id,
        description=description,
        assignee_id=assignee_id,
        due_date=due_date,
        priority=priority,
        status=ActionStatus.PENDING.value,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    action_items[action_id] = action.model_dump()
    _save()
    return action


@mcp.tool
def get_action_item(action_id: int) -> Optional[ActionItem]:
    """Get an action item by ID.

    Args:
        action_id: The action item ID

    Returns:
        Action item details or None
    """
    if action_id in action_items:
        return ActionItem(**action_items[action_id])
    return None


@mcp.tool
def update_action_item(
    action_id: int,
    description: Optional[str] = None,
    assignee_id: Optional[int] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None
) -> Optional[ActionItem]:
    """Update an action item.

    Args:
        action_id: The action item ID
        description: New description
        assignee_id: New assignee
        due_date: New due date
        priority: New priority
        status: New status

    Returns:
        Updated action item or None
    """
    if action_id not in action_items:
        return None

    action = action_items[action_id]
    if description is not None:
        action["description"] = description
    if assignee_id is not None:
        action["assignee_id"] = assignee_id
    if due_date is not None:
        action["due_date"] = due_date
    if priority is not None:
        valid_priorities = [p.value for p in ActionPriority]
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {valid_priorities}")
        action["priority"] = priority
    if status is not None:
        valid_statuses = [s.value for s in ActionStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        action["status"] = status

    action["updated_at"] = datetime.now().isoformat()
    _save()
    return ActionItem(**action)


@mcp.tool
def get_meeting_actions(meeting_id: int) -> list[ActionItem]:
    """Get all action items for a meeting.

    Args:
        meeting_id: The meeting ID

    Returns:
        List of action items
    """
    return [ActionItem(**a) for a in action_items.values() if a["meeting_id"] == meeting_id]


@mcp.tool
def get_pending_actions() -> list[ActionItem]:
    """Get all pending action items.

    Returns:
        List of pending action items
    """
    return [ActionItem(**a) for a in action_items.values() if a["status"] == ActionStatus.PENDING.value]


@mcp.tool
def get_overdue_actions() -> list[ActionItem]:
    """Get all overdue action items.

    Returns:
        List of overdue action items
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return [
        ActionItem(**a) for a in action_items.values()
        if a["status"] not in [ActionStatus.COMPLETED.value, ActionStatus.CANCELLED.value]
        and a.get("due_date") and a["due_date"] < today
    ]


@mcp.tool
def list_meetings(
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> list[Meeting]:
    """List meetings with optional filters.

    Args:
        status: Filter by status
        from_date: Filter by start date
        to_date: Filter by end date

    Returns:
        List of meetings
    """
    result = list(meetings.values())

    if status:
        result = [m for m in result if m["status"] == status]
    if from_date:
        result = [m for m in result if m["scheduled_at"] >= from_date]
    if to_date:
        result = [m for m in result if m["scheduled_at"] <= to_date]

    return [Meeting(**m) for m in sorted(result, key=lambda x: x["scheduled_at"])]


# Resources
@mcp.resource("meetings://upcoming")
def get_upcoming_meetings_resource() -> str:
    """Resource showing upcoming meetings."""
    now = datetime.now().isoformat()
    upcoming = [m for m in meetings.values() if m["scheduled_at"] >= now and m["status"] == "scheduled"]
    upcoming.sort(key=lambda x: x["scheduled_at"])

    if not upcoming:
        return "# Upcoming Meetings\n\nNo upcoming meetings scheduled."

    lines = ["# Upcoming Meetings\n"]
    for m in upcoming[:10]:
        lines.append(f"## {m['title']}")
        lines.append(f"- **When:** {m['scheduled_at']}")
        lines.append(f"- **Duration:** {m['duration_minutes']} minutes")
        if m.get("location"):
            lines.append(f"- **Location:** {m['location']}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("meetings://actions")
def get_actions_resource() -> str:
    """Resource showing pending action items."""
    pending = get_pending_actions()
    overdue = get_overdue_actions()

    lines = ["# Action Items\n"]

    if overdue:
        lines.append("## Overdue")
        for a in overdue:
            meeting = meetings.get(a["meeting_id"], {})
            lines.append(f"- **{a['description']}** (Due: {a['due_date']})")
            lines.append(f"  - Meeting: {meeting.get('title', 'Unknown')}")
        lines.append("")

    lines.append("## Pending")
    if pending:
        for a in pending:
            if a not in overdue:
                meeting = meetings.get(a["meeting_id"], {})
                due = f" (Due: {a['due_date']})" if a.get("due_date") else ""
                lines.append(f"- {a['description']}{due}")
    else:
        lines.append("_No pending action items_")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()