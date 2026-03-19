"""
Project Manager MCP Server
A FastMCP server for managing projects, tasks, and team collaboration.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
from enum import Enum
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Project Manager",
    instructions="A project management server for organizing projects, tasks, milestones, and team members."
)


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TeamMember(BaseModel):
    """A team member."""
    id: int
    name: str
    email: str
    role: Optional[str] = None
    created_at: str


class Project(BaseModel):
    """A project."""
    id: int
    name: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    owner_id: Optional[int] = None
    status: str
    member_ids: list[int] = []
    created_at: str
    updated_at: str


class Task(BaseModel):
    """A task in a project."""
    id: int
    project_id: int
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    priority: str
    status: str
    due_date: Optional[str] = None
    parent_task_id: Optional[int] = None
    created_at: str
    updated_at: str


class Milestone(BaseModel):
    """A project milestone."""
    id: int
    project_id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    completed: bool = False
    completed_at: Optional[str] = None
    created_at: str

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "projects.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "projects": {}, "tasks": {}, "milestones": {}, "team_members": {},
        "next_project_id": 1, "next_task_id": 1, "next_milestone_id": 1, "next_member_id": 1
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
projects: dict[int, dict] = {int(k): v for k, v in _data.get("projects", {}).items()}
tasks: dict[int, dict] = {int(k): v for k, v in _data.get("tasks", {}).items()}
milestones: dict[int, dict] = {int(k): v for k, v in _data.get("milestones", {}).items()}
team_members: dict[int, dict] = {int(k): v for k, v in _data.get("team_members", {}).items()}

_next_project_id = _data.get("next_project_id", 1)
_next_task_id = _data.get("next_task_id", 1)
_next_milestone_id = _data.get("next_milestone_id", 1)
_next_member_id = _data.get("next_member_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "projects": projects, "tasks": tasks, "milestones": milestones,
        "team_members": team_members,
        "next_project_id": _next_project_id, "next_task_id": _next_task_id,
        "next_milestone_id": _next_milestone_id, "next_member_id": _next_member_id
    })


def _get_next_project_id() -> int:
    global _next_project_id
    id_ = _next_project_id
    _next_project_id += 1
    return id_


def _get_next_task_id() -> int:
    global _next_task_id
    id_ = _next_task_id
    _next_task_id += 1
    return id_


def _get_next_milestone_id() -> int:
    global _next_milestone_id
    id_ = _next_milestone_id
    _next_milestone_id += 1
    return id_


def _get_next_member_id() -> int:
    global _next_member_id
    id_ = _next_member_id
    _next_member_id += 1
    return id_


# Team Member Management
@mcp.tool
def create_team_member(name: str, email: str, role: Optional[str] = None) -> TeamMember:
    """Create a team member.

    Args:
        name: Member name
        email: Member email
        role: Member role/title

    Returns:
        The created team member
    """
    member_id = _get_next_member_id()
    member = TeamMember(
        id=member_id,
        name=name,
        email=email,
        role=role,
        created_at=datetime.now().isoformat()
    )
    team_members[member_id] = member.model_dump()
    _save()
    return member


@mcp.tool
def list_team_members() -> list[TeamMember]:
    """List all team members.

    Returns:
        List of team members
    """
    return [TeamMember(**m) for m in team_members.values()]


@mcp.tool
def get_member(member_id: int) -> Optional[TeamMember]:
    """Get a team member by ID.

    Args:
        member_id: The member ID

    Returns:
        Team member details or None
    """
    if member_id in team_members:
        return TeamMember(**team_members[member_id])
    return None


# Project Management
@mcp.tool
def create_project(
    name: str,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    owner_id: Optional[int] = None
) -> Project:
    """Create a new project.

    Args:
        name: Project name
        description: Project description
        start_date: Start date (YYYY-MM-DD)
        end_date: Target end date (YYYY-MM-DD)
        owner_id: ID of the project owner

    Returns:
        The created project
    """
    project_id = _get_next_project_id()
    project = Project(
        id=project_id,
        name=name,
        description=description,
        start_date=start_date,
        end_date=end_date,
        owner_id=owner_id,
        status=ProjectStatus.PLANNING.value,
        member_ids=[],
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    projects[project_id] = project.model_dump()
    _save()
    return project


@mcp.tool
def get_project(project_id: int) -> Optional[Project]:
    """Get a project by ID.

    Args:
        project_id: The project ID

    Returns:
        Project details or None
    """
    if project_id in projects:
        return Project(**projects[project_id])
    return None


@mcp.tool
def update_project(
    project_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None
) -> Optional[Project]:
    """Update a project.

    Args:
        project_id: The project ID
        name: New name
        description: New description
        start_date: New start date
        end_date: New end date
        status: New status

    Returns:
        Updated project or None
    """
    if project_id not in projects:
        return None

    project = projects[project_id]
    if name is not None:
        project["name"] = name
    if description is not None:
        project["description"] = description
    if start_date is not None:
        project["start_date"] = start_date
    if end_date is not None:
        project["end_date"] = end_date
    if status is not None:
        valid_statuses = [s.value for s in ProjectStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        project["status"] = status

    project["updated_at"] = datetime.now().isoformat()
    _save()
    return Project(**project)


@mcp.tool
def delete_project(project_id: int) -> bool:
    """Delete a project and its tasks.

    Args:
        project_id: The project ID

    Returns:
        True if deleted, False if not found
    """
    if project_id in projects:
        del projects[project_id]
        # Delete associated tasks and milestones
        tasks_to_delete = [tid for tid, t in tasks.items() if t.get("project_id") == project_id]
        for tid in tasks_to_delete:
            del tasks[tid]
        milestones_to_delete = [mid for mid, m in milestones.items() if m.get("project_id") == project_id]
        for mid in milestones_to_delete:
            del milestones[mid]
        _save()
        return True
    return False


@mcp.tool
def add_member_to_project(project_id: int, member_id: int) -> Optional[dict]:
    """Add a team member to a project.

    Args:
        project_id: The project ID
        member_id: The member ID

    Returns:
        Updated project or None
    """
    if project_id not in projects:
        return None
    if member_id not in team_members:
        raise ValueError(f"Member {member_id} not found")

    project = projects[project_id]
    if member_id not in project["member_ids"]:
        project["member_ids"].append(member_id)
        project["updated_at"] = datetime.now().isoformat()
        _save()

    return project


@mcp.tool
def list_projects(status: Optional[str] = None) -> list[dict]:
    """List projects with optional filter.

    Args:
        status: Filter by status

    Returns:
        List of projects
    """
    result = list(projects.values())

    if status:
        result = [p for p in result if p["status"] == status]

    return sorted(result, key=lambda x: x["updated_at"], reverse=True)


# Task Management
@mcp.tool
def create_task(
    project_id: int,
    title: str,
    description: Optional[str] = None,
    assignee_id: Optional[int] = None,
    priority: str = "medium",
    due_date: Optional[str] = None,
    parent_task_id: Optional[int] = None
) -> Task:
    """Create a task in a project.

    Args:
        project_id: The project ID
        title: Task title
        description: Task description
        assignee_id: ID of assigned team member
        priority: Task priority (low, medium, high, urgent)
        due_date: Due date (YYYY-MM-DD)
        parent_task_id: ID of parent task for subtasks

    Returns:
        The created task
    """
    if project_id not in projects:
        raise ValueError(f"Project {project_id} not found")

    valid_priorities = [p.value for p in TaskPriority]
    if priority not in valid_priorities:
        raise ValueError(f"Invalid priority. Must be one of: {valid_priorities}")

    task_id = _get_next_task_id()
    task = Task(
        id=task_id,
        project_id=project_id,
        title=title,
        description=description,
        assignee_id=assignee_id,
        priority=priority,
        status=TaskStatus.TODO.value,
        due_date=due_date,
        parent_task_id=parent_task_id,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    tasks[task_id] = task.model_dump()
    _save()
    return task


@mcp.tool
def get_task(task_id: int) -> Optional[Task]:
    """Get a task by ID.

    Args:
        task_id: The task ID

    Returns:
        Task details or None
    """
    if task_id in tasks:
        return Task(**tasks[task_id])
    return None


@mcp.tool
def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    assignee_id: Optional[int] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    due_date: Optional[str] = None
) -> Optional[Task]:
    """Update a task.

    Args:
        task_id: The task ID
        title: New title
        description: New description
        assignee_id: New assignee
        priority: New priority
        status: New status
        due_date: New due date

    Returns:
        Updated task or None
    """
    if task_id not in tasks:
        return None

    task = tasks[task_id]
    if title is not None:
        task["title"] = title
    if description is not None:
        task["description"] = description
    if assignee_id is not None:
        task["assignee_id"] = assignee_id
    if priority is not None:
        valid_priorities = [p.value for p in TaskPriority]
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {valid_priorities}")
        task["priority"] = priority
    if status is not None:
        valid_statuses = [s.value for s in TaskStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        task["status"] = status
    if due_date is not None:
        task["due_date"] = due_date

    task["updated_at"] = datetime.now().isoformat()
    _save()
    return Task(**task)


@mcp.tool
def get_project_tasks(project_id: int, status: Optional[str] = None) -> list[Task]:
    """Get all tasks for a project.

    Args:
        project_id: The project ID
        status: Optional status filter

    Returns:
        List of tasks
    """
    result = [Task(**t) for t in tasks.values() if t["project_id"] == project_id]

    if status:
        result = [t for t in result if t.status == status]

    return sorted(result, key=lambda x: (x.priority, x.due_date or "zzzz"))


@mcp.tool
def get_subtasks(task_id: int) -> list[Task]:
    """Get all subtasks of a task.

    Args:
        task_id: The parent task ID

    Returns:
        List of subtasks
    """
    return [Task(**t) for t in tasks.values() if t.get("parent_task_id") == task_id]


@mcp.tool
def get_member_tasks(member_id: int) -> list[Task]:
    """Get all tasks assigned to a team member.

    Args:
        member_id: The member ID

    Returns:
        List of tasks
    """
    return [
        Task(**t) for t in tasks.values()
        if t.get("assignee_id") == member_id and t["status"] not in [TaskStatus.DONE.value, TaskStatus.CANCELLED.value]
    ]


@mcp.tool
def get_overdue_tasks() -> list[Task]:
    """Get all overdue tasks.

    Returns:
        List of overdue tasks
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return [
        Task(**t) for t in tasks.values()
        if t["status"] not in [TaskStatus.DONE.value, TaskStatus.CANCELLED.value]
        and t.get("due_date") and t["due_date"] < today
    ]


# Milestone Management
@mcp.tool
def create_milestone(
    project_id: int,
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None
) -> Milestone:
    """Create a milestone in a project.

    Args:
        project_id: The project ID
        title: Milestone title
        description: Milestone description
        due_date: Target date (YYYY-MM-DD)

    Returns:
        The created milestone
    """
    if project_id not in projects:
        raise ValueError(f"Project {project_id} not found")

    milestone_id = _get_next_milestone_id()
    milestone = Milestone(
        id=milestone_id,
        project_id=project_id,
        title=title,
        description=description,
        due_date=due_date,
        completed=False,
        completed_at=None,
        created_at=datetime.now().isoformat()
    )
    milestones[milestone_id] = milestone.model_dump()
    _save()
    return milestone


@mcp.tool
def complete_milestone(milestone_id: int) -> Optional[Milestone]:
    """Mark a milestone as complete.

    Args:
        milestone_id: The milestone ID

    Returns:
        Updated milestone or None
    """
    if milestone_id not in milestones:
        return None

    milestone = milestones[milestone_id]
    milestone["completed"] = True
    milestone["completed_at"] = datetime.now().isoformat()
    _save()
    return Milestone(**milestone)


@mcp.tool
def get_project_milestones(project_id: int) -> list[Milestone]:
    """Get all milestones for a project.

    Args:
        project_id: The project ID

    Returns:
        List of milestones
    """
    return [Milestone(**m) for m in milestones.values() if m["project_id"] == project_id]


# Analytics
@mcp.tool
def get_project_progress(project_id: int) -> dict:
    """Get progress statistics for a project.

    Args:
        project_id: The project ID

    Returns:
        Progress statistics
    """
    if project_id not in projects:
        raise ValueError(f"Project {project_id} not found")

    project_tasks = [t for t in tasks.values() if t["project_id"] == project_id]
    total = len(project_tasks)

    if total == 0:
        return {
            "project_id": project_id,
            "total_tasks": 0,
            "completed": 0,
            "in_progress": 0,
            "todo": 0,
            "progress_percent": 0
        }

    completed = len([t for t in project_tasks if t["status"] == TaskStatus.DONE.value])
    in_progress = len([t for t in project_tasks if t["status"] == TaskStatus.IN_PROGRESS.value])
    todo = len([t for t in project_tasks if t["status"] == TaskStatus.TODO.value])

    return {
        "project_id": project_id,
        "total_tasks": total,
        "completed": completed,
        "in_progress": in_progress,
        "todo": todo,
        "progress_percent": round((completed / total) * 100, 1)
    }


# Resources
@mcp.resource("projects://active")
def get_active_projects_resource() -> str:
    """Resource showing active projects."""
    active = list_projects(status="active")

    if not active:
        return "# Active Projects\n\nNo active projects."

    lines = ["# Active Projects\n"]
    for p in active:
        progress = get_project_progress(p["id"])
        lines.append(f"## {p['name']}")
        lines.append(f"- Status: {p['status']}")
        lines.append(f"- Progress: {progress['progress_percent']}%")
        lines.append(f"- Tasks: {progress['completed']}/{progress['total_tasks']}")
        if p.get("end_date"):
            lines.append(f"- Due: {p['end_date']}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("tasks://overdue")
def get_overdue_tasks_resource() -> str:
    """Resource showing overdue tasks."""
    overdue = get_overdue_tasks()

    if not overdue:
        return "# Overdue Tasks\n\nNo overdue tasks!"

    lines = ["# Overdue Tasks\n"]
    for t in overdue:
        project = projects.get(t["project_id"], {})
        lines.append(f"- **{t['title']}** (Project: {project.get('name', 'Unknown')})")
        lines.append(f"  - Due: {t['due_date']}")
        lines.append(f"  - Priority: {t['priority']}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()