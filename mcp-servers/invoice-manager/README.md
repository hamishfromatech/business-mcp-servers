# Invoice Manager MCP Server

A FastMCP server for clients, invoices, payments, recurring billing, and
accounts-receivable aging — the cash-flow backbone of a small business.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## What It Does

- **Clients** — billing details, currency, tax id
- **Invoices** — line items, tax, discounts, draft/sent/paid/overdue states
- **Payments** — partial and full payments with automatic balance tracking
- **Recurring billing** — templates that generate invoices on a schedule
- **A/R aging** — current / 1–30 / 31–60 / 61–90 / 90+ day buckets
- **Revenue reporting** — invoiced vs collected vs outstanding

## Available Tools

### Clients

| Tool | Description |
|------|-------------|
| `create_client` | Create a billing client |
| `get_client` / `list_clients` | Read clients |
| `update_client` | Update client details |
| `delete_client` | Delete (blocked while invoices reference it) |

### Invoices

| Tool | Description |
|------|-------------|
| `create_invoice` | Create an invoice from line items |
| `get_invoice` / `list_invoices` | Read invoices with live balances |
| `update_invoice` | Edit an unpaid invoice and recalculate totals |
| `send_invoice` | Move a draft to sent |
| `void_invoice` | Void (kept for audit, excluded from aging) |
| `delete_invoice` | Delete an invoice and its payments |

### Payments

| Tool | Description |
|------|-------------|
| `record_payment` | Record a partial or full payment |
| `list_payments` | List payments for an invoice |

### Recurring Billing

| Tool | Description |
|------|-------------|
| `create_recurring_invoice` | Create a monthly/quarterly/yearly template |
| `list_recurring_invoices` | List templates |
| `set_recurring_active` | Pause or resume a template |
| `generate_due_invoices` | Materialise every invoice that is due |

### Reporting

| Tool | Description |
|------|-------------|
| `get_aging_report` | A/R buckets and per-invoice overdue detail |
| `get_revenue_summary` | Invoiced / collected / outstanding for a range |
| `get_invoice_stats` | Counts and status breakdown |

## Resources

| Resource | Description |
|----------|-------------|
| `invoices://aging` | Aging report as text |
| `invoices://summary` | Revenue summary as text |

## Example Usage

```python
client = create_client(name="Acme Pty Ltd", email="ap@acme.com", currency="AUD")

invoice = create_invoice(
    client_id=client.id,
    line_items=[
        {"description": "Consulting", "quantity": 10, "unit_price": 150},
        {"description": "Hosting", "quantity": 1, "unit_price": 49},
    ],
    tax_rate=10,
    discount=100,
    send=True,
)

record_payment(invoice.id, amount=500)
get_aging_report()
```

## Storage

Data lives in `data/invoices.json` (override the directory with `MCP_DATA_DIR`).
Writes are atomic and thread-safe.

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
