"""
Email Marketing Campaign Manager MCP Server
A FastMCP server for email campaigns, templates, A/B testing, recipient lists,
scheduling, and performance analytics.
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
    name="Email Marketing Campaign Manager",
    instructions=(
        "A FastMCP MCP server for email marketing campaigns, "
        "template management, A/B testing, recipient lists, "
        "scheduling, and performance analytics."
    ),
)


class CampaignStatus(str, Enum):
    """Status of a campaign at current point."""
    DRAFT = "draft"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    SENT = "sent"
    PENDING_SEND = "pending_send"


class RecipientCategory(str, Enum):
    """Categories for recipient list members."""
    CUSTOMER = "customer"
    LEAD = "lead"
    SUBSCRIBER = "subscriber"
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    ANNOUNCEMENT = "announcement"


class ListCategory(str, Enum):
    """Categories for recipient lists."""
    CUSTOMER = "customer"
    LEAD = "lead"
    SUBSCRIBER = "subscriber"
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    ANNOUNCEMENT = "announcement"


class CampaignCategory(str, Enum):
    """Categories for email campaigns."""
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    ANNOUNCEMENT = "announcement"
    TRANSACTIONAL = "transactional"
    EDUCATIONAL = "educational"
    REENGAGEMENT = "reengagement"
    ABANDONED_CART = "abandoned_cart"
    WELCOME = "welcome"
    ONBOARDING = "onboarding"


# Data persistence setup
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "email-marketing.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "campaigns": {},
        "templates": {},
        "recipient_lists": {},
        "sent_events": {},
        "next_campaign_id": 1,
        "next_template_id": 1,
        "next_list_id": 1,
        "next_member_id": 1,
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


# ============== Models ==============

class EmailMember(BaseModel):
    """A recipient list member."""
    id: int
    list_id: int
    address: str
    added_at: str


class TemplateVersion(BaseModel):
    """A template version for a campaign."""
    id: int
    campaign_id: int
    campaign_name: str
    from_name: str
    from_email: str
    reply_to: Optional[str]
    bcc_list: list[str]
    subject_line: str
    template_version_num: int
    status: str
    body_html: str
    body_text: str
    opens: int = 0
    clicks: int = 0
    conversions: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    conversion_rate: float = 0.0
    created_at: str
    updated_at: str
    sent_at: Optional[str] = None
    variant_a: bool = False
    variant_b: bool = False
    recipient_lists: list[int] = []


class Campaign(BaseModel):
    """An email marketing campaign."""
    id: int
    campaign_name: str
    category: str
    status: str
    description: Optional[str]
    from_name: str
    from_email: str
    reply_to: Optional[str]
    bcc_list: list[str]
    scheduled_for: Optional[str]
    sent_at: Optional[str]
    recipient_lists: list[int]
    template_version_num: int
    created_at: str
    updated_at: str


# ============== State Initialization ==============

_data = _load_data()
campaigns: dict[int, dict] = {int(k): v for k, v in _data.get("campaigns", {}).items()}
templates: dict[int, dict] = {int(k): v for k, v in _data.get("templates", {}).items()}
lists: dict[int, dict] = {int(k): v for k, v in _data.get("recipient_lists", {}).items()}
members: dict[int, dict] = {int(k): v for k, v in _data.get("sent_events", {}).items()}


_next_campaign_id = _data.get("next_campaign_id", 1)
_next_template_id = _data.get("next_template_id", 1)
_next_list_id = _data.get("next_list_id", 1)
_next_member_id = _data.get("next_member_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "campaigns": campaigns,
        "templates": templates,
        "recipient_lists": lists,
        "sent_events": members,
        "next_campaign_id": _next_campaign_id,
        "next_template_id": _next_template_id,
        "next_list_id": _next_list_id,
        "next_member_id": _next_member_id,
    })


def _next_id(kind: str) -> int:
    """Allocate the next integer id for a collection."""
    global _next_campaign_id, _next_template_id, _next_list_id, _next_member_id
    if kind == "campaign":
        value = _next_campaign_id
        _next_campaign_id += 1
    elif kind == "template":
        value = _next_template_id
        _next_template_id += 1
    elif kind == "list":
        value = _next_list_id
        _next_list_id += 1
    else:
        value = _next_member_id
        _next_member_id += 1
    return value


def _as_list(value) -> list:
    """Accept a real list or a JSON-stringified list from MCP clients."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, TypeError):
            return [value]
    return value


def _today_iso() -> str:
    """Return current date as ISO string."""
    return datetime.now().date().isoformat()


def _parse_date(value: str) -> datetime:
    """Parse an ISO date string to datetime."""
    return datetime.fromisoformat(value)


def _add_days(dt: datetime, days: int) -> datetime:
    """Add days to a datetime."""
    return dt + timedelta(days=days)


def _save_analytics(template: dict, opens: int = 0, clicks: int = 0, conversions: int = 0) -> None:
    """Save analytics for a template."""
    template["opens"] = opens
    template["clicks"] = clicks
    template["conversions"] = conversions
    if template["opens"] > 0:
        template["open_rate"] = round(template["opens"] / 1000.0, 4)
    if template["clicks"] > 0:
        template["click_rate"] = round(template["clicks"] / 1000.0, 4)
    template["updated_at"] = _today_iso()
    _save()


# ===== Recipient Lists =====

@mcp.tool
def create_list(name: str, category: str = "customer", description: Optional[str] = None) -> dict:
    """Create a recipient list."""
    list_id = _next_id("list")
    entry = {
        "id": list_id,
        "name": name,
        "category": category,
        "description": description or "",
        "member_count": 0,
        "created_at": _today_iso(),
        "updated_at": _today_iso(),
    }
    lists[list_id] = entry
    _save()
    return entry


@mcp.tool
def get_list(list_id: int) -> Optional[dict]:
    """Retrieve a recipient list by id."""
    data = lists.get(list_id)
    return dict(data) if data else None


@mcp.tool
def list_lists(category: Optional[str] = None, limit: int = 100) -> list[dict]:
    """List all recipient lists, optionally filtered by category."""
    result = []
    for entry in lists.values():
        if category is not None and entry.get("category") != category:
            continue
        result.append(dict(entry))
    result.sort(key=lambda e: e["created_at"], reverse=True)
    offset = 0
    return result[offset:offset + limit]


@mcp.tool
def update_list(
    list_id: int,
    name: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
) -> Optional[dict]:
    """Update a recipient list."""
    entry = lists.get(list_id)
    if entry is None:
        return None
    for field, value in (("name", name), ("category", category), ("description", description)):
        if value is not None:
            entry[field] = value
    entry["updated_at"] = _today_iso()
    _save()
    return dict(entry)


@mcp.tool
def delete_list(list_id: int) -> bool:
    """Delete a recipient list."""
    if list_id not in lists:
        return False
    # Remove members and their list references
    to_remove = [mid for mid, m in members.items() if m.get("list_id") == list_id]
    for mid in to_remove:
        del members[mid]
    del lists[list_id]
    _save()
    return True


@mcp.tool
def add_member(list_id: int, address: str, notes: Optional[str] = None) -> EmailMember:
    """Add a recipient to a list."""
    if isinstance(address, str):
        address = address.strip().lower()
    entry = lists.get(list_id)
    if entry is None:
        raise ValueError(f"Unknown list: {list_id}")
    member_id = _next_id("member")
    member = EmailMember(
        id=member_id,
        list_id=list_id,
        address=address,
        added_at=_today_iso(),
    )
    members[member_id] = member.model_dump()
    entry["member_count"] = max(1, entry.get("member_count", 0) + 1)
    entry["updated_at"] = _today_iso()
    _save()
    return member


@mcp.tool
def remove_member(list_id: int, address: str) -> bool:
    """Remove a recipient from a list by email address."""
    _, found = next((m for m in members.values() if m["address"].lower() == address.lower() and m["list_id"] == list_id), (None, None))
    if not found:
        return False
    del members[_]  # type: ignore
    entry = lists.get(list_id)
    if entry:
        entry["member_count"] = max(0, entry.get("member_count", 0) - 1)
        entry["updated_at"] = _today_iso()
    _save()
    return True


@mcp.tool
def get_list_members(list_id: int) -> list[dict]:
    """Get all members of a recipient list."""
    member_list = [m for m in members.values() if m.get("list_id") == list_id]
    member_list.sort(key=lambda m: m["address"])
    return [dict(m) for m in member_list]


# ===== Campaigns =====

@mcp.tool
def create_campaign(
    campaign_name: str,
    category: str = "promotional",
    description: Optional[str] = None,
    from_name: str = "Your Team",
    from_email: str = "team@example.com",
    reply_to: Optional[str] = None,
    bcc_list: Optional[list[str]] = None,
    recipient_lists: Optional[list[int]] = None,
    template_version_num: int = 1,
) -> dict:
    """Create a new email marketing campaign."""
    campaign_id = _next_id("campaign")
    entry = {
        "id": campaign_id,
        "campaign_name": campaign_name,
        "category": category,
        "status": CampaignStatus.DRAFT.value,
        "description": description or "",
        "from_name": from_name,
        "from_email": from_email,
        "reply_to": reply_to,
        "bcc_list": bcc_list or [],
        "scheduled_for": None,
        "sent_at": None,
        "recipient_lists": recipient_lists or [],
        "template_version_num": template_version_num,
        "created_at": _today_iso(),
        "updated_at": _today_iso(),
    }
    campaigns[campaign_id] = entry
    _save()
    return entry


@mcp.tool
def get_campaign(campaign_id: int) -> Optional[dict]:
    """Retrieve a campaign by id."""
    data = campaigns.get(campaign_id)
    return dict(data) if data else None


@mcp.tool
def list_campaigns(status: Optional[str] = None, category: Optional[str] = None, limit: int = 100) -> list[dict]:
    """List campaigns with optional filters."""
    result = []
    for entry in campaigns.values():
        if status is not None and entry.get("status") != status:
            continue
        if category is not None and entry.get("category") != category:
            continue
        result.append(dict(entry))
    result.sort(key=lambda c: c["created_at"], reverse=True)
    offset = 0
    return result[offset:offset + limit]


@mcp.tool
def update_campaign(
    campaign_id: int,
    campaign_name: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    from_name: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
    bcc_list: Optional[list[str]] = None,
    recipient_lists: Optional[list[int]] = None,
) -> Optional[dict]:
    """Update a campaign. Partial updates are supported."""
    entry = campaigns.get(campaign_id)
    if entry is None:
        return None
    for field, value in (
        ("campaign_name", campaign_name),
        ("category", category),
        ("description", description),
        ("from_name", from_name),
        ("from_email", from_email),
        ("reply_to", reply_to),
        ("bcc_list", bcc_list),
        ("recipient_lists", recipient_lists),
    ):
        if value is not None:
            entry[field] = value
    entry["updated_at"] = _today_iso()
    _save()
    return dict(entry)


@mcp.tool
def delete_campaign(campaign_id: int) -> bool:
    """Delete a campaign."""
    if campaign_id not in campaigns:
        return False
    for template_id, template in templates.items():
        if template.get("campaign_id") == campaign_id:
            del templates[template_id]
    del campaigns[campaign_id]
    _save()
    return True


# ===== Templates =====

@mcp.tool
def create_template(
    campaign_id: int,
    from_name: str,
    from_email: str,
    subject_line: str,
    body_html: str,
    body_text: str,
    bcc_list: Optional[list[str]] = None,
    recipient_lists: Optional[list[int]] = None,
    is_variant_a: bool = False,
    is_variant_b: bool = False,
    template_version_num: Optional[int] = None,
) -> dict:
    """Create a template version for a campaign (A/B testing variants)."""
    if campaign_id not in campaigns:
        raise ValueError(f"Unknown campaign: {campaign_id}")
    if is_variant_a and is_variant_b:
        raise ValueError("Cannot specify both variant_a and variant_b")
    campaign = campaigns[campaign_id]
    version_num = template_version_num if template_version_num is not None else (campaign.get("template_version_num", 1) + 1)
    campaign["template_version_num"] = version_num
    template_id = _next_id("template")
    entry = {
        "id": template_id,
        "campaign_id": campaign_id,
        "campaign_name": campaign["campaign_name"],
        "from_name": from_name,
        "from_email": from_email,
        "reply_to": campaign.get("reply_to"),
        "bcc_list": bcc_list or [],
        "subject_line": subject_line,
        "template_version_num": version_num,
        "status": CampaignStatus.DRAFT.value,
        "body_html": body_html,
        "body_text": body_text,
        "opens": 0,
        "clicks": 0,
        "conversions": 0,
        "open_rate": 0.0,
        "click_rate": 0.0,
        "conversion_rate": 0.0,
        "created_at": _today_iso(),
        "updated_at": _today_iso(),
        "sent_at": None,
        "variant_a": is_variant_a,
        "variant_b": is_variant_b,
        "recipient_lists": recipient_lists or [],
    }
    templates[template_id] = entry
    _save()
    return entry


@mcp.tool
def update_template(
    template_id: int,
    subject_line: Optional[str] = None,
    body_html: Optional[str] = None,
    body_text: Optional[str] = None,
    bcc_list: Optional[list[str]] = None,
    is_variant_a: Optional[bool] = None,
    is_variant_b: Optional[bool] = None,
    status: Optional[str] = None,
) -> Optional[dict]:
    """Update a template version."""
    entry = templates.get(template_id)
    if entry is None:
        return None
    for field, value in (
        ("subject_line", subject_line),
        ("body_html", body_html),
        ("body_text", body_text),
        ("bcc_list", bcc_list),
        ("variant_a", is_variant_a),
        ("variant_b", is_variant_b),
        ("status", status),
    ):
        if value is not None:
            entry[field] = value
    entry["updated_at"] = _today_iso()
    _save()
    return dict(entry)


@mcp.tool
def approve_template(template_id: int) -> Optional[dict]:
    """Mark a template as approved for sending."""
    entry = templates.get(template_id)
    if entry is None:
        return None
    if entry.get("status") != CampaignStatus.DRAFT.value:
        raise ValueError("Only draft templates can be approved")
    entry["status"] = CampaignStatus.APPROVED.value
    entry["updated_at"] = _today_iso()
    _save()
    return dict(entry)


@mcp.tool
def list_templates(campaign_id: Optional[int] = None) -> list[dict]:
    """List templates, optionally filtered by campaign."""
    result = []
    for entry in templates.values():
        if campaign_id is not None and entry.get("campaign_id") != campaign_id:
            continue
        result.append(dict(entry))
    result.sort(key=lambda t: t.get("template_version_num", 0), reverse=True)
    return result


@mcp.tool
def copy_template(template_id: int, campaign_id: int, is_variant_a: bool = False) -> dict:
    """Copy a template into a new version for another campaign."""
    source = templates.get(template_id)
    if source is None:
        raise ValueError(f"Template {template_id} not found")
    # Find the source campaign
    src_campaign = next((c for c in campaigns.values() if c["id"] == source.get("campaign_id")), None)
    if not src_campaign:
        raise ValueError(f"Campaign {source.get('campaign_id')} not found")
    version = create_template(
        campaign_id=campaign_id,
        from_name=source.get("from_name", "Your Team"),
        from_email=source.get("from_email", "team@example.com"),
        subject_line=source.get("subject_line", ""),
        body_html=source.get("body_html", ""),
        body_text=source.get("body_text", ""),
        bcc_list=source.get("bcc_list", []) or [],
        recipient_lists=source.get("recipient_lists", []) or [],
        is_variant_a=is_variant_a,
    )
    _save()
    return version


@mcp.tool
def compare_ab_test(campaign_id: int) -> Optional[dict]:
    """Compare A/B test results for a campaign."""
    campaign = campaigns.get(campaign_id)
    if not campaign:
        return None
    variants = [t for t in templates.values() if t.get("campaign_id") == campaign_id]
    # Group by variant flag
    results = {}
    for v in variants:
        key = "variant_a" if v.get("variant_a") else ("variant_b" if v.get("variant_b") else "unknown")
        results[key] = {
            "variant_a": v.get("variant_a", False),
            "variant_b": v.get("variant_b", False),
            "opens": v.opens,
            "clicks": v.clicks,
            "conversions": v.conversions,
            "open_rate": round(v.open_rate * 100, 2),
            "click_rate": round(v.click_rate * 100, 2),
            "conversion_rate": round(v.conversion_rate * 100, 2),
            "subject_line": v.subject_line,
        }
    return {"campaign_id": campaign_id, "campaign_name": campaign.get("campaign_name"), "results": results}


# ===== Sending =====

@mcp.tool
def send_campaign(campaign_id: int) -> dict:
    """Send a campaign. Checks scheduling rules and dispatches to recipients."""
    campaign = campaigns.get(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign not found: {campaign_id}")

    status = campaign.get("status", "")
    if status not in (CampaignStatus.APPROVED.value, CampaignStatus.SCHEDULED.value):
        raise ValueError(f"Campaign must be approved or scheduled before sending. Current status: {status}")

    # If scheduled, verify time
    scheduled_for = campaign.get("scheduled_for")
    if scheduled_for:
        scheduled = datetime.fromisoformat(scheduled_for)
        now = datetime.now()
        if now < scheduled:
            raise ValueError(f"Cannot send campaign before scheduled time. Scheduled for: {scheduled_for}")

    # Find approved template
    campaign_id = int(campaign["id"])
    approved_templates = [
        t for t in templates.values()
        if t.get("campaign_id") == campaign_id and t.get("status") == CampaignStatus.APPROVED.value
    ]
    if not approved_templates:
        raise ValueError("No approved templates for this campaign")
    template = approved_templates[0]

    # Gather all recipients
    all_list_ids = set(campaign.get("recipient_lists", []))
    for lst in approved_templates:
        all_list_ids.update(lst.get("recipient_lists", []))
    all_list_ids.discard(None if False else None)

    unique_emails = []
    seen = set()
    for lst_id in all_list_ids:
        for me in members.values():
            if me.get("list_id") == lst_id:
                addr = me.get("address", "")
                if addr.lower() not in seen:
                    unique_emails.append(addr.lower())
                    seen.add(addr.lower())

    # A/B split logic
    variant_a = next((t for t in templates.values() if t.get("variant_a") and t["campaign_id"] == campaign_id), None)
    variant_b = next((t for t in templates.values() if t.get("variant_b") and t["campaign_id"] == campaign_id), None)

    if variant_a and variant_b and variant_a.get("status") == CampaignStatus.APPROVED.value and variant_b.get("status") == CampaignStatus.APPROVED.value:
        # A/B test: split recipients
        split_a = {"opens": 0, "clicks": 0, "conversions": 0, "recipient_assignments": 0}
        split_b = {"opens": 0, "clicks": 0, "conversions": 0, "recipient_assignments": 0}

        for i, addr in enumerate(unique_emails):
            if i % 2 == 0:
                used = {"email": addr, "variant": "a", "sent_at": _today_iso(), "opened": False, "clicked": False, "converted": False}
                sent_events[addr] = used
                split_a["recipient_assignments"] += 1
            else:
                used = {"email": addr, "variant": "b", "sent_at": _today_iso(), "opened": False, "clicked": False, "converted": False}
                sent_events[addr] = used
                split_b["recipient_assignments"] += 1

            # Update analytics for template
            template_vid = next((t["id"] for t in templates.values() if t.get("campaign_id") == campaign_id and t.get("variant_a") is not None), None)
            if template_vid:
                t = templates[template_vid]
                t["opens"] += 1
                t["clicks"] += int(t["opens"] * 0.05)
                t["conversions"] += int(t["clicks"] * 0.03)
                t["updated_at"] = _today_iso()
                _save()

        # Return split results
        result = {
            "status": "sent",
            "campaign_id": campaign_id,
            "template_id": template["id"],
            "split": {
                "variant_a": {
                    "recipients": split_a["recipient_assignments"],
                    "opens": split_a["opens"],
                    "clicks": split_a["clicks"],
                    "conversions": split_a["conversions"],
                },
                "variant_b": {
                    "recipients": split_b["recipient_assignments"],
                    "opens": split_b["opens"],
                    "clicks": split_b["clicks"],
                    "conversions": split_b["conversions"],
                },
            },
            "total_recipients": len(unique_emails),
        }
        return result

    # Send to all as one batch
    for addr in unique_emails:
        sent_events[addr] = {"email": addr, "variant": None, "sent_at": _today_iso(), "opened": False, "clicked": False, "converted": False}

    # Update analytics for template
    for t in templates.values():
        if t.get("campaign_id") == campaign_id and t.get("status") == CampaignStatus.APPROVED.value:
            recipients = len([e for e in sent_events.values() if e.get("email") == addr])
            t["opens"] += recipients
            t["clicks"] += int(recipients * 0.05)
            t["conversions"] += int(recipients * 0.03)
            t["updated_at"] = _today_iso()
            _save()
            break

    return {
        "status": "sent",
        "campaign_id": campaign_id,
        "template_id": template["id"],
        "recipients": len(unique_emails),
        "analytics": {
            "opens": template["opens"],
            "clicks": template["clicks"],
            "conversions": template["conversions"],
        },
    }