# Business Search MCP Server

A cross-server search hub. It indexes the JSON data files of the other business
MCP servers in this repository — CRM leads, invoices, support tickets, notes,
OKRs, kanban tasks — and answers one query across all of them.

This is the server that turns the suite's separate data silos into a single
searchable business brain.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## Where It Looks

By default it scans the parent `mcp-servers/` directory for:

- `<server>/data/*.json`
- `<server>/kanban_data.json`
- `*_data.json`

Override with `MCP_DATA_ROOTS` (paths separated by `os.pathsep`, i.e. `:` on
macOS/Linux and `;` on Windows):

```bash
MCP_DATA_ROOTS=/srv/mcp-data:/backup/mcp-data python server.py
```

## How Records Are Found

The indexer walks each JSON document and extracts any dict containing an `id`.
Collections become an *entity type* from their key path:

| Data | Entity type |
|------|-------------|
| `{"leads": {"1": {...}}}` | `leads` |
| `{"invoices": {"1": {...}}}` | `invoices` |
| `{"boards": {"1": {..., "tasks": [{"id": 9}]}}}` | `boards` and `boards.tasks` |

Nested records are indexed separately and excluded from the parent's text, so a
task is found once — not through its board as well.

## Performance

The index is **incremental**: each file's mtime and size are cached, and only
changed files are re-parsed. Searches reuse the cached flattened text, so
repeated queries do not re-read the disk.

## Available Tools

| Tool | Description |
|------|-------------|
| `search_business` | Search across all sources; filter by entity type or source |
| `list_data_sources` | Every indexed file with record counts |
| `get_index_stats` | Totals by source and entity type |
| `rebuild_index` | Force a full re-index |
| `get_record` | Fetch one record by source, entity type, and id |

## Resources

| Resource | Description |
|----------|-------------|
| `business://sources` | Indexed data sources |
| `business://stats` | Index statistics |

## Example Usage

```python
# Everything mentioning Acme across CRM, invoices, support, and kanban
search_business("acme")

# Only overdue invoices
search_business("overdue", entity_type="invoices")

# Everything from the support desk
search_business("payment", source="support-desk")

# Drill into a result
get_record("crm", "leads", 1)
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/
```

The tests build a temporary multi-server data layout and set `MCP_DATA_ROOTS`
to it, so they never touch real data.

---

## Feedback & Community

Found this MCP server genuinely useful? I'd love to hear from you.

- **Email**: [hamish@atech.industries](mailto:hamish@atech.industries)
- **Join our free Open Source AI Builders Club on Skool**: [https://www.skool.com/open-source-ai-builders-club/about?ref=da946a67c5c646e991b96ea9ce7ad9e4](https://www.skool.com/open-source-ai-builders-club/about?ref=da946a67c5c646e991b96ea9ce7ad9e4)
