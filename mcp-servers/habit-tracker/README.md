# Habit Tracker MCP Server

A FastMCP server for tracking daily habits, streaks, and progress.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Habit Management

| Tool | Description |
|------|-------------|
| `create_habit` | Create a new habit to track |
| `get_habit` | Get a habit with streak info |
| `list_habits` | List all habits |
| `update_habit` | Update habit properties |
| `delete_habit` | Delete a habit |

### Check-in Management

| Tool | Description |
|------|-------------|
| `check_in` | Record a habit check-in |
| `batch_check_in` | Check in multiple habits at once |
| `get_check_in` | Get a specific check-in |
| `get_habit_history` | Get check-in history |

### Analytics

| Tool | Description |
|------|-------------|
| `get_daily_summary` | Get summary for a specific day |
| `get_streak_leaderboard` | Get habits ranked by streak |
| `get_weekly_overview` | Get weekly completion overview |

## Habit Frequencies

- `daily` - Every day
- `weekly` - Weekly
- `custom` - Custom days (e.g., Mon/Wed/Fri)

## Resources

| Resource | Description |
|----------|-------------|
| `habits://today` | Today's habit status with completion |
| `habits://leaderboard` | Streak leaderboard |

## Example Usage

```python
# Create habits
habit1 = create_habit(
    name="Exercise",
    description="30 minutes of exercise",
    frequency="daily",
    color="#4CAF50"
)

habit2 = create_habit(
    name="Read",
    frequency="daily",
    target_days=[0, 2, 4]  # Mon, Wed, Fri
)

# Check in for today
check_in(habit_id=1, completed=True, notes="Ran 5km")

# Batch check-in
batch_check_in(habit_ids=[1, 2, 3])

# Get today's summary
summary = get_daily_summary()
# Returns: date, total, completed, pending, completion_rate

# Get streak leaderboard
leaderboard = get_streak_leaderboard()
# Returns habits sorted by current_streak

# Get habit history
history = get_habit_history(habit_id=1, days=30)

# Get weekly overview
week = get_weekly_overview()
# Returns: days with completion counts for each day
```

## Streak Calculation

- Streaks count consecutive days of completion
- If today isn't completed yet, streak counts from yesterday
- Maximum tracking: 365 days

## Storage

This server uses in-memory storage. Data is not persisted between restarts.