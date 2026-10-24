"""
Invoice Manager MCP Server
A FastMCP server for clients, invoices, payments, recurring billing, and
accounts-receivable aging.
"""

from datetime import datetime, timedelta
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
    name="Invoice Manager",
    instructions=(
        "An invoicing server for managing clients, invoices, payments, recurring "
        "billing, and accounts-receivable aging reports."
    ),
)


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    VOID = "void"


class RecurringInterval(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Client(BaseModel):
    """A billing client."""
    id: int
    name: str
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    currency: str = "USD"
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class LineItem(BaseModel):
    """A single invoice line item."""
    description: str
    quantity: float = 1
    unit_price: float = 0

    @property
    def amount(self) -> float:
        return _money(self.quantity * self.unit_price)


class Payment(BaseModel):
    """A payment against an invoice."""
    id: int
    invoice_id: int
    amount: float
    paid_at: str
    method: Optional[str] = None
    reference: Optional[str] = None


class Invoice(BaseModel):
    """An invoice with calculated totals."""
    id: int
    number: str
    client_id: int
    issue_date: str
    due_date: str
    line_items: list[LineItem]
    tax_rate: float = 0
    discount: float = 0
    currency: str = "USD"
    status: str
    notes: Optional[str] = None
    subtotal: float = 0
    tax_amount: float = 0
    total: float = 0
    amount_paid: float = 0
    balance: float = 0
    created_at: str
    updated_at: str


class RecurringInvoice(BaseModel):
    """A template that generates invoices on a schedule."""
    id: int
    client_id: int
    line_items: list[LineItem]
    tax_rate: float = 0
    discount: float = 0
    currency: str = "USD"
    interval: str = "monthly"
    next_run_date: str
    payment_terms_days: int = 30
    active: bool = True
    notes: Optional[str] = None
    created_at: str


# Data persistence setup (MCP_DATA_DIR allows tests / custom deployments)
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "invoices.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "clients": {}, "invoices": {}, "payments": {}, "recurring": {},
        "next_client_id": 1, "next_invoice_id": 1, "next_payment_id": 1,
        "next_recurring_id": 1, "next_invoice_number": 1,
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
clients: dict[int, dict] = {int(k): v for k, v in _data.get("clients", {}).items()}
invoices: dict[int, dict] = {int(k): v for k, v in _data.get("invoices", {}).items()}
payments: dict[int, dict] = {int(k): v for k, v in _data.get("payments", {}).items()}
recurring: dict[int, dict] = {int(k): v for k, v in _data.get("recurring", {}).items()}

_next_client_id = _data.get("next_client_id", 1)
_next_invoice_id = _data.get("next_invoice_id", 1)
_next_payment_id = _data.get("next_payment_id", 1)
_next_recurring_id = _data.get("next_recurring_id", 1)
_next_invoice_number = _data.get("next_invoice_number", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "clients": clients, "invoices": invoices, "payments": payments,
        "recurring": recurring,
        "next_client_id": _next_client_id, "next_invoice_id": _next_invoice_id,
        "next_payment_id": _next_payment_id, "next_recurring_id": _next_recurring_id,
        "next_invoice_number": _next_invoice_number,
    })


def _next_id(kind: str) -> int:
    """Allocate the next integer id for a collection."""
    global _next_client_id, _next_invoice_id, _next_payment_id, _next_recurring_id
    if kind == "client":
        value = _next_client_id
        _next_client_id += 1
    elif kind == "invoice":
        value = _next_invoice_id
        _next_invoice_id += 1
    elif kind == "payment":
        value = _next_payment_id
        _next_payment_id += 1
    else:
        value = _next_recurring_id
        _next_recurring_id += 1
    return value


# --- helpers -----------------------------------------------------------------
def _money(value: float) -> float:
    """Round a monetary value to 2 decimal places."""
    return round(float(value) + 0.0, 2)


def _now() -> str:
    return datetime.now().isoformat()


def _today() -> str:
    return datetime.now().date().isoformat()


def _as_list(value) -> list:
    """Accept a real list or a JSON-stringified list from MCP clients."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, TypeError):
            return [value]
    return value


def _to_items(raw_items) -> list[dict]:
    """Normalise incoming line items into dicts."""
    items = []
    for item in _as_list(raw_items):
        if isinstance(item, LineItem):
            items.append(item.model_dump())
        elif isinstance(item, dict):
            items.append(LineItem(**item).model_dump())
        else:
            raise ValueError(f"Invalid line item: {item!r}")
    return items


def _compute_totals(items: list[dict], tax_rate: float, discount: float) -> dict:
    """Compute subtotal, tax and total for a set of line items."""
    subtotal = _money(sum(float(i["quantity"]) * float(i["unit_price"]) for i in items))
    taxable = max(_money(subtotal - float(discount or 0)), 0.0)
    tax_amount = _money(taxable * float(tax_rate or 0) / 100.0)
    total = _money(taxable + tax_amount)
    return {"subtotal": subtotal, "tax_amount": tax_amount, "total": total}


def _paid_for(invoice_id: int) -> float:
    return _money(sum(float(p["amount"]) for p in payments.values()
                      if int(p["invoice_id"]) == invoice_id))


def _derive_status(entry: dict, as_of: Optional[str] = None) -> str:
    """Derive the effective status from payments and dates."""
    stored = entry.get("status", InvoiceStatus.DRAFT.value)
    if stored == InvoiceStatus.VOID.value:
        return stored
    if stored == InvoiceStatus.DRAFT.value:
        return stored
    paid = _paid_for(int(entry["id"]))
    total = float(entry.get("total", 0))
    if paid >= total - 0.005:
        return InvoiceStatus.PAID.value
    if datetime.fromisoformat(as_of or _today()).date() > datetime.fromisoformat(entry["due_date"]).date():
        return InvoiceStatus.OVERDUE.value
    if paid > 0:
        return InvoiceStatus.PARTIALLY_PAID.value
    return InvoiceStatus.SENT.value


def _invoice_model(entry: dict, as_of: Optional[str] = None) -> Invoice:
    """Build an Invoice model with freshly calculated payment figures."""
    paid = _paid_for(int(entry["id"]))
    total = float(entry.get("total", 0))
    payload = dict(entry)
    payload["amount_paid"] = paid
    payload["balance"] = _money(max(total - paid, 0.0))
    payload["status"] = _derive_status(entry, as_of)
    return Invoice(**payload)


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _add_months(dt: datetime, months: int) -> datetime:
    """Add months without day overflow (Jan 31 + 1 month -> Feb 28/29)."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                       31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return dt.replace(year=year, month=month, day=day)


def _advance(date_str: str, interval: str) -> str:
    """Advance a date by one interval, returning an ISO date string."""
    dt = datetime.fromisoformat(date_str)
    if interval == RecurringInterval.MONTHLY.value:
        dt = _add_months(dt, 1)
    elif interval == RecurringInterval.QUARTERLY.value:
        dt = _add_months(dt, 3)
    elif interval == RecurringInterval.YEARLY.value:
        dt = dt.replace(year=dt.year + 1)
    else:
        raise ValueError(f"Unknown interval: {interval}")
    return dt.date().isoformat()


def _issue_invoice(client_id: int, items: list[dict], issue_date: str, due_date: str,
                   tax_rate: float, discount: float, currency: str,
                   notes: Optional[str], status: str) -> dict:
    """Create and persist an invoice entry (caller saves)."""
    global _next_invoice_number
    totals = _compute_totals(items, tax_rate, discount)
    invoice_id = _next_id("invoice")
    number = f"INV-{_next_invoice_number:04d}"
    _next_invoice_number += 1
    entry = {
        "id": invoice_id,
        "number": number,
        "client_id": client_id,
        "issue_date": issue_date,
        "due_date": due_date,
        "line_items": items,
        "tax_rate": float(tax_rate or 0),
        "discount": float(discount or 0),
        "currency": currency,
        "status": status,
        "notes": notes,
        **totals,
        "amount_paid": 0.0,
        "balance": totals["total"],
        "created_at": _now(),
        "updated_at": _now(),
    }
    invoices[invoice_id] = entry
    return entry


# --- clients -----------------------------------------------------------------
@mcp.tool
def create_client(name: str, email: Optional[str] = None, address: Optional[str] = None,
                  tax_id: Optional[str] = None, currency: str = "USD",
                  notes: Optional[str] = None) -> Client:
    """Create a billing client."""
    client_id = _next_id("client")
    client = Client(
        id=client_id, name=name, email=email, address=address, tax_id=tax_id,
        currency=currency, notes=notes, created_at=_now(), updated_at=_now(),
    )
    clients[client_id] = client.model_dump()
    _save()
    return client


@mcp.tool
def get_client(client_id: int) -> Optional[Client]:
    """Retrieve a client by id."""
    data = clients.get(client_id)
    return Client(**data) if data else None


@mcp.tool
def list_clients() -> list[Client]:
    """List all clients."""
    return [Client(**c) for c in sorted(clients.values(), key=lambda c: c["name"].lower())]


@mcp.tool
def update_client(client_id: int, name: Optional[str] = None, email: Optional[str] = None,
                  address: Optional[str] = None, tax_id: Optional[str] = None,
                  currency: Optional[str] = None, notes: Optional[str] = None) -> Optional[Client]:
    """Update a client."""
    entry = clients.get(client_id)
    if entry is None:
        return None
    for field, value in (("name", name), ("email", email), ("address", address),
                         ("tax_id", tax_id), ("currency", currency), ("notes", notes)):
        if value is not None:
            entry[field] = value
    entry["updated_at"] = _now()
    _save()
    return Client(**entry)


@mcp.tool
def delete_client(client_id: int) -> bool:
    """Delete a client. Refuses when invoices still reference it."""
    if client_id not in clients:
        return False
    if any(int(i["client_id"]) == client_id for i in invoices.values()):
        raise ValueError("Cannot delete a client with existing invoices")
    del clients[client_id]
    _save()
    return True


# --- invoices ----------------------------------------------------------------
@mcp.tool
def create_invoice(client_id: int, line_items: list[dict],
                   issue_date: Optional[str] = None, due_date: Optional[str] = None,
                   tax_rate: float = 0, discount: float = 0,
                   currency: Optional[str] = None, notes: Optional[str] = None,
                   send: bool = False) -> Invoice:
    """Create an invoice.

    Args:
        client_id: Client the invoice is for
        line_items: List of {description, quantity, unit_price}
        issue_date: YYYY-MM-DD (defaults to today)
        due_date: YYYY-MM-DD (defaults to issue date + 30 days)
        tax_rate: Percentage, e.g. 10 for 10%
        discount: Flat amount subtracted before tax
        currency: Currency code (defaults to the client's currency)
        notes: Optional notes
        send: Mark as sent instead of draft
    """
    if client_id not in clients:
        raise ValueError(f"Unknown client: {client_id}")
    items = _to_items(line_items)
    if not items:
        raise ValueError("An invoice needs at least one line item")
    issued = issue_date or _today()
    due = due_date or (datetime.fromisoformat(issued) + timedelta(days=30)).date().isoformat()
    if _parse_date(due).date() < _parse_date(issued).date():
        raise ValueError("due_date cannot be before issue_date")
    entry = _issue_invoice(
        client_id, items, issued, due, tax_rate, discount,
        currency or clients[client_id].get("currency", "USD"), notes,
        InvoiceStatus.SENT.value if send else InvoiceStatus.DRAFT.value,
    )
    _save()
    return _invoice_model(entry)


@mcp.tool
def bulk_create_invoices(client_id: int, invoice_specs: list[dict],
                        send: bool = False) -> list[Invoice]:
    """Create many invoices in a single disk write.

    Each spec may contain: line_items (required), issue_date, due_date,
    tax_rate, discount, currency, notes.
    """
    if client_id not in clients:
        raise ValueError(f"Unknown client: {client_id}")
    created = []
    for spec in _as_list(invoice_specs):
        if not isinstance(spec, dict):
            raise ValueError(f"Invalid invoice spec: {spec!r}")
        items = _to_items(spec.get("line_items"))
        if not items:
            raise ValueError("Each invoice needs at least one line item")
        issued = spec.get("issue_date") or _today()
        due = spec.get("due_date") or (
            datetime.fromisoformat(issued) + timedelta(days=30)
        ).date().isoformat()
        if _parse_date(due).date() < _parse_date(issued).date():
            raise ValueError("due_date cannot be before issue_date")
        entry = _issue_invoice(
            client_id, items, issued, due, float(spec.get("tax_rate", 0)),
            float(spec.get("discount", 0)),
            spec.get("currency") or clients[client_id].get("currency", "USD"),
            spec.get("notes"),
            InvoiceStatus.SENT.value if send else InvoiceStatus.DRAFT.value,
        )
        created.append(_invoice_model(entry))
    if created:
        _save()
    return created


@mcp.tool
def get_invoice(invoice_id: int) -> Optional[Invoice]:
    """Retrieve an invoice with live balance and status."""
    entry = invoices.get(invoice_id)
    return _invoice_model(entry) if entry else None


@mcp.tool
def list_invoices(status: Optional[str] = None, client_id: Optional[int] = None,
                  limit: int = 100, offset: int = 0) -> list[Invoice]:
    """List invoices, optionally filtered by derived status or client."""
    result = []
    for entry in invoices.values():
        model = _invoice_model(entry)
        if status is not None and model.status != status:
            continue
        if client_id is not None and int(entry["client_id"]) != client_id:
            continue
        result.append(model)
    result.sort(key=lambda i: i.issue_date, reverse=True)
    return result[offset:offset + limit]


@mcp.tool
def update_invoice(invoice_id: int, line_items: Optional[list[dict]] = None,
                   issue_date: Optional[str] = None, due_date: Optional[str] = None,
                   tax_rate: Optional[float] = None, discount: Optional[float] = None,
                   notes: Optional[str] = None) -> Optional[Invoice]:
    """Update an invoice and recalculate totals. Paid invoices cannot be edited."""
    entry = invoices.get(invoice_id)
    if entry is None:
        return None
    if _derive_status(entry) == InvoiceStatus.PAID.value:
        raise ValueError("Fully paid invoices cannot be edited")
    if line_items is not None:
        items = _to_items(line_items)
        if not items:
            raise ValueError("An invoice needs at least one line item")
        entry["line_items"] = items
    for field, value in (("issue_date", issue_date), ("due_date", due_date), ("notes", notes)):
        if value is not None:
            entry[field] = value
    if tax_rate is not None:
        entry["tax_rate"] = float(tax_rate)
    if discount is not None:
        entry["discount"] = float(discount)
    entry.update(_compute_totals(entry["line_items"], entry["tax_rate"], entry["discount"]))
    entry["updated_at"] = _now()
    _save()
    return _invoice_model(entry)


@mcp.tool
def send_invoice(invoice_id: int) -> Optional[Invoice]:
    """Mark a draft invoice as sent."""
    entry = invoices.get(invoice_id)
    if entry is None:
        return None
    if entry["status"] == InvoiceStatus.VOID.value:
        raise ValueError("Cannot send a void invoice")
    if entry["status"] == InvoiceStatus.DRAFT.value:
        entry["status"] = InvoiceStatus.SENT.value
        entry["updated_at"] = _now()
        _save()
    return _invoice_model(entry)


@mcp.tool
def void_invoice(invoice_id: int) -> Optional[Invoice]:
    """Void an invoice (kept for audit, excluded from aging)."""
    entry = invoices.get(invoice_id)
    if entry is None:
        return None
    entry["status"] = InvoiceStatus.VOID.value
    entry["updated_at"] = _now()
    _save()
    return _invoice_model(entry)


@mcp.tool
def delete_invoice(invoice_id: int) -> bool:
    """Delete an invoice and its payments."""
    if invoice_id not in invoices:
        return False
    del invoices[invoice_id]
    for payment_id in [pid for pid, p in payments.items() if int(p["invoice_id"]) == invoice_id]:
        del payments[payment_id]
    _save()
    return True


# --- payments ----------------------------------------------------------------
@mcp.tool
def record_payment(invoice_id: int, amount: float, paid_at: Optional[str] = None,
                   method: Optional[str] = None, reference: Optional[str] = None) -> Payment:
    """Record a payment against an invoice."""
    entry = invoices.get(invoice_id)
    if entry is None:
        raise ValueError(f"Unknown invoice: {invoice_id}")
    if entry["status"] == InvoiceStatus.VOID.value:
        raise ValueError("Cannot pay a void invoice")
    amount = _money(amount)
    if amount <= 0:
        raise ValueError("Payment amount must be positive")
    balance = _money(float(entry["total"]) - _paid_for(invoice_id))
    if amount > balance + 0.005:
        raise ValueError(f"Payment exceeds outstanding balance ({balance})")
    payment_id = _next_id("payment")
    payment = Payment(
        id=payment_id, invoice_id=invoice_id, amount=amount,
        paid_at=paid_at or _now(), method=method, reference=reference,
    )
    payments[payment_id] = payment.model_dump()
    if entry["status"] == InvoiceStatus.DRAFT.value:
        entry["status"] = InvoiceStatus.SENT.value
    entry["updated_at"] = _now()
    _save()
    return payment


@mcp.tool
def list_payments(invoice_id: Optional[int] = None) -> list[Payment]:
    """List payments, optionally for a single invoice."""
    result = [Payment(**p) for p in payments.values()
              if invoice_id is None or int(p["invoice_id"]) == invoice_id]
    result.sort(key=lambda p: p.paid_at, reverse=True)
    return result


# --- recurring billing -------------------------------------------------------
@mcp.tool
def create_recurring_invoice(client_id: int, line_items: list[dict],
                             interval: str = "monthly",
                             next_run_date: Optional[str] = None,
                             tax_rate: float = 0, discount: float = 0,
                             currency: Optional[str] = None,
                             payment_terms_days: int = 30,
                             notes: Optional[str] = None) -> RecurringInvoice:
    """Create a recurring invoice template."""
    if client_id not in clients:
        raise ValueError(f"Unknown client: {client_id}")
    if interval not in {i.value for i in RecurringInterval}:
        raise ValueError(f"interval must be one of {[i.value for i in RecurringInterval]}")
    items = _to_items(line_items)
    if not items:
        raise ValueError("A recurring invoice needs at least one line item")
    recurring_id = _next_id("recurring")
    entry = RecurringInvoice(
        id=recurring_id, client_id=client_id, line_items=[LineItem(**i) for i in items],
        tax_rate=float(tax_rate or 0), discount=float(discount or 0),
        currency=currency or clients[client_id].get("currency", "USD"),
        interval=interval, next_run_date=next_run_date or _today(),
        payment_terms_days=payment_terms_days, active=True, notes=notes,
        created_at=_now(),
    )
    recurring[recurring_id] = entry.model_dump()
    _save()
    return entry


@mcp.tool
def list_recurring_invoices() -> list[RecurringInvoice]:
    """List recurring invoice templates."""
    return [RecurringInvoice(**r) for r in recurring.values()]


@mcp.tool
def set_recurring_active(recurring_id: int, active: bool) -> Optional[RecurringInvoice]:
    """Activate or pause a recurring invoice."""
    entry = recurring.get(recurring_id)
    if entry is None:
        return None
    entry["active"] = active
    _save()
    return RecurringInvoice(**entry)


@mcp.tool
def generate_due_invoices(as_of: Optional[str] = None) -> list[Invoice]:
    """Materialise invoices for every recurring template that is due.

    Each generated invoice advances the template's next_run_date by one
    interval, looping while it is still on or before as_of.
    """
    as_of = as_of or _today()
    created = []
    for entry in recurring.values():
        if not entry.get("active", True):
            continue
        while datetime.fromisoformat(entry["next_run_date"]).date() <= datetime.fromisoformat(as_of).date():
            run_date = entry["next_run_date"]
            due = (datetime.fromisoformat(run_date)
                   + timedelta(days=int(entry.get("payment_terms_days", 30)))).date().isoformat()
            item_dicts = [dict(i) for i in entry["line_items"]]
            invoice = _issue_invoice(
                int(entry["client_id"]), item_dicts, run_date, due,
                float(entry.get("tax_rate", 0)), float(entry.get("discount", 0)),
                entry.get("currency", "USD"), entry.get("notes"),
                InvoiceStatus.SENT.value,
            )
            entry["next_run_date"] = _advance(run_date, entry["interval"])
            created.append(_invoice_model(invoice))
    if created:
        _save()
    return created


# --- reporting ---------------------------------------------------------------
@mcp.tool
def get_aging_report(as_of: Optional[str] = None) -> dict:
    """Accounts-receivable aging report with 30/60/90+ day buckets."""
    as_of_dt = datetime.fromisoformat(as_of or _today()).date()
    buckets = {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "61_90": 0.0, "over_90": 0.0}
    details = []
    for entry in invoices.values():
        status = _derive_status(entry, as_of)
        if status in (InvoiceStatus.DRAFT.value, InvoiceStatus.VOID.value, InvoiceStatus.PAID.value):
            continue
        model = _invoice_model(entry, as_of)
        if model.balance <= 0:
            continue
        days = (as_of_dt - datetime.fromisoformat(entry["due_date"]).date()).days
        if days <= 0:
            bucket = "current"
        elif days <= 30:
            bucket = "1_30"
        elif days <= 60:
            bucket = "31_60"
        elif days <= 90:
            bucket = "61_90"
        else:
            bucket = "over_90"
        buckets[bucket] = _money(buckets[bucket] + model.balance)
        details.append({
            "invoice_id": model.id, "number": model.number, "client_id": model.client_id,
            "due_date": model.due_date, "days_overdue": max(days, 0),
            "balance": model.balance, "bucket": bucket, "status": model.status,
        })
    details.sort(key=lambda d: d["days_overdue"], reverse=True)
    return {
        "as_of": as_of or _today(),
        "buckets": buckets,
        "total_outstanding": _money(sum(buckets.values())),
        "invoice_count": len(details),
        "details": details,
    }


@mcp.tool
def get_revenue_summary(start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> dict:
    """Invoiced / collected / outstanding totals for a date range."""
    start = datetime.fromisoformat(start_date or "1970-01-01").date()
    end = datetime.fromisoformat(end_date or _today()).date()
    invoiced = collected = outstanding = 0.0
    count = 0
    for entry in invoices.values():
        issued = datetime.fromisoformat(entry["issue_date"]).date()
        if not (start <= issued <= end):
            continue
        if entry["status"] == InvoiceStatus.VOID.value:
            continue
        model = _invoice_model(entry)
        count += 1
        invoiced += model.total
        collected += model.amount_paid
        outstanding += model.balance
    return {
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "invoice_count": count,
        "total_invoiced": _money(invoiced),
        "total_collected": _money(collected),
        "total_outstanding": _money(outstanding),
    }


@mcp.tool
def get_invoice_stats() -> dict:
    """Vault-wide invoice statistics and status breakdown."""
    by_status: dict[str, int] = {}
    for entry in invoices.values():
        status = _derive_status(entry)
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "clients": len(clients),
        "invoices": len(invoices),
        "payments": len(payments),
        "recurring_templates": len(recurring),
        "by_status": by_status,
        "total_outstanding": _money(sum(_invoice_model(e).balance for e in invoices.values()
                                        if e["status"] != InvoiceStatus.VOID.value)),
    }


# --- resources ---------------------------------------------------------------
@mcp.resource("invoices://aging")
def get_aging_resource() -> str:
    """Aging report as formatted text."""
    report = get_aging_report()
    lines = [f"# A/R Aging Report ({report['as_of']})\n"]
    for bucket, amount in report["buckets"].items():
        lines.append(f"- **{bucket}:** {amount:,.2f}")
    lines.append(f"\n**Total outstanding:** {report['total_outstanding']:,.2f}")
    if report["details"]:
        lines.append("\n## Overdue invoices\n")
        for d in report["details"]:
            lines.append(f"- {d['number']} - {d['days_overdue']} days - {d['balance']:,.2f}")
    return "\n".join(lines)


@mcp.resource("invoices://summary")
def get_summary_resource() -> str:
    """Revenue summary as formatted text."""
    summary = get_revenue_summary()
    return (
        "# Invoice Summary\n\n"
        f"- **Invoiced:** {summary['total_invoiced']:,.2f}\n"
        f"- **Collected:** {summary['total_collected']:,.2f}\n"
        f"- **Outstanding:** {summary['total_outstanding']:,.2f}\n"
        f"- **Invoices:** {summary['invoice_count']}"
    )


if __name__ == "__main__":
    mcp.run()
