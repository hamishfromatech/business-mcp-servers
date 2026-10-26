"""
Project Budget Tracker MCP Server
A FastMCP server for project budget management with approved vs committed
tracking, budget forecasting, and budget utilization analysis.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Project Budget Tracker",
    instructions=(
        "Manages project budgets: approved/committed spending, budget "
        "forecasting, budget utilization, and project-level budget tracking."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "budgets.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"projects": [], "budgets": [], "transactions": [], "next_id": 1}


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
        items.append({"name": p.name, "bytes": p.stat().st_size,
                       "modified_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat()})
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
projects = _data.get("projects", [])
budgets = _data.get("budgets", [])
transactions = _data.get("transactions", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"projects": projects, "budgets": budgets, "transactions": transactions, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


@mcp.tool
def add_project(name, client="", budget_type="approved", total_budget=None):
    project = {
        "id": _get_next_id(),
        "name": name,
        "client": client,
        "budget_type": budget_type,
        "total_budget": total_budget or 0.0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    projects.append(project)
    _save()
    return project


@mcp.tool
def get_project(project_id):
    for i in projects:
        if i["id"] == project_id:
            return i
    return None


@mcp.tool
def search_projects(query):
    q = query.lower()
    results = [p for p in projects if q in p.get("name", "").lower() or q in p.get("client", "").lower()]
    return results


@mcp.tool
def add_budget_entry(project_id, amount, category="", date=None, status="committed", description=""):
    trans = {
        "id": _get_next_id(),
        "project_id": project_id,
        "amount": amount,
        "category": category,
        "date": date or datetime.now().isoformat(),
        "status": status,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    transactions.append(trans)
    _save()
    return trans


@mcp.tool
def get_project_budget(project_id):
    proj = None
    for i in projects:
        if i["id"] == project_id:
            proj = i
            break
    if not proj:
        return None
    total_committed = sum(t.get("amount", 0) for t in transactions if t.get("project_id") == project_id and t.get("status") == "committed")
    total_approved = sum(t.get("amount", 0) for t in transactions if t.get("project_id") == project_id and t.get("status") == "approved")
    return {
        **proj,
        "total_committed": total_committed,
        "total_approved": total_approved,
        "remaining": proj["total_budget"] - total_committed,
    }


@mcp.tool
def delete_transaction(transaction_id):
    for i, t in enumerate(transactions):
        if t["id"] == transaction_id:
            del transactions[i]
            _save()
            return True
    return False


@mcp.tool
def list_transactions():
    return sorted(transactions, key=lambda t: t.get("created_at", ""))


@mcp.tool
def get_transaction_count():
    return len(transactions)


@mcp.tool
def get_project_utilization(project_id):
    proj = None
    for i in projects:
        if i["id"] == project_id:
            proj = i
            break
    if not proj:
        return None
    committed = sum(t.get("amount", 0) for t in transactions if t.get("project_id") == project_id and t.get("status") == "committed")
    utilized = (committed / proj["total_budget"]) if proj["total_budget"] > 0 else 0
    return {"project_id": project_id, "utilized": utilized, "remaining": proj["total_budget"] - committed}


@mcp.tool
def list_projects():
    return sorted(projects, key=lambda p: p.get("name", ""))


@mcp.tool
def get_budget_summary():
    by_status = {"approved": 0, "committed": 0, "expenditure": 0}
    total_approved = 0.0
    total_committed = 0.0
    for t in transactions:
        s = t.get("status", "expenditure")
        by_status[s] = by_status.get(s, 0) + 1
        total_approved += float(t.get("amount", 0)) if s == "approved" else 0.0
        total_committed += float(t.get("amount", 0)) if s == "committed" else 0.0
    return {
        "by_status": by_status,
        "total_approved": total_approved,
        "total_committed": total_committed,
    }


@mcp.resource("budgets://summary")
def summary_resource():
    lines = ["# Budget Summary"]
    s = get_budget_summary()
    lines.append("Approved: {} | Committed: {}".format(s["total_approved"], s["total_committed"]))
    lines.append("By status: {}".format(s["by_status"]))
    if not transactions:
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
