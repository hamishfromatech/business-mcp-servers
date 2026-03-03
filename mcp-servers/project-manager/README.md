# Project Manager MCP Server

A FastMCP server for managing projects, tasks, milestones, and team members.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Team Management

| Tool | Description |
|------|-------------|
| `create_team_member` | Create a team member |
| `list_team_members` | List all team members |
| `get_member` | Get team member by ID |

### Project Management

| Tool | Description |
|------|-------------|
| `create_project` | Create a new project |
| `get_project` | Get project by ID |
| `update_project` | Update project details |
| `delete_project` | Delete a project |
| `list_projects` | List projects with filter |
| `add_member_to_project` | Add member to project |

### Task Management

| Tool | Description |
|------|-------------|
| `create_task` | Create a task in a project |
| `get_task` | Get task by ID |
| `update_task` | Update task details |
| `delete_task` | Delete a task |
| `get_project_tasks` | Get tasks for a project |
| `get_subtasks` | Get subtasks of a task |
| `get_member_tasks` | Get tasks assigned to member |
| `get_overdue_tasks` | Get overdue tasks |

### Milestone Management

| Tool | Description |
|------|-------------|
| `create_milestone` | Create a milestone |
| `complete_milestone` | Mark milestone complete |
| `get_project_milestones` | Get milestones for project |

### Analytics

| Tool | Description |
|------|-------------|
| `get_project_progress` | Get progress statistics |

## Project Statuses

- `planning` - Project in planning phase
- `active` - Project is active
- `on_hold` - Project on hold
- `completed` - Project completed
- `cancelled` - Project cancelled

## Task Statuses

- `todo` - Not started
- `in_progress` - In progress
- `review` - In review
- `done` - Completed
- `cancelled` - Cancelled

## Task Priorities

- `low` - Low priority
- `medium` - Medium priority
- `high` - High priority
- `urgent` - Urgent

## Resources

| Resource | Description |
|----------|-------------|
| `projects://active` | Active projects with progress |
| `tasks://overdue` | Overdue tasks |

## Example Usage

```python
# Create team members
alice = create_team_member(name="Alice", email="alice@company.com", role="PM")
bob = create_team_member(name="Bob", email="bob@company.com", role="Developer")

# Create project
project = create_project(
    name="Website Redesign",
    description="Redesign company website",
    start_date="2024-01-01",
    end_date="2024-03-31",
    owner_id=1
)

# Add members to project
add_member_to_project(project_id=1, member_id=2)

# Create tasks
task = create_task(
    project_id=1,
    title="Design homepage mockup",
    description="Create wireframes and mockups",
    assignee_id=1,
    priority="high",
    due_date="2024-01-15"
)

# Create subtask
subtask = create_task(
    project_id=1,
    title="Get design approval",
    parent_task_id=1,
    assignee_id=2
)

# Create milestone
milestone = create_milestone(
    project_id=1,
    title="Phase 1 Complete",
    due_date="2024-01-31"
)

# Update task status
update_task(task_id=1, status="in_progress")

# Get project progress
progress = get_project_progress(project_id=1)
# Returns: total_tasks, completed, in_progress, todo, progress_percent
```

## Storage

This server uses in-memory storage. Data is not persisted between restarts.