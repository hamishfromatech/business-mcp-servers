"""
Business Intelligence Dashboard MCP Server

A FastMCP server that provides a comprehensive BI dashboard with:
- Cross-server KPI aggregation from business MCP servers
- Dashboard visualizations via built-in web UI (Chart.js)
- Real-time analytics with live data refresh
- Report generation (PDF, CSV, Excel)

Run as stdio MCP server:
    python server.py

Run with web UI:
    python server.py --transport http --port 8000

The web UI will be available at:
    http://127.0.0.1:8080/dashboard
"""

import argparse
import io
import json
import os
import re
import threading
from base64 import b64encode
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Optional

import fpdf
import pandas as pd
from fastmcp import FastMCP

# ---- MCP server ----
mcp = FastMCP(
    name="BI Dashboard",
    instructions=(
        "A Business Intelligence Dashboard that aggregates cross-server KPIs "
        "from all business MCP servers (invoices, expenses, time, support, "
        "CRM, budgets, vendors). Provides real-time analytics, dashboard "
        "visualizations, and report generation."
    ),
)


# ---- data roots ----
def _data_roots() -> list[Path]:
    """Roots to scan for sibling server data files (MCP_DATA_ROOTS overrides)."""
    env = os.environ.get("MCP_DATA_ROOTS")
    if env:
        return [Path(p).expanduser() for p in env.split(os.pathsep) if p.strip()]
    return [Path(__file__).resolve().parent.parent]


def _read_json(source: str, filename: str) -> dict:
    """Read a sibling server's JSON data file, returning {} if absent."""
    for root in _data_roots():
        candidate = root / "mcp-servers" / source / "data" / filename
        if candidate.exists():
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def _int_map(source: str, filename: str, collection: str) -> dict[int, dict]:
    """Load a JSON collection keyed by integer id."""
    document = _read_json(source, filename)
    records = document.get(collection) or {}
    return {int(k): v for k, v in records.items() if isinstance(v, dict)}


# ---- utility functions ----
def _money(value) -> float:
    return round(float(value or 0) + 0.0, 2)


def _parse_date(value: Any) -> Optional[datetime.date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def _in_range(date_value: Any, start: Optional[str], end: Optional[str]) -> bool:
    day = _parse_date(date_value)
    if day is None:
        return True
    if start is not None and day < _parse_date(start):
        return False
    if end is not None and day > _parse_date(end):
        return False
    return True


def _deps_or_fetch():
    """Eagerly import report libraries on first use (lazy loading)."""
    try:
        import fpdf
        import pandas as pd
    except ImportError:
        pass  # Ignore; let the call to those libs raise


# ---- snapshot cache (thread-safe) ----
_lock = threading.RLock()
_snapshots: dict[str, dict[str, Any]] = {}
_cache_ttl = datetime.now().timestamp() + 3600  # 1 hour TTL


def _ensure_fresh(name: str) -> dict[str, Any]:
    """Return snapshot if fresh, else regenerate and store."""
    now = datetime.now().timestamp()
    if name in _snapshots:
        age = now - _snapshots[name].get("_ts", now)
        if age <= 3500:  # 3500ms freshness for no reason, we'll recompute
            return _snapshots[name]
    return None


def _refresh_all() -> dict[str, dict[str, Any]]:
    """Regenerate all snapshots and return a full dict keyed by name."""
    with _lock:
        now = datetime.now().timestamp()
        _snapshots = {
            name: {
                "kpis": compute_kpis(not None),
                "_ts": now,
            }
            for name, _ in _refresh_all.keys()
        }
        return _snapshots


def _compute_date_range(start_date: Optional[str], end_date: Optional[str]):
    """Build date range for monthly aggregation."""
    def get_month_key(d: Optional[datetime.date]) -> str:
        if d is None:
            return ""
        return f"{d.year:04d}-{d.month:02d}"

    def in_range(d: Optional[datetime.date]) -> bool:
        if d is None:
            return True
        if start_date and d < _parse_date(start_date):
            return False
        if end_date and d > _parse_date(end_date):
            return False
        return True

    return get_month_key, in_range


# ---- KPI computation ----
def compute_kpis(refresh: bool = False) -> dict[str, Any]:
    """Compute all aggregated KPIs. If refresh=True, recomputes all else."""
    def get_month_key(d):
        if d is None:
            return ""
        return f"{d.year:04d}-{d.month:02d}"

    def in_range(d):
        if d is None:
            return True
        if start_date and d < _parse_date(start_date):
            return False
        if end_date and d > _parse_date(end_date):
            return False
        return True

    # ==================== REVENUE ====================
    invoices = _int_map("invoice-manager", "invoices.json", "invoices")
    payments = _int_map("invoice-manager", "invoices.json", "payments")

    total_invoiced = total_collected = total_outstanding = 0.0
    invoice_count = 0
    revenue_by_month: dict[str, dict] = {}

    def bucket_m(payment_date=None):
        return get_month_key(_parse_date(payment_date or datetime.now()))

    month_data: dict[str, dict] = {}

    def month_bucket(d):
        if d is None:
            return datetime.now().month
        return get_month_key(d)

    # Monthly revenue
    def month_invoiced(d):
        return get_month_key(_parse_date(d))

    for inv in invoices.values():
        if inv.get("status") == "void":
            continue
        if not in_range(inv.get("issue_date")):
            continue
        month = month_invoiced(inv.get("issue_date"))
        monthly_data[month]["invoiced"] += float(inv.get("total") or 0)
        invoice_count += 1

    for payment in payments.values():
        month = month_bucket(payment.get("created_at"))
        monthly_data[month]["collected"] += float(payment.get("amount") or 0)

    # Expenses
    expenses = _int_map("expense-tracker", "expenses.json", "expenses")
    expense_total = 0.0
    expense_by_category: dict[str, float] = {}
    expense_count = 0
    for exp in expenses.values():
        if not in_range(exp.get("date")):
            continue
        amount = float(exp.get("amount") or 0)
        expense_total += amount
        expense_count += 1
        category = str(exp.get("category") or "uncategorized")
        expense_by_category[category] = expense_by_category.get(category, 0) + amount

    # Time
    entries = _int_map("time-tracker", "time.json", "time_entries")
    projects = _int_map("time-tracker", "time.json", "projects")
    total_minutes = billable_minutes = billable_revenue = 0.0
    time_by_project: dict[str, float] = {}
    for entry in entries.values():
        if not in_range(entry.get("date")):
            continue
        minutes = float(entry.get("duration_minutes") or 0)
        total_minutes += minutes
        if entry.get("billable"):
            billable_minutes += minutes
            project_id = entry.get("project_id")
            if project_id is not None and int(project_id) in projects:
                rate = float(projects[int(project_id)].get("billable_rate") or 0)
                billable_revenue += (minutes / 60.0) * rate
                time_by_project[str(project_id)] = time_by_project.get(str(project_id), 0) + minutes

    # Support
    tickets = _int_map("support-desk", "support.json", "tickets")
    comments = _int_map("support-desk", "support.json", "comments")
    csat = _int_map("support-desk", "support.json", "csat")
    by_status: dict[str, int] = {}
    open_statuses = {"open", "in_progress", "waiting"}
    resolved_hours = []
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
    csat_ratings = [r for r in csat.values() if (r.get("rating") or 0) > 0]
    csat_avg = sum(r.get("rating") or 0 for r in csat_ratings) / len(csat_ratings) if csat_ratings else None

    # Pipeline
    deals = _int_map("crm", "crm.json", "deals")
    by_stage: dict[str, dict] = {}
    for deal in deals.values():
        stage = str(deal.get("stage") or "unknown")
        by_stage[stage] = by_stage.get(stage, {"count": 0, "value": 0.0})
        by_stage[stage]["count"] += 1
        by_stage[stage]["value"] += float(deal.get("value") or 0)
    closed_won = by_stage.get("closed_won", {"value": 0.0})["value"]
    closed_lost = by_stage.get("closed_lost", {"value": 0.0})["value"]
    open_value = sum(
        v["value"] for st, v in by_stage.items() if st not in ("closed_won", "closed_lost")
    )
    win_rate = (
        closed_won / (closed_won + closed_lost) * 100
        if (closed_won + closed_lost) > 0
        else 0.0
    )

    # Budget
    budgets = _int_map("project-budget-tracker", "budgets.json", "budgets")
    budget_spent = budget_allocated = 0.0
    for b in budgets.values():
        budget_allocated += float(b.get("allocated") or 0)
        budget_spent += float(b.get("spent") or 0)

    # Vendor
    pos = _int_map("vendor-manager", "po_items.json", "po_items")
    vendor_spend: dict[str, float] = {}
    vendor_lead_time: dict[str, float] = {}
    for item in pos.values():
        vendor = str(item.get("vendor") or "unknown")
        amount = float(item.get("amount") or 0)
        vendor_spend[vendor] = vendor_spend.get(vendor, 0) + amount
        lead_time = float(item.get("lead_time_days") or 0)
        vendor_lead_time[vendor] = vendor_lead_time.get(vendor, 0) + lead_time

    # Compute overall totals
    expense_total = sum(expense_by_category.values())
    net_profit = total_collected - expense_total

    utilization = (billable_minutes / total_minutes) if total_minutes > 0 else 0.0

    return {
        "revenue": {
            "total_invoiced": _money(total_invoiced),
            "total_collected": _money(total_collected),
            "outstanding": _money(total_outstanding),
            "invoice_count": invoice_count,
        },
        "expenses": {
            "total": _money(expense_total),
            "by_category": {k: _money(v) for k, v in sorted(expense_by_category.items(), key=lambda kv: -kv[1])},
            "expense_count": expense_count,
        },
        "profit": {
            "net_profit": _money(net_profit),
            "margin_pct": _money(net_profit / total_invoiced * 100) if total_invoiced > 0 else 0.0,
            "efficiency_pct": _money(total_collected / total_invoiced * 100) if total_invoiced > 0 else 0.0,
        },
        "time": {
            "total_minutes": _money(total_minutes),
            "billable_minutes": _money(billable_minutes),
            "utilization_pct": round(utilization, 2),
            "billable_revenue": _money(billable_revenue),
            "by_project": {k: _money(v) for k, v in sorted(time_by_project.items(), key=lambda kv: -kv[1])},
        },
        "support": {
            "tickets_by_status": by_status,
            "open_tickets": sum(1 for t in tickets.values() if str(t.get("status") or "open") in open_statuses),
            "resolved_count": resolved_count,
            "comment_count": len(comments),
            "avg_resolution_hours": round(
                sum(resolved_hours) / len(resolved_hours), 2
            )
            if resolved_hours
            else None,
            "sla_compliance_rate": round(sla_ok / sla_total, 2) if sla_total else None,
            "csat_average": csat_avg,
        },
        "pipeline": {
            "by_stage": {st: {"count": v["count"], "value": _money(v["value"])} for st, v in sorted(by_stage.items())},
            "open_value": _money(open_value),
            "closed_won_value": _money(closed_won),
            "closed_lost_value": _money(closed_lost),
            "win_rate_pct": round(win_rate, 2),
        },
        "budget": {
            "budget_allocated": _money(budget_allocated),
            "budget_spent": _money(budget_spent),
        },
        "vendor": {
            "by_vendor": {k: _money(v) for k, v in sorted(vendor_spend.items(), key=lambda kv: -kv[1])},
            "avg_lead_time_days": round(sum(vendor_lead_time.values()) / len(vendor_lead_time), 1) if vendor_lead_time else None,
        },
        "metadata": {"generated_at": datetime.now().isoformat()},
    }


# ---- Tools ----
@mcp.tool
def refresh_dashboard_data():
    """Refresh all cached KPI snapshots. Use before get_kpi_snapshot() for fresh data."""
    with _lock:
        _snapshots["full"] = {
            "kpis": compute_kpis(),
            "sources": [],
            "metadata": {"generated_at": datetime.now().isoformat()},
        }
    return {"status": "ok", "message": "All snapshots refreshed"}


@mcp.tool
def get_kpi_snapshot() -> dict[str, Any]:
    """Get the current cached KPI snapshot. Call refresh_dashboard_data() first for fresh data."""
    snapshot = None
    with _lock:
        if "full" in _snapshots and _snapshots["full"].get("_ts", 0) > (datetime.now().timestamp() - 3600):
            snapshot = _snapshots["full"]
    if snapshot is None:
        raise ValueError("Call refresh_dashboard_data() first to refresh data.")
    del snapshot["_ts"]
    return snapshot["kpis"]


@mcp.tool
def get_revenue_kpis(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """Revenue KPIs: invoiced, collected, outstanding, monthly trend."""
    kpis = compute_kpis()
    monthly_data: dict[str, dict] = {}

    def month_key(d):
        if d is None:
            return ""
        return f"{d.year:04d}-{d.month:02d}"

    invs = _int_map("invoice-manager", "invoices.json", "invoices")
    paym = _int_map("invoice-manager", "invoices.json", "payments")

    for inv in invs.values():
        if inv.get("status") == "void":
            continue
        if not _in_range(inv.get("issue_date"), start_date, end_date):
            continue
        month = month_key(inv.get("issue_date"))
        if month not in monthly_data:
            monthly_data[month] = {"month": month, "invoiced": 0.0, "collected": 0.0}
        monthly_data[month]["invoiced"] += float(inv.get("total") or 0)

    for p in paym.values():
        m = month_key(datetime.fromisoformat(p.get("created_at") or ""))
        if m not in monthly_data:
            monthly_data[m] = {"month": m, "invoiced": 0.0, "collected": 0.0}
        monthly_data[m]["collected"] += float(p.get("amount") or 0)

    # Net by month
    for m in monthly_data:
        monthly_data[m]["net"] = monthly_data[m]["collected"] - monthly_data[m]["invoiced"]

    sorted_months = sorted(monthly_data.keys())
    monthly_trend = [
        {"month": monthly_data[m]["month"], "invoiced": _money(monthly_data[m]["invoiced"]), "collected": _money(monthly_data[m]["collected"]), "net": _money(monthly_data[m]["net"])}
        for m in sorted_months
    ]

    return {
        "total_invoiced": _money(kpis["revenue"]["total_invoiced"]),
        "total_collected": _money(kpis["revenue"]["total_collected"]),
        "outstanding": _money(kpis["revenue"]["outstanding"]),
        "invoice_count": kpis["revenue"]["invoice_count"],
        "monthly_trend": monthly_trend,
    }


@mcp.tool
def get_expense_kpis(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """Expense KPIs: total, by category, top categories."""
    kpis = compute_kpis()
    expenses = _int_map("expense-tracker", "expenses.json", "expenses")

    by_category: dict[str, dict] = {}
    for e in expenses.values():
        if not _in_range(e.get("date"), start_date, end_date):
            continue
        cat = str(e.get("category") or "uncategorized")
        if cat not in by_category:
            by_category[cat] = {"total": 0.0, "count": 0}
        by_category[cat]["total"] += float(e.get("amount") or 0)
        by_category[cat]["count"] += 1

    category_list = [
        {"category": cat, "total": _money(v), "count": v["count"]}
        for cat, v in sorted(by_category.items(), key=lambda kv: -kv[1]["total"])
    ]

    return {
        "total": _money(kpis["expenses"]["total"]),
        "expense_count": kpis["expenses"]["expense_count"],
        "by_category": category_list,
    }


@mcp.tool
def get_profit_kpis() -> dict:
    """Profit KPIs: net profit, margin, efficiency."""
    kpis = compute_kpis()
    return {
        "net_profit": _money(kpis["profit"]["net_profit"]),
        "margin_pct": kpis["profit"]["margin_pct"],
        "efficiency_pct": kpis["profit"]["efficiency_pct"],
        "revenue": _money(kpis["revenue"]["total_invoiced"]),
        "collected": _money(kpis["revenue"]["total_collected"]),
    }


@mcp.tool
def get_utilization_kpis(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """Time utilization KPIs: total, billable %, billable revenue, by project."""
    kpis = compute_kpis()
    return {
        "total_minutes": _money(kpis["time"]["total_minutes"]),
        "billable_minutes": _money(kpis["time"]["billable_minutes"]),
        "utilization_pct": kpis["time"]["utilization_pct"],
        "billable_revenue": _money(kpis["time"]["billable_revenue"]),
        "by_project": [{"project": k, "minutes": _money(v)} for k, v in sorted(kpis["time"]["by_project"].items(), key=lambda kv: -kv[1])],
    }


@mcp.tool
def get_support_kpis() -> dict:
    """Support health: ticket status, resolution time, SLA, CSAT."""
    kpis = compute_kpis()
    return {
        "tickets_by_status": kpis["support"]["tickets_by_status"],
        "open_tickets": kpis["support"]["open_tickets"],
        "resolved_count": kpis["support"]["resolved_count"],
        "comment_count": kpis["support"]["comment_count"],
        "avg_resolution_hours": kpis["support"]["avg_resolution_hours"],
        "sla_compliance_rate": kpis["support"]["sla_compliance_rate"],
        "csat_average": kpis["support"]["csat_average"],
    }


@mcp.tool
def get_pipeline_kpis() -> dict:
    """Pipeline KPIs: value by stage, open value, win/loss rates."""
    kpis = compute_kpis()
    returned = {
        "by_stage": kpis["pipeline"]["by_stage"],
        "open_pipeline_value": _money(kpis["pipeline"]["open_value"]),
        "closed_won_value": _money(kpis["pipeline"]["closed_won_value"]),
        "closed_lost_value": _money(kpis["pipeline"]["closed_lost_value"]),
        "win_rate_pct": kpis["pipeline"]["win_rate_pct"],
    }
    return returned


@mcp.tool
def get_budget_kpis() -> dict:
    """Budget KPIs: allocated vs spent."""
    kpis = compute_kpis()
    return {
        "budget_allocated": _money(kpis["budget"]["budget_allocated"]),
        "budget_spent": _money(kpis["budget"]["budget_spent"]),
        "budget_remaining_pct": _money((1 - kpis["budget"]["budget_spent"] / max(kpis["budget"]["budget_allocated"], 1)) * 100),
    }


@mcp.tool
def get_vendor_kpis() -> dict:
    """Vendor KPIs: spend by vendor, lead time."""
    kpis = compute_kpis()
    return {
        "by_vendor": kpis["vendor"]["by_vendor"],
        "avg_lead_time_days": kpis["vendor"]["avg_lead_time_days"],
    }


@mcp.tool
def generate_report(
    preset: str = "executive_summary",
    format: str = "pdf",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    """
    Generate a report in PDF, CSV, or Excel format.

    Presets:
    - executive_summary - KPI cards + monthly trends
    - financial - revenue, expenses, profit
    - operational - time, support, pipeline
    - comprehensive - all sections

    Args:
        preset: Report preset
        format: pdf | csv | excel
        start_date/end_date: Optional date range
        title: Custom report title
    """
    _deps_or_fetch()
    from datetime import date

    kpis = compute_kpis()
    data = {}

    # Build report data
    if preset == "executive_summary":
        monthly = get_revenue_kpis(start_date, end_date)
        exec_data = {
            "title": title or "Executive Summary",
            "generated_at": datetime.now().isoformat(),
            "kpi_cards": [
                {"name": "Total Revenue", "value": f"${_money(kpis['revenue']['total_invoiced']):,}", "collected": _money(kpis['revenue']['total_collected'])},
                {"name": "Expenses", "value": f"${_money(kpis['expenses']['total']):,}", "trend": "down" if _money(kpis['expenses']['total']) > 1000 else "neutral"},
                {"name": "Net Profit", "value": f"${_money(kpis['profit']['net_profit']):,}", "margin": kpis['profit']['margin_pct']},
                {"name": "Time Utilization", "value": f"{kpis['time']['utilization_pct']}%", "billable_revenue": _money(kpis['time']['billable_revenue'])},
                {"name": "Open Support", "value": str(kpis['support']['open_tickets']), "resolved": kpis['support']['resolved_count']},
                {"name": "Pipeline Value", "value": f"${_money(kpis['pipeline']['open_value']):,}", "win_rate": kpis['pipeline']['win_rate_pct']},
            ],
            "monthly_trend": monthly.get("monthly_trend", []),
        }
        if format == "csv":
            report_df = pd.DataFrame([exec_data])
            report_df.to_csv(io.StringIO(""), index=False)
            output = io.StringIO()
            exec_data["kpi_cards"] = [
                {"Metric": c["name"], "Value": c["value"], "Collected": c.get("collected", 0), "(trend)": c.get("margin", "")}
                for c in exec_data["kpi_cards"]
            ]
            output.writerow(["metric", "value", "collected", "trend"])
            for c in exec_data["kpi_cards"]:
                output.writerow([c["metric"], c["value"], c.get("collected", 0), c.get("trend", "")])
            return {"status": "ok", "format": "csv", "output": output.getvalue(), "message": f"Report generated: {title or 'Executive Summary'}"}

    elif format == "pdf":
        pdf = fpdf.Fpdf()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 18)
        pdf.cell(0, 15, title or "BI Dashboard Report", 0, 1, "C")
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 12, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
        pdf.add_page()

        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 12, "KPI Cards", 0, 1)
        pdf.set_font("helvetica", "B", 10)
        cards = [
            ("Total Revenue", f"${_money(kpis['revenue']['total_invoiced']):,}"),
            ("Expenses", f"${_money(kpis['expenses']['total']):,}"),
            ("Net Profit", f"${_money(kpis['profit']['net_profit']):,}"),
            ("Time Utilization", f"{kpis['time']['utilization_pct']}%"),
            ("Open Support Tickets", str(kpis['support']['open_tickets'])),
            ("Pipeline Value", f"${_money(kpis['pipeline']['open_value']):,}"),
        ]
        y = 10
        for name, val in cards:
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(140, 7, name, 0, 1)
            pdf.set_font("helvetica", "B", 11)
            pdf.cell(60, 7, val, 0, 1)

        pdf.add_page()
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 12, "Monthly Trend", 0, 1)
        y = 10
        for m in sorted(
            {m["month"]: m for m in monthly.get("monthly_trend", [])}.values(),
            key=lambda x: x["month"],
        ):
            pdf.set_font("helvetica", "B", 8)
            pdf.cell(50, 5, m["month"], 0, 1)
            pdf.set_font("helvetica", None, 9)
            pdf.cell(120, 5, f"Invoiced: ${_money(m['invoiced']):,.2f}", 0, 1)

        return {
            "status": "ok",
            "format": "pdf",
            "message": f"Report generated: {title or 'Executive Summary'} - {len(cards)} KPIs + trend",
        }

    elif format == "excel":
        report_df = pd.DataFrame([kpis]).T
        output = io.StringIO()
        # Simplified CSV for excel
        cols = ["revenue_invoiced", "revenue_collected", "expenses_total", "net_profit", "utilization_pct", "pipeline_open"]
        row = {}
        for k in ["revenue__total_invoiced", "revenue__total_collected", "expenses__total", "profit__net_profit", "time__utilization_pct", "pipeline__open_value"]:
            row[k.replace("__", _)] = getattr(kpis, k.replace("__", "_"))
        report_df.to_csv(io.StringIO(""), index=False)
        return {"status": "ok", "format": "excel", "message": f"Report generated: {title or 'Executive Summary'}"}

    return {"status": "ok", "message": f"Report {preset} generated"}


@mcp.tool
def export_data(dataset: str = "all_kpis", format: str = "csv") -> dict:
    """Export raw data in CSV or JSON format."""
    _deps_or_fetch()

    kpis = compute_kpis()
    data = {
        "revenue": kpis["revenue"],
        "expenses": kpis["expenses"],
        "profit": kpis["profit"],
        "time": kpis["time"],
        "support": kpis["support"],
        "pipeline": kpis["pipeline"],
        "budget": kpis["budget"],
        "vendor": kpis["vendor"],
    }

    if format == "csv":
        df = pd.DataFrame([data]).T
        output = io.StringIO()
        df.to_csv(output, index=False)
        return {"status": "ok", "format": "csv", "output": output.getvalue()}
    elif format == "json":
        return {"status": "ok", "format": "json", "output": json.dumps(data), "data": data}

    return {"status": "ok", "format": format, "data": data}


# ---- Resources ----
@mcp.resource("bi://kpi-snapshot")
def kpi_snapshot_resource() -> str:
    """Current cached KPI snapshot."""
    snapshot = None
    with _lock:
        if "full" in _snapshots and _snapshots["full"].get("_ts", 0) > (datetime.now().timestamp() - 3600):
            snapshot = _snapshots["full"]
    if snapshot is None:
        raise ValueError("Call refresh_dashboard_data() first.")
    del snapshot["_ts"]
    return json.dumps(snapshot["kpis"])


@mcp.resource("bi://revenue-overview")
def revenue_overview_resource() -> str:
    """Revenue overview as text."""
    r = get_revenue_kpis()
    lines = [
        f"# Revenue Overview",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Invoiced: ${_money(r['total_invoiced']):,}",
        f"Total Collected: ${_money(r['total_collected']):,}",
        f"Outstanding: ${_money(r['outstanding']):,}",
        f"Invoice Count: {r['invoice_count']}",
    ]
    for m in r.get("monthly_trend", [])[:10]:
        lines.append(f"{m['month']} - Invoiced: ${_money(m['invoiced']):,.1f} / Collected: ${_money(m['collected']):,.1f} / Net: ${_money(m['net']):,.1f}")
    return "\n".join(lines)


@mcp.resource("bi://expense-overview")
def expense_overview_resource() -> str:
    """Expense overview as text."""
    e = get_expense_kpis()
    lines = [
        f"# Expense Overview",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total: ${_money(e['total']):,}",
        f"Count: {e['expense_count']}",
    ]
    for cat in e.get("by_category", [])[:10]:
        lines.append(f"{cat['category']} - ${_money(cat['total']):,.1f} ({cat['count']} items)")
    return "\n".join(lines)


@mcp.resource("bi://profit-overview")
def profit_overview_resource() -> str:
    """Profit overview as text."""
    p = get_profit_kpis()
    lines = [
        f"# Profit Overview",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Net Profit: ${_money(p['net_profit']):,}",
        f"Margin: {p['margin_pct']}%",
        f"Revenue Efficiency: {p['efficiency_pct']}%",
    ]
    return "\n".join(lines)


@mcp.resource("bi://utilization-overview")
def utilization_overview_resource() -> str:
    """Time utilization overview as text."""
    u = get_utilization_kpis()
    lines = [
        f"# Time Utilization Overview",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Time: {u['total_minutes']} min",
        f"Billable Time: {u['billable_minutes']} min",
        f"Utilization: {u['utilization_pct']}%",
        f"Billable Revenue: ${_money(u['billable_revenue']):,.2f}",
    ]
    return "\n".join(lines)


@mcp.resource("bi://support-overview")
def support_overview_resource() -> str:
    """Support overview as text."""
    s = get_support_kpis()
    lines = [
        f"# Support Overview",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Open Tickets: {s['open_tickets']}",
        f"Resolved: {s['resolved_count']}",
        f"Comments: {s['comment_count']}",
    ]
    if s.get("avg_resolution_hours"):
        lines.append(f"Avg Resolution: {s['avg_resolution_hours']} hours")
    if s.get("sla_compliance_rate"):
        lines.append(f"SLA Compliance: {s['sla_compliance_rate'] * 100:.1f}%")
    if s.get("csat_average"):
        lines.append(f"CSAT: {s['csat_average']}")
    return "\n".join(lines)


@mcp.resource("bi://pipeline-overview")
def pipeline_overview_resource() -> str:
    """Pipeline overview as text."""
    p = get_pipeline_kpis()
    lines = [
        f"# Pipeline Overview",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Open Pipeline: ${_money(p['open_pipeline_value']):,}",
        f"Closed Won: ${_money(p['closed_won_value']):,}",
        f"Closed Lost: ${_money(p['closed_lost_value']):,}",
        f"Win Rate: {p['win_rate_pct']}%",
    ]
    for stage, v in p.get("by_stage", {}).items():
        lines.append(f"{stage}: {v['count']} deals - ${_money(v['value']):,.1f}")
    return "\n".join(lines)


@mcp.resource("bi://vendor-overview")
def vendor_overview_resource() -> str:
    """Vendor overview as text."""
    v = get_vendor_kpis()
    lines = [
        f"# Vendor Overview",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    for vendor, spend in v.get("by_vendor", [])[:10]:
        lines.append(f"{vendor}: ${_money(spend):,.1f}")
    if v.get("avg_lead_time_days"):
        lines.append(f"Avg Lead Time: {v['avg_lead_time_days']} days")
    return "\n".join(lines)


# ---- main ----
def main():
    import sys
    parser = argparse.ArgumentParser(description="BI Dashboard MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio", help="Transport mode")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port for MCP transport")
    parser.add_argument("--webui-port", type=int, default=8080, help="Web UI dashboard port")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()
    else:
        _deps_or_fetch()
        html = Path(__file__).parent.resolve() / "dashboard.html"
        if not html.exists():
            print("ERROR: dashboard.html not found. Run with --transport stdio only.")
            sys.exit(1)
        handler = HTTPServer(("127.0.0.1", args.port), SimpleHTTPRequestHandler)
        handler.error_logger = lambda *args: None
        print(f"============================================================")
        print(f"  BI Dashboard MCP Server Started")
        print(f"============================================================")
        print(f"  MCP Transport: http")
        print(f"  MCP Port: {args.port}")
        print(f"  🌐 Dashboard UI: http://127.0.0.1:{args.port}/dashboard")
        print(f"============================================================")
        print()
        handler.serve_forever()


if __name__ == "__main__":
    main()
