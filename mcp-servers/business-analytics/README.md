# Business Analytics MCP Server

A FastMCP server that aggregates cross-server business KPIs from the JSON data
files used by the other business MCP servers (invoices, expenses, time, support,
CRM).

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## What It Does

A read-only aggregation layer. It does not own a data file of its own — it
computes reports from the sibling servers' data:

- **Data sources** — discovers the JSON data files the other business MCP
  servers keep (invoices, expenses, time, support, CRM).
- **Financial overview** — revenue (invoiced / collected / outstanding) vs
  expenses (total + by category) vs net profit.
- **Revenue report** — monthly revenue vs expense vs net trend.
- **Expense breakdown** — expenses grouped by category.
- **Time summary** — logged time: total, billable, billable revenue, utilization.
- **Support stats** — ticket status mix, resolution times, SLA compliance, CSAT.
- **Pipeline summary** — CRM deal pipeline: open value, won and lost totals.

## Available Tools

| Tool | Description |
|------|-------------|
| `list_data_sources` | List sibling data files this hub can read |
| `get_financial_overview` | Revenue vs expenses vs net profit |
| `get_revenue_report` | Monthly revenue / expense / net trend |
| `get_expense_breakdown` | Expenses by category |
| `get_time_summary` | Time logged, billable revenue, utilization |
| `get_support_stats` | Support ticket health, SLA, CSAT |
| `get_pipeline_summary` | CRM pipeline value, won/lost |

## Resources

| Resource | Description |
|----------|-------------|
| `analytics://sources` | Indexed data sources as text |
| `analytics://financial-overview` | Financial overview as text |

## Example Usage

```python
get_financial_overview(start_date="2026-09-01", end_date="2026-09-30")
get_revenue_report(start_date="2026-09-01", end_date="2026-09-30")
get_expense_breakdown()
get_time_summary()
get_support_stats()
get_pipeline_summary()
```

## Storage / Data Sources

Reads sibling server data via `MCP_DATA_ROOTS` (os.pathsep-separated roots,
default: the repository's `mcp-servers/` directory). Override for tests or
custom deployments:

```bash
MCP_DATA_ROOTS=/srv/mcp-data:/backup/mcp-data python server.py
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
