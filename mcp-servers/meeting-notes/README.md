# Meeting Notes MCP Server

A FastMCP server for managing meetings, agendas, notes, and action items.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Attendee Management

| Tool | Description |
|------|-------------|
| `create_attendee` | Create an attendee profile |
| `list_attendees` | List all attendees |

### Meeting Management

| Tool | Description |
|------|-------------|
| `create_meeting` | Create a new meeting |
| `get_meeting` | Get meeting by ID |
| `update_meeting` | Update meeting details |
| `delete_meeting` | Delete a meeting |
| `list_meetings` | List meetings with filters |
| `add_attendee_to_meeting` | Add attendee to meeting |
| `remove_attendee_from_meeting` | Remove attendee from meeting |

### Agenda Management

| Tool | Description |
|------|-------------|
| `set_agenda` | Set meeting agenda |
| `add_agenda_item` | Add item to agenda |

### Notes

| Tool | Description |
|------|-------------|
| `set_meeting_notes` | Set meeting notes |
| `append_meeting_notes` | Append to meeting notes |

### Action Items

| Tool | Description |
|------|-------------|
| `create_action_item` | Create action item from meeting |
| `get_action_item` | Get action item by ID |
| `update_action_item` | Update action item |
| `get_meeting_actions` | Get actions for a meeting |
| `get_pending_actions` | Get all pending actions |
| `get_overdue_actions` | Get overdue actions |

## Meeting Statuses

- `scheduled` - Meeting is scheduled
- `in_progress` - Meeting is in progress
- `completed` - Meeting is completed
- `cancelled` - Meeting was cancelled

## Action Item Priorities

- `low` - Low priority
- `medium` - Medium priority
- `high` - High priority

## Action Item Statuses

- `pending` - Not started
- `in_progress` - In progress
- `completed` - Completed
- `cancelled` - Cancelled

## Resources

| Resource | Description |
|----------|-------------|
| `meetings://upcoming` | Upcoming scheduled meetings |
| `meetings://actions` | Pending and overdue action items |

## Example Usage

```python
# Create attendees
alice = create_attendee(name="Alice", email="alice@company.com", role="Manager")
bob = create_attendee(name="Bob", email="bob@company.com", role="Developer")

# Create meeting
meeting = create_meeting(
    title="Sprint Planning",
    scheduled_at="2024-01-15T10:00:00",
    duration_minutes=60,
    location="Conference Room A",
    description="Plan sprint 5",
    attendee_ids=[1, 2]
)

# Set agenda
set_agenda(meeting_id=1, agenda_items=[
    "Review backlog",
    "Estimate stories",
    "Assign tasks"
])

# Add notes during meeting
append_meeting_notes(
    meeting_id=1,
    notes="Decided to prioritize the API refactor."
)

# Create action items
create_action_item(
    meeting_id=1,
    description="Create API documentation",
    assignee_id=2,
    due_date="2024-01-20",
    priority="high"
)

# Get overdue actions
overdue = get_overdue_actions()
```

## Storage

This server uses in-memory storage. Data is not persisted between restarts.