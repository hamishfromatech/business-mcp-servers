"""
Affiliate Marketing Tracker MCP Server
A FastMCP server for tracking affiliate marketing performance: networks, affiliates,
tracking links, clicks, conversions, commissions, and payouts.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pathlib import Path

import json, os, shutil, atexit, tempfile, threading
from pydantic import BaseModel
from fastmcp import FastMCP

###############################################################################
# MCP SERVER
###############################################################################

mcp = FastMCP(
    name="Affiliate Marketing Tracker",
    instructions="""Affiliate marketing performance tracking. Manage networks, affiliates,
tracking links, clicks, conversions, commissions, and payouts. Provide
comprehensive reporting on clicks, conversion rates, commission amounts,
and payout history across affiliate networks.
""",
)

###############################################################################
# ENUMS
###############################################################################

class AffiliateStatus(str, Enum):
    """Affiliate account status."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"

class CommissionType(str, Enum):
    """Commission type."""
    STANDARD = "standard"
    SPLIT = "split"  # e.g., 70% affiliate / 30% sub-affiliate
    FIXED = "fixed"

class PayoutMethod(str, Enum):
    """Payout payment method."""
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    STRIPE = "stripe"
    DIRECT_DEBIT = "direct_debit"
    CHECK = "check"

class PayoutStatus(str, Enum):
    """Payout payment status."""
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    AWAITING_REVIEW = "awaiting_review"

###############################################################################
# DATA MODELS
###############################################################################

class AffiliateNetwork(BaseModel):
    """An affiliate marketing network (e.g., Amazon Associates, ShareASale)."""
    id: int
    name: str
    slug: str
    currency: str = "USD"
    available: bool = True
    nexus_url: Optional[str] = None
    created_at: str
    updated_at: str


class Affiliate(BaseModel):
    """An affiliate (publisher) promoting network products."""
    id: int
    name: str
    email: str
    status: str
    join_method: Optional[str] = None  # "user" | "seed"
    joined_at: Optional[str] = None
    profile_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    profile: Optional[str] = None
    created_at: str
    updated_at: str


class TrackingLink(BaseModel):
    """A tracking link for an affiliate."""
    id: int
    affiliate_id: int
    network_id: Optional[int] = None
    product_category: Optional[str] = None
    product: Optional[str] = None
    tracking_id: Optional[str] = None
    slug: str
    name: str
    clickable_url: str
    seal_image: Optional[str] = None
    clicks: int = 0
    impressions: int = 0
    link_clicks: int = 0
    add_to_carts: int = 0
    purchases: int = 0
    commission_rate_pct: float = 10.0
    lifetime_commission: float = 0.0
    payout_override_pct: Optional[float] = None
    created_at: str
    updated_at: str


class Commission(BaseModel):
    """A commission record for an affiliate/link."""
    id: int
    affiliate_id: int
    link_id: Optional[int] = None
    type: str
    padded_with: Optional[str] = None
    rate_pct: float = 10.0
    currency: str = "USD"
    period_days: int = 0
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    payout_type: Optional[str] = None
    lower_commission_pct: Optional[float] = None
    earned_commission: float = 0.0
    earned_date: Optional[str] = None
    status: str = "active"  # "active" | "expired" | "overridden"
    created_at: str
    updated_at: str


class Payout(BaseModel):
    """A payout record for an affiliate."""
    id: int
    affiliate_id: int
    commission_id: Optional[int] = None
    amount: float
    currency: str
    payout_type: Optional[str] = None
    payout_status: str
    payout_method: Optional[str] = None
    fees: Optional[float] = None
    payment_date: Optional[str] = None
    invoice_number: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    created_at: str
    updated_at: str


###############################################################################
# DATA PERSISTENCE
###############################################################################

DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "affiliate_marketing.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "affiliate_networks": {},
        "affiliates": {},
        "tracking_links": {},
        "commissions": {},
        "payouts": {},
        "click_log": [],
        "conversion_log": [],
        "next_network_id":  1,
        "next_affiliate_id":  1,
        "next_link_id":  1,
        "next_commission_id":  1,
        "next_payout_id":  1,
        "next_click_id":  1,
        "next_conversion_id":  1,
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


###############################################################################
# BACKUP / RESTORE TOOLS
###############################################################################

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


###############################################################################
# INITIALIZATION & STATE
###############################################################################

_data = _load_data()

affiliate_networks: dict[int, dict] = {int(k): v for k, v in _data.get("affiliate_networks", {}).items()}
affiliates: dict[int, dict] = {int(k): v for k, v in _data.get("affiliates", {}).items()}
tracking_links: dict[int, dict] = {int(k): v for k, v in _data.get("tracking_links", {}).items()}
commissions: dict[int, dict] = {int(k): v for k, v in _data.get("commissions", {}).items()}
payouts: dict[int, dict] = {int(k): v for k, v in _data.get("payouts", {}).items()}
click_log: list[dict] = _data.get("click_log", [])
conversion_log: list[dict] = _data.get("conversion_log", [])

_next_network_id = _data.get("next_network_id", 1)
_next_affiliate_id = _data.get("next_affiliate_id", 1)
_next_link_id = _data.get("next_link_id", 1)
_next_commission_id = _data.get("next_commission_id", 1)
_next_payout_id = _data.get("next_payout_id", 1)
_next_click_id = _data.get("next_click_id", 1)
_next_conversion_id = _data.get("next_conversion_id", 1)


def _get_next_network_id() -> int:
    global _next_network_id
    id_ = _next_network_id
    _next_network_id += 1
    return id_


def _get_next_affiliate_id() -> int:
    global _next_affiliate_id
    id_ = _next_affiliate_id
    _next_affiliate_id += 1
    return id_


def _get_next_link_id() -> int:
    global _next_link_id
    id_ = _next_link_id
    _next_link_id += 1
    return id_


def _get_next_commission_id() -> int:
    global _next_commission_id
    id_ = _next_commission_id
    _next_commission_id += 1
    return id_


def _get_next_payout_id() -> int:
    global _next_payout_id
    id_ = _next_payout_id
    _next_payout_id += 1
    return id_


def _get_next_click_id() -> int:
    global _next_click_id
    id_ = _next_click_id
    _next_click_id += 1
    return id_


def _get_next_conversion_id() -> int:
    global _next_conversion_id
    id_ = _next_conversion_id
    _next_conversion_id += 1
    return id_


def _get_affiliate_network(network_id: int) -> Optional[dict]:
    """Get an affiliate network by ID."""
    network = affiliate_networks.get(network_id)
    if network is None:
        return None
    return AffiliateNetwork(**network)


# Save helper
def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "affiliate_networks": affiliate_networks,
        "affiliates": affiliates,
        "tracking_links": tracking_links,
        "commissions": commissions,
        "payouts": payouts,
        "click_log": click_log,
        "conversion_log": conversion_log,
        "next_network_id": _next_network_id,
        "next_affiliate_id": _next_affiliate_id,
        "next_link_id": _next_link_id,
        "next_commission_id": _next_commission_id,
        "next_payout_id": _next_payout_id,
        "next_click_id": _next_click_id,
        "next_conversion_id": _next_conversion_id,
    })


###############################################################################
# AFFILIATE NETWORKS
###############################################################################

@mcp.tool
def create_affiliate_network(
    name: str,
    slug: str,
    currency: str = "USD",
    available: bool = True,
    nexus_url: Optional[str] = None
) -> AffiliateNetwork:
    """Create a new affiliate network.

    Args:
        name: Network name (e.g., "Amazon Associates")
        slug: URL-friendly identifier
        currency: Network's primary currency
        available: Whether the network is available
        nexus_url: Network's nexus URL / dashboard

    Returns:
        The created network
    """
    network_id = _get_next_network_id()
    network = AffiliateNetwork(
        id=network_id,
        name=name,
        slug=slug,
        currency=currency,
        available=available,
        nexus_url=nexus_url,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )
    affiliate_networks[network_id] = network.model_dump()
    _save()
    return network


@mcp.tool
def get_affiliate_network(network_id: int) -> Optional[AffiliateNetwork]:
    """Get a network by ID."""
    return _get_affiliate_network(network_id)


@mcp.tool
def list_affiliate_networks(available: Optional[bool] = None) -> list[AffiliateNetwork]:
    """List networks with optional filter."""
    result = list(affiliate_networks.values())
    if available is not None:
        result = [n for n in result if n.get("available") == available]
    return [AffiliateNetwork(**n) for n in result]


@mcp.tool
def update_affiliate_network(network_id: int, **data) -> Optional[AffiliateNetwork]:
    """Update a network's fields."""
    if network_id not in affiliate_networks:
        return None
    network = affiliate_networks[network_id]
    for k, v in data.items():
        network[k] = v
    network["updated_at"] = datetime.now().isoformat()
    _save()
    return AffiliateNetwork(**network)


###############################################################################
# AFFILIATES
###############################################################################

@mcp.tool
def create_affiliate(
    name: str,
    email: str,
    status: str = AffiliateStatus.PENDING.value,
    join_method: Optional[str] = None,
    joined_at: Optional[str] = None,
    profile_url: Optional[str] = None,
    bio: Optional[str] = None,
    location: Optional[str] = None,
) -> Affiliate:
    """Create a new affiliate.

    Args:
        name: Affiliate's full name or business name
        email: Affiliate's email
        status: Account status (pending, active, suspended, inactive)
        join_method: How they joined ("user" | "seed")
        joined_at: When they joined (ISO format)
        profile_url: Profile/bio URL
        bio: Short biography
        location: Location

    Returns:
        The created affiliate
    """
    affiliate_id = _get_next_affiliate_id()
    affiliate = Affiliate(
        id=affiliate_id,
        name=name,
        email=email,
        status=status,
        join_method=join_method,
        joined_at=joined_at,
        profile_url=profile_url,
        bio=bio,
        location=location,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )
    affiliates[affiliate_id] = affiliate.model_dump()
    _save()
    return affiliate


@mcp.tool
def get_affiliate(affiliate_id: int) -> Optional[Affiliate]:
    """Get an affiliate by ID."""
    data = affiliates.get(affiliate_id)
    if data is None:
        return None
    return Affiliate(**data)


@mcp.tool
def list_affiliates(
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> list[Affiliate]:
    """List affiliates with optional filter/search."""
    result = list(affiliates.values())

    if status:
        result = [a for a in result if a.get("status") == status]

    if search:
        search_lower = search.lower()
        result = [
            a for a in result
            if search_lower in a.get("name", "").lower() or
               search_lower in a.get("email", "").lower() or
               search_lower in (a.get("location") or "").lower()
        ]

    return [Affiliate(**a) for a in result]


@mcp.tool
def update_affiliate(
    affiliate_id: int,
    **data
) -> Optional[Affiliate]:
    """Update an affiliate's fields."""
    if affiliate_id not in affiliates:
        return None
    affiliate = affiliates[affiliate_id]
    for k, v in data.items():
        affiliate[k] = v
    affiliate["updated_at"] = datetime.now().isoformat()
    _save()
    return Affiliate(**affiliate)


@mcp.tool
def delete_affiliate(affiliate_id: int) -> bool:
    """Delete an affiliate."""
    if affiliate_id in affiliates:
        del affiliates[affiliate_id]
        _save()
        return True
    return False


###############################################################################
# TRACKING LINKS
###############################################################################

@mcp.tool
def create_tracking_link(
    affiliate_id: int,
    name: str,
    slug: str,
    network_id: Optional[int] = None,
    product_category: Optional[str] = None,
    product: Optional[str] = None,
    tracking_id: Optional[str] = None,
    seal_image: Optional[str] = None,
    commission_rate_pct: float = 10.0,
    payout_override_pct: Optional[float] = None,
) -> TrackingLink:
    """Create a new tracking link.

    Args:
        affiliate_id: Affiliate who owns the link
        name: Human-readable link name
        slug: URL-friendly slug
        network_id: Affiliat network ID (optional)
        product_category: Product category slug
        product: Product name / ID
        tracking_id: Custom tracking ID (e.g., from network)
        seal_image: Affiliate seal/image URL
        commission_rate_pct: Base commission rate as percentage
        payout_override_pct: Payout override rate as percentage

    Returns:
        The created tracking link
    """
    link_id = _get_next_link_id()

    clickable_url = f"https://yoursite.com/{slug}"

    link = TrackingLink(
        id=link_id,
        affiliate_id=affiliate_id,
        network_id=network_id,
        product_category=product_category,
        product=product,
        tracking_id=tracking_id,
        slug=slug,
        name=name,
        clickable_url=clickable_url,
        seal_image=seal_image,
        clicks=0,
        impressions=0,
        link_clicks=0,
        add_to_carts=0,
        purchases=0,
        commission_rate_pct=commission_rate_pct,
        lifetime_commission=0.0,
        payout_override_pct=payout_override_pct,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )
    tracking_links[link_id] = link.model_dump()
    _save()
    return link


@mcp.tool
def get_tracking_link(link_id: int) -> Optional[TrackingLink]:
    """Get a tracking link by ID."""
    data = tracking_links.get(link_id)
    if data is None:
        return None
    return TrackingLink(**data)


@mcp.tool
def list_tracking_links(
    affiliate_id: Optional[int] = None,
    network_id: Optional[int] = None,
) -> list[TrackingLink]:
    """List tracking links with optional filter."""
    result = list(tracking_links.values())
    if affiliate_id:
        result = [l for l in result if l.get("affiliate_id") == affiliate_id]
    if network_id:
        result = [l for l in result if l.get("network_id") == network_id]
    return [TrackingLink(**l) for l in result]


@mcp.tool
def update_tracking_link(link_id: int, **data) -> Optional[TrackingLink]:
    """Update a tracking link's fields."""
    if link_id not in tracking_links:
        return None
    link = tracking_links[link_id]
    for k, v in data.items():
        link[k] = v
    link["updated_at"] = datetime.now().isoformat()
    _save()
    return TrackingLink(**link)


###############################################################################
# CLICK TRACKING
###############################################################################

@mcp.tool
def record_click(
    link_id: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    source: Optional[str] = None,
    medium: Optional[str] = None,
    campaign: Optional[str] = None,
    referred_from: Optional[str] = None,
) -> dict:
    """Record a click on a tracking link.

    Args:
        link_id: The tracking link ID
        ip_address: Clicker's IP address
        user_agent: Clicker's user agent
        source: Traffic source (e.g., "google", "facebook")
        medium: Traffic medium (e.g., "cpc", "organic")
        campaign: Campaign name
        referred_from: Referrer URL

    Returns:
        The recorded click details
    """
    if not link_id in tracking_links:
        return {"error": "Link not found", "link_id": link_id}

    click_id = _get_next_click_id()
    click = {
        "id": click_id,
        "link_id": link_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "source": source,
        "medium": medium,
        "campaign": campaign,
        "referred_from": referred_from,
        "clicked_at": datetime.now().isoformat(),
    }
    click_log.append(click)
    _save()

    link = tracking_links[link_id]
    link["clicks"] = link.get("clicks", 0) + 1
    link["impressions"] = link.get("impressions", 0) + 1
    link["link_clicks"] = link.get("link_clicks", 0) + 1
    link["updated_at"] = datetime.now().isoformat()
    tracking_links[link_id] = link.model_dump()

    return {**click, "link_clicks": link["link_clicks"]}


@mcp.tool
def record_impression(
    link_id: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """Record an impression event on a tracking link."""
    if link_id not in tracking_links:
        return {"error": "Link not found", "link_id": link_id}

    click_id = _get_next_click_id()
    impression = {
        "id": click_id,
        "link_id": link_id,
        "type": "impression",
        "ip_address": ip_address,
        "user_agent": user_agent,
        "source": source,
        "impressed_at": datetime.now().isoformat(),
    }
    click_log.append(impression)
    _save()

    link = tracking_links[link_id]
    link["impressions"] = link.get("impressions", 0) + 1
    link["updated_at"] = datetime.now().isoformat()
    tracking_links[link_id] = link.model_dump()

    return impression


@mcp.tool
def get_click_log(
    link_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> list[dict]:
    """Get the click log with optional filters."""
    result = click_log.copy()

    if link_id:
        result = [c for c in result if c.get("link_id") == link_id]

    if start_date:
        result = [c for c in result if c.get("clicked_at", "") >= start_date]

    if end_date:
        result = [c for c in result if c.get("clicked_at", "") <= end_date]

    return result


###############################################################################
# CONVERSION TRACKING
###############################################################################

@mcp.tool
def record_conversion(
    link_id: int,
    conversion_type: str,
    revenue: float = 0.0,
    currency: str = "USD",
    quantity: int = 1,
    price: float = 0.0,
    product: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    source: Optional[str] = None,
    coupon: Optional[str] = None,
) -> dict:
    """Record a conversion event.

    Args:
        link_id: The tracking link ID
        conversion_type: Type of conversion
        revenue: Conversion revenue amount
        currency: Currency code
        quantity: Quantity of items
        price: Price per item
        product: Product name / ID
        ip_address: Converter's IP
        user_agent: Converter's user agent
        source: Traffic source
        coupon: Used coupon code

    Returns:
        The recorded conversion details
    """
    if link_id not in tracking_links:
        return {"error": "Link not found", "link_id": link_id}

    conversion_id = _get_next_conversion_id()
    conversion = {
        "id": conversion_id,
        "link_id": link_id,
        "conversion_type": conversion_type,
        "revenue": revenue,
        "currency": currency,
        "quantity": quantity,
        "price": price,
        "product": product,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "source": source,
        "coupon": coupon,
        "converted_at": datetime.now().isoformat(),
    }
    conversion_log.append(conversion)
    _save()

    return conversion


@mcp.tool
def get_conversion_log(
    link_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> list[dict]:
    """Get the conversion log with optional filters."""
    result = conversion_log.copy()

    if link_id:
        result = [c for c in result if c.get("link_id") == link_id]

    if start_date:
        result = [c for c in result if c.get("converted_at", "") >= start_date]

    if end_date:
        result = [c for c in result if c.get("converted_at", "") <= end_date]

    return result


###############################################################################
# COMMISSIONS
###############################################################################

@mcp.tool
def create_commission(
    affiliate_id: int,
    link_id: Optional[int] = None,
    type: str = CommissionType.STANDARD.value,
    padded_with: Optional[str] = None,
    rate_pct: float = 10.0,
    currency: str = "USD",
    period_days: int = 0,
    effective_from: Optional[str] = None,
    effective_until: Optional[str] = None,
    payout_type: Optional[str] = None,
    lower_commission_pct: Optional[float] = None,
    earned_commission: float = 0.0,
) -> Commission:
    """Create a commission rate / record.

    Args:
        affiliate_id: Affiliate ID
        link_id: Optional tracking link ID
        type: Commission type
        padded_with: How padding is applied
        rate_pct: Commission rate as percentage
        currency: Currency code
        period_days: Payout period in days
        effective_from: Effective from date
        effective_until: Effective until date
        payout_type: Payout type (e.g., "customers", "sales")
        lower_commission_pct: Lower tier commission rate
        earned_commission: Earned commission amount

    Returns:
        The created commission
    """
    commission_id = _get_next_commission_id()
    commission = Commission(
        id=commission_id,
        affiliate_id=affiliate_id,
        link_id=link_id,
        type=type,
        padded_with=padded_with,
        rate_pct=rate_pct,
        currency=currency,
        period_days=period_days,
        effective_from=effective_from,
        effective_until=effective_until,
        payout_type=payout_type,
        lower_commission_pct=lower_commission_pct,
        earned_commission=earned_commission,
        status="active",
        earned_date=datetime.now().isoformat(),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )
    commissions[commission_id] = commission.model_dump()
    _save()
    return commission


@mcp.tool
def get_commission(commission_id: int) -> Optional[Commission]:
    """Get a commission record by ID."""
    data = commissions.get(commission_id)
    if data is None:
        return None
    return Commission(**data)


@mcp.tool
def list_commissions(
    affiliate_id: Optional[int] = None,
    link_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[Commission]:
    """List commissions with optional filters."""
    result = list(commissions.values())
    if affiliate_id:
        result = [c for c in result if c.get("affiliate_id") == affiliate_id]
    if link_id:
        result = [c for c in result if c.get("link_id") == link_id]
    if status:
        result = [c for c in result if c.get("status") == status]

    return [Commission(**c) for c in result]


@mcp.tool
def update_commission(commission_id: int, **data) -> Optional[Commission]:
    """Update a commission record."""
    if commission_id not in commissions:
        return None
    commission = commissions[commission_id]
    for k, v in data.items():
        commission[k] = v
    commission["updated_at"] = datetime.now().isoformat()
    _save()
    return Commission(**commission)


###############################################################################
# PAYOUTS
###############################################################################

@mcp.tool
def create_payout(
    affiliate_id: int,
    commission_id: Optional[int] = None,
    amount: float = 0.0,
    currency: str = "USD",
    payout_type: Optional[str] = None,
    payout_status: str = PayoutStatus.PENDING.value,
    payout_method: Optional[str] = None,
    fees: Optional[float] = None,
    payment_date: Optional[str] = None,
    invoice_number: Optional[str] = None,
    stripe_payment_intent_id: Optional[str] = None,
) -> Payout:
    """Create a payout for an affiliate.

    Args:
        affiliate_id: Affiliate ID
        commission_id: Optional related commission record ID
        amount: Payout amount
        currency: Currency code
        payout_type: Payout type
        payout_status: Payout status
        payout_method: Payment method
        fees: Processing fees
        payment_date: Scheduled payment date
        invoice_number: Invoice number
        stripe_payment_intent_id: Stripe payment intent ID

    Returns:
        The created payout
    """
    payout_id = pg_next_payout_id()
    payout_id = _get_next_payout_id()
    payout = Payout(
        id=payout_id,
        affiliate_id=affiliate_id,
        commission_id=commission_id,
        amount=amount,
        currency=currency,
        payout_type=payout_type,
        payout_status=payout_status,
        payout_method=payout_method,
        fees=fees,
        payment_date=payment_date,
        invoice_number=invoice_number,
        stripe_payment_intent_id=stripe_payment_intent_id,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )
    payouts[payout_id] = payout.model_dump()
    _save()
    return payout


@mcp.tool
def get_payout(payout_id: int) -> Optional[Payout]:
    """Get a payout by ID."""
    data = payouts.get(payout_id)
    if data is None:
        return None
    return Payout(**data)


@mcp.tool
def list_payouts(
    affiliate_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[Payout]:
    """List payouts with optional filters."""
    result = list(payouts.values())

    if affiliate_id:
        result = [p for p in result if p.get("affiliate_id") == affiliate_id]

    if start_date:
        result = [p for p in result if p.get("created_at", "") >= start_date]

    if end_date:
        result = [p for p in result if p.get("created_at", "") <= end_date]

    return [Payout(**p) for p in result]


@mcp.tool
def process_payout(
    payout_id: int,
    payout_status: str,
    fees: Optional[float] = None,
    payment_date: Optional[str] = None,
) -> Optional[Payout]:
    """Update a payout's status and process it.

    Args:
        payout_id: The payout ID
        payout_status: New status
        fees: Processing fees
        payment_date: Payment date

    Returns:
        The updated payout
    """
    if payout_id not in payouts:
        return None
    payout = payouts[payout_id]
    payout["payout_status"] = payout_status
    if fees is not None:
        payout["fees"] = fees
    if payment_date is not None:
        payout["payment_date"] = payment_date
    payout["updated_at"] = datetime.now().isoformat()
    _save()
    return Payout(**payout)


###############################################################################
# LINKED DATA HELPERS
###############################################################################

def _get_affiliate_data(affiliate_id: int) -> Optional[dict]:
    """Get affiliate + their network + their links."""
    affiliate = affiliates.get(affiliate_id)
    if not affiliate:
        return None
    network_id = None
    for link in tracking_links.values():
        if link["affiliate_id"] == affiliate_id:
            network_id = link.get("network_id")
            break
    return {**affiliate, "network_id": network_id}


def _get_link_data(link_id: int) -> Optional[dict]:
    """Get link + its affiliate + click stats."""
    link = tracking_links.get(link_id)
    if not link:
        return None

    affiliate_id = link["affiliate_id"]
    affiliate = affiliates.get(affiliate_id)

    link_clicks = sum(1 for c in click_log if c.get("link_id") == link_id)
    link_impressions = sum(1 for c in click_log if c.get("link_id") == link_id and c.get("type") == "impression")

    conversions = [c for c in conversion_log if c.get("link_id") == link_id]
    total_revenue = sum(c.get("revenue", 0) for c in conversions)

    return {**link, "affiliate": affiliate, "clicks": link_clicks, "impressions": link_impressions, "conversions": len(conversions), "revenue": total_revenue}


###############################################################################
# ANALYTICS / SUMMARY TOOLS
###############################################################################

@mcp.tool
def get_network_summary() -> dict:
    """Get a summary of all affiliate networks and their affiliates."""
    summary = {}
    for network_id, network in affiliate_networks.items():
        if network_id in summary:
            summary[network_id]["affiliates"] += len([a for a in affiliates.values() if a.get("network_id") == network_id])
        else:
            summary[network_id] = {"name": network.get("name"), "affiliates": 0}
    return summary


@mcp.tool
def get_affiliate_performance(affiliate_id: int) -> Optional[dict]:
    """Get comprehensive performance metrics for an affiliate."""
    affiliate = affiliates.get(affiliate_id)
    if not affiliate:
        return None

    links = [l for l in tracking_links.values() if l.get("affiliate_id") == affiliate_id]
    link_ids = {l["id"] for l in links}

    link_stats = {
        "total_clicks": 0,
        "total_impressions": 0,
        "total_conversions": 0,
        "total_revenue": 0.0,
        "link_sums": [],
    }

    for link in links:
        link_ids.add(link["id"])
        link_stats["link_sums"].append({
            "id": link["id"],
            "name": link.get("name"),
            "clicks": link.get("clicks", 0),
            "impressions": link.get("impressions", 0),
            "link_clicks": link.get("link_clicks", 0),
            "purchases": link.get("purchases", 0),
            "lifetime_commission": link.get("lifetime_commission", 0),
        })

    link_stats["total_clicks"] = sum(l.get("clicks", 0) for l in links)
    link_stats["total_impressions"] = sum(l.get("impressions", 0) for l in links)

    affiliate_conversions = [c for c in conversion_log if any(l["id"] == c["link_id"] for l in links)]
    total_revenue = sum(c.get("revenue", 0) for c in affiliate_conversions)
    link_stats["total_conversions"] = len(affiliate_conversions)
    link_stats["total_revenue"] = round(total_revenue, 2)

    payouts = [p for p in payouts.values() if p.get("affiliate_id") == affiliate_id]
    total_payouts = sum(p.get("amount", 0) for p in payouts if p.get("payout_status") in ("paid", "partial"))
    link_stats["total_payouts"] = total_payouts
    link_stats["payout_count"] = len([p for p in payouts if p.get("payout_status") in ("paid", "partial")])

    return {
        **affiliate,
        **link_stats,
        "links_count": len(links),
        "links": link_stats["link_sums"],
    }


@mcp.tool
def get_click_rate(link_id: int) -> Optional[dict]:
    """Get click rate (ctr, cpc, conversion rate) for a link."""
    link = tracking_links.get(link_id)
    if not link:
        return None

    clicks = link.get("clicks", 0)
    impressions = link.get("impressions", 0)

    # Get conversions
    conversions = [c for c in conversion_log if c.get("link_id") == link_id]
    conversion_rate = len(conversions) / impressions if impressions > 0 else 0

    # Click-through rate
    ctr = clicks / impressions if impressions > 0 else 0
    # CPC approximation
    cpc = clicks / clicks if clicks > 0 else 0
    # Cost-per-acquisition (CPA)
    acquisition_cost = clicks / len(conversions) if conversions else 0

    return {
        "link_id": link_id,
        "impressions": impressions,
        "clicks": clicks,
        "ctr": round(ctr * 100, 4),
        "cpc": round(cpc, 4),
        "conversions": len(conversions),
        "conversion_rate": round(conversion_rate * 100, 4),
        "acquisition_cost": round(acquisition_cost, 2),
    }


@mcp.tool
def get_commission_summary() -> dict:
    """Get summary of all commissions and payouts."""
    total_earned = sum(c.get("earned_commission", 0) for c in commissions.values())
    total_payouts = sum(p.get("amount", 0) for p in payouts.values() if p.get("payout_status") in ("paid", "partial"))
    total_fees = sum(p.get("fees", 0) for p in payouts.values())
    commissionearnings = {
        "total_commissions_earned": round(total_earned, 2),
        "total_payouts": round(total_payouts, 2),
        "total_fees": round(total_fees, 2),
        "net_earnings": round(total_earned - total_payouts, 2),
        "active_commissions": len([c for c in commissions.values() if c.get("status") == "active"]),
        "pending_payouts": len([p for p in payouts.values() if p.get("payout_status") == "pending"]),
    }
    return commissionearnings


###############################################################################
# RESOURCES
###############################################################################

@mcp.resource("affiliates://all")
def get_all_affiliates_resource() -> str:
    """Resource listing all affiliates."""
    if not affiliates:
        return "No affiliates found."
    lines = ["# All Affiliates\n"]
    for a in sorted(affiliates.values(), key=lambda x: x.get("created_at", ""), reverse=True):
        lines.append(f"## {a['name']} (ID: {a['id']})")
        lines.append(f"- Status: {a['status']}")
        lines.append(f"- Email: {a['email']}")
        if a.get('profile_url'):
            lines.append(f"- Profile: {a['profile_url']}")
        if a.get('location'):
            lines.append(f"- Location: {a['location']}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("links://all")
def get_all_links_resource() -> str:
    """Resource listing all tracking links with stats."""
    if not tracking_links:
        return "No tracking links found."
    lines = ["# Tracking Links\n"]
    for link in sorted(tracking_links.values(), key=lambda x: x.get("created_at", ""), reverse=True)[:20]:
        lines.append(f"## {link['name']} (ID: {link['id']})")
        lines.append(f"- Affiliate: {link['affiliate_id']}")
        lines.append(f"- Clicks: {link['clicks']} | Impressions: {link['impressions']}")
        lines.append(f"- Link Clicks: {link['link_clicks']} | Add to Carts: {link['add_to_carts']} | Purchases: {link['purchases']}")
        lines.append(f"- Commission Rate: {link['commission_rate_pct']}%")
        if link.get('lifetime_commission'):
            lines.append(f"- Lifetime Commission: ${link['lifetime_commission']}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("performance://summary")
def get_performance_summary_resource() -> str:
    """Resource with overall performance summary."""
    # Aggregate totals
    total_clicks = sum(l.get("clicks", 0) for l in tracking_links.values())
    total_impressions = sum(l.get("impressions", 0) for l in tracking_links.values())
    total_revenue = sum(c.get("revenue", 0) for c in conversion_log)

    lines = ["# Affiliate Marketing Performance Summary\n"]
    lines.append(f"- Total Impressions: {total_impressions:,}")
    lines.append(f"- Total Clicks: {total_clicks:,}")
    if total_impressions > 0:
        lines.append(f"- CTR: {round(total_clicks / total_impressions * 100, 2)}%")
    lines.append(f"- Total Conversions: {len(conversion_log)}")
    if total_impressions > 0:
        lines.append(f"- Conversion Rate: {round(total_clicks / total_impressions * 100, 2)}%")
    lines.append(f"- Total Revenue: ${total_revenue:,.2f}")
    lines.append("")

    # By network
    by_network = {}
    for link in tracking_links.values():
        network = link.get("network_id")
        if network:
            by_network[network] = by_network.get(network, 0) + 1

    if by_network:
        lines.append("## Links by Network\n")
        for net, count in sorted(by_network.items(), key=lambda x: -x[1]):
            lines.append(f"- {net}: {count}")
        lines.append("")

    lines.append("## Top Performing Links\n")
    sorted_links = sorted(tracking_links.values(), key=lambda x: x.get("clicks", 0), reverse=True)[:5]
    for link in sorted_links:
        lines.append(f"- {link['name']}: {link['clicks']} clicks")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()