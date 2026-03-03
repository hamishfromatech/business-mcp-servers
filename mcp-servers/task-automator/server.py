"""
Task Automator MCP Server
A FastMCP server for automating repetitive tasks and workflows.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import uuid
from fastmcp import FastMCP

mcp = FastMCP(
    name="Task Automator",
    instructions="A task automation server for creating workflows, templates, and automating repetitive tasks."
)

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "automator.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "workflows": {}, "templates": {}, "executions": {}, "triggers": {},
        "next_workflow_id": 1, "next_template_id": 1, "next_execution_id": 1, "next_trigger_id": 1
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
workflows: dict[int, dict] = {int(k): v for k, v in _data.get("workflows", {}).items()}
templates: dict[int, dict] = {int(k): v for k, v in _data.get("templates", {}).items()}
executions: dict[int, dict] = {int(k): v for k, v in _data.get("executions", {}).items()}
triggers: dict[int, dict] = {int(k): v for k, v in _data.get("triggers", {}).items()}

_next_workflow_id = _data.get("next_workflow_id", 1)
_next_template_id = _data.get("next_template_id", 1)
_next_execution_id = _data.get("next_execution_id", 1)
_next_trigger_id = _data.get("next_trigger_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "workflows": workflows, "templates": templates,
        "executions": executions, "triggers": triggers,
        "next_workflow_id": _next_workflow_id, "next_template_id": _next_template_id,
        "next_execution_id": _next_execution_id, "next_trigger_id": _next_trigger_id
    })


def _get_next_workflow_id() -> int:
    global _next_workflow_id
    id_ = _next_workflow_id
    _next_workflow_id += 1
    return id_


def _get_next_template_id() -> int:
    global _next_template_id
    id_ = _next_template_id
    _next_template_id += 1
    return id_


def _get_next_execution_id() -> int:
    global _next_execution_id
    id_ = _next_execution_id
    _next_execution_id += 1
    return id_


def _get_next_trigger_id() -> int:
    global _next_trigger_id
    id_ = _next_trigger_id
    _next_trigger_id += 1
    return id_


# Workflow Management
@mcp.tool
def create_workflow(
    name: str,
    description: Optional[str] = None,
    steps: Optional[list[dict]] = None
) -> dict:
    """Create a new workflow.

    Args:
        name: Workflow name
        description: Workflow description
        steps: List of workflow steps, each with 'action', 'params', and optional 'condition'

    Returns:
        The created workflow
    """
    workflow_id = _get_next_workflow_id()
    workflow = {
        "id": workflow_id,
        "name": name,
        "description": description,
        "steps": steps or [],
        "enabled": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    workflows[workflow_id] = workflow
    _save()
    return workflow


@mcp.tool
def get_workflow(workflow_id: int) -> Optional[dict]:
    """Get a workflow by ID.

    Args:
        workflow_id: The workflow ID

    Returns:
        Workflow details or None
    """
    return workflows.get(workflow_id)


@mcp.tool
def update_workflow(
    workflow_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    steps: Optional[list[dict]] = None,
    enabled: Optional[bool] = None
) -> Optional[dict]:
    """Update a workflow.

    Args:
        workflow_id: The workflow ID
        name: New name
        description: New description
        steps: New steps
        enabled: Enable/disable workflow

    Returns:
        Updated workflow or None
    """
    if workflow_id not in workflows:
        return None

    workflow = workflows[workflow_id]
    if name is not None:
        workflow["name"] = name
    if description is not None:
        workflow["description"] = description
    if steps is not None:
        workflow["steps"] = steps
    if enabled is not None:
        workflow["enabled"] = enabled

    workflow["updated_at"] = datetime.now().isoformat()
    _save()
    return workflow


@mcp.tool
def delete_workflow(workflow_id: int) -> bool:
    """Delete a workflow.

    Args:
        workflow_id: The workflow ID

    Returns:
        True if deleted, False if not found
    """
    if workflow_id in workflows:
        del workflows[workflow_id]
        _save()
        return True
    return False


@mcp.tool
def list_workflows(enabled_only: bool = False) -> list[dict]:
    """List all workflows.

    Args:
        enabled_only: Only return enabled workflows

    Returns:
        List of workflows
    """
    result = list(workflows.values())
    if enabled_only:
        result = [w for w in result if w.get("enabled")]
    return result


@mcp.tool
def add_workflow_step(
    workflow_id: int,
    action: str,
    params: Optional[dict] = None,
    condition: Optional[str] = None,
    position: Optional[int] = None
) -> Optional[dict]:
    """Add a step to a workflow.

    Args:
        workflow_id: The workflow ID
        action: The action to perform
        params: Parameters for the action
        condition: Optional condition to check before executing
        position: Position to insert step (appends to end if not specified)

    Returns:
        Updated workflow or None
    """
    if workflow_id not in workflows:
        return None

    step = {
        "action": action,
        "params": params or {},
        "condition": condition
    }

    workflow = workflows[workflow_id]
    if position is not None:
        workflow["steps"].insert(position, step)
    else:
        workflow["steps"].append(step)

    workflow["updated_at"] = datetime.now().isoformat()
    _save()
    return workflow


# Template Management
@mcp.tool
def create_template(
    name: str,
    content: str,
    variables: Optional[list[str]] = None,
    category: Optional[str] = None
) -> dict:
    """Create a reusable template.

    Args:
        name: Template name
        content: Template content with {{variable}} placeholders
        variables: List of variable names used in the template
        category: Optional category for organizing templates

    Returns:
        The created template
    """
    template_id = _get_next_template_id()
    template = {
        "id": template_id,
        "name": name,
        "content": content,
        "variables": variables or [],
        "category": category,
        "created_at": datetime.now().isoformat()
    }
    templates[template_id] = template
    _save()
    return template


@mcp.tool
def get_template(template_id: int) -> Optional[dict]:
    """Get a template by ID.

    Args:
        template_id: The template ID

    Returns:
        Template details or None
    """
    return templates.get(template_id)


@mcp.tool
def render_template(template_id: int, variables: dict) -> Optional[str]:
    """Render a template with variables.

    Args:
        template_id: The template ID
        variables: Dictionary of variable values

    Returns:
        Rendered template content or None
    """
    if template_id not in templates:
        return None

    template = templates[template_id]
    content = template["content"]

    for var_name, var_value in variables.items():
        placeholder = "{{" + var_name + "}}"
        content = content.replace(placeholder, str(var_value))

    return content


@mcp.tool
def list_templates(category: Optional[str] = None) -> list[dict]:
    """List all templates.

    Args:
        category: Optional category filter

    Returns:
        List of templates
    """
    result = list(templates.values())
    if category:
        result = [t for t in result if t.get("category") == category]
    return result


@mcp.tool
def delete_template(template_id: int) -> bool:
    """Delete a template.

    Args:
        template_id: The template ID

    Returns:
        True if deleted, False if not found
    """
    if template_id in templates:
        del templates[template_id]
        _save()
        return True
    return False


# Trigger Management
@mcp.tool
def create_trigger(
    name: str,
    workflow_id: int,
    trigger_type: str,
    config: Optional[dict] = None
) -> dict:
    """Create a trigger for a workflow.

    Args:
        name: Trigger name
        workflow_id: The workflow to trigger
        trigger_type: Type of trigger (manual, schedule, event)
        config: Trigger configuration (schedule, event type, etc.)

    Returns:
        The created trigger
    """
    if workflow_id not in workflows:
        raise ValueError(f"Workflow {workflow_id} not found")

    trigger_id = _get_next_trigger_id()
    trigger = {
        "id": trigger_id,
        "name": name,
        "workflow_id": workflow_id,
        "trigger_type": trigger_type,
        "config": config or {},
        "enabled": True,
        "created_at": datetime.now().isoformat()
    }
    triggers[trigger_id] = trigger
    _save()
    return trigger


@mcp.tool
def list_triggers(workflow_id: Optional[int] = None) -> list[dict]:
    """List all triggers.

    Args:
        workflow_id: Optional filter by workflow

    Returns:
        List of triggers
    """
    result = list(triggers.values())
    if workflow_id is not None:
        result = [t for t in result if t["workflow_id"] == workflow_id]
    return result


@mcp.tool
def delete_trigger(trigger_id: int) -> bool:
    """Delete a trigger.

    Args:
        trigger_id: The trigger ID

    Returns:
        True if deleted, False if not found
    """
    if trigger_id in triggers:
        del triggers[trigger_id]
        _save()
        return True
    return False


# Execution
@mcp.tool
def execute_workflow(workflow_id: int, context: Optional[dict] = None) -> dict:
    """Execute a workflow.

    Args:
        workflow_id: The workflow ID
        context: Optional context data for the execution

    Returns:
        Execution record
    """
    if workflow_id not in workflows:
        raise ValueError(f"Workflow {workflow_id} not found")

    workflow = workflows[workflow_id]
    if not workflow.get("enabled"):
        raise ValueError(f"Workflow {workflow_id} is disabled")

    execution_id = _get_next_execution_id()
    execution = {
        "id": execution_id,
        "workflow_id": workflow_id,
        "workflow_name": workflow["name"],
        "context": context or {},
        "steps_executed": 0,
        "status": "completed",
        "results": [],
        "started_at": datetime.now().isoformat(),
        "completed_at": None
    }

    # Execute each step
    for i, step in enumerate(workflow["steps"]):
        step_result = {
            "step": i + 1,
            "action": step["action"],
            "status": "executed",
            "output": None
        }

        # Simulate execution of common actions
        action = step["action"]
        params = step.get("params", {})

        if action == "log":
            step_result["output"] = f"Logged: {params.get('message', '')}"
        elif action == "wait":
            step_result["output"] = f"Waited: {params.get('duration', 0)} seconds"
        elif action == "set_variable":
            step_result["output"] = f"Set {params.get('name', '')} = {params.get('value', '')}"
        elif action == "render_template":
            template_id = params.get("template_id")
            if template_id and template_id in templates:
                rendered = render_template(template_id, context or {})
                step_result["output"] = rendered
        else:
            step_result["output"] = f"Action '{action}' executed"

        execution["results"].append(step_result)
        execution["steps_executed"] += 1

    execution["completed_at"] = datetime.now().isoformat()
    executions[execution_id] = execution
    _save()

    return execution


@mcp.tool
def get_execution(execution_id: int) -> Optional[dict]:
    """Get an execution record.

    Args:
        execution_id: The execution ID

    Returns:
        Execution record or None
    """
    return executions.get(execution_id)


@mcp.tool
def get_workflow_executions(workflow_id: int, limit: int = 10) -> list[dict]:
    """Get execution history for a workflow.

    Args:
        workflow_id: The workflow ID
        limit: Maximum number of records

    Returns:
        List of executions
    """
    result = [e for e in executions.values() if e["workflow_id"] == workflow_id]
    result.sort(key=lambda x: x["started_at"], reverse=True)
    return result[:limit]


# Snippets and Quick Actions
@mcp.tool
def create_snippet(name: str, code: str, language: str = "python") -> dict:
    """Create a reusable code snippet.

    Args:
        name: Snippet name
        code: The code content
        language: Programming language

    Returns:
        The created snippet (stored as a template)
    """
    return create_template(
        name=f"snippet:{name}",
        content=code,
        category=f"snippet:{language}"
    )


@mcp.tool
def list_snippets(language: Optional[str] = None) -> list[dict]:
    """List all code snippets.

    Args:
        language: Optional language filter

    Returns:
        List of snippets
    """
    category = f"snippet:{language}" if language else None
    result = [t for t in templates.values() if t.get("name", "").startswith("snippet:")]
    if language:
        result = [t for t in result if t.get("category") == category]
    return result


@mcp.tool
def quick_action(action: str, params: Optional[dict] = None) -> dict:
    """Execute a quick action without creating a workflow.

    Args:
        action: The action to perform
        params: Action parameters

    Returns:
        Action result
    """
    import base64 as b64

    params = params or {}
    result = {
        "action": action,
        "params": params,
        "status": "completed",
        "output": None,
        "executed_at": datetime.now().isoformat()
    }

    if action == "generate_uuid":
        result["output"] = str(uuid.uuid4())
    elif action == "generate_timestamp":
        result["output"] = datetime.now().isoformat()
    elif action == "format_date":
        date_format = params.get("format", "%Y-%m-%d")
        result["output"] = datetime.now().strftime(date_format)
    elif action == "json_format":
        data = params.get("data", {})
        result["output"] = json.dumps(data, indent=2)
    elif action == "base64_encode":
        text = params.get("text", "")
        result["output"] = b64.b64encode(text.encode()).decode()
    elif action == "base64_decode":
        encoded = params.get("encoded", "")
        result["output"] = b64.b64decode(encoded.encode()).decode()
    else:
        result["output"] = f"Unknown action: {action}"
        result["status"] = "unknown_action"

    return result


# Statistics
@mcp.tool
def get_automation_stats() -> dict:
    """Get automation statistics.

    Returns:
        Statistics about workflows, templates, and executions
    """
    return {
        "total_workflows": len(workflows),
        "enabled_workflows": len([w for w in workflows.values() if w.get("enabled")]),
        "total_templates": len(templates),
        "total_triggers": len(triggers),
        "total_executions": len(executions),
        "executions_today": len([
            e for e in executions.values()
            if e["started_at"].startswith(datetime.now().strftime("%Y-%m-%d"))
        ])
    }


# Resources
@mcp.resource("automator://workflows")
def get_workflows_resource() -> str:
    """Resource showing all workflows."""
    all_workflows = list_workflows()

    if not all_workflows:
        return "# Workflows\n\nNo workflows created yet."

    lines = ["# Workflows\n"]
    for w in all_workflows:
        status = "✅" if w.get("enabled") else "⏸️"
        lines.append(f"## {status} {w['name']}")
        lines.append(f"- Steps: {len(w.get('steps', []))}")
        lines.append(f"- Status: {'Enabled' if w.get('enabled') else 'Disabled'}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("automator://templates")
def get_templates_resource() -> str:
    """Resource showing all templates."""
    all_templates = list_templates()

    if not all_templates:
        return "# Templates\n\nNo templates created yet."

    lines = ["# Templates\n"]
    for t in all_templates:
        if t.get("name", "").startswith("snippet:"):
            continue  # Skip snippets
        lines.append(f"## {t['name']}")
        if t.get("category"):
            lines.append(f"- Category: {t['category']}")
        lines.append(f"- Variables: {', '.join(t.get('variables', [])) or 'None'}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()