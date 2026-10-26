"""
Business Analytics MCP Server
A FastMCP server that aggregates cross-server business KPIs from the JSON data
files used by the other business MCP servers (invoices, expenses, time,
support, CRM).

Read-only aggregation layer: it does not own a data file of its own, it
computes reports from sibling server data via MCP_DATA_ROOTS.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import os
from fastmcp import FastMCP

mcp = FastMCP(
    name="Business Analytics",
    instructions=(
        "A cross-server analytics hub. Reads the JSON data stores of the other "
        "business MCP servers (invoices, expenses, time, support, ...) and "
        "computes business KPIs such as revenue, expenses, profitability, time "
        "utilization and support health."
    ),
)


def _data_roots() -> list[Path]:
    """Roots to scan for sibling server data files (MCP_DATA_ROOTS overrides)."""
    env = os.environ.get("MCP_DATA_ROOTS")
    if env:
        return [Path(p).expanduser() for p in env.split(os.pathsep) if p.strip()]
    return [Path(__file__).resolve().parent.parent]


SOURCE_FILES: dict[str, tuple[str, str]] = {
    "invoice-manager": ("invoices.json", "invoices"),
    "expense-tracker": ("expenses.json", "expenses"),
    "time-tracker": ("time.json", "time_entries"),
    "crm": ("crm.json", "deals"),
    "support-desk": ("support.json", "tickets"),
}


def _read_json(source: str, filename: str) -> dict:
    """Read a sibling server's data file, returning an empty dict if absent."""
    for root in _data_roots():
        candidate = root / "mcp-servers" / source / "data" / filename
        if candidate.exists():
            with open(candidate, "r", encoding="utf-8") as handle:
                return json.load(handle)
    return {}


def _int_map(source: str, filename: str, collection: str) -> dict[int, dict]:
    """Load a JSON collection of records keyed by string id -> record."""
    document = _read_json(source, filename)
    records = document.get(collection) or {}
    return {int(k): v for k, v in records.items() if isinstance(v, dict)}


def _money(value) -> float:
    return round(float(value or 0) + 0.0, 2)


def _parse_date(value) -> Optional[datetime.date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def _in_range(date_value, start: Optional[str], end: Optional[str]) -> bool:
    day = _parse_date(date_value)
    if day is None:
        return True
    if start is not None and day < _parse_date(start):
        return False
    if end is not None and day > _parse_date(end):
        return False
    return True


# --- tools -------------------------------------------------------------------
@mcp.tool
def list_data_sources() -> list[dict]:
    """List the sibling MCP server data files this analytics hub can read."""
    sources = []
    for source, (filename, collection) in SOURCE_FILES.items():
        records = _int_map(source, filename, collection)
        sources.append({"source": source, "file": filename, "records": len(records)})
    return sources


@mcp.tool
def get_financial_overview(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """Aggregate revenue vs expenses vs net profit across business servers.

    Args:
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    """
    invoices = _int_map("invoice-manager", "invoices.json", "invoices")
    payments = _int_map("invoice-manager", "invoices.json", "payments")
    invoiced = collected = outstanding = 0.0
    invoice_count = 0
    for entry in invoices.values():
        if entry.get("status") == "void":
            continue
        if not _in_range(entry.get("issue_date"), start_date, end_date):
            continue
        invoice_id = int(entry.get("id") or -1)
        paid = sum(
            float(p.get("amount") or 0) for p in payments.values()
            if int(p.get("invoice_id") or -1) == invoice_id
        )
        total = float(entry.get("total") or 0)
        invoiced += total
        collected += paid
        outstanding += max(total - paid, 0.0)
        invoice_count += 1
    expenses = _int_map("expense-tracker", "expenses.json", "expenses")
    expense_total = 0.0
    by_category: dict[str, float] = {}
    expense_count = 0
    for entry in expenses.values():
        if not _in_range(entry.get("date"), start_date, end_date):
            continue
        amount = float(entry.get("amount") or 0)
        expense_total += amount
        expense_count += 1
        category = str(entry.get("category") or "uncategorized")
        by_category[category] = by_category.get(category, 0) + amount
    return {
        "start_date": start_date,
        "end_date": end_date,
        "revenue": {
            "invoiced": _money(invoiced),
            "collected": _money(collected),
            "outstanding": _money(outstanding),
            "invoice_count": invoice_count,
        },
        "expenses": {
            "total": _money(expense_total),
            "by_category": {k: _money(v) for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])},
            "expense_count": expense_count,
        },
        "net_profit": _money(collected - expense_total),
    }


@mcp.tool
def get_revenue_report(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """Monthly revenue vs expense vs net trend over a date range.

    Args:
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    """
    invoices = _int_map("invoice-manager", "invoices.json", "invoices")
    payments = _int_map("invoice-manager", "invoices.json", "payments")
    months: dict[str, dict] = {}

    def bucket(month_key: str) -> dict:
        return months.setdefault(month_key, {"month": month_key, "invoiced": 0.0, "collected": 0.0, "expenses": 0.0})

    for entry in invoices.values():
        if entry.get("status") == "void":
            continue
        if not _in_range(entry.get("issue_date"), start_date, end_date):
            continue
        day = _parse_date(entry.get("issue_date"))
        key = f"{day.year:04d}-{day.month:02d}"
        item = bucket(key)
        item["invoiced"] += float(entry.get("total") or 0)
        invoice_id = int(entry.get("id") or -1)
        item["collected"] += sum(
            float(p.get("amount") or 0) for p in payments.values()
            if int(p.get("invoice_id") or -1) == invoice_id
        )
    expenses = _int_map("expense-tracker", "expenses.json", "expenses")
    for entry in expenses.values():
        if not _in_range(entry.get("date"), start_date, end_date):
            continue
        day = _parse_date(entry.get("date"))
        item = bucket(f"{day.year:04d}-{day.month:02d}")
        item["expenses"] += float(entry.get("amount") or 0)
    month_list = []
    for key in sorted(months):
        item = months[key]
        month_list.append({
            "month": key,
            "invoiced": _money(item["invoiced"]),
            "collected": _money(item["collected"]),
            "expenses": _money(item["expenses"]),
            "net": _money(item["collected"] - item["expenses"]),
        })
    return {"start_date": start_date, "end_date": end_date, "months": month_list}


@mcp.tool
def get_expense_breakdown(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """Summarize expenses by category over a date range.

    Args:
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    """
    expenses = _int_map("expense-tracker", "expenses.json", "expenses")
    categories: dict[str, dict] = {}
    for entry in expenses.values():
        if not _in_range(entry.get("date"), start_date, end_date):
            continue
        amount = float(entry.get("amount") or 0)
        category = str(entry.get("category") or "uncategorized")
        bucket_item = categories.setdefault(category, {"total": 0.0, "count": 0})
        bucket_item["total"] += amount
        bucket_item["count"] += 1
    category_list = [
        {"category": category, "total": _money(values["total"]), "count": values["count"]}
        for category, values in sorted(categories.items(), key=lambda kv: -kv[1]["total"])
    ]
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total": _money(sum(c["total"] for c in category_list)),
        "categories": category_list,
        "expense_count": sum(c["count"] for c in category_list),
    }


@mcp.tool
def get_time_summary(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """Summarize logged time: total, billable, billable revenue and utilization.

    Args:
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    """
    entries = _int_map("time-tracker", "time.json", "time_entries")
    projects = _int_map("time-tracker", "time.json", "projects")
    total_minutes = billable_minutes = billable_revenue = 0.0
    for entry in entries.values():
        if not _in_range(entry.get("date"), start_date, end_date):
            continue
        minutes = float(entry.get("duration_minutes") or 0)
        total_minutes += minutes
        if not entry.get("billable"):
            continue
        billable_minutes += minutes
        rate = 0.0
        project_id = entry.get("project_id")
        if project_id is not None and int(project_id) in projects:
            rate = float(projects[int(project_id)].get("billable_rate") or 0)
        billable_revenue += (minutes / 60.0) * rate
    utilization = (billable_minutes / total_minutes) if total_minutes > 0 else 0.0
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_minutes": _money(total_minutes),
        "billable_minutes": _money(billable_minutes),
        "billable_revenue": _money(billable_revenue),
        "utilization": round(utilization, 2),
    }


@mcp.tool
def get_support_stats() -> dict:
    """Support desk health: ticket status mix, resolution times, SLA and CSAT."""
    tickets = _int_map("support-desk", "support.json", "tickets")
    comments = _int_map("support-desk", "support.json", "comments")
    csat = _int_map("support-desk", "support.json", "csat")
    by_status: dict[str, int] = {}
    open_statuses = {"open", "in_progress", "waiting"}
    resolved_hours: list[float] = []
    sla_ok = sla_total = 0
    resolved_count = 0
    for ticket in tickets.values():
        status = str(ticket.get("status") or "open")
        by_status[status] = by_status.get(status, 0) + 1
        if status == "resolved":
            resolved_count += 1
            resolved_at = _parse_date(ticket.get("resolved_at"))
            created_at = _parse_date(ticket.get("created_at"))
            if resolved_at and created_at:
                resolved_hours.append((resolved_at - created_at).total_seconds() / 3600.0)
        if ticket.get("resolved_at") and ticket.get("sla_due_at"):
            sla_total += 1
            if _parse_date(ticket["resolved_at"]) <= _parse_date(ticket["sla_due_at"]):
                sla_ok += 1
    ratings: list[float] = []
    for response in csat.values():
        rating = float(response.get("rating") or 0)
        if rating > 0:
            ratings.append(rating)
    return {
        "tickets_by_status": by_status,
        "open_tickets": sum(1 for t in tickets.values() if str(t.get("status") or "open") in open_statuses),
        "resolved_count": resolved_count,
        "comment_count": len(comments),
        "avg_resolution_hours": round(sum(resolved_hours) / len(resolved_hours), 2) if resolved_hours else None,
        "sla_compliance_rate": round(sla_ok / sla_total, 2) if sla_total else None,
        "csat_average": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }


@mcp.tool
def get_pipeline_summary() -> dict:
    """CRM pipeline snapshot: open value, won and lost totals by stage."""
    deals = _int_map("crm", "crm.json", "deals")
    by_stage: dict[str, dict] = {}
    for deal in deals.values():
        stage = str(deal.get("stage") or "unknown")
        bucket_item = by_stage.setdefault(stage, {"count": 0, "value": 0.0})
        bucket_item["count"] += 1
        bucket_item["value"] += float(deal.get("value") or 0)
    closed_won = sum(v["value"] for st, v in by_stage.items() if st == "closed_won")
    closed_lost = sum(v["value"] for st, v in by_stage.items() if st == "closed_lost")
    open_value = sum(v["value"] for st, v in by_stage.items() if st not in {"closed_won", "closed_lost"})
    return {
        "by_stage": {st: {"count": v["count"], "value": _money(v["value"])} for st, v in sorted(by_stage.items())},
        "open_pipeline_value": _money(open_value),
        "closed_won_value": _money(closed_won),
        "closed_lost_value": _money(closed_lost),
    }


# --- resources ---------------------------------------------------------------
@mcp.resource("analytics://sources")
def sources_resource() -> str:
    """Indexed data sources as formatted text."""
    sources = list_data_sources()
    lines = ["# Business Analytics Data Sources\n"]
    for item in sources:
        lines.append(f"- **{item['source']}** - {item['records']} records ({item['file']})")
    if not sources:
        lines.append("No data sources found yet.")
    return "\n".join(lines)


@mcp.resource("analytics://financial-overview")
def financial_overview_resource() -> str:
    """Financial overview as formatted text."""
    overview = get_financial_overview()
    lines = ["# Financial Overview\n"]
    lines.append(f"- **Invoiced:** {overview['revenue']['invoiced']:,.2f}")
    lines.append(f"- **Collected:** {overview['revenue']['collected']:,.2f}")
    lines.append(f"- **Outstanding:** {overview['revenue']['outstanding']:,.2f}")
    lines.append(f"- **Expenses:** {overview['expenses']['total']:,.2f}")
    lines.append(f"- **Net profit:** {overview['net_profit']:,.2f}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
