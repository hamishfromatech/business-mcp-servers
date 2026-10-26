"""
Scheduling / Team Calendar MCP Server
A FastMCP server for resource scheduling, team availability, and calendar
booking with recurring events and capacity tracking.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Scheduling Team Calendar",
    instructions=(
        "Manages team availability, resource scheduling, recurring calendar events, "
        "and capacity-based booking. Supports slots, calendars, assignments, and "
        "team-based project scheduling."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "schedule.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"slots": [], "calendars": [], "bookings": [], "next_id": 1}


_write_lock = threading.Lock()
_last_payload: Optional[str] = None
_pending_payload: Optional[str] = None
_flush_timer: Optional[threading.Timer] = None


def _write_payload(payload: str):
    global _last_payload
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, DATA_FILE)
        _last_payload = payload
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _save_data(data: dict):
    global _pending_payload, _flush_timer
    payload = json.dumps(data, indent=2, default=str)
    with _write_lock:
        if payload == _last_payload:
            return
        _pending_payload = payload
        if _flush_timer is not None:
            _flush_timer.cancel()
        _flush_timer = threading.Timer(0.001, _flush_pending)
        _flush_timer.daemon = True
        _flush_timer.start()


def _flush_pending():
    global _pending_payload
    with _write_lock:
        if _pending_payload is not None:
            p, _pending_payload = _pending_payload, None
            _write_payload(p)


@mcp.tool
def flush_data() -> dict:
    _flush_pending()
    return {"flushed": True, "path": str(DATA_FILE)}


@mcp.tool
def backup_data() -> dict:
    _flush_pending()
    if not DATA_FILE.exists():
        raise ValueError("No data file to back up yet")
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = backup_dir / f"{DATA_FILE.stem}-{stamp}.json"
    import shutil
    shutil.copy2(DATA_FILE, target)
    return {"backup": str(target), "bytes": target.stat().st_size}


@mcp.tool
def list_backups() -> list:
    backup_dir = DATA_DIR / "backups"
    if not backup_dir.exists():
        return []
    items = []
    for path in sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        items.append({
            "name": path.name,
            "bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        })
    return items


@mcp.tool
def restore_backup(name: str) -> dict:
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


_data = _load_data()
slots: list = _data.get("slots", [])
calendars: list = _data.get("calendars", [])
bookings: list = _data.get("bookings", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"slots": slots, "calendars": calendars, "bookings": bookings, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


@mcp.tool
def add_resource_calendar(
    name: str, description: str = "",
    members: Optional[list] = None, recurring_pattern: Optional[str] = None,
    timezone: Optional[str] = None, status: str = "active"
):
    """Add a team resource calendar."""
    cal = {
        "id": str(_get_next_id()),
        "name": name,
        "description": description,
        "members": members or [],
        "recurring_pattern": recurring_pattern,
        "timezone": timezone,
        "status": status,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    calendars.append(cal)
    _save()
    return cal


@mcp.tool
def get_resource_calendar(calendar_id: str):
    """Retrieve a calendar by ID."""
    for c in calendars:
        if c["id"] == calendar_id:
            return c
    return None


@mcp.tool
def add_scheduling_slot(
    calendar_id: str, slot_type: str = "standard",
    available_hours: Optional[str] = None,
    slots_per_hour: int = null,  # e.g. 2 slots per hour
):
    """Add a slot definition for a calendar."""
    slot = {
        "id": str(_get_next_id()),
        "calendar_id": calendar_id,
        "slot_type": slot_type,
        "available_hours": available_hours,
        "slots_per_hour": slots_per_hour,
        "created_at": datetime.now().isoformat(),
    }
    slots.append(slot)
    _save()
    return slot


@mcp.tool
def add_booking(
    title: str, description: str = "", calendar_id: str = "",
    start_date: Optional[str] = None, start_time: Optional[str] = None,
    end_time: Optional[str] = None, assigned_to: Optional[str] = None,
    participants: Optional[list] = None, duration_minutes: Optional[int] = None,
    notes: Optional[str] = None, recurring: Optional[bool] = None
):
    """Add a scheduling booking. Returns the booking with generated slots."""
    if not recurring:
        bookings.append({
            "id": str(_get_next_id()),
            "title": title,
            "description": description,
            "calendar_id": calendar_id,
            "start_date": start_date or datetime.now().isoformat(),
            "start_time": start_time,
            "end_time": end_time,
            "assigned_to": assigned_to,
            "participants": participants or [],
            "duration_minutes": duration_minutes or 60,
            "notes": notes,
            "recurring": recurring,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        })
        _save()
        return bookings[-1]
    # Create recurring booking (weekly example)
    n = 4
    results = []
    for i in range(n):
        d = datetime.now().date() + timedelta(days=7 * i)
        results.append({
            "id": str(_get_next_id()),
            "title": title,
            "description": description,
            "calendar_id": calendar_id,
            "start_date": d.isoformat(),
            "start_time": start_time,
            "end_time": end_time,
            "assigned_to": assigned_to,
            "participants": participants or [],
            "duration_minutes": duration_minutes or 60,
            "notes": notes,
            "recurring": True,
            "recurrence_rule": f"FREQ=WEEKLY;INTERVAL=1;COUNT={n}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        })
    _save()
    return results


@mcp.tool
def get_booking(booking_id: str):
    """Retrieve a booking by ID."""
    for b in bookings:
        if b["id"] == booking_id:
            return b
    return None


@mcp.tool
def search_bookings(query: str):
    """Search bookings by title or description."""
    q = query.lower()
    return [
        b for b in bookings
        if q in b.get("title", "").lower() or q in b.get("description", "").lower()
    ]


@mcp.tool
def update_booking(booking_id: str, **kwargs):
    """Update a booking."""
    for i, b in enumerate(bookings):
        if b["id"] == booking_id:
            for k, v in kwargs.items():
                if v is not None:
                    b[k] = v
            b["updated_at"] = datetime.now().isoformat()
            _save()
            return b
    return None


@mcp.tool
def delete_booking(booking_id: str):
    """Delete a booking. Returns False if not found."""
    for i, b in enumerate(bookings):
        if b["id"] == booking_id:
            del bookings[i]
            _save()
            return True
    return False


@mcp.tool
def list_bookings():
    """List all bookings, sorted by date/time."""
    def sort_key(b):
        d = datetime.fromisoformat(str(b.get("start_date", "")))
        return (d, b.get("start_time", ""))
    return sorted(bookings, key=sort_key)


@mcp.tool
def get_bookings_by_calendar(calendar_id: str):
    """Get bookings for a specific calendar."""
    return [b for b in bookings if b.get("calendar_id") == calendar_id]


@mcp.tool
def get_available_slots(calendar_id: str, from_date: Optional[str] = None, to_date: Optional[str] = None):
    """Get available slots for a calendar in a date range."""
    booked = set(b.get("start_date") for b in bookings if b.get("calendar_id") == calendar_id)
    if from_date:
        booked.update(b.get("start_date") for b in bookings if b.get("calendar_id") == calendar_id and b.get("start_date") < from_date)
    return [d for d in sorted(booked) if d not in booked]


@mcp.tool
def get_calendar_overload_schedule():
    """Counts calendars by number of bookings."""
    total = len(calendars)
    active = sum(1 for c in calendars if c.get("status") == "active")
    overloaded = sum(1 for c in calendars if len([b for b in bookings if b.get("calendar_id") == c["id"]]) > 10)
    return {
        "total_calendars": total,
        "active": active,
        "overloaded": overloaded,
    }


@mcp.tool
def get_booking_count() -> int:
    """Total booking count."""
    return len(bookings)


@mcp.resource("schedule://calendar-overview")
def calendar_overview_resource():
    lines = ["# Team Calendar Overview\n"]
    for cal in sorted(calendars, key=lambda c: c.get("name", "")):
        lines.append(f"- **{cal['name']}** (ID: {cal['id']}) — {len(cal.get('members', []))} members")
    if not calendars:
        lines.append("No calendars defined.")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
