"""
Referral Program Manager MCP Server
A FastMCP server for employee referral tracking, rewards, and
referral program management for talent acquisition.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json, os, threading, tempfile
from fastmcp import FastMCP

mcp = FastMCP(
    name="Referral Program Manager",
    instructions=(
        "Manages employee referral programs: employee referrals, "
        "candidate tracking, rewards, acceptance, hiring status."
    ),
)

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "referrals.json"


def _load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"referrals": [], "rewards": [], "next_id": 1}


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
        raise ValueError("Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


_data = _load_data()
referrals = _data.get("referrals", [])
rewards = _data.get("rewards", [])
_next_id = _data.get("next_id", 1)


def _save():
    _save_data({"referrals": referrals, "rewards": rewards, "next_id": _next_id})


def _get_next_id():
    global _next_id
    result = _next_id
    _next_id += 1
    return result


@mcp.tool
def add_referral(employee_id, employee_name, referral_code, position,
                 competitor_name=None, department=None, candidate_email=None):
    ref = {
        "id": _get_next_id(), "employee_id": employee_id,
        "employee_name": employee_name, "referral_code": referral_code,
        "position": position, "competitor_name": competitor_name,
        "department": department, "candidate_email": candidate_email,
        "status": "active", "stage": "application_submitted",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    referrals.append(ref)
    _save()
    return ref


@mcp.tool
def get_referral(referral_id):
    for i in referrals:
        if i["id"] == referral_id:
            return i
    return None


@mcp.tool
def search_referrals(query):
    q = query.lower()
    results = [r for r in referrals if q in r.get("employee_name", "").lower() or q in r.get("referral_code", "").lower()]
    return results


@mcp.tool
def update_referral(referral_id, **kwargs):
    for i, r in enumerate(referrals):
        if r["id"] == referral_id:
            for k, v in kwargs.items():
                if v is not None:
                    r[k] = v
            r["updated_at"] = datetime.now().isoformat()
            _save()
            return r
    return None


@mcp.tool
def delete_referral(referral_id):
    for i, r in enumerate(referrals):
        if r["id"] == referral_id:
            del referrals[i]
            _save()
            return True
    return False


@mcp.tool
def list_referrals():
    return sorted(referrals, key=lambda r: r.get("created_at", ""))


@mcp.tool
def get_referral_count():
    return len(referrals)


@mcp.tool
def add_reward(reward_id, referral_code, reward_type, reward_amount, currency="USD"):
    reward = {
        "id": reward_id, "referral_code": referral_code,
        "reward_type": reward_type, "reward_amount": reward_amount,
        "currency": currency,
        "created_at": datetime.now().isoformat(),
        "redeemed_at": None, "redeemed_by": None,
    }
    rewards.append(reward)
    _save()
    return reward


@mcp.tool
def get_reward(reward_id):
    for i in rewards:
        if i["id"] == reward_id:
            return i
    return None


@mcp.tool
def list_rewards():
    return sorted(rewards, key=lambda r: r.get("created_at", ""))


@mcp.tool
def get_reward_count():
    return len(rewards)


@mcp.tool
def redeem_reward(reward_id, redeemed_by):
    for i, r in enumerate(rewards):
        if r["id"] == reward_id and r.get("redeemed_at") is None:
            r["redeemed_at"] = datetime.now().isoformat()
            r["redeemed_by"] = redeemed_by
            r["updated_at"] = datetime.now().isoformat()
            _save()
            return r
    return None


@mcp.resource("referrals://dashboard")
def dashboard_resource():
    lines = ["# Referral Program Dashboard"]
    active = sum(1 for r in referrals if r.get("status") == "active")
    lines.append("Active Referrals: {}".format(active))
    lines.append("Total: {}".format(len(referrals)))
    if not referrals:
        lines.append("")
    return "\n".join(lines)


@mcp.resource("referrals://summary")
def summary_resource():
    lines = ["# Referral Program Summary"]
    redeemed = sum(1 for r in rewards if r.get("redeemed_at"))
    lines.append("Rewards Redeemed: {}".format(redeemed))
    lines.append("Rewards Available: {}".format(len(rewards) - redeemed))
    if not rewards:
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
