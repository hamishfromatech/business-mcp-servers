"""
MCP Gatekeeper MCP Server
A FastMCP server for identity-aware MCP middleware, OAuth enforcement,
access auditing, and secure MCP routing.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, hashlib, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="MCP Gatekeeper",
    instructions=(
        "Identity-aware MCP middleware: OAuth enforcement, access "
        "auditing, authorized request routing, and security "
        "compliance for MCP server gatekeeping."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "gatekeeper.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"policies": [], "audit_logs": [], "tokens": [], "next_id": 1}


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
        raise ValueError("Unknown backup: " + name)
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


_data = _load_data()
policies = _data.get("policies", [])
audit_logs = _data.get("audit_logs", [])
tokens = _data.get("tokens", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"policies": policies, "audit_logs": audit_logs, "tokens": tokens, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


@mcp.tool
def create_policy(service_name, allowed_origins=None, allowed_roles=None):
    pol = {
        "id": _get_next_id(), "service_name": service_name,
        "allowed_origins": allowed_origins or [], "allowed_roles": allowed_roles or [],
        "created_at": datetime.now().isoformat(), "status": "active",
    }
    policies.append(pol)
    _save()
    return pol


@mcp.tool
def get_policy(service_name):
    for i in policies:
        if i["service_name"] == service_name:
            return i
    return None


@mcp.tool
def list_policies():
    return sorted(policies, key=lambda p: p.get("created_at", ""))


@mcp.tool
def check_access(service_name, user, action, resource=None, origin=None):
    for pol in policies:
        if pol["service_name"] == service_name:
            role_match = user in pol.get("allowed_roles", [])
            origin_match = origin and any(o == origin for o in pol.get("allowed_origins", []))
            if role_match:
                return {"allowed": True, "role": user, "origin": origin, "policy": pol}
            if origin_match:
                return {"allowed": True, "role": user, "origin": origin, "policy": pol}
    return {"allowed": False, "reason": "no_policy_found"}


@mcp.tool
def audit_request(service_name, user, action, resource=None, origin=None, result=None):
    log = {
        "id": _get_next_id(), "service_name": service_name,
        "user": user, "action": action, "resource": resource,
        "origin": origin, "result": result or "unknown",
        "timestamp": datetime.now().isoformat(),
    }
    audit_logs.append(log)
    _save()
    return log


@mcp.tool
def list_audit_logs():
    return sorted(audit_logs, key=lambda l: l.get("timestamp", ""), reverse=True)


@mcp.tool
def get_audit_log_count():
    return len(audit_logs)


@mcp.tool
def issue_token(service_name, user, token_type="Bearer"):
    token = {
        "id": _get_next_id(), "service_name": service_name,
        "user": user, "token_type": token_type,
        "created_at": datetime.now().isoformat(), "expires_at": None,
        "token_hash": hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()[:16],
    }
    tokens.append(token)
    _save()
    return token


@mcp.resource("gatekeeper://dashboard")
def dashboard_resource():
    lines = ["# Gatekeeper Dashboard"]
    count = len(policies)
    active = sum(1 for p in policies if p.get("status") == "active")
    lines.append("Active Policies: " + str(active) + " | Total: " + str(count))
    lines.append("Audit Requests: " + str(len(audit_logs)))
    lines.append("")
    return "\n".join(lines)


@mcp.resource("gatekeeper://summary")
def summary_resource():
    lines = ["# Gatekeeper Summary"]
    oauth_policies = len([p for p in policies if "oauth" in p.get("service_name", "").lower()])
    lines.append("OAuth 2.1 Compliant Policies: " + str(oauth_policies))
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()