# Support Desk MCP Server

A FastMCP server for support tickets, priorities, SLA deadlines, escalations,
resolutions, and customer satisfaction.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## What It Does

- **Tickets** — subject, description, requester, category, tags
- **SLA tracking** — deadlines by priority, on-track / at-risk / breached / met
- **Workflow** — open → in progress → waiting → resolved → closed (and reopen)
- **Comments** — public replies and internal notes; first public reply records
  first-response time
- **CSAT** — 1–5 ratings with comments
- **Reporting** — volumes, average response/resolution time, SLA compliance,
  CSAT average

## SLA Policy

| Priority | Target |
|----------|--------|
| urgent | 4 hours |
| high | 8 hours |
| medium | 24 hours |
| low | 72 hours |

A per-ticket `sla_hours` override is supported at creation time. Changing a
ticket's priority recalculates its deadline from the original creation time.

## Available Tools

### Tickets

| Tool | Description |
|------|-------------|
| `create_ticket` | Open a ticket and start its SLA clock |
| `get_ticket` / `list_tickets` | Read tickets with filters |
| `search_tickets` | Search subject, description, requester, tags |
| `update_ticket` | Update fields; priority change recalculates SLA |
| `assign_ticket` | Assign an agent (moves open → in_progress) |
| `delete_ticket` | Delete a ticket with its comments and CSAT |

### Comments

| Tool | Description |
|------|-------------|
| `add_comment` | Add a public reply or internal note |
| `list_comments` | List comments on a ticket |

### Lifecycle

| Tool | Description |
|------|-------------|
| `resolve_ticket` | Resolve and record the resolution |
| `close_ticket` | Close a ticket |
| `reopen_ticket` | Reopen a resolved/closed ticket |

### CSAT & Reporting

| Tool | Description |
|------|-------------|
| `submit_csat` | Record a 1–5 customer rating |
| `get_sla_status` | On track / at risk / breached / met for one ticket |
| `get_overdue_tickets` | Open tickets past their SLA |
| `get_support_stats` | Volumes, response/resolution time, SLA, CSAT |

## Resources

| Resource | Description |
|----------|-------------|
| `support://queue` | Current open queue with SLA state |
| `support://sla` | SLA policy |

## Example Usage

```python
ticket = create_ticket(
    subject="Checkout failing",
    description="Payment step returns 500",
    requester_name="Alice",
    requester_email="alice@acme.com",
    priority="urgent",
)

assign_ticket(ticket.id, "Hamish")
add_comment(ticket.id, "Hamish", "Looking into the payment gateway logs")
resolve_ticket(ticket.id, "Fixed a bad API key on the gateway")
submit_csat(ticket.id, 5, "Fast turnaround")

get_support_stats()
```

## Storage

Data lives in `data/support.json` (override with `MCP_DATA_DIR`). Writes are
atomic and thread-safe.

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
