"""
Expense Tracker MCP Server
A FastMCP server for tracking expenses, budgets, and financial goals.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json
import os
import shutil
import atexit
import tempfile
import threading
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
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
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


_write_lock = threading.Lock()
_last_payload: Optional[str] = None
_pending_payload: Optional[str] = None
_flush_timer: Optional[threading.Timer] = None
_WRITE_DEBOUNCE_MS = int(os.environ.get("MCP_WRITE_DEBOUNCE_MS", "0") or 0)


def _write_payload(payload: str) -> None:
    """Atomically replace the data file with serialized JSON."""
    global _last_payload
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, DATA_FILE)
        _last_payload = payload
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _flush_pending() -> None:
    """Write any deferred payload to disk immediately."""
    global _pending_payload
    with _write_lock:
        if _pending_payload is not None:
            payload, _pending_payload = _pending_payload, None
            _write_payload(payload)


def _save_data(data: dict) -> None:
    """Save data atomically, skipping unchanged writes.

    Writes to a temp file in the same directory then os.replace()s it into
    place, so an interrupted write can never leave a truncated/corrupt file.
    Set MCP_WRITE_DEBOUNCE_MS>0 to defer disk I/O; pending writes are flushed
    on exit and by the flush_data tool.
    """
    global _pending_payload, _flush_timer
    payload = json.dumps(data, indent=2, default=str)
    if _WRITE_DEBOUNCE_MS <= 0:
        with _write_lock:
            if payload != _last_payload:
                _write_payload(payload)
        return
    with _write_lock:
        if payload == _last_payload:
            return
        _pending_payload = payload
        if _flush_timer is not None:
            _flush_timer.cancel()
        _flush_timer = threading.Timer(_WRITE_DEBOUNCE_MS / 1000.0, _flush_pending)
        _flush_timer.daemon = True
        _flush_timer.start()


atexit.register(_flush_pending)


@mcp.tool
def flush_data() -> dict:
    """Flush any deferred writes to disk immediately."""
    _flush_pending()
    return {"flushed": True, "path": str(DATA_FILE), "debounce_ms": _WRITE_DEBOUNCE_MS}


@mcp.tool
def backup_data() -> dict:
    """Copy the current data file into data/backups/ with a timestamp."""
    _flush_pending()
    if not DATA_FILE.exists():
        raise ValueError("No data file to back up yet")
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = backup_dir / f"{DATA_FILE.stem}-{stamp}.json"
    shutil.copy2(DATA_FILE, target)
    return {"backup": str(target), "bytes": target.stat().st_size}


@mcp.tool
def list_backups() -> list[dict]:
    """List available data backups, newest first."""
    backup_dir = DATA_DIR / "backups"
    if not backup_dir.exists():
        return []
    items = []
    for path in sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        items.append({
            "name": path.name,
            "bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        })
    return items


@mcp.tool
def restore_backup(name: str) -> dict:
    """Restore a backup, replacing current data. Restart the server to load it."""
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


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
def list_categories() -> list[Category]:
    """List all expense categories.

    Returns:
        List of categories
    """
    # Default categories with negative IDs to differentiate from custom categories
    default_cats = [
        Category(id=-(i+1), name=c.value, icon=None, created_at=datetime.now().isoformat())
        for i, c in enumerate(ExpenseCategory)
    ]
    custom_cats = [Category(**c) for c in categories.values()]
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