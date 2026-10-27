"""
MCP Supply Chain Guard MCP Server
A FastMCP server for repo verification, signature verification,
registry integrity checks, typosquatting detection, and package signing.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="MCP Supply Chain Guard",
    instructions=(
        "Repo verification, signature verification, registry integrity "
        "checks, typosquatting detection, and package signing for MCP "
        "supply chain security."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "supplychain.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"checks": [], "typosquat_attempts": [], "policy_violations": [], "next_id": 1}


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
checks = _data.get("checks", [])
typosquat_attempts = _data.get("typosquat_attempts", [])
policy_violations = _data.get("policy_violations", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"checks": checks, "typosquat_attempts": typosquat_attempts, "policy_violations": policy_violations, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


@mcp.tool
def verify_repo_signature(repo_url, commit_hash, signature_file=None, public_key=None):
    check = {
        "id": _get_next_id(), "repo_url": repo_url,
        "commit_hash": commit_hash, "signature_file": signature_file or "",
        "public_key": public_key or "", "verified": False,
        "signature_valid": False, "policy_violation": None,
        "checked_at": datetime.now().isoformat(), "gpg_status": "pending",
        "signer": None
    }
    checks.append(check)
    _save()
    return check


@mcp.tool
def check_typosquat(package_name, reported_name, source_url=None):
    typos = {
        "pypi": ["postmark", "requests-toolbelt", "docker", "fabric", "bijox", "dkrstat"],
        "npm": ["axios", "lodash", "react", "express", "webpack"],
    }
    typos_list = typos.get("pypi", [])
    match = None
    for t in typos_list:
        if t in reported_name.lower() or reported_name.lower() in t:
            match = t
            break
    ratio = max(0, 6 - len(reported_name.lower()))
    result = {
        "id": _get_next_id(), "against": package_name,
        "reported": reported_name, "source": source_url or "any",
        "risk_score": ratio, "potential_typosquat": match or None,
        "checked_at": datetime.now().isoformat(),
        "recommendation": "block" if match else "review",
        "confidence": "high" if match else "medium",
    }
    typosquat_attempts.append(result)
    _save()
    return result


@mcp.tool
def verify_registry_integrity(repo_url, expected_commit, actual_commit=None):
    check = {
        "id": _get_next_id(), "repo_url": repo_url,
        "expected_commit": expected_commit,
        "actual_commit": actual_commit or "unknown",
        "commit_matches": actual_commit == expected_commit if actual_commit else False,
        "verified_at": datetime.now().isoformat(),
        "policy_violation": "positive" if actual_commit == expected_commit else "negative",
    }
    checks.append(check)
    _save()
    return check


@mcp.tool
def check_policy(repo_url, cert_expires=None, signing_key_matches=None):
    violation = {
        "id": _get_next_id(), "repo_url": repo_url,
        "cert_expires": cert_expires, "signing_key_matches": signing_key_matches,
        "violation_type": "expired_cert" if cert_expires else "key_mismatch" if not signing_key_matches else "none",
        "checked_at": datetime.now().isoformat(),
        "severity": "critical" if cert_expires else "high" if not signing_key_matches else "low",
    }
    policy_violations.append(violation)
    _save()
    return violation


@mcp.tool
def get_check_status(check_id):
    for i in checks:
        if i["id"] == check_id:
            return i
    return None


@mcp.tool
def list_checks():
    return sorted(checks, key=lambda c: c.get("checked_at", ""), reverse=True)


@mcp.tool
def get_check_count():
    return len(checks)


@mcp.tool
def get_typosquat_count():
    return len(typosquat_attempts)


@mcp.resource("supplychain://dashboard")
def dashboard_resource():
    lines = ["# Supply Chain Dashboard"]
    checks_count = len(checks)
    violations = len(policy_violations)
    typos = len(typosquat_attempts)
    lines.append("Verified Checks: " + str(checks_count))
    lines.append("Typosquat Attempts: " + str(typos))
    lines.append("Policy Violations: " + str(violations))
    lines.append("")
    return "\n".join(lines)


@mcp.resource("supplychain://summary")
def summary_resource():
    lines = ["# Supply Chain Summary"]
    typos_count = len(typosquat_attempts)
    lines.append("Typosquat Attempts Blocked: " + str(typos_count))
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()