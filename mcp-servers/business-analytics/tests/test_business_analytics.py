"""Tests for the Business Analytics MCP server aggregation logic."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1] / "server.py"


def _load(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def analytics(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_DATA_ROOTS", str(tmp_path))
    sys.modules.pop("business_analytics", None)
    module = _load("business_analytics")
    for source, filename in {
        "invoice-manager": "invoices.json",
        "expense-tracker": "expenses.json",
        "time-tracker": "time.json",
        "crm": "crm.json",
        "support-desk": "support.json",
    }.items():
        data_dir = tmp_path / "mcp-servers" / source / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / filename).write_text("{}", encoding="utf-8")
    return module


def _write_json(tmp_path, source: str, filename: str, payload) -> None:
    path = tmp_path / "mcp-servers" / source / "data" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_list_data_sources(analytics):
    sources = analytics.list_data_sources()
    assert len(sources) == 5
    by_source = {s["source"]: s for s in sources}
    assert by_source["invoice-manager"]["records"] == 0
    assert by_source["expense-tracker"]["records"] == 0


def test_financial_overview_aggregates_invoices_and_expenses(analytics, tmp_path):
    _write_json(tmp_path, "invoice-manager", "invoices.json", {
        "invoices": {
            "1": {
                "id": 1, "number": "INV-0001", "client_id": 1, "issue_date": "2026-09-01",
                "due_date": "2026-10-01", "line_items": [{"description": "Work", "quantity": 1, "unit_price": 100}],
                "tax_rate": 0, "discount": 0, "currency": "USD", "status": "sent", "notes": None,
                "subtotal": 100, "tax_amount": 0, "total": 100, "amount_paid": 0, "balance": 100,
                "created_at": "2026-09-01T00:00:00", "updated_at": "2026-09-01T00:00:00",
            },
            "2": {
                "id": 2, "number": "INV-0002", "client_id": 1, "issue_date": "2026-10-15",
                "due_date": "2026-11-15", "line_items": [{"description": "Work", "quantity": 2, "unit_price": 100}],
                "tax_rate": 0, "discount": 0, "currency": "USD", "status": "partially_paid", "notes": None,
                "subtotal": 200, "tax_amount": 0, "total": 200, "amount_paid": 50, "balance": 150,
                "created_at": "2026-10-15T00:00:00", "updated_at": "2026-10-20T00:00:00",
            },
        },
        "payments": {
            "1": {"id": 1, "invoice_id": 2, "amount": 50, "paid_at": "2026-10-20", "method": "card", "reference": None},
        },
    })
    _write_json(tmp_path, "expense-tracker", "expenses.json", {
        "expenses": {
            "1": {"id": 1, "amount": 30, "category": "food", "description": "Team lunch", "date": "2026-09-10", "tags": []},
            "2": {"id": 2, "amount": 20, "category": "transport", "description": "Uber", "date": "2026-09-12", "tags": []},
        },
    })

    overview = analytics.get_financial_overview()
    assert overview["revenue"]["invoiced"] == 300.0
    assert overview["revenue"]["collected"] == 50.0
    assert overview["revenue"]["outstanding"] == 250.0
    assert overview["revenue"]["invoice_count"] == 2
    assert overview["expenses"]["total"] == 50.0
    assert overview["expenses"]["by_category"] == {"food": 30.0, "transport": 20.0}
    assert overview["net_profit"] == 0.0


def test_get_revenue_report_monthly_buckets(analytics, tmp_path):
    _write_json(tmp_path, "invoice-manager", "invoices.json", {
        "invoices": {
            "1": {
                "id": 1, "number": "INV-0001", "client_id": 1, "issue_date": "2026-09-01",
                "due_date": "2026-10-01", "line_items": [{"description": "Work", "quantity": 1, "unit_price": 100}],
                "tax_rate": 0, "discount": 0, "currency": "USD", "status": "sent", "notes": None,
                "subtotal": 100, "tax_amount": 0, "total": 100, "amount_paid": 0, "balance": 100,
                "created_at": "2026-09-01T00:00:00", "updated_at": "2026-09-01T00:00:00",
            },
        },
        "payments": {},
    })
    _write_json(tmp_path, "expense-tracker", "expenses.json", {
        "expenses": {
            "1": {"id": 1, "amount": 50, "category": "food", "description": "Rent", "date": "2026-09-10", "tags": []},
        },
    })

    report = analytics.get_revenue_report()
    assert len(report["months"]) == 1
    assert report["months"][0]["month"] == "2026-09"
    assert report["months"][0]["invoiced"] == 100.0
    assert report["months"][0]["collected"] == 0.0
    assert report["months"][0]["expenses"] == 50.0
    assert report["months"][0]["net"] == -50.0


def test_get_expense_breakdown_by_category(analytics, tmp_path):
    _write_json(tmp_path, "expense-tracker", "expenses.json", {
        "expenses": {
            "1": {"id": 1, "amount": 30, "category": "food", "description": "Team lunch", "date": "2026-09-10", "tags": []},
            "2": {"id": 2, "amount": 20, "category": "transport", "description": "Uber", "date": "2026-09-12", "tags": []},
        },
    })
    breakdown = analytics.get_expense_breakdown()
    assert breakdown["total"] == 50.0
    assert breakdown["expense_count"] == 2
    assert breakdown["categories"][0]["category"] == "food"
    assert breakdown["categories"][0]["total"] == 30.0


def test_get_time_summary_billable_revenue_and_utilization(analytics, tmp_path):
    _write_json(tmp_path, "time-tracker", "time.json", {
        "projects": {
            "1": {"id": 1, "name": "Acme Retainer", "client": "Acme", "color": "#fff", "billable_rate": 100, "budget_hours": None, "active": True, "created_at": "2026-01-01T00:00:00"},
        },
        "time_entries": {
            "1": {"id": 1, "project_id": 1, "description": "Consulting", "duration_minutes": 60, "duration_formatted": "1:00", "start_time": None, "end_time": None, "date": "2026-09-05", "tags": [], "billable": True, "created_at": "2026-09-05T00:00:00"},
            "2": {"id": 2, "project_id": 1, "description": "Admin", "duration_minutes": 30, "duration_formatted": "0:30", "start_time": None, "end_time": None, "date": "2026-09-06", "tags": [], "billable": False, "created_at": "2026-09-06T00:00:00"},
        },
        "active_timer": None,
    })
    summary = analytics.get_time_summary()
    assert summary["total_minutes"] == 90.0
    assert summary["billable_minutes"] == 60.0
    assert summary["billable_revenue"] == 100.0
    assert summary["utilization"] == 0.67


def test_get_support_stats(analytics, tmp_path):
    _write_json(tmp_path, "support-desk", "support.json", {
        "tickets": {
            "1": {"id": 1, "subject": "Login issue", "description": "Can't log in", "requester_name": "Acme", "requester_email": "a@b.c", "status": "resolved", "priority": "high", "category": "tech", "assignee": "Me", "tags": [], "sla_due_at": "2026-09-10T00:00:00", "first_response_at": "2026-09-01T00:00:00", "resolved_at": "2026-09-02T00:00:00", "resolution": "Fixed", "created_at": "2026-08-30T00:00:00", "updated_at": "2026-09-02T00:00:00"},
            "2": {"id": 2, "subject": "Billing", "description": "Wrong charge", "requester_name": "Beta", "requester_email": None, "status": "open", "priority": "medium", "category": "billing", "assignee": None, "tags": [], "sla_due_at": None, "first_response_at": None, "resolved_at": None, "resolution": None, "created_at": "2026-09-20T00:00:00", "updated_at": "2026-09-20T00:00:00"},
        },
        "comments": {},
        "csat": {
            "1": {"id": 1, "ticket_id": 1, "rating": 5, "comment": "Great", "created_at": "2026-09-02T00:00:00"},
        },
    })
    stats = analytics.get_support_stats()
    assert stats["tickets_by_status"] == {"resolved": 1, "open": 1}
    assert stats["open_tickets"] == 1
    assert stats["resolved_count"] == 1
    assert stats["avg_resolution_hours"] == 72.0
    assert stats["sla_compliance_rate"] == 1.0
    assert stats["csat_average"] == 5.0


def test_get_pipeline_summary(analytics, tmp_path):
    _write_json(tmp_path, "crm", "crm.json", {
        "deals": {
            "1": {"id": 1, "title": "Acme website", "customer_id": 1, "value": 5000, "stage": "closed_won", "expected_close_date": None, "created_at": "2026-08-01T00:00:00", "updated_at": "2026-09-01T00:00:00"},
            "2": {"id": 2, "title": "Acme retainer", "customer_id": 1, "value": 1000, "stage": "negotiation", "expected_close_date": None, "created_at": "2026-09-01T00:00:00", "updated_at": "2026-09-10T00:00:00"},
        },
    })
    summary = analytics.get_pipeline_summary()
    assert summary["by_stage"]["closed_won"]["value"] == 5000.0
    assert summary["by_stage"]["negotiation"]["value"] == 1000.0
    assert summary["open_pipeline_value"] == 1000.0
    assert summary["closed_won_value"] == 5000.0
    assert summary["closed_lost_value"] == 0.0
