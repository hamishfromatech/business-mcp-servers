# CRM MCP Server

A FastMCP server for customer relationship management with leads, deals, and interactions.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Lead Management

| Tool | Description |
|------|-------------|
| `create_lead` | Create a new lead |
| `update_lead_status` | Update lead status (new, contacted, qualified, lost, converted) |
| `convert_lead_to_customer` | Convert a qualified lead to a customer |

### Deal Management

| Tool | Description |
|------|-------------|
| `create_deal` | Create a new deal |
| `update_deal_stage` | Update deal stage |
| `get_pipeline_summary` | Get sales pipeline summary |

### Customer Management

| Tool | Description |
|------|-------------|
| `create_customer` | Create a new customer |
| `get_customer` | Get customer by ID |

### Interaction Management

| Tool | Description |
|------|-------------|
| `log_interaction` | Log a customer interaction |
| `get_customer_interactions` | Get all interactions for a customer |

## Lead Statuses

- `new` - New lead
- `contacted` - Lead has been contacted
- `qualified` - Lead is qualified
- `lost` - Lead was lost
- `converted` - Lead converted to customer

## Deal Stages

- `prospecting` - Initial prospecting
- `qualification` - Qualifying the deal
- `proposal` - Proposal sent
- `negotiation` - In negotiation
- `closed_won` - Deal closed successfully
- `closed_lost` - Deal was lost

## Resources

| Resource | Description |
|----------|-------------|
| `crm://pipeline` | Sales pipeline summary by stage |
| `crm://leads` | All leads formatted as markdown |

## Example Usage

```python
# Create a lead
lead = create_lead(
    name="Jane Smith",
    email="jane@company.com",
    company="Tech Inc",
    source="website"
)

# Create a deal
deal = create_deal(
    title="Enterprise License",
    customer_id=1,
    value=50000,
    stage="prospecting"
)

# Log an interaction
log_interaction(
    customer_id=1,
    interaction_type="call",
    summary="Discussed pricing options"
)

# Get pipeline summary
summary = get_pipeline_summary()
```

## Storage

This server uses in-memory storage. Data is not persisted between restarts.