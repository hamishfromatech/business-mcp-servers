"""
IT Service Desk MCP Server
A FastMCP server for IT helpdesk ticket management with knowledge base
integration, categorization, and priority-based queuing.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="IT Service Desk",
    instructions=(
        "Manages IT helpdesk tickets with priority queues, categorization, "
        "knowledge base articles, and resolution tracking. Supports KB search, "
        "self-service, and ticket templates."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "tickets.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tickets": [], "knowledge_base": [], "next_id": 1}


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
tickets = _data.get("tickets", [])
kb_articles = _data.get("knowledge_base", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"tickets": tickets, "knowledge_base": kb_articles, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


@mcp.tool
def create_ticket(title, description="", category="", priority="normal",
                  assignment="", assigned_to="", reporter="", due_date=None,
                  request_type="support", tickets_tags=None,
                  steps_to_reproduce=None, environment=None):
    ticket = {
        "id": _get_next_id(), "title": title, "description": description,
        "category": category, "priority": priority, "assignment": assignment,
        "assigned_to": assigned_to, "reporter": reporter, "due_date": due_date,
        "request_type": request_type, "tickets_tags": tickets_tags or [],
        "steps_to_reproduce": steps_to_reproduce, "environment": environment,
        "status": "open", "resolved_at": None, "resolved_by": None,
        "updated_at": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
    }
    tickets.append(ticket)
    _save()
    return ticket


@mcp.tool
def get_ticket(ticket_id):
    for i in tickets:
        if i["id"] == ticket_id:
            return i
    return None


@mcp.tool
def search_tickets(query):
    q = query.lower()
    results = [t for t in tickets if q in t.get("title", "").lower() or q in t.get("description", "").lower()]
    return results


@mcp.tool
def update_ticket(ticket_id, **kwargs):
    for i, t in enumerate(tickets):
        if t["id"] == ticket_id:
            for k, v in kwargs.items():
                if v is not None:
                    t[k] = v
            t["updated_at"] = datetime.now().isoformat()
            _save()
            return t
    return None


@mcp.tool
def close_ticket(ticket_id, notes=None):
    for i, t in enumerate(tickets):
        if t["id"] == ticket_id:
            if t.get("status") not in ("resolved", "closed", "pending"):
                t["status"] = "resolved"
                t["resolved_at"] = datetime.now().isoformat()
                t["resolved_by"] = "user"
                t["updated_at"] = datetime.now().isoformat()
                _save()
                return t
    return None


@mcp.tool
def delete_ticket(ticket_id):
    for i, t in enumerate(tickets):
        if t["id"] == ticket_id:
            del tickets[i]
            _save()
            return True
    return False


@mcp.tool
def list_tickets():
    return sorted(tickets, key=lambda t: t.get("created_at", ""))


@mcp.tool
def get_ticket_count():
    return len(tickets)


@mcp.tool
def get_open_tickets():
    return [t for t in tickets if t.get("status") == "open"]


@mcp.tool
def get_pending_tickets():
    return [t for t in tickets if t.get("status") == "pending"]


@mcp.tool
def get_resolved_tickets():
    return [t for t in tickets if t.get("status") == "resolved"]


@mcp.tool
def get_tickets_by_priority(priority):
    return [t for t in tickets if t.get("priority") == priority]


def _search_kb(query):
    q = query.lower()
    results = []
    for a in kb_articles:
        if q in a.get("title", "").lower() or q in a.get("content", "").lower():
            results.append(a)
    return results


@mcp.tool
def search_kb(query):
    return _search_kb(query)


@mcp.tool
def create_kb_article(title, content, category="", lang="en", references=None):
    article = {
        "id": _get_next_id(), "title": title, "content": content,
        "category": category, "lang": lang,
        "references": references or "",
        "updated_at": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
    }
    kb_articles.append(article)
    _save()
    return article


@mcp.tool
def delete_kb_article(article_id):
    for i, a in enumerate(kb_articles):
        if a["id"] == article_id:
            del kb_articles[i]
            _save()
            return True
    return False


@mcp.tool
def list_kb_articles():
    return sorted(kb_articles, key=lambda a: a.get("created_at", ""))


@mcp.tool
def get_kb_article(article_id):
    for i in kb_articles:
        if i["id"] == article_id:
            return i
    return None


@mcp.resource("tickets://dashboard")
def dashboard_resource():
    lines = ["# IT Service Desk Dashboard"]
    open_t = sum(1 for t in tickets if t.get("status") == "open")
    pending_t = sum(1 for t in tickets if t.get("status") == "pending")
    resolved_t = sum(1 for t in tickets if t.get("status") == "resolved")
    lines.append(f"- Open: {open_t} | Pending: {pending_t} | Resolved: {resolved_t}")
    if not tickets:
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
