"""Tests for the Vendor Manager MCP server core logic."""

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
def vm(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_DATA_DIR", str(tmp_path))
    sys.modules.pop("vendor_server", None)
    return _load("vendor_server")


def _today(offset: int = 0) -> str:
    return (datetime.now() + timedelta(days=offset)).date().isoformat()


def test_po_total_and_lifecycle(vm):
    vendor = vm.create_vendor("Acme Parts")
    po = vm.create_purchase_order(vendor.id, [
        {"description": "Bolt", "quantity": 10, "unit_price": 2.5},
        {"description": "Nut", "quantity": 10, "unit_price": 1.5},
    ])
    assert po.total == 40.0
    assert po.status == "ordered"
    assert po.reference == "PO-0001"

    received = vm.receive_order(po.id)
    assert received.status == "received"
    assert received.received_at is not None


def test_expected_at_uses_lead_time(vm):
    vendor = vm.create_vendor("Slow Co", lead_time_days=14)
    po = vm.create_purchase_order(vendor.id, [
        {"description": "Widget", "quantity": 1, "unit_price": 10},
    ])
    assert po.expected_at == _today(14)


def test_draft_order_can_be_placed(vm):
    vendor = vm.create_vendor("Acme")
    po = vm.create_purchase_order(vendor.id, [
        {"description": "Widget", "quantity": 1, "unit_price": 10},
    ], place=False)
    assert po.status == "draft"
    assert vm.place_order(po.id).status == "ordered"


def test_late_delivery_lowers_on_time_rate(vm):
    vendor = vm.create_vendor("Acme")
    late = vm.create_purchase_order(vendor.id, [
        {"description": "Widget", "quantity": 1, "unit_price": 10},
    ], expected_at=_today(-5))
    on_time = vm.create_purchase_order(vendor.id, [
        {"description": "Gadget", "quantity": 1, "unit_price": 10},
    ], expected_at=_today(5))
    vm.receive_order(late.id)
    vm.receive_order(on_time.id)

    card = vm.get_vendor_scorecard(vendor.id)
    assert card["received_orders"] == 2
    assert card["late_deliveries"] == 1
    assert card["on_time_rate"] == 0.5
    assert card["total_spend"] == 20.0


def test_review_averages_and_rating(vm):
    vendor = vm.create_vendor("Acme")
    vm.add_vendor_review(vendor.id, on_time_delivery=5, quality=4,
                         communication=3, pricing=2)
    review = vm.add_vendor_review(vendor.id, on_time_delivery=4, quality=4,
                                  communication=4, pricing=4)
    assert review.overall == 4.0

    card = vm.get_vendor_scorecard(vendor.id)
    assert card["review_averages"]["on_time_delivery"] == 4.5
    assert card["review_averages"]["overall"] == 3.75
    assert card["overall_rating"] == 3.75


def test_review_score_bounds(vm):
    vendor = vm.create_vendor("Acme")
    with pytest.raises(ValueError):
        vm.add_vendor_review(vendor.id, on_time_delivery=6, quality=4,
                             communication=3, pricing=2)


def test_spend_by_vendor(vm):
    a = vm.create_vendor("A")
    b = vm.create_vendor("B")
    vm.create_purchase_order(a.id, [{"description": "x", "quantity": 1, "unit_price": 100}])
    vm.create_purchase_order(b.id, [{"description": "y", "quantity": 1, "unit_price": 50}])
    cancelled = vm.create_purchase_order(b.id, [{"description": "z", "quantity": 1, "unit_price": 999}])
    vm.cancel_order(cancelled.id)

    spend = vm.get_vendor_spend()
    assert spend["by_vendor"] == {"A": 100.0, "B": 50.0}
    assert spend["total_spend"] == 150.0


def test_cancel_rules(vm):
    vendor = vm.create_vendor("Acme")
    po = vm.create_purchase_order(vendor.id, [{"description": "x", "quantity": 1, "unit_price": 1}])
    vm.receive_order(po.id)
    with pytest.raises(ValueError):
        vm.cancel_order(po.id)


def test_delete_vendor_blocked_by_orders(vm):
    vendor = vm.create_vendor("Acme")
    vm.create_purchase_order(vendor.id, [{"description": "x", "quantity": 1, "unit_price": 1}])
    with pytest.raises(ValueError):
        vm.delete_vendor(vendor.id)


def test_low_rated_vendors(vm):
    good = vm.create_vendor("Good", rating=4.5)
    bad = vm.create_vendor("Bad", rating=2.0)
    low = vm.get_low_rated_vendors(threshold=3.0)
    assert [item["vendor_id"] for item in low] == [bad.id]


def test_stats(vm):
    vendor = vm.create_vendor("Acme")
    vm.create_purchase_order(vendor.id, [{"description": "x", "quantity": 1, "unit_price": 10}])
    stats = vm.get_vendor_stats()
    assert stats["vendors"] == 1
    assert stats["purchase_orders"] == 1
    assert stats["purchase_orders_by_status"]["ordered"] == 1
    assert stats["total_spend"] == 10.0
