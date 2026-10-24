"""Tests for the Invoice Manager MCP server core logic."""

import importlib.util
import sys
from datetime import datetime, timedelta
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
def inv(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_DATA_DIR", str(tmp_path))
    sys.modules.pop("invoice_server", None)
    return _load("invoice_server")


def _today(offset_days: int = 0) -> str:
    return (datetime.now() + timedelta(days=offset_days)).date().isoformat()


def test_totals_with_tax_and_discount(inv):
    client = inv.create_client(name="Acme", currency="AUD")
    invoice = inv.create_invoice(
        client_id=client.id,
        line_items=[
            {"description": "Consulting", "quantity": 2, "unit_price": 100},
            {"description": "Hosting", "quantity": 1, "unit_price": 50},
        ],
        tax_rate=10,
        discount=50,
    )
    # 250 subtotal - 50 discount = 200 taxable, 10% tax = 20, total 220
    assert invoice.subtotal == 250.0
    assert invoice.tax_amount == 20.0
    assert invoice.total == 220.0
    assert invoice.balance == 220.0
    assert invoice.status == "draft"
    assert invoice.number == "INV-0001"


def test_payment_lifecycle(inv):
    client = inv.create_client(name="Acme")
    invoice = inv.create_invoice(
        client_id=client.id,
        line_items=[{"description": "Work", "quantity": 1, "unit_price": 100}],
        send=True,
    )
    inv.record_payment(invoice.id, 40)
    partial = inv.get_invoice(invoice.id)
    assert partial.amount_paid == 40.0
    assert partial.balance == 60.0
    assert partial.status == "partially_paid"

    inv.record_payment(invoice.id, 60)
    paid = inv.get_invoice(invoice.id)
    assert paid.balance == 0.0
    assert paid.status == "paid"
    assert len(inv.list_payments(invoice.id)) == 2


def test_overpayment_rejected(inv):
    client = inv.create_client(name="Acme")
    invoice = inv.create_invoice(
        client_id=client.id,
        line_items=[{"description": "Work", "quantity": 1, "unit_price": 100}],
        send=True,
    )
    with pytest.raises(ValueError):
        inv.record_payment(invoice.id, 150)


def test_aging_buckets(inv):
    client = inv.create_client(name="Acme")
    fresh = inv.create_invoice(
        client_id=client.id,
        line_items=[{"description": "Current", "quantity": 1, "unit_price": 100}],
        issue_date=_today(-10), due_date=_today(10), send=True,
    )
    overdue_45 = inv.create_invoice(
        client_id=client.id,
        line_items=[{"description": "Late", "quantity": 1, "unit_price": 200}],
        issue_date=_today(-75), due_date=_today(-45), send=True,
    )
    report = inv.get_aging_report()
    assert report["buckets"]["current"] == fresh.balance
    assert report["buckets"]["31_60"] == overdue_45.balance
    assert report["total_outstanding"] == 300.0
    assert inv.get_invoice(overdue_45.id).status == "overdue"


def test_void_excluded_from_aging(inv):
    client = inv.create_client(name="Acme")
    invoice = inv.create_invoice(
        client_id=client.id,
        line_items=[{"description": "Work", "quantity": 1, "unit_price": 500}],
        send=True,
    )
    inv.void_invoice(invoice.id)
    report = inv.get_aging_report()
    assert report["total_outstanding"] == 0.0


def test_recurring_generation_advances_schedule(inv):
    client = inv.create_client(name="Acme")
    template = inv.create_recurring_invoice(
        client_id=client.id,
        line_items=[{"description": "Retainer", "quantity": 1, "unit_price": 1000}],
        interval="monthly",
        next_run_date="2026-01-01",
    )
    created = inv.generate_due_invoices(as_of="2026-03-01")
    assert len(created) == 3
    assert [c.issue_date for c in created] == ["2026-01-01", "2026-02-01", "2026-03-01"]
    stored = inv.list_recurring_invoices()[0]
    assert stored.next_run_date == "2026-04-01"
    # nothing further due the same day
    assert inv.generate_due_invoices(as_of="2026-03-01") == []


def test_cannot_delete_client_with_invoices(inv):
    client = inv.create_client(name="Acme")
    inv.create_invoice(
        client_id=client.id,
        line_items=[{"description": "Work", "quantity": 1, "unit_price": 10}],
    )
    with pytest.raises(ValueError):
        inv.delete_client(client.id)


def test_invoice_persists_and_reloads(tmp_path, monkeypatch, inv):
    client = inv.create_client(name="Acme")
    inv.create_invoice(
        client_id=client.id,
        line_items=[{"description": "Work", "quantity": 1, "unit_price": 100}],
        send=True,
    )
    data = (tmp_path / "invoices.json").read_text()
    assert "Acme" in data
    assert not list(tmp_path.glob("*.tmp"))
