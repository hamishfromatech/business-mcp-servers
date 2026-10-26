"""
Facilities Manager MCP Server
A FastMCP server for facilities operations: maintenance requests,
work orders, space management, and recurring maintenance schedules.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Facilities Manager",
    instructions=(
        "Manages facilities operations: maintenance requests, work orders, "
        "space/room management, and recurring maintenance schedules."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "facilities.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"requests": [], "spaces": [], "work_orders": [],
            "maintenance_schedules": [], "next_id": 1}


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
requests = _data.get("requests", [])
spaces = _data.get("spaces", [])
work_orders = _data.get("work_orders", [])
maintenance_schedules = _data.get("maintenance_schedules", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"requests": requests, "spaces": spaces, "work_orders": work_orders,
                "maintenance_schedules": maintenance_schedules, "next_id": _next_id})


def _get_next_id():
    global _next_id
    global_var = _next_id
    _next_id += 1
    return global_var


def _assign_status(req, new_status, **kwargs):
    if req.get("status") != new_status:
        req["status"] = new_status
    for k, v in kwargs.items():
        if v is not None:
            req[k] = v
    req["updated_at"] = datetime.now().isoformat()
    _save()
    return req


@mcp.tool
def add_maintenance_request(title, description="", location=None,
                             request_type=None, priority="normal",
                             status="open", assigned_to=None,
                             due_date=None, scheduled_for=None,
                             requester_id=None, notes=None):
    req = {
        "id": _get_next_id(), "title": title, "description": description,
        "location": location, "request_type": request_type,
        "priority": priority, "status": status,
        "assigned_to": assigned_to, "due_date": due_date,
        "scheduled_for": scheduled_for, "requester_id": requester_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "closed_at": None, "closed_by": None,
    }
    req["status_log"] = [{"action": "created", "timestamp": datetime.now().isoformat(),
                          "performed_by": "N/A"}]
    requests.append(req)
    _save()
    return req


@mcp.tool
def get_maintenance_request(request_id):
    for i in requests:
        if i["id"] == request_id:
            return i
    return None


@mcp.tool
def search_maintenance_requests(query):
    q = query.lower()
    results = [
        i for i in requests
        if q in i.get("title", "").lower() or q in i.get("location", "").lower()
    ]
    return results


@mcp.tool
def update_maintenance_request(request_id, **kwargs):
    for i, req in enumerate(requests):
        if req["id"] == request_id:
            for k, v in kwargs.items():
                if v is not None:
                    req[k] = v
            req["updated_at"] = datetime.now().isoformat()
            _save()
            return req
    return None


@mcp.tool
def close_maintenance_request(request_id, closed_by=None, notes=None):
    for i, req in enumerate(requests):
        if req["id"] == request_id:
            if req.get("status") not in ("closed", "resolved"):
                req["status"] = "closed"
                req["closed_at"] = datetime.now().isoformat()
                req["closed_by"] = closed_by
                if notes:
                    req["closed_notes"] = notes
                req["updated_at"] = datetime.now().isoformat()
                _save()
                return requests[i]
    return None


@mcp.tool
def delete_maintenance_request(request_id):
    for i, req in enumerate(requests):
        if req["id"] == request_id:
            del requests[i]
            _save()
            return True
    return False


@mcp.tool
def list_maintenance_requests():
    return sorted(requests, key=lambda r: r.get("created_at", ""))


@mcp.tool
def get_open_requests():
    return [r for r in requests if r.get("status") in ("open", "in_progress", "pending")]


@mcp.tool
def get_requests_by_priority(priority):
    return [r for r in requests if r.get("priority") == priority]


@mcp.tool
def get_overdue_requests():
    now = datetime.now().date()
    result = []
    for r in requests:
        if r.get("status") not in ("closed", "resolved"):
            due = datetime.fromisoformat(r.get("due_date", "")).date() if r.get("due_date") else None
            if due and due < now:
                result.insert(0, r)
    return result


@mcp.tool
def add_space(location, space_type="", size_sqft=None,
              floor=None, manager=None, status="active"):
    space = {
        "id": _get_next_id(), "location": location, "space_type": space_type,
        "size_sqft": size_sqft, "floor": floor, "manager": manager,
        "status": status,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    spaces.append(space)
    _save()
    return space


@mcp.tool
def get_space(space_id):
    for i in spaces:
        if i["id"] == space_id:
            return i
    return None


@mcp.tool
def delete_space(space_id):
    for i, s in enumerate(spaces):
        if s["id"] == space_id:
            del spaces[i]
            _save()
            return True
    return False


@mcp.tool
def add_work_order(title, description="", space_id=None,
                   priority="normal", status="open",
                   assigned_to=None, due_date=None,
                   category=None, work_notes=None):
    work_order = {
        "id": _get_next_id(), "title": title, "description": description,
        "space_id": space_id, "priority": priority, "status": status,
        "assigned_to": assigned_to, "due_date": due_date,
        "category": category, "work_notes": work_notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "completed_at": None, "completed_by": None,
    }
    work_orders.append(work_order)
    _save()
    return work_order


@mcp.tool
def get_work_order(work_order_id):
    for i in work_orders:
        if i["id"] == work_order_id:
            return i
    return None


@mcp.tool
def complete_work_order(work_order_id, completed_by=None):
    for i, wo in enumerate(work_orders):
        if wo["id"] == work_order_id:
            if wo.get("status") not in ("closed", "completed"):
                wo["status"] = "closed"
                wo["completed_at"] = datetime.now().isoformat()
                wo["completed_by"] = completed_by
                wo["updated_at"] = datetime.now().isoformat()
                _save()
                return wo
    return None


@mcp.tool
def add_maintenance_schedule(hour, day_of_week=None):
    schedule = {
        "id": _get_next_id(), "hour": hour, "day_of_week": day_of_week,
        "enabled": True,
        "created_at": datetime.now().isoformat(),
    }
    maintenance_schedules.append(schedule)
    _save()
    return schedule


@mcp.tool
def get_facilities_summary():
    by_status = {"open": 0, "in_progress": 0, "pending": 0, "closed": 0, "resolved": 0}
    total_open = 0
    for r in requests:
        s = r.get("status", "open").lower()
        by_status[s] = by_status.get(s, 0) + 1
        if s in ("open", "in_progress", "pending"):
            total_open += 1
    return {
        "total_requests": len(requests),
        "open_requests": total_open,
        "by_status": by_status,
    }


@mcp.tool
def get_overall_spaces_count():
    active = sum(1 for s in spaces if s.get("status") == "active")
    return {"total": len(spaces), "active": active}


@mcp.tool
def list_spaces():
    return sorted(spaces, key=lambda s: s.get("location", ""))


@mcp.tool
def add_maintenance_schedule_hour(hour, day_of_week=None):
    schedule = {
        "id": _get_next_id(),
        "hour": hour, "day_of_week": day_of_week,
        "enabled": True,
        "created_at": datetime.now().isoformat(),
    }
    maintenance_schedules.append(schedule)
    _save()
    return schedule


@mcp.resource("facilities://dashboard")
def dashboard_resource():
    lines = ["# Facilities Dashboard"]
    summary = get_facilities_summary()
    spaces = get_overall_spaces_count()
    lines.append(
        "- Maintenance requests: {} (open: {})".format(
            summary["total_requests"], summary["open_requests"]
        )
    )
    lines.append(
        "- Spaces: {} (active: {})".format(spaces["total"], spaces["active"])
    )
    if not requests:
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
