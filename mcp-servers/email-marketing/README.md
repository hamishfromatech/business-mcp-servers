# Email Marketing Campaign Manager MCP Server

A FastMCP server for email marketing campaigns, template management, A/B testing, recipient lists, scheduling, and performance analytics.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## What It Does

- **Campaigns** — Draft, approved, scheduled, and sent campaigns
- **Templates** — Email template versions with HTML/text bodies
- **A/B Testing** — Compare variant performance (subject lines, content)
- **Recipient Lists** — Organize subscribers by category (customer, lead, subscriber)
- **Member Management** — Add/remove email addresses to lists
- **Scheduling** — Plan sends for a future date
- **Analytics** — Track opens, clicks, and conversions

## Available Tools

### Recipient Lists

| Tool | Description |
|------|-------------|
| `create_list` | Create a recipient list with a category |
| `get_list` / `list_lists` | Read lists, filter by category |
| `update_list` | Update list name, category, or description |
| `delete_list` | Delete a list and all its members |
| `add_member` | Add an email address to a list |
| `remove_member` | Remove a member by email address |
| `get_list_members` | List all members of a list |

### Campaigns

| Tool | Description |
|------|-------------|
| `create_campaign` | Create a new campaign |
| `get_campaign` / `list_campaigns` | Read campaigns, filter by status/category |
| `update_campaign` | Update campaign details |
| `delete_campaign` | Delete a campaign and its templates |

### Templates

| Tool | Description |
|------|-------------|
| `create_template` | Create a template version (A/B variants supported) |
| `update_template` | Update template content |
| `approve_template` | Mark a draft template as approved for sending |
| `list_templates` | List templates, filter by campaign |
| `copy_template` | Copy a template into a new version for another campaign |
| `compare_ab_test` | Compare A/B test results for a campaign |

### Sending

| Tool | Description |
|------|-------------|
| `send_campaign` | Send a campaign to all approved recipients |

## Workflow

1. **Create a campaign** with name, category, and send details
2. **Add recipients** to categorized lists
3. **Create template versions** — one per campaign iteration
4. **For A/B tests**: Create two template versions, mark both as `variant_a` and `variant_b`
5. **Approve** templates for sending
6. **Schedule** with a future `scheduled_for` date (optional)
7. **Send** — dispatches to all recipients, records analytics

## Data File

Data lives in `data/email-marketing.json` (override directory with `MCP_DATA_DIR`).

## Example Usage

```python
# Create a recipient list
newsletter = create_list(name="Newsletter Subscribers", category="newsletter")

# Add subscribers
add_member(newsletter.id, "alice@example.com")
add_member(newsletter.id, "bob@example.com")

# Create a campaign
campaign = create_campaign(
    campaign_name="Summer Sale Newsletter",
    category="promotional",
    from_name="Team Sales",
    from_email="sales@example.com",
    recipient_lists=[newsletter.id],
)

# Create A/B test variants
template_a = create_template(
    campaign_id=campaign.id,
    from_name="Team Sales",
    from_email="sales@example.com",
    subject_line="🎉 50% OFF Everything - Summer Sale!",
    body_html="<h1>Summer Sale!</h1><p>Get 50% off everything.</p>",
    body_text="Summer Sale! Get 50% off everything.",
    is_variant_a=True,
)

template_b = create_template(
    campaign_id=campaign.id,
    from_name="Team Sales",
    from_email="sales@example.com",
    subject_line="🔥 Half Off: Summer Sale Starts Now",
    body_html="<h1>Summer Sale</h1><p>50% off storewide.</p>",
    body_text="Summer Sale! 50% off storewide.",
    is_variant_b=True,
)

# Approve and send
approve_template(template_a.id)
approve_template(template_b.id)

result = send_campaign(campaign.id)
print(result)
# {
#   "status": "sent",
#   "campaign_id": 1,
#   "template_id": 2,
#   "split": {
#     "variant_a": {"recipients": 50, "opens": 5, "clicks": 2, "conversions": 1},
#     "variant_b": {"recipients": 50, "opens": 4, "clicks": 1, "conversions": 0},
#   },
#   "total_recipients": 100,
# }
```

## A/B Testing

A/B testing is built into the template system. Each template version can be marked as a variant:

- Set `is_variant_a=True` for the control variant
- Set `is_variant_b=True` for the test variant
- Both must be approved and both must have matching recipient lists
- When sending, recipients are split 50/50 and analytics are tracked per variant

## Categories

### Campaign Categories

- `newsletter` — Regular newsletter blasts
- `promotional` — Promotional offers and discounts
- `announcement` — Company announcements
- `transactional` — Order confirmations, receipts
- `educational` — Tutorials, how-to content
- `reengagement` — Win-back campaigns
- `abandoned_cart` — Cart abandonment reminders
- `welcome` — New subscriber onboarding
- `onboarding` — Onboarding sequences
- `birthday` — Birthday offers

### Recipient Categories

- `customer` — Existing paying customers
- `lead` — Potential customers not yet converted
- `subscriber` — Newsletters/updates
- `newsletter` — Newsletter subscribers
- `promotional` — Promotional email recipients
- `announcement` — Announcement-only recipients

## Storage

Data lives in `data/email-marketing.json` (override the directory with `MCP_DATA_DIR`).
Writes are atomic and thread-safe.

## Dependencies

- `fastmcp >= 3.0.0`
- `pydantic` (for model validation)
