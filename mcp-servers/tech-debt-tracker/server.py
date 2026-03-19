"""
Tech Debt Tracker MCP Server
A FastMCP server for tracking technical debt, managing refactoring tasks, and monitoring code quality metrics.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
from enum import Enum
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Tech Debt Tracker",
    instructions="A technical debt tracking server for managing debt items, prioritizing refactoring tasks, and monitoring code quality improvements."
)


class DebtPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NICE_TO_HAVE = "nice_to_have"


class DebtStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class DebtCategory(str, Enum):
    ARCHITECTURE = "architecture"
    CODE_QUALITY = "code_quality"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DEPENDENCIES = "dependencies"
    INFRASTRUCTURE = "infrastructure"
    MAINTAINABILITY = "maintainability"


class EffortEstimate(str, Enum):
    TRIVIAL = "trivial"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    VERY_LARGE = "very_large"
    EPIC = "epic"


class ImpactLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class DebtItem(BaseModel):
    """A technical debt item."""
    id: int
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    status: str
    impact: str
    effort: str
    component: Optional[str] = None
    assignee: Optional[str] = None
    interest_rate: float = 0.0
    created_at: str
    updated_at: str


class RefactoringTask(BaseModel):
    """A refactoring task."""
    id: int
    debt_item_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    assigned_to: Optional[str] = None
    estimated_effort: Optional[str] = None
    created_at: str
    updated_at: str


class QualityMetric(BaseModel):
    """A code quality metric."""
    id: int
    name: str
    value: float
    unit: str
    threshold: Optional[float] = None
    recorded_at: str


class DebtSnapshot(BaseModel):
    """A snapshot of tech debt at a point in time."""
    id: int
    date: str
    total_items: int
    open_items: int
    resolved_items: int
    by_category: dict = {}
    by_priority: dict = {}
    created_at: str


# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "tech_debt.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "debt_items": {},
        "refactoring_tasks": {},
        "quality_metrics": {},
        "debt_snapshots": {},
        "next_debt_id": 1,
        "next_task_id": 1,
        "next_metric_id": 1,
        "next_snapshot_id": 1,
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
debt_items: dict[int, dict] = {int(k): v for k, v in _data.get("debt_items", {}).items()}
refactoring_tasks: dict[int, dict] = {int(k): v for k, v in _data.get("refactoring_tasks", {}).items()}
quality_metrics: dict[int, dict] = {int(k): v for k, v in _data.get("quality_metrics", {}).items()}
debt_snapshots: dict[int, dict] = {int(k): v for k, v in _data.get("debt_snapshots", {}).items()}
_next_debt_id = _data.get("next_debt_id", 1)
_next_task_id = _data.get("next_task_id", 1)
_next_metric_id = _data.get("next_metric_id", 1)
_next_snapshot_id = _data.get("next_snapshot_id", 1)


def _get_next_debt_id() -> int:
    global _next_debt_id
    id_ = _next_debt_id
    _next_debt_id += 1
    return id_


def _get_next_task_id() -> int:
    global _next_task_id
    id_ = _next_task_id
    _next_task_id += 1
    return id_


def _get_next_metric_id() -> int:
    global _next_metric_id
    id_ = _next_metric_id
    _next_metric_id += 1
    return id_


def _get_next_snapshot_id() -> int:
    global _next_snapshot_id
    id_ = _next_snapshot_id
    _next_snapshot_id += 1
    return id_


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "debt_items": debt_items,
        "refactoring_tasks": refactoring_tasks,
        "quality_metrics": quality_metrics,
        "debt_snapshots": debt_snapshots,
        "next_debt_id": _next_debt_id,
        "next_task_id": _next_task_id,
        "next_metric_id": _next_metric_id,
        "next_snapshot_id": _next_snapshot_id,
    })


# === DEBT ITEM TOOLS ===

@mcp.tool
def create_debt_item(
    title: str,
    category: str,
    description: str,
    priority: str = DebtPriority.MEDIUM.value,
    impact: str = ImpactLevel.MEDIUM.value,
    effort: str = EffortEstimate.MEDIUM.value,
    file_path: Optional[str] = None,
    component: Optional[str] = None,
    tags: Optional[list[str]] = None,
    related_items: Optional[list[int]] = None,
    business_value: Optional[str] = None,
) -> dict:
    """Create a new technical debt item.

    Args:
        title: Brief title describing the debt
        category: Category (architecture, code_quality, documentation, testing, performance, security, dependencies, infrastructure, maintainability)
        description: Detailed description of the debt
        priority: Priority level (critical, high, medium, low, nice_to_have)
        impact: Business impact (critical, high, medium, low, minimal)
        effort: Estimated effort to fix (trivial, small, medium, large, very_large, epic)
        file_path: Related file path(s)
        component: Affected component/module
        tags: Tags for categorization
        related_items: IDs of related debt items
        business_value: Business value of fixing this debt

    Returns:
        The created debt item
    """
    debt_id = _get_next_debt_id()
    debt = {
        "id": debt_id,
        "title": title,
        "category": category,
        "description": description,
        "priority": priority,
        "impact": impact,
        "effort": effort,
        "file_path": file_path,
        "component": component,
        "tags": tags or [],
        "related_items": related_items or [],
        "business_value": business_value,
        "status": DebtStatus.OPEN.value,
        "assigned_to": None,
        "resolution": None,
        "resolution_date": None,
        "interest_accrued": 0,  # Tracks how much "interest" (extra work) this debt has caused
        "interest_notes": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    debt_items[debt_id] = debt
    _save()
    return debt


@mcp.tool
def get_debt_item(debt_id: int) -> Optional[dict]:
    """Get a debt item by ID.

    Args:
        debt_id: The debt item ID

    Returns:
        The debt item details or None if not found
    """
    return debt_items.get(debt_id)


@mcp.tool
def list_debt_items(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    component: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List debt items with optional filters.

    Args:
        status: Filter by status
        category: Filter by category
        priority: Filter by priority
        component: Filter by component
        assigned_to: Filter by assignee
        limit: Maximum number of results

    Returns:
        List of matching debt items
    """
    result = list(debt_items.values())

    if status:
        result = [d for d in result if d.get("status") == status]
    if category:
        result = [d for d in result if d.get("category") == category]
    if priority:
        result = [d for d in result if d.get("priority") == priority]
    if component:
        result = [d for d in result if component.lower() in (d.get("component") or "").lower()]
    if assigned_to:
        result = [d for d in result if assigned_to.lower() in (d.get("assigned_to") or "").lower()]

    # Sort by priority
    priority_order = {
        DebtPriority.CRITICAL.value: 0,
        DebtPriority.HIGH.value: 1,
        DebtPriority.MEDIUM.value: 2,
        DebtPriority.LOW.value: 3,
        DebtPriority.NICE_TO_HAVE.value: 4,
    }
    result.sort(key=lambda d: priority_order.get(d.get("priority", "medium"), 2))

    return result[:limit]


@mcp.tool
def update_debt_item(
    debt_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    impact: Optional[str] = None,
    effort: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Optional[dict]:
    """Update a debt item.

    Args:
        debt_id: The debt item ID
        title: New title
        description: New description
        priority: New priority
        impact: New impact level
        effort: New effort estimate
        status: New status
        assigned_to: Person assigned to fix
        tags: New tags

    Returns:
        The updated debt item or None if not found
    """
    if debt_id not in debt_items:
        return None

    debt = debt_items[debt_id]
    if title is not None:
        debt["title"] = title
    if description is not None:
        debt["description"] = description
    if priority is not None:
        debt["priority"] = priority
    if impact is not None:
        debt["impact"] = impact
    if effort is not None:
        debt["effort"] = effort
    if status is not None:
        debt["status"] = status
    if assigned_to is not None:
        debt["assigned_to"] = assigned_to
    if tags is not None:
        debt["tags"] = tags
    debt["updated_at"] = datetime.now().isoformat()
    _save()
    return debt


@mcp.tool
def resolve_debt_item(
    debt_id: int,
    resolution: str,
    resolved_by: Optional[str] = None,
) -> Optional[dict]:
    """Mark a debt item as resolved.

    Args:
        debt_id: The debt item ID
        resolution: Description of how it was resolved
        resolved_by: Person who resolved it

    Returns:
        The resolved debt item or None if not found
    """
    if debt_id not in debt_items:
        return None

    debt = debt_items[debt_id]
    debt["status"] = DebtStatus.RESOLVED.value
    debt["resolution"] = resolution
    debt["resolved_by"] = resolved_by
    debt["resolution_date"] = datetime.now().isoformat()
    debt["updated_at"] = datetime.now().isoformat()
    _save()
    return debt


@mcp.tool
def accrue_interest(
    debt_id: int,
    hours: float,
    description: str,
) -> Optional[dict]:
    """Record interest (extra work) accrued on a debt item.

    Args:
        debt_id: The debt item ID
        hours: Hours of extra work caused by this debt
        description: Description of the extra work

    Returns:
        The updated debt item or None if not found
    """
    if debt_id not in debt_items:
        return None

    debt = debt_items[debt_id]
    debt["interest_accrued"] = debt.get("interest_accrued", 0) + hours
    debt.setdefault("interest_notes", []).append({
        "hours": hours,
        "description": description,
        "date": datetime.now().isoformat(),
    })
    debt["updated_at"] = datetime.now().isoformat()
    _save()
    return debt


@mcp.tool
def delete_debt_item(debt_id: int) -> bool:
    """Delete a debt item.

    Args:
        debt_id: The debt item ID

    Returns:
        True if deleted, False if not found
    """
    if debt_id in debt_items:
        del debt_items[debt_id]
        _save()
        return True
    return False


# === REFACTORING TASK TOOLS ===

@mcp.tool
def create_refactoring_task(
    title: str,
    description: str,
    debt_ids: Optional[list[int]] = None,
    file_paths: Optional[list[str]] = None,
    effort: str = EffortEstimate.MEDIUM.value,
    benefits: Optional[list[str]] = None,
    risks: Optional[list[str]] = None,
    prerequisites: Optional[list[int]] = None,
) -> dict:
    """Create a refactoring task.

    Args:
        title: Task title
        description: Detailed description
        debt_ids: IDs of debt items this task addresses
        file_paths: Files to be modified
        effort: Estimated effort
        benefits: List of expected benefits
        risks: List of potential risks
        prerequisites: IDs of tasks that must be completed first

    Returns:
        The created refactoring task
    """
    task_id = _get_next_task_id()
    task = {
        "id": task_id,
        "title": title,
        "description": description,
        "debt_ids": debt_ids or [],
        "file_paths": file_paths or [],
        "effort": effort,
        "benefits": benefits or [],
        "risks": risks or [],
        "prerequisites": prerequisites or [],
        "status": "pending",
        "assigned_to": None,
        "progress": 0,  # Percentage complete
        "started_at": None,
        "completed_at": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    refactoring_tasks[task_id] = task
    _save()
    return task


@mcp.tool
def get_refactoring_task(task_id: int) -> Optional[dict]:
    """Get a refactoring task by ID.

    Args:
        task_id: The task ID

    Returns:
        The task details or None if not found
    """
    return refactoring_tasks.get(task_id)


@mcp.tool
def list_refactoring_tasks(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List refactoring tasks with optional filters.

    Args:
        status: Filter by status
        assigned_to: Filter by assignee
        limit: Maximum number of results

    Returns:
        List of matching tasks
    """
    result = list(refactoring_tasks.values())

    if status:
        result = [t for t in result if t.get("status") == status]
    if assigned_to:
        result = [t for t in result if assigned_to.lower() in (t.get("assigned_to") or "").lower()]

    result.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return result[:limit]


@mcp.tool
def update_refactoring_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    assigned_to: Optional[str] = None,
) -> Optional[dict]:
    """Update a refactoring task.

    Args:
        task_id: The task ID
        title: New title
        description: New description
        status: New status
        progress: Progress percentage (0-100)
        assigned_to: Person assigned

    Returns:
        The updated task or None if not found
    """
    if task_id not in refactoring_tasks:
        return None

    task = refactoring_tasks[task_id]
    if title is not None:
        task["title"] = title
    if description is not None:
        task["description"] = description
    if status is not None:
        task["status"] = status
        if status == "in_progress" and not task.get("started_at"):
            task["started_at"] = datetime.now().isoformat()
        if status == "completed":
            task["completed_at"] = datetime.now().isoformat()
            task["progress"] = 100
    if progress is not None:
        task["progress"] = max(0, min(100, progress))
    if assigned_to is not None:
        task["assigned_to"] = assigned_to
    task["updated_at"] = datetime.now().isoformat()
    _save()
    return task


@mcp.tool
def complete_refactoring_task(
    task_id: int,
    summary: str,
    completed_by: Optional[str] = None,
) -> Optional[dict]:
    """Mark a refactoring task as completed.

    Args:
        task_id: The task ID
        summary: Summary of changes made
        completed_by: Person who completed it

    Returns:
        The completed task or None if not found
    """
    if task_id not in refactoring_tasks:
        return None

    task = refactoring_tasks[task_id]
    task["status"] = "completed"
    task["progress"] = 100
    task["completed_at"] = datetime.now().isoformat()
    task["completion_summary"] = summary
    task["completed_by"] = completed_by
    task["updated_at"] = datetime.now().isoformat()

    # Mark related debt items as resolved
    for debt_id in task.get("debt_ids", []):
        if debt_id in debt_items:
            debt_items[debt_id]["status"] = DebtStatus.RESOLVED.value
            debt_items[debt_id]["resolution"] = f"Resolved by refactoring task {task_id}"
            debt_items[debt_id]["resolution_date"] = datetime.now().isoformat()

    _save()
    return task


@mcp.tool
def delete_refactoring_task(task_id: int) -> bool:
    """Delete a refactoring task.

    Args:
        task_id: The task ID

    Returns:
        True if deleted, False if not found
    """
    if task_id in refactoring_tasks:
        del refactoring_tasks[task_id]
        _save()
        return True
    return False


# === QUALITY METRICS TOOLS ===

@mcp.tool
def record_quality_metric(
    name: str,
    value: float,
    unit: str,
    component: Optional[str] = None,
    threshold: Optional[float] = None,
    notes: Optional[str] = None,
) -> dict:
    """Record a code quality metric.

    Args:
        name: Metric name (e.g., "code_coverage", "cyclomatic_complexity", "duplication")
        value: Metric value
        unit: Unit of measurement (e.g., "%", "count", "lines")
        component: Component/module this metric applies to
        threshold: Target threshold for this metric
        notes: Additional notes

    Returns:
        The created metric record
    """
    metric_id = _get_next_metric_id()
    metric = {
        "id": metric_id,
        "name": name,
        "value": value,
        "unit": unit,
        "component": component,
        "threshold": threshold,
        "notes": notes,
        "meets_threshold": threshold is None or value >= threshold if threshold is not None else None,
        "created_at": datetime.now().isoformat(),
    }
    quality_metrics[metric_id] = metric
    _save()
    return metric


@mcp.tool
def get_quality_metric(metric_id: int) -> Optional[dict]:
    """Get a quality metric by ID.

    Args:
        metric_id: The metric ID

    Returns:
        The metric details or None if not found
    """
    return quality_metrics.get(metric_id)


@mcp.tool
def list_quality_metrics(
    name: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List quality metrics with optional filters.

    Args:
        name: Filter by metric name
        component: Filter by component
        limit: Maximum number of results

    Returns:
        List of matching metrics
    """
    result = list(quality_metrics.values())

    if name:
        result = [m for m in result if name.lower() in m.get("name", "").lower()]
    if component:
        result = [m for m in result if component.lower() in (m.get("component") or "").lower()]

    result.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return result[:limit]


@mcp.tool
def get_metric_history(
    name: str,
    component: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Get historical values for a specific metric.

    Args:
        name: Metric name
        component: Filter by component
        limit: Maximum number of results

    Returns:
        List of historical metric values
    """
    result = [m for m in quality_metrics.values() if m.get("name") == name]

    if component:
        result = [m for m in result if m.get("component") == component]

    result.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return result[:limit]


@mcp.tool
def delete_quality_metric(metric_id: int) -> bool:
    """Delete a quality metric.

    Args:
        metric_id: The metric ID

    Returns:
        True if deleted, False if not found
    """
    if metric_id in quality_metrics:
        del quality_metrics[metric_id]
        _save()
        return True
    return False


# === DEBT SNAPSHOT TOOLS ===

@mcp.tool
def create_debt_snapshot(
    name: str,
    description: Optional[str] = None,
) -> dict:
    """Create a snapshot of current technical debt state.

    Args:
        name: Snapshot name (e.g., "Q1 2024", "Before Refactor")
        description: Optional description

    Returns:
        The created snapshot
    """
    snapshot_id = _get_next_snapshot_id()

    # Calculate current debt statistics
    open_debt = [d for d in debt_items.values() if d.get("status") == DebtStatus.OPEN.value]
    in_progress_debt = [d for d in debt_items.values() if d.get("status") == DebtStatus.IN_PROGRESS.value]
    resolved_debt = [d for d in debt_items.values() if d.get("status") == DebtStatus.RESOLVED.value]

    total_interest = sum(d.get("interest_accrued", 0) for d in debt_items.values())

    by_category = {}
    by_priority = {}
    for debt in open_debt + in_progress_debt:
        cat = debt.get("category", "unknown")
        pri = debt.get("priority", "medium")
        by_category[cat] = by_category.get(cat, 0) + 1
        by_priority[pri] = by_priority.get(pri, 0) + 1

    snapshot = {
        "id": snapshot_id,
        "name": name,
        "description": description,
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "total_items": len(debt_items),
            "open_items": len(open_debt),
            "in_progress_items": len(in_progress_debt),
            "resolved_items": len(resolved_debt),
            "total_interest_hours": total_interest,
            "by_category": by_category,
            "by_priority": by_priority,
        },
        "debt_item_ids": list(debt_items.keys()),
        "task_ids": list(refactoring_tasks.keys()),
    }
    debt_snapshots[snapshot_id] = snapshot
    _save()
    return snapshot


@mcp.tool
def get_debt_snapshot(snapshot_id: int) -> Optional[dict]:
    """Get a debt snapshot by ID.

    Args:
        snapshot_id: The snapshot ID

    Returns:
        The snapshot details or None if not found
    """
    return debt_snapshots.get(snapshot_id)


@mcp.tool
def list_debt_snapshots(limit: int = 20) -> list[dict]:
    """List all debt snapshots.

    Args:
        limit: Maximum number of results

    Returns:
        List of snapshots
    """
    result = list(debt_snapshots.values())
    result.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
    return result[:limit]


@mcp.tool
def compare_snapshots(snapshot_id_1: int, snapshot_id_2: int) -> Optional[dict]:
    """Compare two debt snapshots.

    Args:
        snapshot_id_1: First snapshot ID
        snapshot_id_2: Second snapshot ID

    Returns:
        Comparison results or None if either snapshot not found
    """
    if snapshot_id_1 not in debt_snapshots or snapshot_id_2 not in debt_snapshots:
        return None

    snap1 = debt_snapshots[snapshot_id_1]
    snap2 = debt_snapshots[snapshot_id_2]

    stats1 = snap1.get("statistics", {})
    stats2 = snap2.get("statistics", {})

    comparison = {
        "snapshot_1": {"id": snapshot_id_1, "name": snap1.get("name"), "timestamp": snap1.get("timestamp")},
        "snapshot_2": {"id": snapshot_id_2, "name": snap2.get("name"), "timestamp": snap2.get("timestamp")},
        "changes": {
            "total_items": stats2.get("total_items", 0) - stats1.get("total_items", 0),
            "open_items": stats2.get("open_items", 0) - stats1.get("open_items", 0),
            "in_progress_items": stats2.get("in_progress_items", 0) - stats1.get("in_progress_items", 0),
            "resolved_items": stats2.get("resolved_items", 0) - stats1.get("resolved_items", 0),
            "total_interest_hours": stats2.get("total_interest_hours", 0) - stats1.get("total_interest_hours", 0),
        },
        "category_changes": {},
        "priority_changes": {},
    }

    # Calculate category changes
    all_categories = set(stats1.get("by_category", {}).keys()) | set(stats2.get("by_category", {}).keys())
    for cat in all_categories:
        count1 = stats1.get("by_category", {}).get(cat, 0)
        count2 = stats2.get("by_category", {}).get(cat, 0)
        if count2 != count1:
            comparison["category_changes"][cat] = count2 - count1

    # Calculate priority changes
    all_priorities = set(stats1.get("by_priority", {}).keys()) | set(stats2.get("by_priority", {}).keys())
    for pri in all_priorities:
        count1 = stats1.get("by_priority", {}).get(pri, 0)
        count2 = stats2.get("by_priority", {}).get(pri, 0)
        if count2 != count1:
            comparison["priority_changes"][pri] = count2 - count1

    return comparison


@mcp.tool
def delete_debt_snapshot(snapshot_id: int) -> bool:
    """Delete a debt snapshot.

    Args:
        snapshot_id: The snapshot ID

    Returns:
        True if deleted, False if not found
    """
    if snapshot_id in debt_snapshots:
        del debt_snapshots[snapshot_id]
        _save()
        return True
    return False


# === ANALYTICS TOOLS ===

@mcp.tool
def get_debt_summary() -> dict:
    """Get a summary of technical debt.

    Returns:
        Summary with counts by category, priority, and status
    """
    open_debt = [d for d in debt_items.values() if d.get("status") == DebtStatus.OPEN.value]
    in_progress_debt = [d for d in debt_items.values() if d.get("status") == DebtStatus.IN_PROGRESS.value]
    blocked_debt = [d for d in debt_items.values() if d.get("status") == DebtStatus.BLOCKED.value]
    resolved_debt = [d for d in debt_items.values() if d.get("status") == DebtStatus.RESOLVED.value]

    total_interest = sum(d.get("interest_accrued", 0) for d in debt_items.values())

    by_category = {}
    by_priority = {}
    by_status = {}
    by_component = {}

    for debt in debt_items.values():
        if debt.get("status") != DebtStatus.RESOLVED.value:
            cat = debt.get("category", "unknown")
            pri = debt.get("priority", "medium")
            stat = debt.get("status", "open")
            comp = debt.get("component", "unknown")

            by_category[cat] = by_category.get(cat, 0) + 1
            by_priority[pri] = by_priority.get(pri, 0) + 1
            by_status[stat] = by_status.get(stat, 0) + 1
            by_component[comp] = by_component.get(comp, 0) + 1

    # Calculate debt score (weighted by priority)
    priority_weights = {
        DebtPriority.CRITICAL.value: 10,
        DebtPriority.HIGH.value: 5,
        DebtPriority.MEDIUM.value: 3,
        DebtPriority.LOW.value: 1,
        DebtPriority.NICE_TO_HAVE.value: 0.5,
    }
    debt_score = sum(priority_weights.get(d.get("priority", "medium"), 1) for d in open_debt + in_progress_debt + blocked_debt)

    return {
        "total_items": len(debt_items),
        "open_items": len(open_debt),
        "in_progress_items": len(in_progress_debt),
        "blocked_items": len(blocked_debt),
        "resolved_items": len(resolved_debt),
        "total_interest_hours": total_interest,
        "debt_score": debt_score,
        "by_category": by_category,
        "by_priority": by_priority,
        "by_status": by_status,
        "by_component": by_component,
        "active_tasks": len([t for t in refactoring_tasks.values() if t.get("status") == "in_progress"]),
        "pending_tasks": len([t for t in refactoring_tasks.values() if t.get("status") == "pending"]),
        "completed_tasks": len([t for t in refactoring_tasks.values() if t.get("status") == "completed"]),
    }


@mcp.tool
def get_priority_items(limit: int = 10) -> list[dict]:
    """Get highest priority debt items that need attention.

    Args:
        limit: Maximum number of items to return

    Returns:
        List of priority debt items sorted by urgency
    """
    active_debt = [
        d for d in debt_items.values()
        if d.get("status") in [DebtStatus.OPEN.value, DebtStatus.IN_PROGRESS.value, DebtStatus.BLOCKED.value]
    ]

    # Calculate urgency score (higher = more urgent)
    priority_weights = {
        DebtPriority.CRITICAL.value: 100,
        DebtPriority.HIGH.value: 75,
        DebtPriority.MEDIUM.value: 50,
        DebtPriority.LOW.value: 25,
        DebtPriority.NICE_TO_HAVE.value: 10,
    }
    impact_weights = {
        ImpactLevel.CRITICAL.value: 20,
        ImpactLevel.HIGH.value: 15,
        ImpactLevel.MEDIUM.value: 10,
        ImpactLevel.LOW.value: 5,
        ImpactLevel.MINIMAL.value: 1,
    }

    def urgency_score(debt):
        pri = priority_weights.get(debt.get("priority", "medium"), 50)
        imp = impact_weights.get(debt.get("impact", "medium"), 10)
        interest = debt.get("interest_accrued", 0)
        return pri + imp + interest

    active_debt.sort(key=urgency_score, reverse=True)
    return active_debt[:limit]


@mcp.tool
def search_debt_items(query: str) -> list[dict]:
    """Search debt items by title, description, or component.

    Args:
        query: Search term

    Returns:
        List of matching debt items
    """
    query_lower = query.lower()
    results = []

    for debt in debt_items.values():
        if (
            query_lower in debt.get("title", "").lower() or
            query_lower in debt.get("description", "").lower() or
            query_lower in (debt.get("component") or "").lower() or
            query_lower in (debt.get("file_path") or "").lower() or
            any(query_lower in tag.lower() for tag in debt.get("tags", []))
        ):
            results.append(debt)

    return results[:20]


@mcp.tool
def get_component_debt(component: str) -> dict:
    """Get debt summary for a specific component.

    Args:
        component: Component name

    Returns:
        Debt summary for the component
    """
    component_debt = [
        d for d in debt_items.values()
        if d.get("component", "").lower() == component.lower()
    ]

    open_items = [d for d in component_debt if d.get("status") == DebtStatus.OPEN.value]
    in_progress_items = [d for d in component_debt if d.get("status") == DebtStatus.IN_PROGRESS.value]
    resolved_items = [d for d in component_debt if d.get("status") == DebtStatus.RESOLVED.value]

    total_interest = sum(d.get("interest_accrued", 0) for d in component_debt)

    by_category = {}
    by_priority = {}
    for debt in open_items + in_progress_items:
        cat = debt.get("category", "unknown")
        pri = debt.get("priority", "medium")
        by_category[cat] = by_category.get(cat, 0) + 1
        by_priority[pri] = by_priority.get(pri, 0) + 1

    return {
        "component": component,
        "total_items": len(component_debt),
        "open_items": len(open_items),
        "in_progress_items": len(in_progress_items),
        "resolved_items": len(resolved_items),
        "total_interest_hours": total_interest,
        "by_category": by_category,
        "by_priority": by_priority,
        "items": component_debt[:20],
    }


# === RESOURCES ===

@mcp.resource("debt://summary")
def get_debt_summary_resource() -> str:
    """Resource providing technical debt summary."""
    summary = get_debt_summary()

    lines = ["# Technical Debt Summary\n"]
    lines.append(f"- **Total Items:** {summary['total_items']}")
    lines.append(f"- **Open Items:** {summary['open_items']}")
    lines.append(f"- **In Progress:** {summary['in_progress_items']}")
    lines.append(f"- **Blocked:** {summary['blocked_items']}")
    lines.append(f"- **Resolved:** {summary['resolved_items']}")
    lines.append(f"- **Total Interest Accrued:** {summary['total_interest_hours']} hours")
    lines.append(f"- **Debt Score:** {summary['debt_score']}")

    if summary["by_category"]:
        lines.append("\n## By Category\n")
        for cat, count in sorted(summary["by_category"].items()):
            lines.append(f"- {cat}: {count}")

    if summary["by_priority"]:
        lines.append("\n## By Priority\n")
        for pri, count in sorted(summary["by_priority"].items()):
            lines.append(f"- {pri}: {count}")

    lines.append("\n## Refactoring Tasks\n")
    lines.append(f"- **Active:** {summary['active_tasks']}")
    lines.append(f"- **Pending:** {summary['pending_tasks']}")
    lines.append(f"- **Completed:** {summary['completed_tasks']}")

    return "\n".join(lines)


@mcp.resource("debt://priority")
def get_priority_debt_resource() -> str:
    """Resource providing priority debt items."""
    priority_items = get_priority_items(limit=15)

    if not priority_items:
        return "No priority debt items found."

    lines = ["# Priority Debt Items\n"]

    priority_emoji = {
        DebtPriority.CRITICAL.value: "\U0001F534",
        DebtPriority.HIGH.value: "\U0001F7E0",
        DebtPriority.MEDIUM.value: "\U0001F7E1",
        DebtPriority.LOW.value: "\U0001F7E2",
        DebtPriority.NICE_TO_HAVE.value: "\U0001F4A1",
    }

    for debt in priority_items:
        emoji = priority_emoji.get(debt.get("priority", "medium"), "\u2753")
        status = debt.get("status", "open")

        lines.append(f"## {emoji} {debt.get('title', 'Untitled')} (ID: {debt['id']})")
        lines.append(f"- **Status:** {status}")
        lines.append(f"- **Category:** {debt.get('category', 'unknown')}")
        lines.append(f"- **Priority:** {debt.get('priority', 'medium')}")
        lines.append(f"- **Impact:** {debt.get('impact', 'medium')}")
        lines.append(f"- **Effort:** {debt.get('effort', 'medium')}")
        if debt.get("component"):
            lines.append(f"- **Component:** {debt['component']}")
        if debt.get("interest_accrued", 0) > 0:
            lines.append(f"- **Interest Accrued:** {debt['interest_accrued']} hours")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("debt://open")
def get_open_debt_resource() -> str:
    """Resource providing all open debt items."""
    open_debt = [d for d in debt_items.values() if d.get("status") == DebtStatus.OPEN.value]

    if not open_debt:
        return "No open debt items."

    lines = ["# Open Technical Debt\n"]

    # Group by category
    by_category = {}
    for debt in open_debt:
        cat = debt.get("category", "unknown")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(debt)

    for category, items in sorted(by_category.items()):
        lines.append(f"\n## {category.title()}\n")
        for debt in sorted(items, key=lambda d: d.get("title", "")):
            lines.append(f"- **{debt.get('title', 'Untitled')}** (ID: {debt['id']})")
            lines.append(f"  - Priority: {debt.get('priority', 'medium')}")
            lines.append(f"  - Impact: {debt.get('impact', 'medium')}")
            if debt.get("component"):
                lines.append(f"  - Component: {debt['component']}")
            lines.append("")

    return "\n".join(lines)


@mcp.resource("tasks://active")
def get_active_tasks_resource() -> str:
    """Resource providing active refactoring tasks."""
    active_tasks = [t for t in refactoring_tasks.values() if t.get("status") == "in_progress"]

    if not active_tasks:
        return "No active refactoring tasks."

    lines = ["# Active Refactoring Tasks\n"]

    for task in sorted(active_tasks, key=lambda t: t.get("created_at", "")):
        progress = task.get("progress", 0)
        progress_bar = "\u2588" * (progress // 10) + "\u2591" * (10 - progress // 10)

        lines.append(f"## {task.get('title', 'Untitled')} (ID: {task['id']})")
        lines.append(f"- **Progress:** [{progress_bar}] {progress}%")
        if task.get("assigned_to"):
            lines.append(f"- **Assigned to:** {task['assigned_to']}")
        if task.get("debt_ids"):
            lines.append(f"- **Addresses debt items:** {', '.join(map(str, task['debt_ids']))}")
        if task.get("started_at"):
            lines.append(f"- **Started:** {task['started_at']}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("metrics://latest")
def get_latest_metrics_resource() -> str:
    """Resource providing latest quality metrics."""
    if not quality_metrics:
        return "No quality metrics recorded."

    # Get latest metric for each name
    latest_by_name = {}
    for metric in sorted(quality_metrics.values(), key=lambda m: m.get("created_at", ""), reverse=True):
        name = metric.get("name")
        if name not in latest_by_name:
            latest_by_name[name] = metric

    lines = ["# Latest Quality Metrics\n"]

    for name, metric in sorted(latest_by_name.items()):
        value = metric.get("value")
        unit = metric.get("unit", "")
        threshold = metric.get("threshold")
        meets = metric.get("meets_threshold")

        status = "\u2705" if meets is True else "\u274c" if meets is False else "\u2139\uFE0F"
        threshold_str = f" (threshold: {threshold}{unit})" if threshold else ""

        lines.append(f"- **{name}:** {status} {value}{unit}{threshold_str}")

    return "\n".join(lines)


@mcp.resource("snapshots://all")
def get_all_snapshots_resource() -> str:
    """Resource providing all debt snapshots."""
    if not debt_snapshots:
        return "No debt snapshots recorded."

    lines = ["# Debt Snapshots\n"]

    for snapshot in sorted(debt_snapshots.values(), key=lambda s: s.get("timestamp", ""), reverse=True):
        stats = snapshot.get("statistics", {})
        lines.append(f"## {snapshot.get('name', 'Unnamed')} (ID: {snapshot['id']})")
        lines.append(f"- **Date:** {snapshot.get('timestamp')}")
        lines.append(f"- **Total Items:** {stats.get('total_items', 0)}")
        lines.append(f"- **Open Items:** {stats.get('open_items', 0)}")
        lines.append(f"- **Interest Hours:** {stats.get('total_interest_hours', 0)}")
        if snapshot.get("description"):
            lines.append(f"- **Description:** {snapshot['description']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
