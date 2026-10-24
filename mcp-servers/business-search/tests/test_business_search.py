"""Tests for the Business Search hub server."""

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
def hub(tmp_path, monkeypatch):
    """Build a fake multi-server data layout and load the hub against it."""
    (tmp_path / "crm" / "data").mkdir(parents=True)
    (tmp_path / "crm" / "data" / "crm.json").write_text(json.dumps({
        "leads": {
            "1": {"id": 1, "name": "Acme Corp", "email": "buyer@acme.com",
                  "status": "qualified"},
        },
        "next_lead_id": 2,
    }))
    (tmp_path / "invoice-manager" / "data").mkdir(parents=True)
    (tmp_path / "invoice-manager" / "data" / "invoices.json").write_text(json.dumps({
        "invoices": {
            "1": {"id": 1, "number": "INV-0001", "notes": "Acme overdue retainer",
                  "total": 500},
        },
        "next_invoice_id": 2,
    }))
    (tmp_path / "kanban-mcp").mkdir(parents=True)
    (tmp_path / "kanban-mcp" / "kanban_data.json").write_text(json.dumps({
        "boards": {
            "1": {"id": 1, "name": "Ops", "tasks": [
                {"id": 9, "title": "Fix pump at Acme site"},
            ]},
        },
        "next_board_id": 2,
    }))

    monkeypatch.setenv("MCP_DATA_ROOTS", str(tmp_path))
    sys.modules.pop("business_search_server", None)
    return _load("business_search_server")


def test_search_finds_records_across_sources(hub):
    hits = hub.search_business("acme")
    sources = {hit.source for hit in hits}
    assert {"crm", "invoice-manager"} <= sources
    assert all(hit.matched_terms >= 1 for hit in hits)


def test_entity_type_filter(hub):
    hits = hub.search_business("acme", entity_type="leads")
    assert hits
    assert {hit.entity_type for hit in hits} == {"leads"}


def test_source_filter(hub):
    hits = hub.search_business("acme", source="invoice-manager")
    assert hits
    assert {hit.source for hit in hits} == {"invoice-manager"}


def test_nested_records_are_indexed(hub):
    hits = hub.search_business("pump")
    assert len(hits) == 1
    assert hits[0].entity_type == "boards.tasks"
    assert hits[0].record_id == 9


def test_multi_term_ranking_prefers_more_matches(hub):
    hits = hub.search_business("acme overdue")
    assert hits[0].entity_type == "invoices"
    assert hits[0].matched_terms == 2


def test_stats_and_sources(hub):
    stats = hub.get_index_stats()
    assert stats["sources"] == 3
    # one lead, one invoice, plus the board and its nested task
    assert stats["records"] == 4
    assert stats["by_source"]["crm"] == 1
    assert stats["by_source"]["kanban-mcp"] == 2
    assert stats["by_entity_type"]["boards"] == 1
    assert stats["by_entity_type"]["boards.tasks"] == 1
    sources = hub.list_data_sources()
    assert {s.source for s in sources} == {"crm", "invoice-manager", "kanban-mcp"}


def test_get_record(hub):
    record = hub.get_record("crm", "leads", 1)
    assert record["name"] == "Acme Corp"
    assert hub.get_record("crm", "leads", 999) is None


def test_incremental_refresh_and_rebuild(hub, tmp_path):
    path = tmp_path / "crm" / "data" / "crm.json"
    document = json.loads(path.read_text())
    document["leads"]["2"] = {"id": 2, "name": "Globex", "status": "new"}
    path.write_text(json.dumps(document))

    # a changed size/mtime is picked up without an explicit rebuild
    hits = hub.search_business("globex")
    assert hits and hits[0].record_id == 2

    stats = hub.rebuild_index()
    assert stats["records"] == 5


def test_empty_query_returns_nothing(hub):
    assert hub.search_business("   ") == []


def test_limit_is_respected(hub):
    assert len(hub.search_business("acme", limit=1)) == 1
