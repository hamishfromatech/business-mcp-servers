"""
Incident Manager MCP Server
A FastMCP server for IT incident ticket management with priority,
escalation, SLA tracking, and status transitions.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Incident Manager",
    instructions=(
        "Manages IT incident ticket management with priority, escalation, "
        "SLA tracking, and status transitions. Supports open/in-progress/"
        "resolved/closed states and automated SLA breach detection."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "incidents.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"incidents": [], "escalations": {}, "next_id": 1}


_write_lock = threading.Lock()
_last_payload = None
_pending_payload = None
_flush_timer = None


def _write_payload(payload):
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


def _save_data(data):
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
def flush_data():
    _flush_pending()
    return {"flushed": True, "path": str(DATA_FILE)}


@mcp.tool
def backup_data():
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
def list_backups():
    backup_dir = DATA_DIR / "backups"
    if not backup_dir.exists():
        return []
    items = []
    for p in sorted(backup_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        items.append({
            "name": p.name, "bytes": p.stat().st_size,
            "modified_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        })
    return items


@mcp.tool
def restore_backup(name):
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


_data = _load_data()
incidents = _data.get("incidents", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"incidents": incidents, "escalations": {}, "next_id": _next_id})


def _get_next_id():
    global _next_id
    global_var = _next_id
    _next_id += 1
    return global_var


def _within_range(d, start, end):
    d = datetime.fromisoformat(str(d)).date() if d else None
    if d is None:
        return True
    if start and d < datetime.fromisoformat(str(start)).date():
        return False
    if end and d > datetime.fromisoformat(str(end)).date():
        return False
    return True


@mcp.tool
def add_incident(title, description="", priority="medium", status="open",
                 category="incidents", reporter_id=None, assignee_id=None,
                 impact="low", assigned_to=None, sla_hours=24, start_date=None,
                 due_date=None, notes=None):
    incident = {
        "id": _get_next_id(), "title": title, "description": description,
        "priority": priority, "status": status, "category": category,
        "reporter_id": reporter_id, "assignee_id": assignee_id,
        "impact": impact, "assigned_to": assigned_to, "sla_hours": sla_hours,
        "start_date": start_date or datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "resolved_at": None, "resolved_by": None, "resolved_notes": None,
        "created_at": datetime.now().isoformat(),
    }
    incidents.append(incident)
    _save()
    ekey = "escalation_" + str(incident["id"])
    if ekey not in escalations:
        escalations[ekey] = {"level": 0, "escalated_at": datetime.now().isoformat(), "chain": []}
    escalations[ekey]["level"] = escalations[ekey].get("level", 0) + 1
    escalations[ekey]["escalated_at"] = datetime.now().isoformat()
    escalations[ekey]["chain"].append(assigned_to or "team")
    return incident


@mcp.tool
def get_incident(incident_id):
    for i in incidents:
        if i["id"] == incident_id:
            return i
    return None


@mcp.tool
def search_incidents(query):
    q = query.lower()
    results = [
        i for i in incidents
        if q in i.get("title", "").lower() or q in i.get("description", "").lower()
    ]
    return results


@mcp.tool
def update_incident(incident_id, **kwargs):
    for i, inc in enumerate(incidents):
        if inc["id"] == incident_id:
            for k, v in kwargs.items():
                if v is not None:
                    inc[k] = v
            inc["updated_at"] = datetime.now().isoformat()
            _save()
            return inc
    return None


@mcp.tool
def escalate_incident(incident_id, level=None, escalation_reason=None):
    for i, inc in enumerate(incidents):
        if inc["id"] == incident_id:
            if inc.get("status") not in ("open", "in_progress"):
                return None
            inc["assignee_id"] = escalation_reason
            ekey = "escalation_" + str(incident_id)
            if ekey not in escalations:
                escalations[ekey] = {"level": 0, "escalated_at": datetime.now().isoformat(), "chain": []}
            escalations[ekey]["level"] = escalations[ekey].get("level", 0) + 1
            escalations[ekey]["escalated_at"] = datetime.now().isoformat()
            escalations[ekey]["chain"].append(escalation_reason)
            _save()
            return inc
    return None


@mcp.tool
def close_incident(incident_id, resolved_by=None, notes=None):
    for i, inc in enumerate(incidents):
        if inc["id"] == incident_id:
            if inc.get("status") not in ("resolved", "closed"):
                inc["status"] = "resolved"
                inc["resolved_at"] = datetime.now().isoformat()
                inc["resolved_by"] = resolved_by
                inc["resolved_notes"] = notes
                inc["updated_at"] = datetime.now().isoformat()
                _save()
                return incidents[i]
    return None


@mcp.tool
def delete_incident(incident_id):
    for i, inc in enumerate(incidents):
        if inc["id"] == incident_id:
            del incidents[i]
            _save()
            return True
    return False


@mcp.tool
def list_incidents():
    return sorted(incidents, key=lambda i: i.get("created_at", ""))


@mcp.tool
def get_incident_count():
    return len(incidents)


@mcp.tool
def get_open_incidents():
    return [i for i in incidents if i.get("status") in ("open", "in_progress")]


@mcp.tool
def get_incidents_by_status(status):
    return [i for i in incidents if i.get("status") == status]


@mcp.tool
def get_sla_breached_incidents():
    now = datetime.now().date()
    breached = []
    for inc in incidents:
        if inc.get("status") != "resolved":
            continue
        if not inc.get("resolved_at"):
            continue
        sla_due = datetime.fromisoformat(inc["start_date"]).date() + timedelta(days=inc.get("sla_hours", 24))
        if now < sla_due:
            continue
        breached.insert(0, inc)
    return breached


@mcp.tool
def get_sla_compliance_rate():
    resolved = [i for i in incidents if i.get("status") == "resolved" and i.get("resolved_at")]
    if not resolved:
        return {"resolved_count": 0, "compliance_rate": None}
    resolved_within = 0
    now = datetime.now().date()
    for inc in resolved:
        sla_due = datetime.fromisoformat(inc["start_date"]).date() + timedelta(days=inc.get("sla_hours", 24))
        resolved_date = datetime.fromisoformat(inc["resolved_at"]).date()
        if resolved_date >= sla_due:
            resolved_within += 1
    return {
        "resolved_count": len(resolved),
        "within_sla": resolved_within,
        "compliance_rate": round(resolved_within / len(resolved), 2),
    }


@mcp.resource("incidents://status-dashboard")
def status_dashboard_resource():
    lines = ["# Incident Status Dashboard"]
    for state in ("open", "in_progress", "resolved", "escalated"):
        count = sum(1 for i in incidents if i.get("status") == state)
        lines.append("- {}: {}".format(state.upper(), count))
    if not incidents:
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
