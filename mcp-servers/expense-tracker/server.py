"""
Expense Tracker MCP Server
A FastMCP server for tracking expenses, budgets, and financial goals.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json
from enum import Enum
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Expense Tracker",
    instructions="An expense tracking server for managing expenses, budgets, and financial insights."
)


class ExpenseCategory(str, Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    UTILITIES = "utilities"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    HEALTH = "health"
    EDUCATION = "education"
    OTHER = "other"


class Expense(BaseModel):
    """An expense entry."""
    id: int
    amount: float
    category: str
    description: str
    date: str
    tags: list[str] = []
    created_at: str


class Budget(BaseModel):
    """A budget entry."""
    id: int
    name: str
    amount: float
    category: Optional[str] = None
    period: str
    start_date: str
    created_at: str


class Category(BaseModel):
    """An expense category."""
    id: int
    name: str
    icon: Optional[str] = None
    created_at: str

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "expenses.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "expenses": {}, "budgets": {}, "categories": {},
        "next_expense_id": 1, "next_budget_id": 1, "next_category_id": 1
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
expenses: dict[int, dict] = {int(k): v for k, v in _data.get("expenses", {}).items()}
budgets: dict[int, dict] = {int(k): v for k, v in _data.get("budgets", {}).items()}
categories: dict[int, dict] = {int(k): v for k, v in _data.get("categories", {}).items()}

_next_expense_id = _data.get("next_expense_id", 1)
_next_budget_id = _data.get("next_budget_id", 1)
_next_category_id = _data.get("next_category_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "expenses": expenses, "budgets": budgets, "categories": categories,
        "next_expense_id": _next_expense_id, "next_budget_id": _next_budget_id,
        "next_category_id": _next_category_id
    })


def _get_next_expense_id() -> int:
    global _next_expense_id
    id_ = _next_expense_id
    _next_expense_id += 1
    return id_


def _get_next_budget_id() -> int:
    global _next_budget_id
    id_ = _next_budget_id
    _next_budget_id += 1
    return id_


def _get_next_category_id() -> int:
    global _next_category_id
    id_ = _next_category_id
    _next_category_id += 1
    return id_


# Category Management
@mcp.tool
def create_category(name: str, icon: Optional[str] = None) -> Category:
    """Create a custom expense category.

    Args:
        name: Category name
        icon: Optional emoji or icon identifier

    Returns:
        The created category
    """
    category_id = _get_next_category_id()
    category = Category(
        id=category_id,
        name=name,
        icon=icon,
        created_at=datetime.now().isoformat()
    )
    categories[category_id] = category.model_dump()
    _save()
    return category


@mcp.tool
def list_categories() -> list[dict]:
    """List all expense categories.

    Returns:
        List of categories
    """
    default_cats = [{"name": c.value, "icon": None} for c in ExpenseCategory]
    custom_cats = [Category(**c).model_dump() for c in categories.values()]
    return default_cats + custom_cats


# Expense Management
@mcp.tool
def add_expense(
    amount: float,
    category: str,
    description: str,
    date: Optional[str] = None,
    tags: Optional[list[str]] = None
) -> Expense:
    """Add a new expense.

    Args:
        amount: Expense amount in dollars
        category: Expense category (food, transport, utilities, etc.)
        description: Description of the expense
        date: Date of expense (YYYY-MM-DD), defaults to today
        tags: Optional tags for the expense

    Returns:
        The created expense
    """
    expense_id = _get_next_expense_id()
    expense = Expense(
        id=expense_id,
        amount=amount,
        category=category.lower(),
        description=description,
        date=date or datetime.now().strftime("%Y-%m-%d"),
        tags=tags or [],
        created_at=datetime.now().isoformat()
    )
    expenses[expense_id] = expense.model_dump()
    _save()
    return expense


@mcp.tool
def get_expense(expense_id: int) -> Optional[Expense]:
    """Get an expense by ID.

    Args:
        expense_id: The expense ID

    Returns:
        Expense details or None
    """
    data = expenses.get(expense_id)
    if data is None:
        return None
    return Expense(**data)


@mcp.tool
def update_expense(
    expense_id: int,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    date: Optional[str] = None,
    tags: Optional[list[str]] = None
) -> Optional[Expense]:
    """Update an existing expense.

    Args:
        expense_id: The expense ID
        amount: New amount
        category: New category
        description: New description
        date: New date
        tags: New tags

    Returns:
        Updated expense or None
    """
    if expense_id not in expenses:
        return None

    expense = expenses[expense_id]
    if amount is not None:
        expense["amount"] = amount
    if category is not None:
        expense["category"] = category.lower()
    if description is not None:
        expense["description"] = description
    if date is not None:
        expense["date"] = date
    if tags is not None:
        expense["tags"] = tags
    _save()

    return Expense(**expense)


@mcp.tool
def delete_expense(expense_id: int) -> bool:
    """Delete an expense.

    Args:
        expense_id: The expense ID

    Returns:
        True if deleted, False if not found
    """
    if expense_id in expenses:
        del expenses[expense_id]
        _save()
        return True
    return False


@mcp.tool
def get_expenses_by_date(start_date: str, end_date: str) -> list[Expense]:
    """Get expenses within a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        List of expenses in the date range
    """
    return [
        Expense(**e) for e in expenses.values()
        if start_date <= e["date"] <= end_date
    ]


@mcp.tool
def get_expenses_by_category(category: str) -> list[Expense]:
    """Get all expenses in a category.

    Args:
        category: Category name

    Returns:
        List of expenses in the category
    """
    cat_lower = category.lower()
    return [
        Expense(**e) for e in expenses.values()
        if e["category"] == cat_lower
    ]


@mcp.tool
def get_total_expenses(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """Get total expenses, optionally filtered by date range.

    Args:
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        Summary with total and breakdown by category
    """
    filtered = list(expenses.values())

    if start_date:
        filtered = [e for e in filtered if e["date"] >= start_date]
    if end_date:
        filtered = [e for e in filtered if e["date"] <= end_date]

    total = sum(e["amount"] for e in filtered)

    by_category: dict[str, float] = {}
    for e in filtered:
        cat = e["category"]
        by_category[cat] = by_category.get(cat, 0) + e["amount"]

    return {
        "total": total,
        "count": len(filtered),
        "by_category": by_category
    }


# Budget Management
@mcp.tool
def create_budget(
    name: str,
    amount: float,
    category: Optional[str] = None,
    period: str = "monthly",
    start_date: Optional[str] = None
) -> Budget:
    """Create a budget.

    Args:
        name: Budget name
        amount: Budget amount in dollars
        category: Optional category this budget applies to
        period: Budget period (daily, weekly, monthly, yearly)
        start_date: When the budget starts (YYYY-MM-DD)

    Returns:
        The created budget
    """
    budget_id = _get_next_budget_id()
    budget = Budget(
        id=budget_id,
        name=name,
        amount=amount,
        category=category.lower() if category else None,
        period=period,
        start_date=start_date or datetime.now().strftime("%Y-%m-%d"),
        created_at=datetime.now().isoformat()
    )
    budgets[budget_id] = budget.model_dump()
    _save()
    return budget


@mcp.tool
def get_budget_status(budget_id: int) -> Optional[dict]:
    """Get the current status of a budget.

    Args:
        budget_id: The budget ID

    Returns:
        Budget status with spent amount and remaining
    """
    if budget_id not in budgets:
        return None

    budget = budgets[budget_id]
    today = datetime.now()

    # Calculate period start
    if budget["period"] == "daily":
        period_start = today.strftime("%Y-%m-%d")
    elif budget["period"] == "weekly":
        week_start = today - timedelta(days=today.weekday())
        period_start = week_start.strftime("%Y-%m-%d")
    elif budget["period"] == "monthly":
        period_start = today.strftime("%Y-%m") + "-01"
    else:  # yearly
        period_start = today.strftime("%Y") + "-01-01"

    # Calculate spent
    filtered = [e for e in expenses.values() if e["date"] >= period_start]
    if budget.get("category"):
        filtered = [e for e in filtered if e["category"] == budget["category"]]

    spent = sum(e["amount"] for e in filtered)
    remaining = budget["amount"] - spent
    percent_used = (spent / budget["amount"] * 100) if budget["amount"] > 0 else 0

    return {
        "budget": Budget(**budget).model_dump(),
        "spent": spent,
        "remaining": remaining,
        "percent_used": round(percent_used, 1),
        "period_start": period_start,
        "status": "over" if remaining < 0 else "under"
    }


@mcp.tool
def list_budgets() -> list[Budget]:
    """List all budgets.

    Returns:
        List of all budgets
    """
    return [Budget(**b) for b in budgets.values()]


# Resources
@mcp.resource("expenses://summary")
def get_expense_summary_resource() -> str:
    """Resource showing expense summary."""
    total_info = get_total_expenses()

    lines = ["# Expense Summary\n"]
    lines.append(f"**Total Expenses:** ${total_info['total']:,.2f}")
    lines.append(f"**Number of Transactions:** {total_info['count']}\n")

    lines.append("## By Category")
    for cat, amount in sorted(total_info["by_category"].items(), key=lambda x: -x[1]):
        lines.append(f"- {cat.title()}: ${amount:,.2f}")

    return "\n".join(lines)


@mcp.resource("expenses://recent")
def get_recent_expenses_resource() -> str:
    """Resource showing recent expenses."""
    recent = sorted(
        expenses.values(),
        key=lambda e: e["date"],
        reverse=True
    )[:10]

    if not recent:
        return "# Recent Expenses\n\nNo expenses recorded yet."

    lines = ["# Recent Expenses\n"]
    for e in recent:
        lines.append(f"- **${e['amount']:,.2f}** - {e['description']} ({e['category']}) - {e['date']}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()