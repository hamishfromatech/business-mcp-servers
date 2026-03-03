# Expense Tracker MCP Server

A FastMCP server for tracking expenses, budgets, and financial goals.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Category Management

| Tool | Description |
|------|-------------|
| `create_category` | Create a custom expense category |
| `list_categories` | List all expense categories |

### Expense Management

| Tool | Description |
|------|-------------|
| `add_expense` | Add a new expense |
| `get_expense` | Get an expense by ID |
| `update_expense` | Update an existing expense |
| `delete_expense` | Delete an expense |
| `get_expenses_by_date` | Get expenses within a date range |
| `get_expenses_by_category` | Get expenses by category |
| `get_total_expenses` | Get total expenses with breakdown |

### Budget Management

| Tool | Description |
|------|-------------|
| `create_budget` | Create a budget |
| `get_budget_status` | Get budget status (spent, remaining) |
| `list_budgets` | List all budgets |

## Default Categories

- `food` - Food and dining
- `transport` - Transportation
- `utilities` - Utilities
- `entertainment` - Entertainment
- `shopping` - Shopping
- `health` - Health and medical
- `education` - Education
- `other` - Miscellaneous

## Budget Periods

- `daily` - Daily budget
- `weekly` - Weekly budget
- `monthly` - Monthly budget
- `yearly` - Yearly budget

## Resources

| Resource | Description |
|----------|-------------|
| `expenses://summary` | Expense summary with totals by category |
| `expenses://recent` | Recent expenses |

## Example Usage

```python
# Add an expense
expense = add_expense(
    amount=25.50,
    category="food",
    description="Lunch at cafe",
    date="2024-01-15",
    tags=["lunch", "work"]
)

# Create a monthly budget
budget = create_budget(
    name="Food Budget",
    amount=500.00,
    category="food",
    period="monthly"
)

# Get expenses by date range
expenses = get_expenses_by_date(
    start_date="2024-01-01",
    end_date="2024-01-31"
)

# Check budget status
status = get_budget_status(budget["id"])
# Returns: spent, remaining, percent_used, status

# Get totals
total = get_total_expenses(
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

## Storage

This server uses in-memory storage. Data is not persisted between restarts.