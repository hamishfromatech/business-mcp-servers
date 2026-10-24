# Contract Manager MCP Server

A FastMCP server for contract lifecycle management — agreements, renewal notice
deadlines, expiry, and contractual obligations.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## What It Does

- **Contracts** — title, counterparty, type, value, term, owner, renewal terms
- **Expiry** — status is derived from `end_date` (expired automatically)
- **Renewal notices** — notice deadline = `end_date - notice_days`, with
  "notice passed" warnings for auto-renewing agreements
- **Obligations** — dated contractual duties (reports, audits, payments) with
  recurring schedules that roll forward when completed
- **Reporting** — portfolio stats, expiring contracts, renewal calendar

## Why It Matters

Auto-renewing contracts are the classic silent budget leak. This server makes
the **notice deadline** a first-class value so nothing renews by accident.

## Available Tools

### Contracts

| Tool | Description |
|------|-------------|
| `create_contract` | Create an agreement |
| `get_contract` / `list_contracts` | Read with derived status |
| `update_contract` | Update terms |
| `terminate_contract` | Terminate early with an optional reason |
| `delete_contract` | Delete with its obligations |

### Renewals & Expiry

| Tool | Description |
|------|-------------|
| `get_expiring_contracts` | Active contracts ending within N days |
| `get_renewal_calendar` | Renewable contracts ordered by notice deadline |

### Obligations

| Tool | Description |
|------|-------------|
| `add_obligation` | Add a dated obligation (optionally recurring) |
| `complete_obligation` | Complete it; recurring ones roll to the next date |
| `list_obligations` | List by contract or status |
| `get_overdue_obligations` | Pending and past due |
| `get_upcoming_obligations` | Pending and due within N days |

### Reporting

| Tool | Description |
|------|-------------|
| `get_contract_stats` | Counts, active value, obligation health |
| `flush_data` | Flush deferred writes |
| `backup_data` / `list_backups` / `restore_backup` | Data protection |

## Resources

| Resource | Description |
|----------|-------------|
| `contracts://expiring` | Contracts expiring in 30 days |
| `contracts://stats` | Portfolio statistics |

## Example Usage

```python
contract = create_contract(
    title="CRM subscription",
    counterparty="Acme SaaS",
    start_date="2026-01-01",
    end_date="2026-12-31",
    contract_type="service",
    value=12000,
    renewal_type="auto",
    notice_days=60,
)

add_obligation(contract.id, "Quarterly usage report", due_date="2026-03-31",
               recurring="quarterly")

get_expiring_contracts(90)
get_renewal_calendar()
```

## Storage

Data lives in `data/contracts.json` (override with `MCP_DATA_DIR`). Writes are
atomic, thread-safe, and support optional debouncing via
`MCP_WRITE_DEBOUNCE_MS`. Backups land in `data/backups/`.

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
