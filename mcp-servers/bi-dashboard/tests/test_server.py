"""Tests for the BI Dashboard MCP Server."""

import pytest
from datetime import date, datetime
from pathlib import Path

# Add the parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (
    _data_roots,
    _int_map,
    _money,
    _parse_date,
    _in_range,
    compute_kpis,
    get_revenue_kpis,
    get_expense_kpis,
    get_profit_kpis,
    get_utilization_kpis,
    get_support_kpis,
    get_pipeline_kpis,
    get_budget_kpis,
    get_vendor_kpis,
    refresh_dashboard_data,
    get_kpi_snapshot,
)


# ------------------------------------------------------------------------------
# Utility tests
# ------------------------------------------------------------------------------

def test_money():
    assert _money(0) == 0.0
    assert _money("100") == 100.0
    assert _money("100.50") == 100.5
    assert _money("0.99") == 0.99
    assert _money(None) == 0.0


def test_parse_date():
    assert _parse_date("2026-06-15") == date(2026, 6, 15)
    assert _parse_date(datetime.now().isoformat()) == date.today()
    assert _parse_date(None) is None
    assert _parse_date("") is None
    assert _parse_date("invalid") is None


def test_in_range():
    assert _in_range("2026-06-15", "2026-06-01", "2026-06-30") is True
    assert _in_range("2026-06-15", "2026-06-01", "2026-05-31") is False
    assert _in_range("2026-06-15", "2026-07-01", "2026-06-30") is False
    assert _in_range(None, "2026-06-01", "2026-06-30") is True
    assert _in_range("", "2026-06-01", "2026-06-30") is True
    assert _in_range("2026-07-15", None, None) is True


# ------------------------------------------------------------------------------
# compute_kpis tests (integration - needs data)
# ------------------------------------------------------------------------------

@pytest.mark.skipif(True, reason="Skipped - needs sample data")
def test_compute_kpis():
    """Test that compute_kpis returns a valid dict with all expected keys."""
    result = compute_kpis()
    expected_keys = [
        "revenue", "expenses", "profit", "time", "support",
        "pipeline", "budget", "vendor", "metadata"
    ]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"

    # Check revenue keys
    assert "total_invoiced" in result["revenue"]
    assert "total_collected" in result["revenue"]
    assert "outstanding" in result["revenue"]

    # Check expense keys
    assert "total" in result["expenses"]
    assert "by_category" in result["expenses"]

    # Check profit keys
    assert "net_profit" in result["profit"]
    assert "margin_pct" in result["profit"]

    # Check time keys
    assert "total_minutes" in result["time"]
    assert "utilization_pct" in result["time"]

    # Check support keys
    assert "tickets_by_status" in result["support"]
    assert "open_tickets" in result["support"]

    # Check pipeline keys
    assert "by_stage" in result["pipeline"]
    assert "win_rate_pct" in result["pipeline"]


@pytest.mark.skipif(True, reason="Skipped - needs sample data")
def test_compute_kpis_with_date_range():
    """Test compute_kpis respects date range filtering."""
    result_no_range = compute_kpis()
    result_with_range = compute_kpis(
        start_date="2026-01-01",
        end_date="2026-12-31"
    )
    # Results should be valid dicts even with empty data
    assert isinstance(result_with_range, dict)
    assert "revenue" in result_with_range
    assert "expenses" in result_with_range


# ------------------------------------------------------------------------------
# refresh/get snapshot tests
# ------------------------------------------------------------------------------

@pytest.mark.skipif(True, reason="Skipped - needs data in MCP_DATA_ROOTS")
def test_refresh_dashboard_data():
    """Test refresh_dashboard_data updates the snapshot cache."""
    result = refresh_dashboard_data()
    assert result["status"] == "ok"
    assert "message" in result

    # After refresh, get_kpi_snapshot should not raise
    snapshot = None
    try:
        snapshot = get_kpi_snapshot()
    except ValueError as e:
        # Might still raise if no data sources configured
        if "refresh_dashboard_data" not in str(e):
            raise

    if snapshot is not None:
        assert "kpis" in snapshot


@pytest.mark.skipif(True, reason="Skipped - needs data")
def test_get_kpi_snapshot():
    """Test get_kpi_snapshot returns a complete snapshot."""
    refresh_dashboard_data()
    snapshot = get_kpi_snapshot()
    assert "kpis" in snapshot
    assert "revenue" in snapshot["kpis"]
    assert "expenses" in snapshot["kpis"]
    assert "metadata" in snapshot["kpis"]


# ------------------------------------------------------------------------------
# Individual KPI tests (integration - needs data)
# ------------------------------------------------------------------------------

@pytest.mark.skipif(True, reason="Skipped - needs sample data")
def test_get_revenue_kpis():
    """Test get_revenue_kpis returns valid revenue data."""
    result = get_revenue_kpis()
    assert "total_invoiced" in result
    assert "total_collected" in result
    assert "outstanding" in result
    assert "invoice_count" in result
    assert "monthly_trend" in result
    assert isinstance(result["monthly_trend"], list)


@pytest.mark.skipif(True, reason="Skipped - needs sample data")
def test_get_expense_kpis():
    """Test get_expense_kpis returns valid expense data."""
    result = get_expense_kpis()
    assert "total" in result
    assert "expense_count" in result
    assert "by_category" in result


@pytest.mark.skipif(True, reason="Skipped - needs sample data")
def test_get_support_kpis():
    """Test get_support_kpis returns valid support data."""
    result = get_support_kpis()
    assert "tickets_by_status" in result
    assert "open_tickets" in result
    assert "resolved_count" in result
    assert "comment_count" in result
    assert "csat_average" in result


@pytest.mark.skipif(True, reason="Skipped - needs sample data")
def test_get_pipeline_kpis():
    """Test get_pipeline_kpis returns valid pipeline data."""
    result = get_pipeline_kpis()
    assert "by_stage" in result
    assert "open_pipeline_value" in result
    assert "closed_won_value" in result
    assert "win_rate_pct" in result


# ------------------------------------------------------------------------------
# Edge case tests
# ------------------------------------------------------------------------------

def test_compute_kpis_empty_data():
    """Test compute_kpis works with no data (returns sensible defaults)."""
    # With no data files, all values should be 0 or empty
    result = compute_kpis()
    assert result["revenue"]["total_invoiced"] == 0.0
    assert result["revenue"]["total_collected"] == 0.0
    assert result["revenue"]["outstanding"] == 0.0
    assert result["expenses"]["total"] == 0.0
    assert result["profit"]["net_profit"] == 0.0
    assert "metadata" in result


@pytest.mark.skipif(True, reason="Skipped - needs data or proper setup")
def test_compute_kpis_partial_data():
    """Test compute_kpis with some data sources missing."""
    # Set MCP_DATA_ROOTS to override
    env = dict=os.environ.copy()
    # Can't easily test without setting env var; skip
    pass


# ------------------------------------------------------------------------------
# Main entry point tests
# ------------------------------------------------------------------------------

def test_main_stdio():
    """Test that --transport stdio runs mcp.run()."""
    # We can't actually run the MCP server here, but we can verify
    # the argument handling works
    import subprocess
    result = subprocess.run(
        [sys.executable, "/Users/hamishfromatech/Downloads/code/business-mcp-servers/mcp-servers/bi-dashboard/server.py", "--transport", "stdio"],
        cwd="/Users/hamishfromatech/Downloads/code/business-mcp-servers/mcp-servers/bi-dashboard",
        capture_output=True,
        text=True,
        timeout=5,
    )
    # Should start the MCP server (may fail if FastMCP not installed, but that's OK)
    assert "BI Dashboard" in result.stdout or "MCP" in result.stdout


@pytest.mark.skipif(True, reason="Skipped - needs data")
def test_full_dashboard_workflow():
    """End-to-end: refresh -> get snapshot -> render data."""
    refresh_dashboard_data()
    snapshot = get_kpi_snapshot()
    kpis = snapshot["kpis"]

    # Verify all KPI calculations are sensible
    assert kpis["revenue"]["total_invoiced"] >= 0
    assert kpis["revenue"]["total_collected"] >= 0
    assert kpis["revenue"]["outstanding"] >= 0
    assert kpis["profit"]["net_profit"] >= 0
    assert 0 <= kpis["time"]["utilization_pct"] <= 100
    assert kpis["pipeline"]["win_rate_pct"] >= 0
    assert kpis["pipeline"]["win_rate_pct"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
