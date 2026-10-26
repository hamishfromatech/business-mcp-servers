"""
Compliance and Risk Tracker MCP Server
A FastMCP server for corporate governance: regulatory deadlines,
compliance certifications, audit requirements, and risk registers.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Compliance and Risk Tracker",
    instructions=(
        "Manages compliance requirements, risk registers, regulatory deadlines, "
        "audit trails, and internal policies. Tracks LV deadlines with notice "
        "windows and identifies at-risk or breached items."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "compliance.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"compliance_requirements": [], "risks": [], "next_id": 1}


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
compliance = _data.get("compliance_requirements", [])
risks = _data.get("risks", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"compliance_requirements": compliance, "risks": risks, "next_id": _next_id})


def _get_next_id():
    global _next_id
    global_var = _next_id
    _next_id += 1
    return global_var


def _in_range(d, start, end):
    d = datetime.fromisoformat(str(d)).date() if d else None
    if d is None:
        return True
    if start and d < datetime.fromisoformat(str(start)).date():
        return False
    if end and d > datetime.fromisoformat(str(end)).date():
        return False
    return True


@mcp.tool
def add_compliance_requirement(title, description="", regulation=None,
                               standard=None, category=None, deadline=None,
                               status="active", notice_days=30,
                               responsible_team=None,
                               compliance_document_url=None,
                               sub_status=None):
    sub_status = sub_status or "on_track"
    notice_dl = datetime.now().date() + timedelta(days=-notice_days)
    req = {
        "id": _get_next_id(), "title": title, "description": description,
        "regulation": regulation, "standard": standard, "category": category,
        "deadline": deadline, "status": status, "notice_days": notice_days,
        "responsible_team": responsible_team,
        "compliance_document_url": compliance_document_url,
        "sub_status": sub_status,
        "notice_deadline": notice_dl.isoformat(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    compliance.append(req)
    _save()
    return req


@mcp.tool
def get_compliance_requirement(req_id):
    for i in compliance:
        if i["id"] == req_id:
            return i
    return None


@mcp.tool
def search_compliance(query):
    q = query.lower()
    results = [
        i for i in compliance
        if q in i.get("title", "").lower() or q in i.get("description", "").lower()
    ]
    return results


@mcp.tool
def update_compliance_requirement(req_id, **kwargs):
    for i, inc in enumerate(compliance):
        if inc["id"] == req_id:
            for k, v in kwargs.items():
                if v is not None:
                    inc[k] = v
            inc["updated_at"] = datetime.now().isoformat()
            _save()
            return inc
    return None


@mcp.tool
def add_risk(title, description="", impact="medium", likelihood="medium",
             risk_level="medium", category=None, risk_owner=None,
             mitigating_actions=None):
    risk = {
        "id": _get_next_id(), "title": title, "description": description,
        "impact": impact, "likelihood": likelihood, "risk_level": risk_level,
        "category": category, "risk_owner": risk_owner,
        "mitigating_actions": mitigating_actions,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    risks.append(risk)
    _save()
    return risk


@mcp.tool
def get_risk(risk_id):
    for i in risks:
        if i["id"] == risk_id:
            return i
    return None


@mcp.tool
def search_risks(query):
    q = query.lower()
    results = [
        i for i in risks
        if q in i.get("title", "").lower() or q in i.get("description", "").lower()
    ]
    return results


@mcp.tool
def update_risk(risk_id, **kwargs):
    for i, risk in enumerate(risks):
        if risk["id"] == risk_id:
            for k, v in kwargs.items():
                if v is not None:
                    risk[k] = v
            risk["updated_at"] = datetime.now().isoformat()
            _save()
            return risk
    return None


@mcp.tool
def delete_risk(risk_id):
    for i, risk in enumerate(risks):
        if risk["id"] == risk_id:
            del risks[i]
            _save()
            return True
    return False


@mcp.tool
def list_compliance_requirements():
    return sorted(compliance, key=lambda i: i.get("title", ""))


@mcp.tool
def list_risks():
    return sorted(risks, key=lambda i: i.get("title", ""))


@mcp.tool
def get_all_risk_levels():
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}
    for r in risks:
        level = r.get("risk_level", "none").lower()
        counts[level] = counts.get(level, 0) + 1
    return counts


@mcp.tool
def get_non_compliant_requirements():
    return [r for r in compliance if r.get("status") == "active" and r.get("sub_status") == "breached"]


@mcp.tool
def get_overdue_requirements():
    now = datetime.now().date()
    result = []
    for r in compliance:
        notice_dl = datetime.fromisoformat(r.get("notice_deadline", "")).date() if r.get("notice_deadline") else None
        if notice_dl and notice_dl < now:
            result.insert(0, r)
    return result


@mcp.tool
def get_compliance_summary():
    statuses = {r.get("status", "unknown") for r in compliance}
    total = len(compliance)
    active = sum(1 for r in compliance if r.get("status") == "active")
    overdue = sum(1 for r in get_overdue_requirements())
    return {
        "total": total,
        "active": active,
        "overdue": overdue,
        "by_status": {s: sum(1 for r in compliance if r.get("status") == s) for s in statuses},
    }


@mcp.resource("compliance://summary")
def summary_resource():
    lines = ["# Compliance Summary"]
    s = get_compliance_summary()
    lines.append("- Total requirements: {}".format(s["total"]))
    lines.append("- Active: {}".format(s["active"]))
    lines.append("- Overdue notice: {}".format(s["overdue"]))
    if not compliance:
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
