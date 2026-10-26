"""
Vendor Supplier Portal MCP Server
A FastMCP server for vendor/supplier management with onboarding,
scorecards, portal access, and contract integration.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Vendor Supplier Portal",
    instructions=(
        "Manages vendor/supplier onboarding, scorecards, portal access, "
        "and contract linkage for procurement management."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "vendors.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"vendors": [], "scorecards": [], "portal_access": [], "next_id": 1}


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
vendors = _data.get("vendors", [])
scorecards = _data.get("scorecards", [])
portal_access = _data.get("portal_access", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"vendors": vendors, "scorecards": scorecards, "portal_access": portal_access, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


@mcp.tool
def onboard_vendor(name, company, email, category, status="active",
                    onboarding_completed=False, orientation_date=None):
    vendor = {
        "id": _get_next_id(),
        "name": name,
        "company": company,
        "email": email,
        "category": category,
        "status": status,
        "onboarding_completed": onboarding_completed,
        "orientation_date": orientation_date or datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    vendors.append(vendor)
    _save()
    return vendor


@mcp.tool
def get_vendor(vendor_id):
    for i in vendors:
        if i["id"] == vendor_id:
            return i
    return None


@mcp.tool
def search_vendors(query):
    q = query.lower()
    results = []
    for v in vendors:
        if q in v.get("name", "").lower() or q in v.get("company", "").lower():
            results.append(v)
    return results


@mcp.tool
def add_scorecard(vendor_id, criterion, score, rating, comment=""):
    sc = {
        "id": _get_next_id(),
        "vendor_id": vendor_id,
        "criterion": criterion,
        "score": score,
        "rating": rating or "N/A",
        "comment": comment,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    scorecards.append(sc)
    _save()
    return sc


@mcp.tool
def get_vendor_scorecard(vendor_id):
    vendor = None
    for i in vendors:
        if i["id"] == vendor_id:
            vendor = i
            break
    if not vendor:
        return None
    scorecards_for_vendor = [s for s in scorecards if s.get("vendor_id") == vendor_id]
    return {**vendor, "scorecards": scorecards_for_vendor}


@mcp.tool
def delete_scorecard(scorecard_id):
    for i, s in enumerate(scorecards):
        if s["id"] == scorecard_id:
            del scorecards[i]
            _save()
            return True
    return False


@mcp.tool
def list_scorecards():
    return sorted(scorecards, key=lambda s: s.get("created_at", ""))


@mcp.tool
def add_portal_access(vendor_id, access_level, permissions, expires_date=None):
    access = {
        "id": _get_next_id(),
        "vendor_id": vendor_id,
        "access_level": access_level,
        "permissions": permissions or [],
        "expires_date": expires_date or datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    portal_access.append(access)
    _save()
    return access


@mcp.tool
def get_portal_access(vendor_id):
    vendor = None
    for i in vendors:
        if i["id"] == vendor_id:
            vendor = i
            break
    if not vendor:
        return None
    access = [a for a in portal_access if a.get("vendor_id") == vendor_id]
    return {**vendor, "access": access}


@mcp.tool
def delete_portal_access(access_id):
    for i, a in enumerate(portal_access):
        if a["id"] == access_id:
            del portal_access[i]
            _save()
            return True
    return False


@mcp.tool
def list_portal_access():
    return sorted(portal_access, key=lambda a: a.get("created_at", ""))


@mcp.tool
def list_vendors():
    return sorted(vendors, key=lambda v: v.get("name", ""))


@mcp.tool
def get_vendor_count():
    return len(vendors)


@mcp.tool
def get_vendor_categories():
    cats = {}
    for v in vendors:
        c = v.get("category", "uncategorized")
        cats[c] = cats.get(c, 0) + 1
    return cats


@mcp.tool
def list_active_vendors():
    active = [v for v in vendors if v.get("status") == "active"]
    return sorted(active, key=lambda v: v.get("name", ""))


@mcp.tool
def get_compliance_status(vendor_id):
    vendor = None
    for i in vendors:
        if i["id"] == vendor_id:
            vendor = i
            break
    if not vendor:
        return None
    scorecards = [s for s in scorecards if s.get("vendor_id") == vendor_id]
    avg_score = sum(s.get("score", 0) for s in scorecards) / len(scorecards) if scorecards else 0
    return {
        "vendor_id": vendor_id,
        "name": vendor.get("name", ""),
        "company": vendor.get("company", ""),
        "onboarding_completed": vendor.get("onboarding_completed"),
        "orientation_date": vendor.get("orientation_date"),
        "total_scorecards": len(scorecards),
        "average_score": round(avg_score, 1),
    }


@mcp.resource("vendors://dashboard")
def dashboard_resource():
    lines = ["# Vendor Dashboard"]
    active = sum(1 for v in vendors if v.get("status") == "active")
    onboarded = sum(1 for v in vendors if v.get("onboarding_completed"))
    total = len(vendors)
    lines.append(f"- Total vendors: {total}")
    lines.append(f"- Active: {active} | Onboarded: {onboarded}")
    if not vendors:
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
