"""
Support Desk MCP Server
A FastMCP server for support tickets, SLA tracking, escalations, and CSAT.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from enum import Enum
import json
import os
import shutil
import atexit
import tempfile
import threading
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Support Desk",
    instructions=(
        "A helpdesk server for managing support tickets, priorities, SLA "
        "deadlines, escalations, resolutions, and customer satisfaction."
    ),
)


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Default first-response / resolution SLA targets in hours, by priority.
SLA_HOURS: dict[str, int] = {
    Priority.URGENT.value: 4,
    Priority.HIGH.value: 8,
    Priority.MEDIUM.value: 24,
    Priority.LOW.value: 72,
}

OPEN_STATUSES = {TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value, TicketStatus.WAITING.value}


class Ticket(BaseModel):
    """A support ticket."""
    id: int
    subject: str
    description: str
    requester_name: str
    requester_email: Optional[str] = None
    status: str
    priority: str
    category: Optional[str] = None
    assignee: Optional[str] = None
    tags: list[str] = []
    sla_due_at: Optional[str] = None
    first_response_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None
    created_at: str
    updated_at: str


class Comment(BaseModel):
    """A comment or note on a ticket."""
    id: int
    ticket_id: int
    author: str
    body: str
    internal: bool = False
    created_at: str


class CSATResponse(BaseModel):
    """A customer satisfaction response."""
    id: int
    ticket_id: int
    rating: int
    comment: Optional[str] = None
    created_at: str


# Data persistence setup (MCP_DATA_DIR allows tests / custom deployments)
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "support.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "tickets": {}, "comments": {}, "csat": {},
        "next_ticket_id": 1, "next_comment_id": 1, "next_csat_id": 1,
    }


_write_lock = threading.Lock()
_last_payload: Optional[str] = None
_pending_payload: Optional[str] = None
_flush_timer: Optional[threading.Timer] = None
_WRITE_DEBOUNCE_MS = int(os.environ.get("MCP_WRITE_DEBOUNCE_MS", "0") or 0)


def _write_payload(payload: str) -> None:
    """Atomically replace the data file with serialized JSON."""
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


def _flush_pending() -> None:
    """Write any deferred payload to disk immediately."""
    global _pending_payload
    with _write_lock:
        if _pending_payload is not None:
            payload, _pending_payload = _pending_payload, None
            _write_payload(payload)


def _save_data(data: dict) -> None:
    """Save data atomically, skipping unchanged writes.

    Writes to a temp file in the same directory then os.replace()s it into
    place, so an interrupted write can never leave a truncated/corrupt file.
    Set MCP_WRITE_DEBOUNCE_MS>0 to defer disk I/O; pending writes are flushed
    on exit and by the flush_data tool.
    """
    global _pending_payload, _flush_timer
    payload = json.dumps(data, indent=2, default=str)
    if _WRITE_DEBOUNCE_MS <= 0:
        with _write_lock:
            if payload != _last_payload:
                _write_payload(payload)
        return
    with _write_lock:
        if payload == _last_payload:
            return
        _pending_payload = payload
        if _flush_timer is not None:
            _flush_timer.cancel()
        _flush_timer = threading.Timer(_WRITE_DEBOUNCE_MS / 1000.0, _flush_pending)
        _flush_timer.daemon = True
        _flush_timer.start()


atexit.register(_flush_pending)


@mcp.tool
def flush_data() -> dict:
    """Flush any deferred writes to disk immediately."""
    _flush_pending()
    return {"flushed": True, "path": str(DATA_FILE), "debounce_ms": _WRITE_DEBOUNCE_MS}


@mcp.tool
def backup_data() -> dict:
    """Copy the current data file into data/backups/ with a timestamp."""
    _flush_pending()
    if not DATA_FILE.exists():
        raise ValueError("No data file to back up yet")
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = backup_dir / f"{DATA_FILE.stem}-{stamp}.json"
    shutil.copy2(DATA_FILE, target)
    return {"backup": str(target), "bytes": target.stat().st_size}


@mcp.tool
def list_backups() -> list[dict]:
    """List available data backups, newest first."""
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
    """Restore a backup, replacing current data. Restart the server to load it."""
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


# Initialize data
_data = _load_data()
tickets: dict[int, dict] = {int(k): v for k, v in _data.get("tickets", {}).items()}
comments: dict[int, dict] = {int(k): v for k, v in _data.get("comments", {}).items()}
csat: dict[int, dict] = {int(k): v for k, v in _data.get("csat", {}).items()}

_next_ticket_id = _data.get("next_ticket_id", 1)
_next_comment_id = _data.get("next_comment_id", 1)
_next_csat_id = _data.get("next_csat_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "tickets": tickets, "comments": comments, "csat": csat,
        "next_ticket_id": _next_ticket_id, "next_comment_id": _next_comment_id,
        "next_csat_id": _next_csat_id,
    })


def _next_id(kind: str) -> int:
    """Allocate the next integer id."""
    global _next_ticket_id, _next_comment_id, _next_csat_id
    if kind == "ticket":
        value = _next_ticket_id
        _next_ticket_id += 1
    elif kind == "comment":
        value = _next_comment_id
        _next_comment_id += 1
    else:
        value = _next_csat_id
        _next_csat_id += 1
    return value


# --- helpers -----------------------------------------------------------------
def _now() -> str:
    return datetime.now().isoformat()


def _as_list(value) -> list:
    """Accept a real list or a JSON-stringified list from MCP clients."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, TypeError):
            return [value]
    return value


def _sla_due(created_at: str, priority: str, sla_hours: Optional[float] = None) -> str:
    hours = sla_hours if sla_hours is not None else SLA_HOURS.get(priority, SLA_HOURS["medium"])
    return (datetime.fromisoformat(created_at) + timedelta(hours=hours)).isoformat()


def _validate_enum(value: str, enum_cls, field: str) -> str:
    allowed = {e.value for e in enum_cls}
    if value not in allowed:
        raise ValueError(f"{field} must be one of {sorted(allowed)}")
    return value


def _hours_between(start: Optional[str], end: Optional[str]) -> Optional[float]:
    if not start or not end:
        return None
    return round((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 3600.0, 2)


# --- tickets -----------------------------------------------------------------
@mcp.tool
def create_ticket(subject: str, description: str, requester_name: str,
                  requester_email: Optional[str] = None, priority: str = "medium",
                  category: Optional[str] = None, assignee: Optional[str] = None,
                  tags: Optional[list[str]] = None,
                  sla_hours: Optional[float] = None) -> Ticket:
    """Open a support ticket and start its SLA clock."""
    _validate_enum(priority, Priority, "priority")
    ticket_id = _next_id("ticket")
    created = _now()
    ticket = Ticket(
        id=ticket_id, subject=subject, description=description,
        requester_name=requester_name, requester_email=requester_email,
        status=TicketStatus.OPEN.value, priority=priority, category=category,
        assignee=assignee, tags=_as_list(tags), sla_due_at=_sla_due(created, priority, sla_hours),
        created_at=created, updated_at=created,
    )
    tickets[ticket_id] = ticket.model_dump()
    _save()
    return ticket


@mcp.tool
def bulk_create_tickets(ticket_specs: list[dict]) -> list[Ticket]:
    """Create many tickets in a single disk write.

    Each spec requires subject, description, requester_name; optional
    requester_email, priority, category, assignee, tags, sla_hours.
    """
    created = []
    for spec in _as_list(ticket_specs):
        if not isinstance(spec, dict):
            raise ValueError(f"Invalid ticket spec: {spec!r}")
        priority = spec.get("priority", Priority.MEDIUM.value)
        _validate_enum(priority, Priority, "priority")
        created_at = _now()
        ticket = Ticket(
            id=_next_id("ticket"),
            subject=spec["subject"],
            description=spec["description"],
            requester_name=spec["requester_name"],
            requester_email=spec.get("requester_email"),
            status=TicketStatus.OPEN.value,
            priority=priority,
            category=spec.get("category"),
            assignee=spec.get("assignee"),
            tags=_as_list(spec.get("tags")),
            sla_due_at=_sla_due(created_at, priority, spec.get("sla_hours")),
            created_at=created_at,
            updated_at=created_at,
        )
        tickets[ticket.id] = ticket.model_dump()
        created.append(ticket)
    if created:
        _save()
    return created


@mcp.tool
def get_ticket(ticket_id: int) -> Optional[Ticket]:
    """Retrieve a ticket by id."""
    data = tickets.get(ticket_id)
    return Ticket(**data) if data else None


@mcp.tool
def list_tickets(status: Optional[str] = None, priority: Optional[str] = None,
                 assignee: Optional[str] = None, limit: int = 100,
                 offset: int = 0) -> list[Ticket]:
    """List tickets with optional filters."""
    result = []
    for entry in tickets.values():
        if status is not None and entry["status"] != status:
            continue
        if priority is not None and entry["priority"] != priority:
            continue
        if assignee is not None and entry.get("assignee") != assignee:
            continue
        result.append(Ticket(**entry))
    result.sort(key=lambda t: t.created_at, reverse=True)
    return result[offset:offset + limit]


@mcp.tool
def search_tickets(query: str, limit: int = 50) -> list[Ticket]:
    """Search tickets by subject, description, requester, or tags."""
    q = query.lower()
    result = []
    for entry in tickets.values():
        haystack = " ".join([
            entry.get("subject", ""), entry.get("description", ""),
            entry.get("requester_name", ""), entry.get("requester_email") or "",
            " ".join(entry.get("tags", [])),
        ]).lower()
        if q in haystack:
            result.append(Ticket(**entry))
    return result[:limit]


@mcp.tool
def update_ticket(ticket_id: int, subject: Optional[str] = None,
                  description: Optional[str] = None, priority: Optional[str] = None,
                  category: Optional[str] = None, assignee: Optional[str] = None,
                  tags: Optional[list[str]] = None) -> Optional[Ticket]:
    """Update ticket fields. A priority change recalculates the SLA deadline."""
    entry = tickets.get(ticket_id)
    if entry is None:
        return None
    if priority is not None:
        _validate_enum(priority, Priority, "priority")
        entry["priority"] = priority
        entry["sla_due_at"] = _sla_due(entry["created_at"], priority)
    for field, value in (("subject", subject), ("description", description),
                         ("category", category), ("assignee", assignee)):
        if value is not None:
            entry[field] = value
    if tags is not None:
        entry["tags"] = _as_list(tags)
    entry["updated_at"] = _now()
    _save()
    return Ticket(**entry)


@mcp.tool
def assign_ticket(ticket_id: int, assignee: str) -> Optional[Ticket]:
    """Assign a ticket to an agent."""
    entry = tickets.get(ticket_id)
    if entry is None:
        return None
    entry["assignee"] = assignee
    if entry["status"] == TicketStatus.OPEN.value:
        entry["status"] = TicketStatus.IN_PROGRESS.value
    entry["updated_at"] = _now()
    _save()
    return Ticket(**entry)


# --- comments ----------------------------------------------------------------
@mcp.tool
def add_comment(ticket_id: int, author: str, body: str, internal: bool = False) -> Comment:
    """Add a comment. The first public comment records first-response time."""
    entry = tickets.get(ticket_id)
    if entry is None:
        raise ValueError(f"Unknown ticket: {ticket_id}")
    comment_id = _next_id("comment")
    comment = Comment(
        id=comment_id, ticket_id=ticket_id, author=author, body=body,
        internal=internal, created_at=_now(),
    )
    comments[comment_id] = comment.model_dump()
    if not internal and entry.get("first_response_at") is None:
        entry["first_response_at"] = comment.created_at
    if entry["status"] == TicketStatus.OPEN.value:
        entry["status"] = TicketStatus.IN_PROGRESS.value
    entry["updated_at"] = _now()
    _save()
    return comment


@mcp.tool
def list_comments(ticket_id: int, include_internal: bool = True) -> list[Comment]:
    """List comments on a ticket."""
    result = [Comment(**c) for c in comments.values()
              if int(c["ticket_id"]) == ticket_id
              and (include_internal or not c["internal"])]
    result.sort(key=lambda c: c.created_at)
    return result


# --- lifecycle ---------------------------------------------------------------
@mcp.tool
def resolve_ticket(ticket_id: int, resolution: str) -> Optional[Ticket]:
    """Resolve a ticket and record the resolution."""
    entry = tickets.get(ticket_id)
    if entry is None:
        return None
    entry["status"] = TicketStatus.RESOLVED.value
    entry["resolution"] = resolution
    entry["resolved_at"] = _now()
    entry["updated_at"] = _now()
    _save()
    return Ticket(**entry)


@mcp.tool
def close_ticket(ticket_id: int) -> Optional[Ticket]:
    """Close a ticket (resolves it first if needed)."""
    entry = tickets.get(ticket_id)
    if entry is None:
        return None
    if entry["status"] != TicketStatus.RESOLVED.value:
        entry["resolved_at"] = entry.get("resolved_at") or _now()
    entry["status"] = TicketStatus.CLOSED.value
    entry["updated_at"] = _now()
    _save()
    return Ticket(**entry)


@mcp.tool
def reopen_ticket(ticket_id: int) -> Optional[Ticket]:
    """Reopen a resolved or closed ticket."""
    entry = tickets.get(ticket_id)
    if entry is None:
        return None
    entry["status"] = TicketStatus.OPEN.value
    entry["resolved_at"] = None
    entry["updated_at"] = _now()
    _save()
    return Ticket(**entry)


@mcp.tool
def delete_ticket(ticket_id: int) -> bool:
    """Delete a ticket with its comments and CSAT responses."""
    if ticket_id not in tickets:
        return False
    del tickets[ticket_id]
    for comment_id in [cid for cid, c in comments.items() if int(c["ticket_id"]) == ticket_id]:
        del comments[comment_id]
    for csat_id in [sid for sid, s in csat.items() if int(s["ticket_id"]) == ticket_id]:
        del csat[csat_id]
    _save()
    return True


# --- CSAT --------------------------------------------------------------------
@mcp.tool
def submit_csat(ticket_id: int, rating: int, comment: Optional[str] = None) -> CSATResponse:
    """Record a customer satisfaction rating (1-5)."""
    if ticket_id not in tickets:
        raise ValueError(f"Unknown ticket: {ticket_id}")
    if not 1 <= rating <= 5:
        raise ValueError("rating must be between 1 and 5")
    csat_id = _next_id("csat")
    response = CSATResponse(
        id=csat_id, ticket_id=ticket_id, rating=rating,
        comment=comment, created_at=_now(),
    )
    csat[csat_id] = response.model_dump()
    _save()
    return response


# --- SLA & reporting ---------------------------------------------------------
@mcp.tool
def get_sla_status(ticket_id: int, as_of: Optional[str] = None) -> Optional[dict]:
    """Report whether a ticket is on track, at risk, breached, or met."""
    entry = tickets.get(ticket_id)
    if entry is None:
        return None
    if not entry.get("sla_due_at"):
        return {"ticket_id": ticket_id, "state": "not_applicable", "due_at": None}
    now = datetime.fromisoformat(as_of or _now())
    due = datetime.fromisoformat(entry["sla_due_at"])
    window_hours = SLA_HOURS.get(entry["priority"], SLA_HOURS["medium"])
    if entry["status"] in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
        met = entry.get("resolved_at") is not None and datetime.fromisoformat(entry["resolved_at"]) <= due
        return {
            "ticket_id": ticket_id, "state": "met" if met else "breached",
            "due_at": entry["sla_due_at"], "resolved_at": entry.get("resolved_at"),
        }
    remaining = round((due - now).total_seconds() / 3600.0, 2)
    if remaining < 0:
        state = "breached"
    elif remaining <= window_hours * 0.25:
        state = "at_risk"
    else:
        state = "on_track"
    return {
        "ticket_id": ticket_id, "state": state, "due_at": entry["sla_due_at"],
        "remaining_hours": remaining,
    }


@mcp.tool
def get_overdue_tickets(as_of: Optional[str] = None) -> list[Ticket]:
    """List open tickets whose SLA deadline has passed."""
    now = datetime.fromisoformat(as_of or _now())
    result = [Ticket(**t) for t in tickets.values()
              if t["status"] in OPEN_STATUSES and t.get("sla_due_at")
              and datetime.fromisoformat(t["sla_due_at"]) < now]
    result.sort(key=lambda t: t.sla_due_at)
    return result


@mcp.tool
def get_support_stats(start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> dict:
    """Support metrics: volumes, response/resolution time, SLA, and CSAT."""
    start = datetime.fromisoformat(start_date or "1970-01-01")
    end = datetime.fromisoformat(end_date or "2100-01-01")
    in_range = [t for t in tickets.values()
                if start <= datetime.fromisoformat(t["created_at"]) <= end]

    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    first_response_hours, resolution_hours = [], []
    resolved_with_sla = sla_met = 0

    for t in in_range:
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
        by_priority[t["priority"]] = by_priority.get(t["priority"], 0) + 1
        fr = _hours_between(t["created_at"], t.get("first_response_at"))
        if fr is not None:
            first_response_hours.append(fr)
        rh = _hours_between(t["created_at"], t.get("resolved_at"))
        if rh is not None:
            resolution_hours.append(rh)
        if t["status"] in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value) and t.get("sla_due_at"):
            resolved_with_sla += 1
            if t.get("resolved_at") and datetime.fromisoformat(t["resolved_at"]) <= datetime.fromisoformat(t["sla_due_at"]):
                sla_met += 1

    ratings = [s["rating"] for s in csat.values()
               if int(s["ticket_id"]) in {int(t["id"]) for t in in_range}]

    def _avg(values: list[float]) -> Optional[float]:
        return round(sum(values) / len(values), 2) if values else None

    return {
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "total_tickets": len(in_range),
        "open_tickets": sum(1 for t in in_range if t["status"] in OPEN_STATUSES),
        "by_status": by_status,
        "by_priority": by_priority,
        "avg_first_response_hours": _avg(first_response_hours),
        "avg_resolution_hours": _avg(resolution_hours),
        "sla_compliance_pct": round(sla_met / resolved_with_sla * 100, 1) if resolved_with_sla else None,
        "csat_average": _avg([float(r) for r in ratings]),
        "csat_responses": len(ratings),
    }


# --- resources ---------------------------------------------------------------
@mcp.resource("support://queue")
def get_queue_resource() -> str:
    """Current open queue as formatted text."""
    open_tickets = list_tickets()
    open_tickets = [t for t in open_tickets if t.status in OPEN_STATUSES]
    if not open_tickets:
        return "# Support Queue\n\nNo open tickets."

    lines = [f"# Support Queue ({len(open_tickets)} open)\n"]
    for t in open_tickets:
        sla = get_sla_status(t.id)
        lines.append(f"- **#{t.id} [{t.priority}] {t.subject}**")
        lines.append(f"  - Status: {t.status} | Assignee: {t.assignee or 'unassigned'}")
        lines.append(f"  - SLA: {sla['state']} (due {sla['due_at']})")
    return "\n".join(lines)


@mcp.resource("support://sla")
def get_sla_resource() -> str:
    """SLA policy as formatted text."""
    lines = ["# SLA Policy (target hours)\n"]
    for priority, hours in SLA_HOURS.items():
        lines.append(f"- **{priority}:** {hours}h")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
