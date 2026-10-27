"""
MCP Security Scanner MCP Server
A FastMCP server for CVE detection, tool-poisoning identification,
vulnerability tracking, and security alert generation.
"""
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP
mcp = FastMCP(name="MCP Security Scanner", instructions=(
    "Scans MCP servers for CVEs, command injection flaws, "
    "tool-poisoning indicators, vulnerability tracking, and security compliance reporting."))
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "security_scans.json"
def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"scans": [], "vulnerabilities": [], "cves": [], "next_id": 1}
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
        items.append({"name": p.name, "bytes": p.stat().st_size, "modified_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat()})
    return items
@mcp.tool
def restore_backup(name):
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError("Unknown backup: " + name)
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}
_data = _load_data()
scans = _data.get("scans", [])
vulnerabilities = _data.get("vulnerabilities", [])
cves = _data.get("cves", [])
_next_id = _data.get("next_id", 1)
def _save():
    _save_data({"scans": scans, "vulnerabilities": vulnerabilities, "cves": cves, "next_id": _next_id})
def _get_next_id():
    global _next_id
    result, _next_id = _next_id, _next_id + 1
    return result
@mcp.tool
def run_cve_scan(selector, targets=None, severity_filter=None, exclude_patterns=None):
    scan = {"id": _get_next_id(), "selector": selector, "targets": targets or [], "severity_filter": severity_filter,
            "scanned_at": datetime.now().isoformat(), "status": "running", "results": [], "vulnerable_targets": [], "in_progress": True}
    scans.append(scan); _save(); return scan
@mcp.tool
def get_scan(scan_id):
    for i in scans:
        if i["id"] == scan_id:
            return i
    return None
@mcp.tool
def complete_scan(scan_id, findings, tool_poisoned=None):
    for i, s in enumerate(scans):
        if s["id"] == scan_id:
            s["status"] = "completed"; s["in_progress"] = False
            s["findings"] = findings or []; s["vulnerable_targets"] = tool_poisoned or []
            s["completed_at"] = datetime.now().isoformat(); _save(); return s
    return None
@mcp.tool
def add_vulnerability(title, category, severity=None, target=None, cvss_score=None, cve_id=None, description=None, mitigation=None, references=None):
    vuln = {"id": _get_next_id(), "title": title, "category": category, "severity": severity or "medium", "target": target,
            "cvss_score": cvss_score or "0.0", "cve_id": cve_id or "NONE", "description": description or "",
            "mitigation": mitigation or "", "references": references or [], "reported_at": datetime.now().isoformat(), "status": "new"}
    vulnerabilities.append(vuln); _save(); return vuln
@mcp.tool
def get_vulnerability(vuln_id):
    for i in vulnerabilities:
        if i["id"] == vuln_id:
            return i
    return None
@mcp.tool
def search_vulnerabilities(query):
    q = query.lower()
    return [v for v in vulnerabilities if q in v.get("title", "").lower() or q in v.get("category", "").lower()]
@mcp.tool
def get_vulnerability_count():
    return len(vulnerabilities)
@mcp.tool
def list_scans():
    return sorted(scans, key=lambda s: s.get("scanned_at", ""))
@mcp.tool
def get_scan_count():
    return len(scans)
@mcp.resource("security://dashboard")
def dashboard_resource():
    lines = ["# Security Scanner Dashboard", "Total Scans: " + str(len(scans)), "Vulnerabilities: " + str(len(vulnerabilities))]
    return "\n".join(lines)
@mcp.resource("security://summary")
def summary_resource():
    lines = ["# Security Summary"]
    return "\n".join(lines)
if __name__ == "__main__":
    mcp.run()
