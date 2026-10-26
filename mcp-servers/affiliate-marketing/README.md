# Affiliate Marketing Tracker

A FastMCP server for tracking affiliate marketing performance across networks, affiliates, tracking links, clicks, conversions, commissions, and payouts.

## Overview

This server provides comprehensive affiliate marketing tracking with:

- **Affiliate Networks** - Manage your affiliate marketing networks (Amazon Associates, ShareASale, CJ Affiliate, etc.)
- **Affiliates** - Track publisher accounts with status, join method, and profile data
- **Tracking Links** - Create and monitor affiliate links with click and conversion metrics
- **Click Tracking** - Record impressions, clicks, and traffic sources per link
- **Conversion Tracking** - Track conversions, revenue, coupons, and pricing
- **Commissions** - Manage commission rates, tiers, and earned commission records
- **Payouts** - Track payout requests, payment methods, and payment status

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
cd mcp-servers/affiliate-marketing
python server.py
```

Or with FastMCP CLI:
```bash
fastmcp run server.py
```

## Data Persistence

The server stores all data in a single JSON file: `data/affiliate_marketing.json`

```
affiliate-marketing/
├── server.py
├── requirements.txt
├── requirements-dev.txt
└── data/
    └── affiliate_marketing.json   # All data persisted here
```

## Available Tools

### Affiliate Networks

| Tool | Description |
|------|-------------|
| `create_affiliate_network` | Create a new affiliate network |
| `get_affiliate_network` | Get a network by ID |
| `list_affiliate_networks` | List networks (filter by availability) |
| `update_affiliate_network` | Update a network's fields |

### Affiliates

| Tool | Description |
|------|-------------|
| `create_affiliate` | Create a new affiliate/publisher |
| `get_affiliate` | Get an affiliate by ID |
| `list_affiliates` | List affiliates (filter by status/search) |
| `update_affiliate` | Update an affiliate's fields |
| `delete_affiliate` | Delete an affiliate |

### Tracking Links

| Tool | Description |
|------|-------------|
| `create_tracking_link` | Create a tracking link for an affiliate |
| `get_tracking_link` | Get a tracking link by ID |
| `list_tracking_links` | List links (filter by affiliate/network) |
| `update_tracking_link` | Update a tracking link's fields |

### Click Tracking

| Tool | Description |
|------|-------------|
| `record_click` | Record a click event on a tracking link |
| `record_impression` | Record an impression event |
| `get_click_log` | Get click log with filters |

### Conversion Tracking

| Tool | Description |
|------|-------------|
| `record_conversion` | Record a conversion event with revenue |
| `get_conversion_log` | Get conversion log with filters |

### Commissions

| Tool | Description |
|------|-------------|
| `create_commission` | Create a commission rate/record |
| `get_commission` | Get a commission by ID |
| `list_commissions` | List commissions (filter by affiliate/link/status) |
| `update_commission` | Update a commission record |

### Payouts

| Tool | Description |
|------|-------------|
| `create_payout` | Create a payout request |
| `get_payout` | Get a payout by ID |
| `list_payouts` | List payouts (filter by affiliate/date) |
| `process_payout` | Update payout status and process |

### Backup / Restore

| Tool | Description |
|------|-------------|
| `flush_data` | Flush deferred writes to disk |
| `backup_data` | Create a timestamped backup |
| `list_backups` | List available backups |
| `restore_backup` | Restore from a backup file |

### Performance Analytics

| Tool | Description |
|------|-------------|
| `get_network_summary` | Summary of networks and their affiliates |
| `get_affiliate_performance` | Full performance metrics for an affiliate |
| `get_click_rate` | CTR, CPC, conversion rate for a link |
| `get_commission_summary` | Total commissions, payouts, fees, net earnings |

## Data Models

### AffiliateNetwork
```python
{
    "id": 1,
    "name": "Amazon Associates",
    "slug": "amazon-associates",
    "currency": "USD",
    "available": true,
    "nexus_url": "https://affiliate-program.amazon.com/",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
}
```

### Affiliate
```python
{
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "status": "active",
    "join_method": "user",
    "joined_at": "2025-01-01T00:00:00Z",
    "profile_url": "https://...",
    "bio": "Short bio",
    "location": "San Francisco, CA",
    "created_at": "...",
    "updated_at": "..."
}
```

### TrackingLink
```python
{
    "id": 1,
    "affiliate_id": 123,
    "network_id": 1,
    "product_category": "electronics",
    "product": "acme-laptop-2025",
    "tracking_id": "tech-term-001",
    "slug": "affiliate-laptop-link",
    "name": "Acme Laptop Deal",
    "clickable_url": "https://yoursite.com/affiliate-laptop-link",
    "seal_image": "https://...",
    "clicks": 150,
    "impressions": 1000,
    "link_clicks": 50,
    "add_to_carts": 25,
    "purchases": 10,
    "commission_rate_pct": 5.0,
    "lifetime_commission": 250.00,
    "payout_override_pct": 3.0,
    "created_at": "...",
    "updated_at": "..."
}
```

### Commission
```python
{
    "id": 1,
    "affiliate_id": 123,
    "link_id": 456,
    "type": "standard",
    "padded_with": "commission",
    "rate_pct": 5.0,
    "currency": "USD",
    "period_days": 30,
    "effective_from": "2025-01-01",
    "effective_until": "2025-03-01",
    "payout_type": "customers",
    "lower_commission_pct": 2.5,
    "earned_commission": 125.50,
    "earned_date": "2025-01-15",
    "status": "active",
    "created_at": "...",
    "updated_at": "..."
}
```

### Payout
```python
{
    "id": 1,
    "affiliate_id": 123,
    "commission_id": 456,
    "amount": 125.50,
    "currency": "USD",
    "payout_type": "customers",
    "payout_status": "paid",
    "payout_method": "paypal",
    "fees": 2.51,
    "payment_date": "2025-01-15",
    "invoice_number": "INV-001",
    "stripe_payment_intent_id": "pi_12345",
    "created_at": "...",
    "updated_at": "..."
}
```

## Tool Parameters

### add_contact → create_affiliate
```python
create_affiliate(
    name: str,                          # Required: Affiliate's name
    email: str,                         # Required: Email
    status: str = "pending",            # pending | active | suspended | inactive
    join_method: str = None,            # "user" | "seed"
    joined_at: str = None,
    profile_url: str = None,
    bio: str = None,
    location: str = None
)
```

### add_contact → create_tracking_link
```python
create_tracking_link(
    affiliate_id: int,                   # Required: Owner affiliate
    name: str,                           # Required: Link name
    slug: str,                           # Required: URL slug
    network_id: int = None,             # Optional: Network ID
    product_category: str = None,
    product: str = None,
    tracking_id: str = None,            # Custom tracking ID
    seal_image: str = None,
    commission_rate_pct: float = 10.0,
    payout_override_pct: float = None
)
```

### record_click
```python
record_click(
    link_id: int,                        # Required: The link ID
    ip_address: str = None,
    user_agent: str = None,
    source: str = None,                   # e.g., "google", "facebook"
    medium: str = None,                   # e.g., "cpc", "organic"
    campaign: str = None,
    referred_from: str = None            # Referrer URL
)
```

### record_conversion
```python
record_conversion(
    link_id: int,                        # Required: The link ID
    conversion_type: str,                 # e.g., "purchase", "lead", "signup"
    revenue: float = 0.0,                 # Revenue amount
    currency: str = "USD",
    quantity: int = 1,
    price: float = 0.0,
    product: str = None,
    ip_address: str = None,
    user_agent: str = None,
    source: str = None,
    coupon: str = None                   # Used coupon code
)
```

## Example Usage

### Create a network and affiliate

```python
# Create Amazon Associates network
network = create_affiliate_network(
    name="Amazon Associates",
    slug="amazon-associates",
    currency="USD",
    available=True,
    nexus_url="https://affiliate-program.amazon.com/"
)

# Create an affiliate
affiliate = create_affiliate(
    name="John Doe",
    email="john@example.com",
    status="active",
    join_method="user",
    location="San Francisco, CA"
)
```

### Create a tracking link

```python
link = create_tracking_link(
    affiliate_id=affiliate.id,
    name="Acme Laptop Deal",
    slug="acme-laptop-2025",
    network_id=network.id,
    product_category="electronics",
    product="acme-laptop-2025",
    commission_rate_pct=5.0
)
```

### Record a click and conversion

```python
# Record a click
click = record_click(
    link_id=link.id,
    source="google",
    medium="cpc",
    campaign="winter-sale"
)

# Record a conversion
conv = record_conversion(
    link_id=link.id,
    conversion_type="purchase",
    revenue=999.00,
    currency="USD",
    quantity=1,
    price=999.00,
    product="acme-laptop-2025"
)
```

### Create a payout

```python
payout = create_payout(
    affiliate_id=affiliate.id,
    amount=499.50,
    currency="USD",
    payout_status="pending",
    payout_method="paypal",
    invoice_number="INV-001"
)

# Process the payout
processed = process_payout(
    payout_id=payout.id,
    payout_status="paid",
    payment_date="2025-01-15"
)
```

### Get performance metrics

```python
performance = get_affiliate_performance(affiliate_id=affiliate.id)
print(f"Total clicks: {performance['total_clicks']:,}")
print(f"Total revenue: ${performance['total_revenue']:,.2f}")
print(f"Payouts: ${performance['total_payouts']:,.2f}")

click_rate = get_click_rate(link_id=link.id)
print(f"CTR: {click_rate['ctr']}%")
print(f"Conversion Rate: {click_rate['conversion_rate']}%")
```

## Resource Endpoints

| Resource | Description |
|----------|-------------|
| `affiliates://all` | All affiliates as a markdown list |
| `links://all` | All tracking links with stats |
| `performance://summary` | Overall performance summary |

## Stripe Integration

The server supports Stripe payment intents for payouts:

- `stripe_payment_intent_id`: Store the Stripe payment intent ID for a payout
- `payout_method`: Set to `"stripe"` for Stripe-based payouts
- `fees`: Processing fees are tracked separately

## Configuration

### MCP Desktop / Claude Code

Add to your `claude_desktop_config.json` or `.claude/settings.json`:

```json
{
  "mcpServers": {
    "affiliate-marketing": {
      "command": "python",
      "args": ["./mcp-servers/affiliate-marketing/server.py"]
    }
  }
}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MCP_DATA_DIR` | Alternate data directory (default: server's `data/` folder) |
| `MCP_WRITE_DEBOUNCE_MS` | Write debounce delay in milliseconds (default: 0 = immediate) |

## Backup & Restore

```bash
# Backup data
python -c "import sys; sys.path.insert(0, '.'); from server import backup_data; print(backup_data())"

# Restore
python -c "import sys; sys.path.insert(0, '.'); from server import restore_backup; print(restore_backup('backup-20250101-120000.json'))"
```

## Troubleshooting

**Server won't start:**
```bash
pip install fastmcp
python server.py
```

**Data not persisting:**
- Check the server has write permissions to its `data/` directory
- Check the `MCP_DATA_DIR` environment variable if using a custom path

## See Also

- [README.md](../../README.md) - Main repo README
- [contact-book](../../contact-book/) - Simple contact management reference
- [tech-debt-tracker](../../tech-debt-tracker/) - Advanced tracking patterns reference

---

Created by **hamishfromatech** - [YouTube](https://youtube.com/@hamishfromatech)
