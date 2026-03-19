"""
CRM MCP Server
A FastMCP server for customer relationship management - leads, deals, and interactions.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
from enum import Enum
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="CRM",
    instructions="A CRM server for managing leads, deals, customers, and interactions."
)


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    LOST = "lost"
    CONVERTED = "converted"


class DealStage(str, Enum):
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class Lead(BaseModel):
    """A lead in the CRM."""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class Deal(BaseModel):
    """A deal in the CRM."""
    id: int
    title: str
    customer_id: Optional[int] = None
    value: float
    stage: str
    expected_close_date: Optional[str] = None
    created_at: str
    updated_at: str


class Customer(BaseModel):
    """A customer in the CRM."""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class Interaction(BaseModel):
    """An interaction with a customer."""
    id: int
    customer_id: int
    deal_id: Optional[int] = None
    type: str
    summary: str
    created_at: str

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "crm.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "leads": {}, "deals": {}, "customers": {}, "interactions": {},
        "next_lead_id": 1, "next_deal_id": 1, "next_customer_id": 1, "next_interaction_id": 1
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
leads: dict[int, dict] = {int(k): v for k, v in _data.get("leads", {}).items()}
deals: dict[int, dict] = {int(k): v for k, v in _data.get("deals", {}).items()}
customers: dict[int, dict] = {int(k): v for k, v in _data.get("customers", {}).items()}
interactions: dict[int, dict] = {int(k): v for k, v in _data.get("interactions", {}).items()}

_next_lead_id = _data.get("next_lead_id", 1)
_next_deal_id = _data.get("next_deal_id", 1)
_next_customer_id = _data.get("next_customer_id", 1)
_next_interaction_id = _data.get("next_interaction_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "leads": leads, "deals": deals, "customers": customers, "interactions": interactions,
        "next_lead_id": _next_lead_id, "next_deal_id": _next_deal_id,
        "next_customer_id": _next_customer_id, "next_interaction_id": _next_interaction_id
    })


def _get_next_lead_id() -> int:
    global _next_lead_id
    id_ = _next_lead_id
    _next_lead_id += 1
    return id_


def _get_next_deal_id() -> int:
    global _next_deal_id
    id_ = _next_deal_id
    _next_deal_id += 1
    return id_


def _get_next_customer_id() -> int:
    global _next_customer_id
    id_ = _next_customer_id
    _next_customer_id += 1
    return id_


def _get_next_interaction_id() -> int:
    global _next_interaction_id
    id_ = _next_interaction_id
    _next_interaction_id += 1
    return id_


# Lead Management
@mcp.tool
def create_lead(
    name: str,
    email: str,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    source: Optional[str] = None,
    notes: Optional[str] = None
) -> Lead:
    """Create a new lead.

    Args:
        name: Lead's full name
        email: Lead's email address
        phone: Lead's phone number
        company: Lead's company
        source: Lead source (e.g., website, referral)
        notes: Additional notes

    Returns:
        The created lead
    """
    lead_id = _get_next_lead_id()
    lead = Lead(
        id=lead_id,
        name=name,
        email=email,
        phone=phone,
        company=company,
        source=source,
        status=LeadStatus.NEW.value,
        notes=notes,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    leads[lead_id] = lead.model_dump()
    _save()
    return lead


@mcp.tool
def update_lead_status(lead_id: int, status: str) -> Optional[Lead]:
    """Update a lead's status.

    Args:
        lead_id: The lead ID
        status: New status (new, contacted, qualified, lost, converted)

    Returns:
        Updated lead or None if not found
    """
    if lead_id not in leads:
        return None

    valid_statuses = [s.value for s in LeadStatus]
    if status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

    leads[lead_id]["status"] = status
    leads[lead_id]["updated_at"] = datetime.now().isoformat()
    _save()
    return Lead(**leads[lead_id])


@mcp.tool
def convert_lead_to_customer(lead_id: int) -> Optional[Customer]:
    """Convert a qualified lead to a customer.

    Args:
        lead_id: The lead ID to convert

    Returns:
        The new customer record
    """
    if lead_id not in leads:
        return None

    lead = leads[lead_id]
    customer = create_customer(
        name=lead["name"],
        email=lead["email"],
        phone=lead.get("phone"),
        company=lead.get("company")
    )
    leads[lead_id]["status"] = LeadStatus.CONVERTED.value
    leads[lead_id]["updated_at"] = datetime.now().isoformat()
    _save()
    return customer


# Deal Management
@mcp.tool
def create_deal(
    title: str,
    customer_id: Optional[int] = None,
    value: float = 0.0,
    stage: str = "prospecting",
    expected_close_date: Optional[str] = None
) -> Deal:
    """Create a new deal.

    Args:
        title: Deal title/name
        customer_id: Associated customer ID
        value: Deal value in dollars
        stage: Current stage (prospecting, qualification, proposal, negotiation, closed_won, closed_lost)
        expected_close_date: Expected close date (YYYY-MM-DD)

    Returns:
        The created deal
    """
    valid_stages = [s.value for s in DealStage]
    if stage not in valid_stages:
        raise ValueError(f"Invalid stage. Must be one of: {valid_stages}")

    deal_id = _get_next_deal_id()
    deal = Deal(
        id=deal_id,
        title=title,
        customer_id=customer_id,
        value=value,
        stage=stage,
        expected_close_date=expected_close_date,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    deals[deal_id] = deal.model_dump()
    _save()
    return deal


@mcp.tool
def update_deal_stage(deal_id: int, stage: str) -> Optional[Deal]:
    """Update a deal's stage.

    Args:
        deal_id: The deal ID
        stage: New stage

    Returns:
        Updated deal or None if not found
    """
    if deal_id not in deals:
        return None

    valid_stages = [s.value for s in DealStage]
    if stage not in valid_stages:
        raise ValueError(f"Invalid stage. Must be one of: {valid_stages}")

    deals[deal_id]["stage"] = stage
    deals[deal_id]["updated_at"] = datetime.now().isoformat()
    _save()
    return Deal(**deals[deal_id])


@mcp.tool
def get_pipeline_summary() -> dict:
    """Get a summary of the sales pipeline.

    Returns:
        Summary with counts and values by stage
    """
    summary = {stage.value: {"count": 0, "total_value": 0.0} for stage in DealStage}

    for deal in deals.values():
        stage = deal["stage"]
        summary[stage]["count"] += 1
        summary[stage]["total_value"] += deal.get("value", 0)

    return summary


# Customer Management
@mcp.tool
def create_customer(
    name: str,
    email: str,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    notes: Optional[str] = None
) -> Customer:
    """Create a new customer.

    Args:
        name: Customer's full name
        email: Customer's email
        phone: Customer's phone
        company: Customer's company
        notes: Additional notes

    Returns:
        The created customer
    """
    customer_id = _get_next_customer_id()
    customer = Customer(
        id=customer_id,
        name=name,
        email=email,
        phone=phone,
        company=company,
        notes=notes,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    customers[customer_id] = customer.model_dump()
    _save()
    return customer


@mcp.tool
def get_customer(customer_id: int) -> Optional[Customer]:
    """Get a customer by ID.

    Args:
        customer_id: The customer ID

    Returns:
        Customer details or None
    """
    data = customers.get(customer_id)
    if data is None:
        return None
    return Customer(**data)


# Interaction Management
@mcp.tool
def log_interaction(
    customer_id: int,
    interaction_type: str,
    summary: str,
    deal_id: Optional[int] = None
) -> Interaction:
    """Log an interaction with a customer.

    Args:
        customer_id: The customer ID
        interaction_type: Type (call, email, meeting, note)
        summary: Summary of the interaction
        deal_id: Related deal ID

    Returns:
        The logged interaction
    """
    interaction_id = _get_next_interaction_id()
    interaction = Interaction(
        id=interaction_id,
        customer_id=customer_id,
        deal_id=deal_id,
        type=interaction_type,
        summary=summary,
        created_at=datetime.now().isoformat()
    )
    interactions[interaction_id] = interaction.model_dump()
    _save()
    return interaction


@mcp.tool
def get_customer_interactions(customer_id: int) -> list[Interaction]:
    """Get all interactions for a customer.

    Args:
        customer_id: The customer ID

    Returns:
        List of interactions
    """
    return [
        Interaction(**i) for i in interactions.values()
        if i["customer_id"] == customer_id
    ]


# Resources
@mcp.resource("crm://pipeline")
def get_pipeline_resource() -> str:
    """Resource showing the current sales pipeline."""
    summary = get_pipeline_summary()
    lines = ["# Sales Pipeline\n"]

    for stage, data in summary.items():
        lines.append(f"## {stage.replace('_', ' ').title()}")
        lines.append(f"- Count: {data['count']}")
        lines.append(f"- Total Value: ${data['total_value']:,.2f}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("crm://leads")
def get_leads_resource() -> str:
    """Resource showing all leads."""
    if not leads:
        return "No leads found."

    lines = ["# Leads\n"]
    for lead in sorted(leads.values(), key=lambda l: l.get("created_at", ""), reverse=True):
        lines.append(f"## {lead['name']} (ID: {lead['id']})")
        lines.append(f"- Email: {lead['email']}")
        lines.append(f"- Status: {lead['status']}")
        if lead.get('company'):
            lines.append(f"- Company: {lead['company']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()