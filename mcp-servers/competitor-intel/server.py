"""
Competitor Intelligence Tracker MCP Server
A FastMCP server for tracking competitors, pricing, new products,
launches, and market alerts for business intelligence.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Competitor Intelligence Tracker",
    instructions=(
        "Tracks competitors, price tracking, new product tracking, "
        "launch tracking, and market alerts. Provides competitor "
        "benchmarks, price comparison, new product alerts, launch "
        "tracking, and trend analysis."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "competitors.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"competitors": [], "price_tracks": [], "product_tracks": [],
            "launches": [], "alerts": [], "next_id": 1}


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
competitors = _data.get("competitors", [])
price_tracks = _data.get("price_tracks", [])
product_tracks = _data.get("product_tracks", [])
launches = _data.get("launches", [])
alerts = _data.get("alerts", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"competitors": competitors, "price_tracks": price_tracks,
               "product_tracks": product_tracks, "launches": launches,
               "alerts": alerts, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


@mcp.tool
def add_competitor(name, industry, website, market_share=None, ranking=None, region="global"):
    competitor = {
        "id": _get_next_id(), "name": name, "industry": industry,
        "website": website, "market_share": market_share, "ranking": ranking,
        "region": region,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    competitors.append(competitor)
    _save()
    return competitor


@mcp.tool
def get_competitor(competitor_id):
    for i in competitors:
        if i["id"] == competitor_id:
            return i
    return None


@mcp.tool
def search_competitors(query):
    q = query.lower()
    results = [c for c in competitors if q in c.get("name", "").lower() or q in c.get("industry", "").lower()]
    return results


@mcp.tool
def add_price_track(competitor_id, product_name, current_price, currency="USD", tracking_notes=None):
    track = {
        "id": _get_next_id(), "competitor_id": competitor_id,
        "product_name": product_name, "current_price": current_price,
        "currency": currency, "tracking_notes": tracking_notes or "",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    price_tracks.append(track)
    _save()
    return track


@mcp.tool
def record_price_change(track_id, new_price, currency="USD", source=None):
    for i, t in enumerate(price_tracks):
        if t["id"] == track_id:
            t["current_price"] = new_price
            t["currency"] = currency
            t["updated_at"] = datetime.now().isoformat()
            _save()
            return t
    return None


@mcp.tool
def get_price_tracking(competitor_id):
    return [t for t in price_tracks if t.get("competitor_id") == competitor_id]


@mcp.tool
def list_price_tracks():
    return sorted(price_tracks, key=lambda t: t.get("created_at", ""))


@mcp.tool
def get_price_tracks_count():
    return len(price_tracks)


@mcp.tool
def add_product_track(name, category, price_range, competitive_status, platform=None):
    product = {
        "id": _get_next_id(), "name": name, "category": category,
        "price_range": price_range, "competitive_status": competitive_status,
        "platform": platform,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    product_tracks.append(product)
    _save()
    return product


@mcp.tool
def get_product_track(product_id):
    for i in product_tracks:
        if i["id"] == product_id:
            return i
    return None


@mcp.tool
def list_product_tracks():
    return sorted(product_tracks, key=lambda p: p.get("name", ""))


@mcp.tool
def add_launch(title, announcement_date, launch_date, product_category, platforms=None, competitive_impact="unknown"):
    launch = {
        "id": _get_next_id(), "title": title, "announcement_date": announcement_date,
        "launch_date": launch_date, "product_category": product_category,
        "platforms": platforms or [], "competitive_impact": competitive_impact,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    launches.append(launch)
    _save()
    return launch


@mcp.tool
def get_launch(launch_id):
    for i in launches:
        if i["id"] == launch_id:
            return i
    return None


@mcp.tool
def list_launches():
    return sorted(launches, key=lambda l: l.get("launch_date", ""))


@mcp.tool
def add_alert(title, category, priority="medium", description="", triggered_by=None, status="active"):
    alert = {
        "id": _get_next_id(), "title": title, "category": category,
        "priority": priority, "description": description,
        "triggered_by": triggered_by, "status": status,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    alerts.append(alert)
    _save()
    return alert


@mcp.tool
def get_alert(alert_id):
    for i in alerts:
        if i["id"] == alert_id:
            return i
    return None


@mcp.tool
def update_alert(alert_id, **kwargs):
    for i, a in enumerate(alerts):
        if a["id"] == alert_id:
            for k, v in kwargs.items():
                if v is not None:
                    a[k] = v
            a["updated_at"] = datetime.now().isoformat()
            _save()
            return a
    return None


@mcp.tool
def delete_alert(alert_id):
    for i, a in enumerate(alerts):
        if a["id"] == alert_id:
            del alerts[i]
            _save()
            return True
    return False


@mcp.tool
def list_alerts():
    return sorted(alerts, key=lambda a: a.get("created_at", ""))


@mcp.tool
def list_competitors():
    return sorted(competitors, key=lambda c: c.get("name", ""))


@mcp.tool
def get_competitor_count():
    return len(competitors)


@mcp.tool
def get_competitor_benchmarks():
    return {"competitors": len(competitors), "price_tracks": len(price_tracks),
            "product_tracks": len(product_tracks), "launches": len(launches)}


@mcp.resource("competitors://dashboard")
def dashboard_resource():
    lines = ["# Competitor Intelligence Dashboard"]
    lines.append("Competitors: {} | Price Tracks: {} | Product Tracks: {}"
                 .format(len(competitors), len(price_tracks), len(product_tracks)))
    lines.append("Launches: {} | Alerts: {}"
                 .format(len(launches), len(alerts)))
    if not competitors:
        lines.append("")
    return "\n".join(lines)


@mcp.resource("competitors://summary")
def summary_resource():
    lines = ["# Competitor Intelligence Summary"]
    active = sum(1 for a in alerts if a.get("status") == "active")
    lines.append("Active Alerts: {}".format(active))
    lines.append("Competitors: {} | Price Tracks: {}"
                 .format(len(competitors), len(price_tracks)))
    if not alerts:
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
