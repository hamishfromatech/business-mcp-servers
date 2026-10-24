"""
Vendor Manager MCP Server
A FastMCP server for suppliers, purchase orders, lead times, and vendor
scorecards.
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
    name="Vendor Manager",
    instructions=(
        "A procurement server for managing suppliers, purchase orders, lead "
        "times, spend, and vendor performance scorecards."
    ),
)


class VendorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_HOLD = "on_hold"


class POStatus(str, Enum):
    DRAFT = "draft"
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class Vendor(BaseModel):
    """A supplier."""
    id: int
    name: str
    category: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    payment_terms_days: int = 30
    lead_time_days: int = 0
    status: str = "active"
    rating: Optional[float] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class LineItem(BaseModel):
    """A purchase order line item."""
    description: str
    quantity: float = 1
    unit_price: float = 0

    @property
    def amount(self) -> float:
        return _money(self.quantity * self.unit_price)


class PurchaseOrder(BaseModel):
    """A purchase order sent to a vendor."""
    id: int
    reference: str
    vendor_id: int
    items: list[LineItem]
    status: str
    currency: str = "USD"
    total: float = 0
    ordered_at: Optional[str] = None
    expected_at: Optional[str] = None
    received_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class VendorReview(BaseModel):
    """A performance review for a vendor (each score is 1-5)."""
    id: int
    vendor_id: int
    on_time_delivery: int
    quality: int
    communication: int
    pricing: int
    overall: float
    comment: Optional[str] = None
    created_at: str


# Data persistence setup (MCP_DATA_DIR allows tests / custom deployments)
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "vendors.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "vendors": {}, "purchase_orders": {}, "reviews": {},
        "next_vendor_id": 1, "next_po_id": 1, "next_review_id": 1,
        "next_po_number": 1,
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
vendors: dict[int, dict] = {int(k): v for k, v in _data.get("vendors", {}).items()}
purchase_orders: dict[int, dict] = {int(k): v for k, v in _data.get("purchase_orders", {}).items()}
reviews: dict[int, dict] = {int(k): v for k, v in _data.get("reviews", {}).items()}

_next_vendor_id = _data.get("next_vendor_id", 1)
_next_po_id = _data.get("next_po_id", 1)
_next_review_id = _data.get("next_review_id", 1)
_next_po_number = _data.get("next_po_number", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "vendors": vendors, "purchase_orders": purchase_orders, "reviews": reviews,
        "next_vendor_id": _next_vendor_id, "next_po_id": _next_po_id,
        "next_review_id": _next_review_id, "next_po_number": _next_po_number,
    })


def _next_id(kind: str) -> int:
    global _next_vendor_id, _next_po_id, _next_review_id
    if kind == "vendor":
        value = _next_vendor_id
        _next_vendor_id += 1
    elif kind == "po":
        value = _next_po_id
        _next_po_id += 1
    else:
        value = _next_review_id
        _next_review_id += 1
    return value


# --- helpers -----------------------------------------------------------------
def _money(value: float) -> float:
    return round(float(value) + 0.0, 2)


def _now() -> str:
    return datetime.now().isoformat()


def _today() -> str:
    return datetime.now().date().isoformat()


def _date(value: str):
    return datetime.fromisoformat(value).date()


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, TypeError):
            return [value]
    return value


def _to_items(raw_items) -> list[dict]:
    items = []
    for item in _as_list(raw_items):
        if isinstance(item, LineItem):
            items.append(item.model_dump())
        elif isinstance(item, dict):
            items.append(LineItem(**item).model_dump())
        else:
            raise ValueError(f"Invalid line item: {item!r}")
    return items


def _validate_status(value: str, enum_cls, field: str) -> str:
    allowed = {e.value for e in enum_cls}
    if value not in allowed:
        raise ValueError(f"{field} must be one of {sorted(allowed)}")
    return value


def _validate_score(value: int, field: str) -> int:
    if not 1 <= int(value) <= 5:
        raise ValueError(f"{field} must be between 1 and 5")
    return int(value)


def _po_model(entry: dict) -> PurchaseOrder:
    return PurchaseOrder(**entry)


def _review_averages(vendor_id: int) -> Optional[dict]:
    items = [r for r in reviews.values() if int(r["vendor_id"]) == vendor_id]
    if not items:
        return None
    fields = ("on_time_delivery", "quality", "communication", "pricing", "overall")
    return {
        field: round(sum(float(r[field]) for r in items) / len(items), 2)
        for field in fields
    }


# --- vendors -----------------------------------------------------------------
@mcp.tool
def create_vendor(name: str, category: Optional[str] = None,
                  contact_name: Optional[str] = None, email: Optional[str] = None,
                  phone: Optional[str] = None, website: Optional[str] = None,
                  payment_terms_days: int = 30, lead_time_days: int = 0,
                  status: str = "active", rating: Optional[float] = None,
                  notes: Optional[str] = None) -> Vendor:
    """Create a supplier record."""
    _validate_status(status, VendorStatus, "status")
    if rating is not None and not 0 <= float(rating) <= 5:
        raise ValueError("rating must be between 0 and 5")
    vendor_id = _next_id("vendor")
    vendor = Vendor(
        id=vendor_id, name=name, category=category, contact_name=contact_name,
        email=email, phone=phone, website=website,
        payment_terms_days=payment_terms_days, lead_time_days=lead_time_days,
        status=status, rating=rating, notes=notes,
        created_at=_now(), updated_at=_now(),
    )
    vendors[vendor_id] = vendor.model_dump()
    _save()
    return vendor


@mcp.tool
def get_vendor(vendor_id: int) -> Optional[Vendor]:
    """Retrieve a vendor by id."""
    entry = vendors.get(vendor_id)
    return Vendor(**entry) if entry else None


@mcp.tool
def list_vendors(status: Optional[str] = None, category: Optional[str] = None,
                 limit: int = 100, offset: int = 0) -> list[Vendor]:
    """List vendors with optional filters."""
    result = []
    for entry in vendors.values():
        if status is not None and entry["status"] != status:
            continue
        if category is not None and (entry.get("category") or "").lower() != category.lower():
            continue
        result.append(Vendor(**entry))
    result.sort(key=lambda v: v.name.lower())
    return result[offset:offset + limit]


@mcp.tool
def update_vendor(vendor_id: int, name: Optional[str] = None,
                  category: Optional[str] = None, contact_name: Optional[str] = None,
                  email: Optional[str] = None, phone: Optional[str] = None,
                  website: Optional[str] = None, payment_terms_days: Optional[int] = None,
                  lead_time_days: Optional[int] = None, status: Optional[str] = None,
                  rating: Optional[float] = None, notes: Optional[str] = None) -> Optional[Vendor]:
    """Update a vendor."""
    entry = vendors.get(vendor_id)
    if entry is None:
        return None
    if status is not None:
        _validate_status(status, VendorStatus, "status")
    if rating is not None and not 0 <= float(rating) <= 5:
        raise ValueError("rating must be between 0 and 5")
    for field, value in (("name", name), ("category", category),
                         ("contact_name", contact_name), ("email", email),
                         ("phone", phone), ("website", website),
                         ("payment_terms_days", payment_terms_days),
                         ("lead_time_days", lead_time_days), ("status", status),
                         ("rating", rating), ("notes", notes)):
        if value is not None:
            entry[field] = value
    entry["updated_at"] = _now()
    _save()
    return Vendor(**entry)


@mcp.tool
def delete_vendor(vendor_id: int) -> bool:
    """Delete a vendor. Refuses while purchase orders reference it."""
    if vendor_id not in vendors:
        return False
    if any(int(po["vendor_id"]) == vendor_id for po in purchase_orders.values()):
        raise ValueError("Cannot delete a vendor with existing purchase orders")
    del vendors[vendor_id]
    for review_id in [rid for rid, r in reviews.items() if int(r["vendor_id"]) == vendor_id]:
        del reviews[review_id]
    _save()
    return True


# --- purchase orders ---------------------------------------------------------
@mcp.tool
def create_purchase_order(vendor_id: int, items: list[dict],
                          expected_at: Optional[str] = None,
                          reference: Optional[str] = None,
                          currency: str = "USD", notes: Optional[str] = None,
                          place: bool = True) -> PurchaseOrder:
    """Create a purchase order for a vendor.

    Args:
        vendor_id: Vendor to order from
        items: List of {description, quantity, unit_price}
        expected_at: Expected delivery date (defaults to today + lead time)
        reference: Optional PO reference (defaults to PO-000N)
        place: Mark as ordered (otherwise draft)
    """
    global _next_po_number
    if vendor_id not in vendors:
        raise ValueError(f"Unknown vendor: {vendor_id}")
    item_dicts = _to_items(items)
    if not item_dicts:
        raise ValueError("A purchase order needs at least one line item")
    vendor = vendors[vendor_id]
    po_id = _next_id("po")
    if reference is None:
        reference = f"PO-{_next_po_number:04d}"
        _next_po_number += 1
    if expected_at is None:
        expected_at = (_date(_today())
                       + timedelta(days=int(vendor.get("lead_time_days", 0)))).isoformat()
    total = _money(sum(float(i["quantity"]) * float(i["unit_price"]) for i in item_dicts))
    entry = {
        "id": po_id, "reference": reference, "vendor_id": vendor_id,
        "items": item_dicts, "status": POStatus.ORDERED.value if place else POStatus.DRAFT.value,
        "currency": currency, "total": total,
        "ordered_at": _now() if place else None,
        "expected_at": expected_at, "received_at": None, "notes": notes,
        "created_at": _now(), "updated_at": _now(),
    }
    purchase_orders[po_id] = entry
    _save()
    return _po_model(entry)


@mcp.tool
def get_purchase_order(po_id: int) -> Optional[PurchaseOrder]:
    """Retrieve a purchase order."""
    entry = purchase_orders.get(po_id)
    return _po_model(entry) if entry else None


@mcp.tool
def list_purchase_orders(vendor_id: Optional[int] = None,
                         status: Optional[str] = None,
                         limit: int = 100) -> list[PurchaseOrder]:
    """List purchase orders with optional filters."""
    result = [ _po_model(po) for po in purchase_orders.values()
               if (vendor_id is None or int(po["vendor_id"]) == vendor_id)
               and (status is None or po["status"] == status)]
    result.sort(key=lambda po: po.created_at, reverse=True)
    return result[:limit]


@mcp.tool
def place_order(po_id: int) -> Optional[PurchaseOrder]:
    """Move a draft purchase order to ordered."""
    entry = purchase_orders.get(po_id)
    if entry is None:
        return None
    if entry["status"] == POStatus.CANCELLED.value:
        raise ValueError("Cannot place a cancelled order")
    if entry["status"] == POStatus.DRAFT.value:
        entry["status"] = POStatus.ORDERED.value
        entry["ordered_at"] = _now()
        entry["updated_at"] = _now()
        _save()
    return _po_model(entry)


@mcp.tool
def receive_order(po_id: int) -> Optional[PurchaseOrder]:
    """Mark a purchase order as received."""
    entry = purchase_orders.get(po_id)
    if entry is None:
        return None
    if entry["status"] == POStatus.CANCELLED.value:
        raise ValueError("Cannot receive a cancelled order")
    entry["status"] = POStatus.RECEIVED.value
    entry["received_at"] = _now()
    entry["updated_at"] = _now()
    _save()
    return _po_model(entry)


@mcp.tool
def cancel_order(po_id: int) -> Optional[PurchaseOrder]:
    """Cancel a purchase order."""
    entry = purchase_orders.get(po_id)
    if entry is None:
        return None
    if entry["status"] == POStatus.RECEIVED.value:
        raise ValueError("Cannot cancel a received order")
    entry["status"] = POStatus.CANCELLED.value
    entry["updated_at"] = _now()
    _save()
    return _po_model(entry)


# --- reviews & scorecards ----------------------------------------------------
@mcp.tool
def add_vendor_review(vendor_id: int, on_time_delivery: int, quality: int,
                      communication: int, pricing: int,
                      comment: Optional[str] = None) -> VendorReview:
    """Record a vendor performance review (each score 1-5)."""
    if vendor_id not in vendors:
        raise ValueError(f"Unknown vendor: {vendor_id}")
    scores = {
        "on_time_delivery": _validate_score(on_time_delivery, "on_time_delivery"),
        "quality": _validate_score(quality, "quality"),
        "communication": _validate_score(communication, "communication"),
        "pricing": _validate_score(pricing, "pricing"),
    }
    overall = round(sum(scores.values()) / len(scores), 2)
    review_id = _next_id("review")
    review = VendorReview(
        id=review_id, vendor_id=vendor_id, overall=overall,
        comment=comment, created_at=_now(), **scores,
    )
    reviews[review_id] = review.model_dump()
    _save()
    return review


@mcp.tool
def list_vendor_reviews(vendor_id: int) -> list[VendorReview]:
    """List reviews for a vendor, newest first."""
    result = [VendorReview(**r) for r in reviews.values()
              if int(r["vendor_id"]) == vendor_id]
    result.sort(key=lambda r: r.created_at, reverse=True)
    return result


@mcp.tool
def get_vendor_scorecard(vendor_id: int) -> Optional[dict]:
    """Performance scorecard: ratings, order volume, spend, and on-time rate."""
    vendor = vendors.get(vendor_id)
    if vendor is None:
        return None
    orders = [po for po in purchase_orders.values() if int(po["vendor_id"]) == vendor_id]
    received = [po for po in orders if po["status"] == POStatus.RECEIVED.value]
    late = [po for po in received
            if po.get("expected_at") and po.get("received_at")
            and _date(po["received_at"]) > _date(po["expected_at"])]
    spend = _money(sum(float(po["total"]) for po in orders
                       if po["status"] != POStatus.CANCELLED.value))
    averages = _review_averages(vendor_id)
    return {
        "vendor_id": vendor_id, "name": vendor["name"],
        "status": vendor["status"],
        "orders": len(orders),
        "received_orders": len(received),
        "late_deliveries": len(late),
        "on_time_rate": round((len(received) - len(late)) / len(received), 4)
        if received else None,
        "total_spend": spend,
        "review_averages": averages,
        "overall_rating": averages["overall"] if averages else vendor.get("rating"),
        "reviews": len([r for r in reviews.values() if int(r["vendor_id"]) == vendor_id]),
    }


@mcp.tool
def get_low_rated_vendors(threshold: float = 3.0) -> list[dict]:
    """Vendors whose overall rating is below the threshold."""
    result = []
    for vendor_id, vendor in vendors.items():
        averages = _review_averages(vendor_id)
        rating = averages["overall"] if averages else vendor.get("rating")
        if rating is not None and float(rating) < threshold:
            result.append({"vendor_id": vendor_id, "name": vendor["name"],
                           "rating": rating})
    result.sort(key=lambda item: item["rating"])
    return result


@mcp.tool
def get_vendor_spend(start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> dict:
    """Spend by vendor for orders placed in a date range."""
    start = _date(start_date or "1970-01-01")
    end = _date(end_date or _today())
    by_vendor: dict[str, float] = {}
    total = 0.0
    for po in purchase_orders.values():
        if po["status"] == POStatus.CANCELLED.value or not po.get("ordered_at"):
            continue
        placed = _date(po["ordered_at"])
        if not (start <= placed <= end):
            continue
        name = vendors.get(int(po["vendor_id"]), {}).get("name", f"vendor-{po['vendor_id']}")
        by_vendor[name] = _money(by_vendor.get(name, 0) + float(po["total"]))
        total += float(po["total"])
    return {
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "total_spend": _money(total),
        "by_vendor": by_vendor,
    }


@mcp.tool
def get_vendor_stats() -> dict:
    """Vendor and procurement statistics."""
    by_status: dict[str, int] = {}
    for vendor in vendors.values():
        by_status[vendor["status"]] = by_status.get(vendor["status"], 0) + 1
    by_po_status: dict[str, int] = {}
    for po in purchase_orders.values():
        by_po_status[po["status"]] = by_po_status.get(po["status"], 0) + 1
    return {
        "vendors": len(vendors),
        "vendors_by_status": by_status,
        "purchase_orders": len(purchase_orders),
        "purchase_orders_by_status": by_po_status,
        "reviews": len(reviews),
        "total_spend": _money(sum(float(po["total"]) for po in purchase_orders.values()
                                  if po["status"] != POStatus.CANCELLED.value)),
    }


# --- resources ---------------------------------------------------------------
@mcp.resource("vendors://scorecards")
def get_scorecards_resource() -> str:
    """All vendor scorecards as formatted text."""
    if not vendors:
        return "# Vendor Scorecards\n\nNo vendors yet."
    lines = ["# Vendor Scorecards\n"]
    for vendor_id in vendors:
        card = get_vendor_scorecard(vendor_id)
        rating = card["overall_rating"]
        lines.append(f"- **{card['name']}** - rating {rating if rating is not None else 'n/a'}"
                     f" | spend {card['total_spend']:,.2f}"
                     f" | on-time {card['on_time_rate'] if card['on_time_rate'] is not None else 'n/a'}")
    return "\n".join(lines)


@mcp.resource("vendors://stats")
def get_stats_resource() -> str:
    """Procurement statistics."""
    stats = get_vendor_stats()
    return (
        "# Procurement\n\n"
        f"- **Vendors:** {stats['vendors']}\n"
        f"- **Purchase orders:** {stats['purchase_orders']}\n"
        f"- **Total spend:** {stats['total_spend']:,.2f}\n"
        f"- **Reviews:** {stats['reviews']}"
    )


if __name__ == "__main__":
    mcp.run()
