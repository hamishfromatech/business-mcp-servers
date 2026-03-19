"""
Habit Tracker MCP Server
A FastMCP server for tracking daily habits, streaks, and progress.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json
from enum import Enum
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Habit Tracker",
    instructions="A habit tracking server for building and maintaining daily habits with streak tracking."
)


class HabitFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class Habit(BaseModel):
    """A habit to track."""
    id: int
    name: str
    description: Optional[str] = None
    frequency: str
    color: str
    target_days: Optional[list[int]] = None
    created_at: str
    archived: bool = False


class CheckIn(BaseModel):
    """A habit check-in."""
    habit_id: int
    date: str
    completed: bool
    notes: Optional[str] = None
    recorded_at: str

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "habits.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"habits": {}, "check_ins": {}, "next_habit_id": 1}


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
habits: dict[int, dict] = {int(k): v for k, v in _data.get("habits", {}).items()}
check_ins: dict[str, dict] = _data.get("check_ins", {})
_next_habit_id = _data.get("next_habit_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "habits": habits,
        "check_ins": check_ins,
        "next_habit_id": _next_habit_id
    })


def _get_next_habit_id() -> int:
    global _next_habit_id
    id_ = _next_habit_id
    _next_habit_id += 1
    return id_


def _get_checkin_key(habit_id: int, date: str) -> str:
    return f"{habit_id}:{date}"


def _calculate_streak(habit_id: int, end_date: Optional[str] = None) -> int:
    """Calculate current streak for a habit."""
    if habit_id not in habits:
        return 0

    habit = habits[habit_id]
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    current_date = datetime.strptime(end_date, "%Y-%m-%d")
    streak = 0

    # Check if today is completed first
    today_key = _get_checkin_key(habit_id, current_date.strftime("%Y-%m-%d"))
    if today_key not in check_ins or not check_ins[today_key].get("completed"):
        # If today not completed, check from yesterday
        current_date -= timedelta(days=1)

    while True:
        date_str = current_date.strftime("%Y-%m-%d")
        key = _get_checkin_key(habit_id, date_str)

        if key in check_ins and check_ins[key].get("completed"):
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break

        # Limit search to prevent infinite loops
        if streak > 365:
            break

    return streak


def _calculate_completion_rate(habit_id: int, days: int = 30) -> float:
    """Calculate completion rate for the last N days."""
    if habit_id not in habits:
        return 0.0

    completed = 0
    today = datetime.now()

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        key = _get_checkin_key(habit_id, date_str)

        if key in check_ins and check_ins[key].get("completed"):
            completed += 1

    return (completed / days) * 100


# Habit Management
@mcp.tool
def create_habit(
    name: str,
    description: Optional[str] = None,
    frequency: str = "daily",
    color: Optional[str] = None,
    target_days: Optional[list[int]] = None
) -> Habit:
    """Create a new habit to track.

    Args:
        name: Habit name
        description: Optional description
        frequency: How often (daily, weekly, custom)
        color: Optional color for UI display
        target_days: For custom frequency, days of week (0=Monday, 6=Sunday)

    Returns:
        The created habit
    """
    habit_id = _get_next_habit_id()
    habit = Habit(
        id=habit_id,
        name=name,
        description=description,
        frequency=frequency,
        color=color or "#4CAF50",
        target_days=target_days,
        created_at=datetime.now().isoformat(),
        archived=False
    )
    habits[habit_id] = habit.model_dump()
    _save()
    return habit


@mcp.tool
def get_habit(habit_id: int) -> Optional[Habit]:
    """Get a habit by ID.

    Args:
        habit_id: The habit ID

    Returns:
        Habit details with current streak
    """
    if habit_id not in habits:
        return None

    habit = habits[habit_id].copy()
    habit["current_streak"] = _calculate_streak(habit_id)
    habit["completion_rate_30d"] = round(_calculate_completion_rate(habit_id), 1)
    return Habit(**habit)


@mcp.tool
def list_habits(include_archived: bool = False) -> list[Habit]:
    """List all habits.

    Args:
        include_archived: Whether to include archived habits

    Returns:
        List of habits with streak info
    """
    result = []
    for habit in habits.values():
        if not include_archived and habit.get("archived"):
            continue

        habit_data = habit.copy()
        habit_data["current_streak"] = _calculate_streak(habit["id"])
        habit_data["completion_rate_30d"] = round(_calculate_completion_rate(habit["id"]), 1)
        result.append(Habit(**habit_data))

    return result


@mcp.tool
def update_habit(
    habit_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    archived: Optional[bool] = None
) -> Optional[Habit]:
    """Update a habit.

    Args:
        habit_id: The habit ID
        name: New name
        description: New description
        color: New color
        archived: Archive status

    Returns:
        Updated habit or None
    """
    if habit_id not in habits:
        return None

    habit = habits[habit_id]
    if name is not None:
        habit["name"] = name
    if description is not None:
        habit["description"] = description
    if color is not None:
        habit["color"] = color
    if archived is not None:
        habit["archived"] = archived
    _save()

    return Habit(**habit)


@mcp.tool
def delete_habit(habit_id: int) -> bool:
    """Delete a habit.

    Args:
        habit_id: The habit ID

    Returns:
        True if deleted, False if not found
    """
    if habit_id in habits:
        del habits[habit_id]
        # Also remove associated check-ins
        keys_to_delete = [k for k in check_ins.keys() if k.startswith(f"{habit_id}:")]
        for key in keys_to_delete:
            del check_ins[key]
        _save()
        return True
    return False


# Check-in Management
@mcp.tool
def check_in(habit_id: int, date: Optional[str] = None, completed: bool = True, notes: Optional[str] = None) -> CheckIn:
    """Record a habit check-in.

    Args:
        habit_id: The habit ID
        date: Date of check-in (YYYY-MM-DD), defaults to today
        completed: Whether the habit was completed
        notes: Optional notes for this check-in

    Returns:
        The check-in record
    """
    if habit_id not in habits:
        raise ValueError(f"Habit {habit_id} not found")

    date_str = date or datetime.now().strftime("%Y-%m-%d")
    key = _get_checkin_key(habit_id, date_str)

    record = CheckIn(
        habit_id=habit_id,
        date=date_str,
        completed=completed,
        notes=notes,
        recorded_at=datetime.now().isoformat()
    )
    check_ins[key] = record.model_dump()
    _save()

    return record


@mcp.tool
def batch_check_in(habit_ids: list[int], date: Optional[str] = None) -> list[CheckIn]:
    """Check in multiple habits at once.

    Args:
        habit_ids: List of habit IDs to check in
        date: Date of check-in (YYYY-MM-DD), defaults to today

    Returns:
        List of check-in records
    """
    date_str = date or datetime.now().strftime("%Y-%m-%d")
    results = []

    for habit_id in habit_ids:
        try:
            result = check_in(habit_id, date_str, completed=True)
            results.append(result)
        except ValueError:
            # Skip habits that don't exist, but continue
            pass

    return results


@mcp.tool
def get_check_in(habit_id: int, date: str) -> Optional[CheckIn]:
    """Get a specific check-in.

    Args:
        habit_id: The habit ID
        date: The date (YYYY-MM-DD)

    Returns:
        Check-in record or None
    """
    key = _get_checkin_key(habit_id, date)
    if key in check_ins:
        return CheckIn(**check_ins[key])
    return None


@mcp.tool
def get_habit_history(habit_id: int, days: int = 30) -> list[CheckIn]:
    """Get check-in history for a habit.

    Args:
        habit_id: The habit ID
        days: Number of days to retrieve

    Returns:
        List of check-ins for the period
    """
    if habit_id not in habits:
        return []

    history = []
    today = datetime.now()

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        key = _get_checkin_key(habit_id, date_str)

        if key in check_ins:
            history.append(CheckIn(**check_ins[key]))
        else:
            history.append(CheckIn(
                habit_id=habit_id,
                date=date_str,
                completed=False,
                notes=None,
                recorded_at=""
            ))

    return history


# Analytics
@mcp.tool
def get_daily_summary(date: Optional[str] = None) -> dict:
    """Get a summary of all habits for a specific day.

    Args:
        date: Date to summarize (YYYY-MM-DD), defaults to today

    Returns:
        Summary with completed and pending habits
    """
    date_str = date or datetime.now().strftime("%Y-%m-%d")

    completed = []
    pending = []

    for habit in habits.values():
        if habit.get("archived"):
            continue

        key = _get_checkin_key(habit["id"], date_str)
        check_in_record = check_ins.get(key)

        habit_info = {
            "id": habit["id"],
            "name": habit["name"],
            "color": habit["color"]
        }

        if check_in_record and check_in_record.get("completed"):
            completed.append(habit_info)
        else:
            pending.append(habit_info)

    return {
        "date": date_str,
        "total": len(completed) + len(pending),
        "completed": completed,
        "pending": pending,
        "completion_rate": round((len(completed) / (len(completed) + len(pending))) * 100, 1) if (len(completed) + len(pending)) > 0 else 0
    }


@mcp.tool
def get_streak_leaderboard() -> list[dict]:
    """Get habits ranked by current streak.

    Returns:
        List of habits with their streaks, sorted by streak
    """
    leaderboard = []

    for habit in habits.values():
        if habit.get("archived"):
            continue

        streak = _calculate_streak(habit["id"])
        leaderboard.append({
            "id": habit["id"],
            "name": habit["name"],
            "current_streak": streak,
            "completion_rate_30d": round(_calculate_completion_rate(habit["id"]), 1)
        })

    return sorted(leaderboard, key=lambda x: x["current_streak"], reverse=True)


@mcp.tool
def get_weekly_overview(start_date: Optional[str] = None) -> dict:
    """Get a weekly overview of habit completions.

    Args:
        start_date: Start of the week (YYYY-MM-DD), defaults to this Monday

    Returns:
        Weekly overview with daily completion counts
    """
    today = datetime.now()
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        # Get Monday of current week
        start = today - timedelta(days=today.weekday())

    days = []
    active_habits = [h for h in habits.values() if not h.get("archived")]

    for i in range(7):
        date = start + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")

        completed_count = 0
        for habit in active_habits:
            key = _get_checkin_key(habit["id"], date_str)
            if check_ins.get(key, {}).get("completed"):
                completed_count += 1

        days.append({
            "date": date_str,
            "day_name": date.strftime("%A"),
            "completed": completed_count,
            "total": len(active_habits),
            "percentage": round((completed_count / len(active_habits)) * 100, 1) if active_habits else 0
        })

    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": (start + timedelta(days=6)).strftime("%Y-%m-%d"),
        "total_habits": len(active_habits),
        "days": days
    }


# Resources
@mcp.resource("habits://today")
def get_today_resource() -> str:
    """Resource showing today's habit status."""
    summary = get_daily_summary()

    lines = [f"# Habits for {summary['date']}\n"]
    lines.append(f"**Completion Rate:** {summary['completion_rate']}%\n")

    lines.append("## Completed")
    if summary["completed"]:
        for h in summary["completed"]:
            lines.append(f"- [x] {h['name']}")
    else:
        lines.append("_No habits completed yet_")

    lines.append("\n## Pending")
    if summary["pending"]:
        for h in summary["pending"]:
            lines.append(f"- [ ] {h['name']}")
    else:
        lines.append("_All done!_")

    return "\n".join(lines)


@mcp.resource("habits://leaderboard")
def get_leaderboard_resource() -> str:
    """Resource showing streak leaderboard."""
    leaderboard = get_streak_leaderboard()

    if not leaderboard:
        return "# Streak Leaderboard\n\nNo active habits."

    lines = ["# Streak Leaderboard\n"]

    for i, entry in enumerate(leaderboard, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        lines.append(f"{emoji} **{entry['name']}** - {entry['current_streak']} day streak ({entry['completion_rate_30d']}% 30d)")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()