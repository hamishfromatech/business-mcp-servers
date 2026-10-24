# Vendor Manager MCP Server

A FastMCP server for procurement — suppliers, purchase orders, lead times,
spend, and vendor performance scorecards.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## What It Does

- **Vendors** — contacts, category, payment terms, lead time, status, rating
- **Purchase orders** — line items, totals, expected delivery from lead time,
  draft → ordered → received (or cancelled)
- **Scorecards** — review scores for delivery, quality, communication, pricing
- **On-time rate** — compares `received_at` against `expected_at` per order
- **Spend** — by vendor and date range, with cancelled orders excluded

## Available Tools

### Vendors

| Tool | Description |
|------|-------------|
| `create_vendor` | Create a supplier |
| `get_vendor` / `list_vendors` | Read with filters |
| `update_vendor` | Update details or status |
| `delete_vendor` | Delete (blocked while orders reference it) |

### Purchase Orders

| Tool | Description |
|------|-------------|
| `create_purchase_order` | Create a PO (ordered or draft) |
| `get_purchase_order` / `list_purchase_orders` | Read |
| `place_order` | Draft → ordered |
| `receive_order` | Mark received (records delivery time) |
| `cancel_order` | Cancel a non-received order |

### Performance

| Tool | Description |
|------|-------------|
| `add_vendor_review` | Review on-time delivery, quality, communication, pricing (1–5) |
| `list_vendor_reviews` | Review history |
| `get_vendor_scorecard` | Ratings, order volume, spend, late deliveries, on-time rate |
| `get_low_rated_vendors` | Vendors below a rating threshold |

### Reporting

| Tool | Description |
|------|-------------|
| `get_vendor_spend` | Spend by vendor for a date range |
| `get_vendor_stats` | Vendor and PO counts, total spend |
| `flush_data` | Flush deferred writes |
| `backup_data` / `list_backups` / `restore_backup` | Data protection |

## Resources

| Resource | Description |
|----------|-------------|
| `vendors://scorecards` | All vendor scorecards |
| `vendors://stats` | Procurement statistics |

## Example Usage

```python
vendor = create_vendor("Acme Parts", category="components", lead_time_days=14,
                       payment_terms_days=30)

po = create_purchase_order(vendor.id, [
    {"description": "Bolt M8", "quantity": 500, "unit_price": 0.45},
    {"description": "Nut M8", "quantity": 500, "unit_price": 0.20},
])
# total = 325.00, expected_at = today + 14 days

receive_order(po.id)

add_vendor_review(vendor.id, on_time_delivery=4, quality=5,
                  communication=4, pricing=3, comment="Solid, slightly pricey")

get_vendor_scorecard(vendor.id)
get_vendor_spend()
```

## Storage

Data lives in `data/vendors.json` (override with `MCP_DATA_DIR`). Writes are
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
