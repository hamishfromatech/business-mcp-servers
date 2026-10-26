# Business Intelligence Dashboard MCP Server

A FastMCP server that provides a comprehensive Business Intelligence dashboard with
cross-server KPI aggregation, real-time analytics, dashboard visualizations, and
report generation — aggregating data from all business MCP servers into a single
source of truth.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## What It Does

The BI Dashboard is a read-only analytics Hub that sits on top of the business
MCP servers (invoice-manager, expense-tracker, time-tracker, crm, support-desk,
project-budget-tracker, vendor-manager) and provides:

- **Cross-server KPI aggregation** — discovers and reads JSON data from sibling
  servers, computing unified KPIs across revenue, expenses, time, pipeline,
  support, and budgets.
- **Dashboard visualizations** — built-in web dashboard with interactive charts
  (Chart.js) for revenue trends, expense breakdowns, pipeline stages, and
  utilization metrics, accessible at `http://localhost:8080/dashboard`.
- **Real-time analytics** — cached snapshots with `refresh_dashboard_data()` to
  recompute everything, plus `get_kpi_snapshot()` for immediate access.
- **Report generation** — export KPI snapshots and analytics as PDF, CSV, or
  Excel via the `generate_report()` tool.

## Available Tools

### Dashboard Management

| Tool | Description |
|------|-------------|
| `create_dashboard` | Create a new dashboard with custom KPI widgets |
| `list_dashboards` | List all dashboards |
| `get_dashboard` | Get dashboard configuration |
| `delete_dashboard` | Delete a dashboard |

### Data Refresh

| Tool | Description |
|------|-------------|
| `refresh_dashboard_data` | Refresh all cached KPI snapshots |
| `get_kpi_snapshot` | Get current cached KPI snapshot |

### KPI Analytics

| Tool | Description |
|------|-------------|
| `get_revenue_kpis` | Revenue KPIs: invoiced, collected, outstanding |
| `get_expense_kpis` | Expense KPIs: total, by category |
| `get_profit_kpis` | Net profit, margin, revenue-efficiency |
| `get_utilization_kpis` | Time utilization, billable %, billable revenue |
| `get_support_kpis` | Support health: ticket status, resolution time, CSAT |
| `get_pipeline_kpis` | Pipeline value by stage, win/loss rates |
| `get_budget_kpis` | Budget vs. actual spend |
| `get_vendor_kpis` | Spend by vendor, lead-time, scorecards |

### Reports

| Tool | Description |
|------|-------------|
| `generate_report` | Generate report: PDF, CSV, Excel |
| `export_data` | Export raw data in specified format |

## Resources

| Resource | Description |
|----------|-------------|
| `bi://kpi-snapshot` | Complete KPI snapshot snapshot |
| `bi://revenue-overview` | Revenue overview as text |
| `bi://expense-overview` | Expense overview as text |
| `bi://profit-overview` | Profit overview as text |
| `bi://utilization-overview` | Time utilization as text |
| `bi://support-overview` | Support overview as text |
| `bi://pipeline-overview` | Pipeline overview as text |
| `bi://budget-overview` | Budget overview as text |
| `bi://vendor-overview` | Vendor overview as text |

## Dashboard Widgets

The built-in web dashboard shows these interactive charts:

### KPI Cards
- **Total Revenue** — Invoiced, Collected, Outstanding
- **Total Expenses** — Total, Top categories
- **Net Profit** — Profit, Margin %, Efficiency
- **Time Utilization** — Total hours, Billable %, Billable revenue
- **Support Health** — Status breakdown, resolution time, CSAT
- **Pipeline Value** — Stage distribution, open value

### Interactive Charts
- Revenue Trend (line chart) — monthly revenue vs expenses vs net
- Expense Breakdown (donut chart) — by category
- Pipeline Chart (pie chart) — by stage
- Time Allocation (bar chart) — by project
- Vendor Spend (bar chart) — top vendors

## Example Usage

```python
# Refresh data and get a snapshot
refresh_dashboard_data()
snapshot = get_kpi_snapshot()

# Get individual KPIs
revenue = get_revenue_kpis(start_date="2026-01-01", end_date="2026-06-30")
expenses = get_expense_kpis(start_date="2026-01-01", end_date="2026-06-30")
utilization = get_utilization_kpis(start_date="2026-01-01", end_date="2026-06-30")
pipeline = get_pipeline_kpis()

# Generate reports
generate_report(preset="executive_summary", format="pdf", start_date="2026-01-01", end_date="2026-06-30")
export_data(dataset="all_kpis", format="csv")
```

## Data Sources

Reads sibling server data via `MCP_DATA_ROOTS` (default: repo `mcp-servers/`
directory). Override for tests or custom deployments:

```bash
MCP_DATA_ROOTS=/srv/mcp-data python server.py
```

## Running with Web UI

```bash
python server.py --transport http --port 8000
```

This starts:
- MCP server on port 8000
- Web dashboard UI on port 8080 → `http://127.0.0.1:8080/dashboard`

## Storage / Data Sources

Reads sibling server data. Stores dashboard configs in `data/dashboards.json`:

```
bi-dashboard/
├── data/
│   └── dashboards.json        # Dashboard configurations
├── data/
│   └── snapshots.json         # Cached KPI snapshots
```

## Backup / Reset

```bash
# Backup
cp -r bi-dashboard/data/ backup/bi-dashboard/

# Reset the data
rm bi-dashboard/data/*.json
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/
```

---

## Feedback & Community

Found this MCP server genuinely useful? I'd love to hear from you.

- **Email**: [hamish@atech.industries](mailto:hamish@atech.industries)
- **Join our free Open Source AI Builders Club on Skool**: [https://www.skool.com/open-source-ai-builders-club/about?ref=da946a67c5c646e991b96ea9ce7ad9e4](https://www.skool.com/open-source-ai-builders-club/about?ref=da946a67c5c646e991b96ea9ce7ad9e4)
