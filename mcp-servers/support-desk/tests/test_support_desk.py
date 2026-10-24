"""Tests for the Support Desk MCP server core logic."""

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
def desk(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_DATA_DIR", str(tmp_path))
    sys.modules.pop("support_server", None)
    return _load("support_server")


def _future(hours: float = 24) -> str:
    return (datetime.now() + timedelta(hours=hours)).isoformat()


def test_sla_due_by_priority(desk):
    urgent = desk.create_ticket("Outage", "Everything down", "Alice", priority="urgent")
    low = desk.create_ticket("Question", "How do I export?", "Bob", priority="low")
    urgent_window = (datetime.fromisoformat(urgent.sla_due_at)
                     - datetime.fromisoformat(urgent.created_at))
    low_window = (datetime.fromisoformat(low.sla_due_at)
                  - datetime.fromisoformat(low.created_at))
    assert urgent_window == timedelta(hours=4)
    assert low_window == timedelta(hours=72)


def test_custom_sla_hours_override(desk):
    ticket = desk.create_ticket("Custom", "x", "Alice", priority="medium", sla_hours=2)
    window = (datetime.fromisoformat(ticket.sla_due_at)
              - datetime.fromisoformat(ticket.created_at))
    assert window == timedelta(hours=2)


def test_first_response_recorded_once(desk):
    ticket = desk.create_ticket("Help", "x", "Alice")
    first = desk.add_comment(ticket.id, "agent", "Looking into it")
    desk.add_comment(ticket.id, "agent", "Second update")
    stored = desk.get_ticket(ticket.id)
    assert stored.first_response_at == first.created_at
    assert stored.status == "in_progress"


def test_internal_comment_does_not_start_response_clock(desk):
    ticket = desk.create_ticket("Help", "x", "Alice")
    desk.add_comment(ticket.id, "agent", "internal note", internal=True)
    assert desk.get_ticket(ticket.id).first_response_at is None


def test_resolve_and_met_sla(desk):
    ticket = desk.create_ticket("Help", "x", "Alice", priority="high")
    desk.add_comment(ticket.id, "agent", "On it")
    desk.resolve_ticket(ticket.id, "Fixed the config")
    stored = desk.get_ticket(ticket.id)
    assert stored.status == "resolved"
    assert stored.resolution == "Fixed the config"
    assert stored.resolved_at is not None
    assert desk.get_sla_status(ticket.id)["state"] == "met"


def test_breach_detection(desk):
    ticket = desk.create_ticket("Late", "x", "Alice", priority="urgent")
    status = desk.get_sla_status(ticket.id, as_of=_future(48))
    assert status["state"] == "breached"
    assert status["remaining_hours"] < 0
    assert [t.id for t in desk.get_overdue_tickets(as_of=_future(48))] == [ticket.id]


def test_at_risk_detection(desk):
    ticket = desk.create_ticket("Soon", "x", "Alice", priority="urgent")
    # 90% of the 4h window elapsed -> 0.4h remaining
    status = desk.get_sla_status(ticket.id, as_of=_future(3.6))
    assert status["state"] == "at_risk"


def test_priority_change_recalculates_sla(desk):
    ticket = desk.create_ticket("Help", "x", "Alice", priority="low")
    before = ticket.sla_due_at
    updated = desk.update_ticket(ticket.id, priority="urgent")
    assert updated.sla_due_at != before
    window = (datetime.fromisoformat(updated.sla_due_at)
              - datetime.fromisoformat(updated.created_at))
    assert window == timedelta(hours=4)


def test_csat_and_stats(desk):
    ticket = desk.create_ticket("Help", "x", "Alice", priority="medium")
    desk.add_comment(ticket.id, "agent", "On it")
    desk.resolve_ticket(ticket.id, "Done")
    desk.submit_csat(ticket.id, 4, "Quick")
    desk.submit_csat(ticket.id, 5)
    stats = desk.get_support_stats()
    assert stats["total_tickets"] == 1
    assert stats["avg_first_response_hours"] is not None
    assert stats["avg_resolution_hours"] is not None
    assert stats["sla_compliance_pct"] == 100.0
    assert stats["csat_average"] == 4.5
    assert stats["csat_responses"] == 2


def test_csat_rating_bounds(desk):
    ticket = desk.create_ticket("Help", "x", "Alice")
    with pytest.raises(ValueError):
        desk.submit_csat(ticket.id, 6)


def test_reopen_clears_resolution(desk):
    ticket = desk.create_ticket("Help", "x", "Alice")
    desk.resolve_ticket(ticket.id, "Fixed")
    reopened = desk.reopen_ticket(ticket.id)
    assert reopened.status == "open"
    assert reopened.resolved_at is None


def test_invalid_priority_rejected(desk):
    with pytest.raises(ValueError):
        desk.create_ticket("Help", "x", "Alice", priority="whenever")


def test_bulk_create_tickets_uses_one_write(desk, monkeypatch):
    writes = []
    original = desk._write_payload
    monkeypatch.setattr(desk, "_write_payload",
                        lambda payload: (writes.append(1), original(payload))[1])
    created = desk.bulk_create_tickets([
        {"subject": "A", "description": "x", "requester_name": "Alice", "priority": "urgent"},
        {"subject": "B", "description": "y", "requester_name": "Bob"},
        {"subject": "C", "description": "z", "requester_name": "Cara", "tags": ["vip"]},
    ])
    assert len(created) == 3
    assert created[0].priority == "urgent"
    assert created[2].tags == ["vip"]
    assert len(writes) == 1
    assert len(desk.list_tickets()) == 3
