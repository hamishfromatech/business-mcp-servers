"""
IT Asset Manager MCP Server
A FastMCP server for tracking IT assets, device lifecycle, procurement,
and asset inventory management with low-stock alerts.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="IT Asset Manager",
    instructions=(
        "Tracks IT assets (laptops, monitors, furniture, peripherals), "
        "device lifecycle states (allocated, in-use, maintained, returned, "
        "decommissioned), procurement history, and low-stock alerts."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "assets.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"assets": [], "categories": {}, "next_id": 1}


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
            "name": p.name,
            "bytes": p.stat().st_size,
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
assets = _data.get("assets", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"assets": assets, "categories": {}, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


def _search_assets(query):
    q = query.lower()
    results = []
    for a in assets:
        if any(q in str(v).lower() for k, v in a.items() if v is not None and k != "id"):
            results.append(a)
    return results


@mcp.tool
def add_asset(asset_type, description="", serial_number=None, model_number=None,
              quantity=1, location=None, asset_tag=None, status="in-stock",
              assignee_id=None, assigned_date=None, purchase_date=None,
              supplier=None, warranty_expiry=None, cost=None, notes=None):
    asset = {
        "id": _get_next_id(), "asset_type": asset_type, "description": description,
        "serial_number": serial_number, "model_number": model_number,
        "quantity": quantity, "location": location, "asset_tag": asset_tag,
        "status": status, "assignee_id": assignee_id, "assigned_date": assigned_date,
        "purchase_date": purchase_date, "supplier": supplier, "warranty_expiry": warranty_expiry,
        "cost": cost, "notes": notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    assets.append(asset)
    _save()
    return asset


@mcp.tool
def get_asset(asset_id):
    for a in assets:
        if a["id"] == asset_id:
            return a
    return None


@mcp.tool
def search_assets(query):
    return _search_assets(query)


@mcp.tool
def update_asset(asset_id, **kwargs):
    for i, a in enumerate(assets):
        if a["id"] == asset_id:
            for k, v in kwargs.items():
                if v is not None:
                    a[k] = v
            a["updated_at"] = datetime.now().isoformat()
            _save()
            return a
    return None


@mcp.tool
def delete_asset(asset_id):
    for i, a in enumerate(assets):
        if a["id"] == asset_id:
            del a
            _save()
            return True
    return False


@mcp.tool
def list_assets():
    return sorted(assets, key=lambda a: str(a.get("description", "")))


@mcp.tool
def get_asset_count():
    return len(assets)


@mcp.tool
def get_assets_by_status(status=None):
    if status is None:
        return assets
    return [a for a in assets if a.get("status") == status]


@mcp.tool
def get_assets_by_type(asset_type):
    return [a for a in assets if a.get("asset_type") == asset_type]


@mcp.tool
def get_low_stock_assets():
    return [a for a in assets if a.get("quantity", 0) < 5 and a.get("status") == "in-stock"]


@mcp.tool
def get_warranty_expiring_assets(days=30):
    today = datetime.now().date()
    cutoff = today + timedelta(days=days)
    results = []
    for a in assets:
        if a.get("warranty_expiry"):
            exp = datetime.fromisoformat(a["warranty_expiry"]).date()
            if exp <= cutoff:
                results.append(a)
    return results


@mcp.resource("assets://inventory")
def inventory_resource():
    lines = ["# IT Asset Inventory"]
    for a in sorted(assets, key=lambda x: str(x.get("description", ""))):
        lines.append("- **{}] ({}) — Status: {} | Quantity: {} | Tag: {}"
                     .format(a.get("description", ""), a.get("asset_type", ""),
                             a.get("status"), a.get("quantity"), a.get("asset_tag")))
    if not assets:
        lines.append("No assets in inventory.")
    return "\n".join(lines)


@mcp.resource("assets://status-summary")
def status_summary_resource():
    lines = ["# Asset Status Summary"]
    by_status, by_type, total_value = {}, {}, 0.0
    for a in assets:
        s, t = a.get("status", "unknown"), a.get("asset_type", "other")
        by_status[s] = by_status.get(s, 0) + 1
        by_type[t] = by_type.get(t, 0) + 1
        if a.get("cost"):
            total_value += float(a["cost"])
    for s in sorted(by_status):
        lines.append("- {}: {}".format(s, by_status[s]))
    lines.append("")
    lines.append(" By type: {}, total value: ${}"
                 .format(", ".join("{}: {}".format(k, v) for k, v in sorted(by_type.items())), total_value))
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
