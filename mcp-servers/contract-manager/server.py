"""
Contract Manager MCP Server
A FastMCP server for tracking contracts, renewal deadlines, expiry, and
contractual obligations.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from enum import Enum
import json
import os
import atexit
import shutil
import tempfile
import threading
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Contract Manager",
    instructions=(
        "A contract lifecycle server for tracking agreements, renewal notice "
        "deadlines, expiry, and contractual obligations."
    ),
)


class ContractStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class ContractType(str, Enum):
    SERVICE = "service"
    NDA = "nda"
    LEASE = "lease"
    EMPLOYMENT = "employment"
    SUPPLIER = "supplier"
    OTHER = "other"


class RenewalType(str, Enum):
    NONE = "none"
    AUTO = "auto"
    MANUAL = "manual"


class ObligationStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"


class Contract(BaseModel):
    """An agreement with a counterparty."""
    id: int
    title: str
    counterparty: str
    contract_type: str = "service"
    value: float = 0
    currency: str = "USD"
    start_date: str
    end_date: str
    renewal_type: str = "manual"
    notice_days: int = 30
    owner: Optional[str] = None
    status: str = "active"
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class Obligation(BaseModel):
    """A dated obligation attached to a contract."""
    id: int
    contract_id: int
    description: str
    due_date: str
    recurring: str = "none"
    owner: Optional[str] = None
    status: str = "pending"
    completed_at: Optional[str] = None
    created_at: str


# Data persistence setup (MCP_DATA_DIR allows tests / custom deployments)
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "contracts.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "contracts": {}, "obligations": {},
        "next_contract_id": 1, "next_obligation_id": 1,
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
    """Save data atomically, skipping unchanged writes."""
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


# Initialize data
_data = _load_data()
contracts: dict[int, dict] = {int(k): v for k, v in _data.get("contracts", {}).items()}
obligations: dict[int, dict] = {int(k): v for k, v in _data.get("obligations", {}).items()}

_next_contract_id = _data.get("next_contract_id", 1)
_next_obligation_id = _data.get("next_obligation_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "contracts": contracts, "obligations": obligations,
        "next_contract_id": _next_contract_id,
        "next_obligation_id": _next_obligation_id,
    })


def _next_id(kind: str) -> int:
    global _next_contract_id, _next_obligation_id
    if kind == "contract":
        value = _next_contract_id
        _next_contract_id += 1
    else:
        value = _next_obligation_id
        _next_obligation_id += 1
    return value


# --- helpers -----------------------------------------------------------------
def _now() -> str:
    return datetime.now().isoformat()


def _today() -> str:
    return datetime.now().date().isoformat()


def _date(value: str):
    return datetime.fromisoformat(value).date()


def _validate(value: str, enum_cls, field: str) -> str:
    allowed = {e.value for e in enum_cls}
    if value not in allowed:
        raise ValueError(f"{field} must be one of {sorted(allowed)}")
    return value


def _days_between(start: str, end: str) -> int:
    return (_date(end) - _date(start)).days


def _advance(date_str: str, interval: str) -> str:
    """Advance a date by a recurring interval."""
    dt = datetime.fromisoformat(date_str)
    if interval == "monthly":
        month_index = dt.month
        year = dt.year + (1 if month_index == 12 else 0)
        month = 1 if month_index == 12 else month_index + 1
        day = min(dt.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                           31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return dt.replace(year=year, month=month, day=day).date().isoformat()
    if interval == "quarterly":
        return _advance(_advance(_advance(dt.date().isoformat(), "monthly"), "monthly"), "monthly")
    if interval == "yearly":
        return dt.replace(year=dt.year + 1).date().isoformat()
    return date_str


def _derive_status(entry: dict, as_of: Optional[str] = None) -> str:
    stored = entry.get("status", ContractStatus.ACTIVE.value)
    if stored in (ContractStatus.DRAFT.value, ContractStatus.TERMINATED.value):
        return stored
    if _date(entry["end_date"]) < _date(as_of or _today()):
        return ContractStatus.EXPIRED.value
    return ContractStatus.ACTIVE.value


def _contract_model(entry: dict, as_of: Optional[str] = None) -> Contract:
    payload = dict(entry)
    payload["status"] = _derive_status(entry, as_of)
    return Contract(**payload)


def _notice_deadline(entry: dict) -> str:
    return (_date(entry["end_date"]) - timedelta(days=int(entry.get("notice_days", 0)))).isoformat()


# --- contracts ---------------------------------------------------------------
@mcp.tool
def create_contract(title: str, counterparty: str, start_date: str, end_date: str,
                    contract_type: str = "service", value: float = 0,
                    currency: str = "USD", renewal_type: str = "manual",
                    notice_days: int = 30, owner: Optional[str] = None,
                    notes: Optional[str] = None,
                    status: str = "active") -> Contract:
    """Create a contract.

    Args:
        title: Contract title
        counterparty: Other party
        start_date / end_date: YYYY-MM-DD
        contract_type: service | nda | lease | employment | supplier | other
        value: Contract value (0 if not monetary)
        renewal_type: none | auto | manual
        notice_days: Days before end_date that notice must be given
    """
    _validate(contract_type, ContractType, "contract_type")
    _validate(renewal_type, RenewalType, "renewal_type")
    _validate(status, ContractStatus, "status")
    if _date(end_date) < _date(start_date):
        raise ValueError("end_date cannot be before start_date")
    if notice_days < 0:
        raise ValueError("notice_days cannot be negative")
    contract_id = _next_id("contract")
    entry = {
        "id": contract_id, "title": title, "counterparty": counterparty,
        "contract_type": contract_type, "value": float(value), "currency": currency,
        "start_date": start_date, "end_date": end_date,
        "renewal_type": renewal_type, "notice_days": int(notice_days),
        "owner": owner, "status": status, "notes": notes,
        "created_at": _now(), "updated_at": _now(),
    }
    contracts[contract_id] = entry
    _save()
    return _contract_model(entry)


@mcp.tool
def get_contract(contract_id: int) -> Optional[Contract]:
    """Retrieve a contract, with expired status derived from the end date."""
    entry = contracts.get(contract_id)
    return _contract_model(entry) if entry else None


@mcp.tool
def list_contracts(status: Optional[str] = None, counterparty: Optional[str] = None,
                   contract_type: Optional[str] = None,
                   limit: int = 100, offset: int = 0) -> list[Contract]:
    """List contracts with optional filters."""
    result = []
    for entry in contracts.values():
        model = _contract_model(entry)
        if status is not None and model.status != status:
            continue
        if counterparty is not None and counterparty.lower() not in model.counterparty.lower():
            continue
        if contract_type is not None and model.contract_type != contract_type:
            continue
        result.append(model)
    result.sort(key=lambda c: c.end_date)
    return result[offset:offset + limit]


@mcp.tool
def update_contract(contract_id: int, title: Optional[str] = None,
                    counterparty: Optional[str] = None, value: Optional[float] = None,
                    currency: Optional[str] = None, start_date: Optional[str] = None,
                    end_date: Optional[str] = None, contract_type: Optional[str] = None,
                    renewal_type: Optional[str] = None, notice_days: Optional[int] = None,
                    owner: Optional[str] = None, notes: Optional[str] = None,
                    status: Optional[str] = None) -> Optional[Contract]:
    """Update a contract."""
    entry = contracts.get(contract_id)
    if entry is None:
        return None
    if contract_type is not None:
        _validate(contract_type, ContractType, "contract_type")
    if renewal_type is not None:
        _validate(renewal_type, RenewalType, "renewal_type")
    if status is not None:
        _validate(status, ContractStatus, "status")
    for field, value_ in (("title", title), ("counterparty", counterparty),
                          ("value", value), ("currency", currency),
                          ("start_date", start_date), ("end_date", end_date),
                          ("contract_type", contract_type), ("renewal_type", renewal_type),
                          ("notice_days", notice_days), ("owner", owner),
                          ("notes", notes), ("status", status)):
        if value_ is not None:
            entry[field] = value_
    if _date(entry["end_date"]) < _date(entry["start_date"]):
        raise ValueError("end_date cannot be before start_date")
    entry["updated_at"] = _now()
    _save()
    return _contract_model(entry)


@mcp.tool
def terminate_contract(contract_id: int, reason: Optional[str] = None) -> Optional[Contract]:
    """Terminate a contract early."""
    entry = contracts.get(contract_id)
    if entry is None:
        return None
    entry["status"] = ContractStatus.TERMINATED.value
    if reason:
        entry["notes"] = (entry.get("notes") or "") + f"\nTerminated: {reason}"
    entry["updated_at"] = _now()
    _save()
    return _contract_model(entry)


@mcp.tool
def delete_contract(contract_id: int) -> bool:
    """Delete a contract and its obligations."""
    if contract_id not in contracts:
        return False
    del contracts[contract_id]
    for obligation_id in [oid for oid, o in obligations.items()
                          if int(o["contract_id"]) == contract_id]:
        del obligations[obligation_id]
    _save()
    return True


@mcp.tool
def get_expiring_contracts(days: int = 30, as_of: Optional[str] = None) -> list[dict]:
    """Active contracts ending within N days, with notice deadlines."""
    reference = as_of or _today()
    horizon = (_date(reference) + timedelta(days=days)).isoformat()
    result = []
    for entry in contracts.values():
        if _derive_status(entry, reference) != ContractStatus.ACTIVE.value:
            continue
        if not (_date(reference) <= _date(entry["end_date"]) <= _date(horizon)):
            continue
        notice = _notice_deadline(entry)
        result.append({
            "contract_id": entry["id"], "title": entry["title"],
            "counterparty": entry["counterparty"], "end_date": entry["end_date"],
            "renewal_type": entry["renewal_type"], "notice_deadline": notice,
            "days_until_end": _days_between(reference, entry["end_date"]),
            "days_until_notice": _days_between(reference, notice),
            "notice_passed": _date(reference) > _date(notice),
        })
    result.sort(key=lambda item: item["end_date"])
    return result


@mcp.tool
def get_renewal_calendar(as_of: Optional[str] = None, days: int = 365) -> list[dict]:
    """Renewable contracts ordered by notice deadline."""
    reference = as_of or _today()
    horizon = (_date(reference) + timedelta(days=days)).isoformat()
    result = []
    for entry in contracts.values():
        if entry.get("renewal_type", "none") == RenewalType.NONE.value:
            continue
        if _derive_status(entry, reference) != ContractStatus.ACTIVE.value:
            continue
        if _date(entry["end_date"]) > _date(horizon):
            continue
        notice = _notice_deadline(entry)
        result.append({
            "contract_id": entry["id"], "title": entry["title"],
            "counterparty": entry["counterparty"],
            "renewal_type": entry["renewal_type"],
            "notice_deadline": notice,
            "end_date": entry["end_date"],
            "days_until_notice": _days_between(reference, notice),
            "action_required": _date(reference) >= _date(notice),
        })
    result.sort(key=lambda item: item["notice_deadline"])
    return result


# --- obligations -------------------------------------------------------------
@mcp.tool
def add_obligation(contract_id: int, description: str, due_date: str,
                   recurring: str = "none", owner: Optional[str] = None) -> Obligation:
    """Add a dated obligation to a contract (e.g. report, payment, audit)."""
    if contract_id not in contracts:
        raise ValueError(f"Unknown contract: {contract_id}")
    if recurring not in ("none", "monthly", "quarterly", "yearly"):
        raise ValueError("recurring must be none | monthly | quarterly | yearly")
    obligation_id = _next_id("obligation")
    obligation = Obligation(
        id=obligation_id, contract_id=contract_id, description=description,
        due_date=due_date, recurring=recurring, owner=owner,
        status=ObligationStatus.PENDING.value, created_at=_now(),
    )
    obligations[obligation_id] = obligation.model_dump()
    _save()
    return obligation


@mcp.tool
def complete_obligation(obligation_id: int) -> Optional[Obligation]:
    """Complete an obligation. Recurring obligations roll to the next due date."""
    entry = obligations.get(obligation_id)
    if entry is None:
        return None
    entry["completed_at"] = _now()
    if entry.get("recurring", "none") != "none":
        entry["due_date"] = _advance(entry["due_date"], entry["recurring"])
        entry["status"] = ObligationStatus.PENDING.value
    else:
        entry["status"] = ObligationStatus.DONE.value
    _save()
    return Obligation(**entry)


@mcp.tool
def list_obligations(contract_id: Optional[int] = None,
                     status: Optional[str] = None,
                     limit: int = 200) -> list[Obligation]:
    """List obligations, optionally for one contract or by status."""
    result = [Obligation(**o) for o in obligations.values()
              if (contract_id is None or int(o["contract_id"]) == contract_id)
              and (status is None or o["status"] == status)]
    result.sort(key=lambda o: o.due_date)
    return result[:limit]


@mcp.tool
def get_overdue_obligations(as_of: Optional[str] = None) -> list[Obligation]:
    """Pending obligations whose due date has passed."""
    reference = as_of or _today()
    result = [Obligation(**o) for o in obligations.values()
              if o["status"] == ObligationStatus.PENDING.value
              and _date(o["due_date"]) < _date(reference)]
    result.sort(key=lambda o: o.due_date)
    return result


@mcp.tool
def get_upcoming_obligations(days: int = 30, as_of: Optional[str] = None) -> list[Obligation]:
    """Pending obligations due within N days."""
    reference = as_of or _today()
    horizon = (_date(reference) + timedelta(days=days)).isoformat()
    result = [Obligation(**o) for o in obligations.values()
              if o["status"] == ObligationStatus.PENDING.value
              and _date(reference) <= _date(o["due_date"]) <= _date(horizon)]
    result.sort(key=lambda o: o.due_date)
    return result


# --- reporting ---------------------------------------------------------------
@mcp.tool
def get_contract_stats(as_of: Optional[str] = None) -> dict:
    """Contract portfolio statistics."""
    reference = as_of or _today()
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    total_value = 0.0
    for entry in contracts.values():
        status = _derive_status(entry, reference)
        by_status[status] = by_status.get(status, 0) + 1
        by_type[entry["contract_type"]] = by_type.get(entry["contract_type"], 0) + 1
        if status == ContractStatus.ACTIVE.value:
            total_value += float(entry.get("value", 0))
    return {
        "as_of": reference,
        "contracts": len(contracts),
        "by_status": by_status,
        "by_type": by_type,
        "active_value": round(total_value, 2),
        "pending_obligations": sum(1 for o in obligations.values()
                                   if o["status"] == ObligationStatus.PENDING.value),
        "overdue_obligations": len(get_overdue_obligations(reference)),
    }


# --- resources ---------------------------------------------------------------
@mcp.resource("contracts://expiring")
def get_expiring_resource() -> str:
    """Contracts expiring in the next 30 days."""
    items = get_expiring_contracts(30)
    if not items:
        return "# Expiring Contracts\n\nNothing expiring in the next 30 days."
    lines = [f"# Expiring Contracts ({len(items)})\n"]
    for item in items:
        flag = " - NOTICE PASSED" if item["notice_passed"] else ""
        lines.append(f"- **{item['title']}** ({item['counterparty']})")
        lines.append(f"  - Ends {item['end_date']} ({item['days_until_end']} days)"
                     f" | notice {item['notice_deadline']}{flag}")
    return "\n".join(lines)


@mcp.resource("contracts://stats")
def get_stats_resource() -> str:
    """Contract statistics."""
    stats = get_contract_stats()
    return (
        "# Contract Portfolio\n\n"
        f"- **Contracts:** {stats['contracts']}\n"
        f"- **Active value:** {stats['active_value']:,.2f}\n"
        f"- **Pending obligations:** {stats['pending_obligations']}\n"
        f"- **Overdue obligations:** {stats['overdue_obligations']}"
    )


if __name__ == "__main__":
    mcp.run()
