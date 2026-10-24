"""Tests for the Contract Manager MCP server core logic."""

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
def cm(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_DATA_DIR", str(tmp_path))
    sys.modules.pop("contract_server", None)
    return _load("contract_server")


def _today(offset: int = 0) -> str:
    return (datetime.now() + timedelta(days=offset)).date().isoformat()


def test_expired_status_is_derived(cm):
    expired = cm.create_contract("Old lease", "Landlord",
                                 start_date=_today(-400), end_date=_today(-40))
    assert cm.get_contract(expired.id).status == "expired"


def test_active_contract_and_notice_deadline(cm):
    contract = cm.create_contract("SaaS", "Vendor", start_date=_today(-300),
                                  end_date=_today(20), notice_days=30,
                                  renewal_type="auto")
    assert cm.get_contract(contract.id).status == "active"

    expiring = cm.get_expiring_contracts(30)
    assert len(expiring) == 1
    assert expiring[0]["days_until_end"] == 20
    # notice deadline was 30 days before the end date, so it already passed
    assert expiring[0]["notice_passed"] is True


def test_renewal_calendar_skips_non_renewing(cm):
    cm.create_contract("One-off", "Vendor", start_date=_today(-10),
                       end_date=_today(10), renewal_type="none")
    cm.create_contract("Auto", "Vendor", start_date=_today(-10),
                       end_date=_today(10), renewal_type="auto")
    calendar = cm.get_renewal_calendar()
    assert [item["title"] for item in calendar] == ["Auto"]
    assert calendar[0]["action_required"] is True


def test_end_before_start_rejected(cm):
    with pytest.raises(ValueError):
        cm.create_contract("Bad", "Vendor", start_date=_today(10), end_date=_today(0))


def test_recurring_obligation_rolls_forward(cm):
    contract = cm.create_contract("Service", "Vendor",
                                  start_date="2026-01-01", end_date="2026-12-31")
    obligation = cm.add_obligation(contract.id, "Monthly report",
                                   due_date="2026-01-15", recurring="monthly")
    completed = cm.complete_obligation(obligation.id)
    assert completed.status == "pending"
    assert completed.due_date == "2026-02-15"
    assert completed.completed_at is not None


def test_one_off_obligation_is_done(cm):
    contract = cm.create_contract("Service", "Vendor",
                                  start_date="2026-01-01", end_date="2026-12-31")
    obligation = cm.add_obligation(contract.id, "Initial audit", due_date="2026-02-01")
    assert cm.complete_obligation(obligation.id).status == "done"
    assert cm.list_obligations(contract.id, status="done")[0].id == obligation.id


def test_overdue_and_upcoming_obligations(cm):
    contract = cm.create_contract("Service", "Vendor",
                                  start_date=_today(-100), end_date=_today(100))
    cm.add_obligation(contract.id, "Late", due_date=_today(-5))
    cm.add_obligation(contract.id, "Soon", due_date=_today(10))
    assert [o.description for o in cm.get_overdue_obligations()] == ["Late"]
    assert [o.description for o in cm.get_upcoming_obligations(30)] == ["Soon"]


def test_terminate_contract(cm):
    contract = cm.create_contract("Service", "Vendor",
                                  start_date=_today(-10), end_date=_today(100))
    terminated = cm.terminate_contract(contract.id, reason="Project cancelled")
    assert terminated.status == "terminated"
    assert "Project cancelled" in terminated.notes


def test_stats_and_validation(cm):
    cm.create_contract("A", "Vendor", start_date=_today(-10), end_date=_today(10),
                       value=1000)
    stats = cm.get_contract_stats()
    assert stats["contracts"] == 1
    assert stats["by_status"]["active"] == 1
    assert stats["active_value"] == 1000.0
    with pytest.raises(ValueError):
        cm.create_contract("B", "Vendor", start_date=_today(0), end_date=_today(10),
                           contract_type="nonsense")


def test_delete_contract_removes_obligations(cm):
    contract = cm.create_contract("Service", "Vendor",
                                  start_date=_today(-1), end_date=_today(100))
    cm.add_obligation(contract.id, "Report", due_date=_today(5))
    assert cm.delete_contract(contract.id) is True
    assert cm.list_obligations() == []
