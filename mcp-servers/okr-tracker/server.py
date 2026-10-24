"""
OKR Tracker MCP Server
A FastMCP server for objectives, key results, weekly check-ins, and progress
rollups.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
from enum import Enum
import json
import os
import shutil
import atexit
import tempfile
import threading
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="OKR Tracker",
    instructions=(
        "A goals server for tracking objectives and key results with check-ins, "
        "confidence levels, and progress rollups."
    ),
)


class ObjectiveStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"
    DONE = "done"
    CANCELLED = "cancelled"


class KeyResult(BaseModel):
    """A measurable key result belonging to an objective."""
    id: int
    title: str
    metric_unit: Optional[str] = None
    start_value: float = 0
    target_value: float = 0
    current_value: float = 0
    confidence: Optional[int] = None
    updated_at: str


class Objective(BaseModel):
    """An objective with its key results and rolled-up progress."""
    id: int
    title: str
    description: Optional[str] = None
    owner: str
    period: str
    status: str
    key_results: list[KeyResult] = []
    progress: float = 0.0
    created_at: str
    updated_at: str


class CheckIn(BaseModel):
    """A progress check-in."""
    id: int
    objective_id: int
    key_result_id: Optional[int] = None
    value: Optional[float] = None
    confidence: Optional[int] = None
    note: Optional[str] = None
    created_at: str


# Data persistence setup (MCP_DATA_DIR allows tests / custom deployments)
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "okrs.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "objectives": {}, "check_ins": {},
        "next_objective_id": 1, "next_key_result_id": 1, "next_check_in_id": 1,
    }


_write_lock = threading.Lock()
_last_payload: Optional[str] = None
_pending_payload: Optional[str] = None
_flush_timer: Optional[threading.Timer] = None
_WRITE_DEBOUNCE_MS = int(os.environ.get("MCP_WRITE_DEBOUNCE_MS", "0") or 0)


def _write_payload(payload: str) -> None:
    """Atomically replace the data file with serialized JSON."""
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


def _flush_pending() -> None:
    """Write any deferred payload to disk immediately."""
    global _pending_payload
    with _write_lock:
        if _pending_payload is not None:
            payload, _pending_payload = _pending_payload, None
            _write_payload(payload)


def _save_data(data: dict) -> None:
    """Save data atomically, skipping unchanged writes.

    Writes to a temp file in the same directory then os.replace()s it into
    place, so an interrupted write can never leave a truncated/corrupt file.
    Set MCP_WRITE_DEBOUNCE_MS>0 to defer disk I/O; pending writes are flushed
    on exit and by the flush_data tool.
    """
    global _pending_payload, _flush_timer
    payload = json.dumps(data, indent=2, default=str)
    if _WRITE_DEBOUNCE_MS <= 0:
        with _write_lock:
            if payload != _last_payload:
                _write_payload(payload)
        return
    with _write_lock:
        if payload == _last_payload:
            return
        _pending_payload = payload
        if _flush_timer is not None:
            _flush_timer.cancel()
        _flush_timer = threading.Timer(_WRITE_DEBOUNCE_MS / 1000.0, _flush_pending)
        _flush_timer.daemon = True
        _flush_timer.start()


atexit.register(_flush_pending)


@mcp.tool
def flush_data() -> dict:
    """Flush any deferred writes to disk immediately."""
    _flush_pending()
    return {"flushed": True, "path": str(DATA_FILE), "debounce_ms": _WRITE_DEBOUNCE_MS}


@mcp.tool
def backup_data() -> dict:
    """Copy the current data file into data/backups/ with a timestamp."""
    _flush_pending()
    if not DATA_FILE.exists():
        raise ValueError("No data file to back up yet")
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = backup_dir / f"{DATA_FILE.stem}-{stamp}.json"
    shutil.copy2(DATA_FILE, target)
    return {"backup": str(target), "bytes": target.stat().st_size}


@mcp.tool
def list_backups() -> list[dict]:
    """List available data backups, newest first."""
    backup_dir = DATA_DIR / "backups"
    if not backup_dir.exists():
        return []
    items = []
    for path in sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        items.append({
            "name": path.name,
            "bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        })
    return items


@mcp.tool
def restore_backup(name: str) -> dict:
    """Restore a backup, replacing current data. Restart the server to load it."""
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


# Initialize data
_data = _load_data()
objectives: dict[int, dict] = {int(k): v for k, v in _data.get("objectives", {}).items()}
check_ins: dict[int, dict] = {int(k): v for k, v in _data.get("check_ins", {}).items()}

_next_objective_id = _data.get("next_objective_id", 1)
_next_key_result_id = _data.get("next_key_result_id", 1)
_next_check_in_id = _data.get("next_check_in_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "objectives": objectives, "check_ins": check_ins,
        "next_objective_id": _next_objective_id,
        "next_key_result_id": _next_key_result_id,
        "next_check_in_id": _next_check_in_id,
    })


def _next_id(kind: str) -> int:
    """Allocate the next integer id."""
    global _next_objective_id, _next_key_result_id, _next_check_in_id
    if kind == "objective":
        value = _next_objective_id
        _next_objective_id += 1
    elif kind == "key_result":
        value = _next_key_result_id
        _next_key_result_id += 1
    else:
        value = _next_check_in_id
        _next_check_in_id += 1
    return value


# --- helpers -----------------------------------------------------------------
def _now() -> str:
    return datetime.now().isoformat()


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _as_list(value) -> list:
    """Accept a real list or a JSON-stringified list from MCP clients."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, TypeError):
            return [value]
    return value


def _kr_progress(kr: dict) -> float:
    """Progress toward a key result's target (handles decreasing targets)."""
    start = float(kr.get("start_value", 0))
    target = float(kr.get("target_value", 0))
    current = float(kr.get("current_value", start))
    if target == start:
        return 1.0 if current >= target else 0.0
    return round(_clamp((current - start) / (target - start)), 4)


def _objective_progress(entry: dict) -> float:
    """Objective progress is the mean of its key results' progress."""
    krs = entry.get("key_results", [])
    if not krs:
        return 0.0
    return round(sum(_kr_progress(kr) for kr in krs) / len(krs), 4)


def _objective_model(entry: dict) -> Objective:
    payload = dict(entry)
    payload["progress"] = _objective_progress(entry)
    return Objective(**payload)


def _find_key_result(entry: dict, key_result_id: int) -> Optional[dict]:
    for kr in entry.get("key_results", []):
        if int(kr["id"]) == key_result_id:
            return kr
    return None


def _validate_status(status: str) -> str:
    allowed = {s.value for s in ObjectiveStatus}
    if status not in allowed:
        raise ValueError(f"status must be one of {sorted(allowed)}")
    return status


def _validate_confidence(confidence: Optional[int]) -> Optional[int]:
    if confidence is None:
        return None
    if not 0 <= confidence <= 100:
        raise ValueError("confidence must be between 0 and 100")
    return confidence


# --- objectives --------------------------------------------------------------
@mcp.tool
def create_objective(title: str, owner: str, period: str,
                     description: Optional[str] = None,
                     status: str = "on_track") -> Objective:
    """Create an objective.

    Args:
        title: Objective statement
        owner: Person accountable
        period: Period label, e.g. "2026-Q4"
        description: Optional detail
        status: on_track | at_risk | off_track | done | cancelled
    """
    _validate_status(status)
    objective_id = _next_id("objective")
    entry = {
        "id": objective_id, "title": title, "description": description,
        "owner": owner, "period": period, "status": status,
        "key_results": [], "created_at": _now(), "updated_at": _now(),
    }
    objectives[objective_id] = entry
    _save()
    return _objective_model(entry)


@mcp.tool
def bulk_add_key_results(objective_id: int,
                         key_result_specs: list[dict]) -> list[KeyResult]:
    """Add many key results to an objective in a single disk write.

    Each spec requires title and target_value; optional start_value,
    current_value, metric_unit, confidence.
    """
    entry = objectives.get(objective_id)
    if entry is None:
        raise ValueError(f"Unknown objective: {objective_id}")
    created = []
    for spec in _as_list(key_result_specs):
        if not isinstance(spec, dict):
            raise ValueError(f"Invalid key result spec: {spec!r}")
        confidence = spec.get("confidence")
        _validate_confidence(confidence)
        start_value = float(spec.get("start_value", 0))
        kr = KeyResult(
            id=_next_id("key_result"),
            title=spec["title"],
            metric_unit=spec.get("metric_unit"),
            start_value=start_value,
            target_value=float(spec["target_value"]),
            current_value=float(spec.get("current_value", start_value)),
            confidence=confidence,
            updated_at=_now(),
        )
        entry["key_results"].append(kr.model_dump())
        created.append(kr)
    if created:
        entry["updated_at"] = _now()
        _save()
    return created


@mcp.tool
def get_objective(objective_id: int) -> Optional[Objective]:
    """Retrieve an objective with computed progress."""
    entry = objectives.get(objective_id)
    return _objective_model(entry) if entry else None


@mcp.tool
def list_objectives(period: Optional[str] = None, owner: Optional[str] = None,
                    status: Optional[str] = None,
                    limit: int = 100, offset: int = 0) -> list[Objective]:
    """List objectives with optional filters."""
    result = []
    for entry in objectives.values():
        if period is not None and entry["period"] != period:
            continue
        if owner is not None and entry["owner"] != owner:
            continue
        if status is not None and entry["status"] != status:
            continue
        result.append(_objective_model(entry))
    result.sort(key=lambda o: o.created_at, reverse=True)
    return result[offset:offset + limit]


@mcp.tool
def update_objective(objective_id: int, title: Optional[str] = None,
                     description: Optional[str] = None, owner: Optional[str] = None,
                     period: Optional[str] = None,
                     status: Optional[str] = None) -> Optional[Objective]:
    """Update objective metadata or status."""
    entry = objectives.get(objective_id)
    if entry is None:
        return None
    if status is not None:
        _validate_status(status)
        entry["status"] = status
    for field, value in (("title", title), ("description", description),
                         ("owner", owner), ("period", period)):
        if value is not None:
            entry[field] = value
    entry["updated_at"] = _now()
    _save()
    return _objective_model(entry)


@mcp.tool
def delete_objective(objective_id: int) -> bool:
    """Delete an objective and its check-ins."""
    if objective_id not in objectives:
        return False
    del objectives[objective_id]
    for check_in_id in [cid for cid, c in check_ins.items()
                        if int(c["objective_id"]) == objective_id]:
        del check_ins[check_in_id]
    _save()
    return True


# --- key results -------------------------------------------------------------
@mcp.tool
def add_key_result(objective_id: int, title: str, target_value: float,
                   start_value: float = 0, metric_unit: Optional[str] = None,
                   current_value: Optional[float] = None,
                   confidence: Optional[int] = None) -> Optional[KeyResult]:
    """Add a measurable key result to an objective."""
    entry = objectives.get(objective_id)
    if entry is None:
        return None
    _validate_confidence(confidence)
    kr = KeyResult(
        id=_next_id("key_result"), title=title, metric_unit=metric_unit,
        start_value=start_value, target_value=target_value,
        current_value=start_value if current_value is None else current_value,
        confidence=confidence, updated_at=_now(),
    )
    entry["key_results"].append(kr.model_dump())
    entry["updated_at"] = _now()
    _save()
    return kr


@mcp.tool
def update_key_result(objective_id: int, key_result_id: int,
                      title: Optional[str] = None,
                      metric_unit: Optional[str] = None,
                      start_value: Optional[float] = None,
                      target_value: Optional[float] = None,
                      current_value: Optional[float] = None,
                      confidence: Optional[int] = None) -> Optional[KeyResult]:
    """Update a key result's definition or current value."""
    entry = objectives.get(objective_id)
    if entry is None:
        return None
    kr = _find_key_result(entry, key_result_id)
    if kr is None:
        return None
    _validate_confidence(confidence)
    for field, value in (("title", title), ("metric_unit", metric_unit),
                         ("start_value", start_value), ("target_value", target_value),
                         ("current_value", current_value), ("confidence", confidence)):
        if value is not None:
            kr[field] = value
    kr["updated_at"] = _now()
    entry["updated_at"] = _now()
    _save()
    return KeyResult(**kr)


@mcp.tool
def delete_key_result(objective_id: int, key_result_id: int) -> bool:
    """Remove a key result from an objective."""
    entry = objectives.get(objective_id)
    if entry is None:
        return False
    before = len(entry.get("key_results", []))
    entry["key_results"] = [kr for kr in entry.get("key_results", [])
                            if int(kr["id"]) != key_result_id]
    if len(entry["key_results"]) == before:
        return False
    entry["updated_at"] = _now()
    _save()
    return True


# --- check-ins ---------------------------------------------------------------
@mcp.tool
def check_in(objective_id: int, value: Optional[float] = None,
             key_result_id: Optional[int] = None,
             confidence: Optional[int] = None,
             note: Optional[str] = None) -> CheckIn:
    """Record a check-in, optionally updating a key result's value."""
    entry = objectives.get(objective_id)
    if entry is None:
        raise ValueError(f"Unknown objective: {objective_id}")
    _validate_confidence(confidence)
    if key_result_id is not None:
        kr = _find_key_result(entry, key_result_id)
        if kr is None:
            raise ValueError(f"Unknown key result: {key_result_id}")
        if value is not None:
            kr["current_value"] = value
        if confidence is not None:
            kr["confidence"] = confidence
        kr["updated_at"] = _now()
    entry["updated_at"] = _now()

    check_in_id = _next_id("check_in")
    record = CheckIn(
        id=check_in_id, objective_id=objective_id, key_result_id=key_result_id,
        value=value, confidence=confidence, note=note, created_at=_now(),
    )
    check_ins[check_in_id] = record.model_dump()
    _save()
    return record


@mcp.tool
def list_check_ins(objective_id: Optional[int] = None,
                   limit: int = 100) -> list[CheckIn]:
    """List check-ins, newest first."""
    result = [CheckIn(**c) for c in check_ins.values()
              if objective_id is None or int(c["objective_id"]) == objective_id]
    result.sort(key=lambda c: c.created_at, reverse=True)
    return result[:limit]


# --- reporting ---------------------------------------------------------------
@mcp.tool
def get_progress(objective_id: int) -> Optional[dict]:
    """Detailed per-key-result and overall progress for an objective."""
    entry = objectives.get(objective_id)
    if entry is None:
        return None
    krs = []
    for kr in entry.get("key_results", []):
        krs.append({
            "key_result_id": kr["id"], "title": kr["title"],
            "start_value": kr.get("start_value", 0),
            "target_value": kr.get("target_value", 0),
            "current_value": kr.get("current_value", 0),
            "metric_unit": kr.get("metric_unit"),
            "progress": _kr_progress(kr),
            "confidence": kr.get("confidence"),
        })
    return {
        "objective_id": objective_id, "title": entry["title"],
        "owner": entry["owner"], "period": entry["period"],
        "status": entry["status"],
        "progress": _objective_progress(entry),
        "key_results": krs,
    }


@mcp.tool
def get_okr_summary(period: Optional[str] = None) -> dict:
    """Roll up OKR health across objectives for a period."""
    scope = [e for e in objectives.values()
             if period is None or e["period"] == period]
    by_status: dict[str, int] = {}
    for entry in scope:
        by_status[entry["status"]] = by_status.get(entry["status"], 0) + 1
    progress_values = [_objective_progress(e) for e in scope]
    at_risk = [
        {"objective_id": e["id"], "title": e["title"],
         "progress": _objective_progress(e), "status": e["status"]}
        for e in scope if e["status"] in (ObjectiveStatus.AT_RISK.value,
                                          ObjectiveStatus.OFF_TRACK.value)
    ]
    return {
        "period": period or "all",
        "objectives": len(scope),
        "key_results": sum(len(e.get("key_results", [])) for e in scope),
        "average_progress": round(sum(progress_values) / len(progress_values), 4)
        if progress_values else 0.0,
        "by_status": by_status,
        "at_risk": at_risk,
    }


# --- resources ---------------------------------------------------------------
@mcp.resource("okr://summary")
def get_summary_resource() -> str:
    """OKR summary as formatted text."""
    summary = get_okr_summary()
    lines = [
        f"# OKR Summary ({summary['period']})\n",
        f"- **Objectives:** {summary['objectives']}",
        f"- **Key results:** {summary['key_results']}",
        f"- **Average progress:** {summary['average_progress'] * 100:.1f}%",
    ]
    if summary["at_risk"]:
        lines.append("\n## At risk\n")
        for item in summary["at_risk"]:
            lines.append(f"- #{item['objective_id']} {item['title']} "
                         f"({item['progress'] * 100:.0f}%) - {item['status']}")
    return "\n".join(lines)


@mcp.resource("okr://objectives")
def get_objectives_resource() -> str:
    """All objectives with progress as formatted text."""
    items = list_objectives()
    if not items:
        return "# Objectives\n\nNo objectives yet."
    lines = ["# Objectives\n"]
    for obj in items:
        lines.append(f"## {obj.title} ({obj.period}) - {obj.progress * 100:.0f}%")
        lines.append(f"- Owner: {obj.owner} | Status: {obj.status}")
        for kr in obj.key_results:
            lines.append(f"  - {kr.title}: {kr.current_value}/{kr.target_value} "
                         f"({_kr_progress(kr.model_dump()) * 100:.0f}%)")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
