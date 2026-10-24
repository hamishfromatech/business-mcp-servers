"""Tests for the OKR Tracker MCP server core logic."""

import importlib.util
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
def okr(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_DATA_DIR", str(tmp_path))
    sys.modules.pop("okr_server", None)
    return _load("okr_server")


def test_increasing_kr_progress(okr):
    objective = okr.create_objective("Grow revenue", "Hamish", "2026-Q4")
    okr.add_key_result(objective.id, "New MRR", target_value=100, start_value=0)
    kr = okr.get_objective(objective.id).key_results[0]
    okr.update_key_result(objective.id, kr.id, current_value=50)
    assert okr.get_objective(objective.id).progress == 0.5
    okr.update_key_result(objective.id, kr.id, current_value=100)
    assert okr.get_objective(objective.id).progress == 1.0


def test_decreasing_target_progress(okr):
    objective = okr.create_objective("Reduce churn", "Hamish", "2026-Q4")
    okr.add_key_result(objective.id, "Churn %", target_value=0, start_value=100,
                       current_value=25)
    assert okr.get_objective(objective.id).progress == 0.75


def test_progress_is_clamped(okr):
    objective = okr.create_objective("Ship", "Hamish", "2026-Q4")
    kr = okr.add_key_result(objective.id, "Features", target_value=10, start_value=0,
                            current_value=25)
    assert okr.get_objective(objective.id).progress == 1.0


def test_objective_rollup_is_mean_of_key_results(okr):
    objective = okr.create_objective("Grow", "Hamish", "2026-Q4")
    okr.add_key_result(objective.id, "A", target_value=100, start_value=0,
                       current_value=100)
    okr.add_key_result(objective.id, "B", target_value=100, start_value=0,
                       current_value=0)
    # one complete, one untouched -> 0.5
    assert okr.get_objective(objective.id).progress == 0.5


def test_degenerate_target_is_complete_when_reached(okr):
    objective = okr.create_objective("Hold", "Hamish", "2026-Q4")
    okr.add_key_result(objective.id, "Flat", target_value=5, start_value=5,
                       current_value=5)
    assert okr.get_objective(objective.id).progress == 1.0


def test_check_in_updates_value_and_records_history(okr):
    objective = okr.create_objective("Grow", "Hamish", "2026-Q4")
    kr = okr.add_key_result(objective.id, "MRR", target_value=100)
    record = okr.check_in(objective.id, value=40, key_result_id=kr.id,
                          confidence=70, note="week 1")
    assert record.value == 40
    stored_kr = okr.get_objective(objective.id).key_results[0]
    assert stored_kr.current_value == 40
    assert stored_kr.confidence == 70
    assert len(okr.list_check_ins(objective.id)) == 1


def test_confidence_bounds(okr):
    objective = okr.create_objective("Grow", "Hamish", "2026-Q4")
    with pytest.raises(ValueError):
        okr.add_key_result(objective.id, "KR", target_value=1, confidence=101)


def test_invalid_status_rejected(okr):
    with pytest.raises(ValueError):
        okr.create_objective("Grow", "Hamish", "2026-Q4", status="vibes")


def test_summary_and_at_risk(okr):
    on_track = okr.create_objective("Grow", "Hamish", "2026-Q4")
    at_risk = okr.create_objective("Fix support", "Alice", "2026-Q4", status="at_risk")
    okr.add_key_result(on_track.id, "MRR", target_value=100, current_value=50)
    okr.add_key_result(at_risk.id, "CSAT", target_value=5, current_value=1)
    summary = okr.get_okr_summary("2026-Q4")
    assert summary["objectives"] == 2
    assert summary["key_results"] == 2
    assert summary["by_status"]["on_track"] == 1
    assert [item["objective_id"] for item in summary["at_risk"]] == [at_risk.id]


def test_delete_objective_removes_check_ins(okr):
    objective = okr.create_objective("Grow", "Hamish", "2026-Q4")
    kr = okr.add_key_result(objective.id, "MRR", target_value=100)
    okr.check_in(objective.id, value=10, key_result_id=kr.id)
    assert okr.delete_objective(objective.id) is True
    assert okr.get_objective(objective.id) is None
    assert okr.list_check_ins(objective.id) == []
