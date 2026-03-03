# Task Automator MCP Server

A FastMCP server for automating repetitive tasks and workflows.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Workflow Management

| Tool | Description |
|------|-------------|
| `create_workflow` | Create a new workflow |
| `get_workflow` | Get workflow by ID |
| `update_workflow` | Update workflow |
| `delete_workflow` | Delete workflow |
| `list_workflows` | List all workflows |
| `add_workflow_step` | Add step to workflow |

### Template Management

| Tool | Description |
|------|-------------|
| `create_template` | Create a reusable template |
| `get_template` | Get template by ID |
| `render_template` | Render template with variables |
| `list_templates` | List all templates |
| `delete_template` | Delete template |

### Trigger Management

| Tool | Description |
|------|-------------|
| `create_trigger` | Create a trigger for workflow |
| `list_triggers` | List triggers |
| `delete_trigger` | Delete trigger |

### Execution

| Tool | Description |
|------|-------------|
| `execute_workflow` | Execute a workflow |
| `get_execution` | Get execution record |
| `get_workflow_executions` | Get execution history |

### Quick Actions

| Tool | Description |
|------|-------------|
| `quick_action` | Execute a quick action |
| `create_snippet` | Create code snippet |
| `list_snippets` | List code snippets |

## Template Variables

Templates use `{{variable}}` syntax:

```python
template = create_template(
    name="Email Template",
    content="Hello {{name}}, your order {{order_id}} is ready.",
    variables=["name", "order_id"]
)

rendered = render_template(
    template_id=1,
    variables={"name": "Alice", "order_id": "12345"}
)
```

## Workflow Steps

Each step has:
- `action` - The action to perform
- `params` - Parameters for the action
- `condition` - Optional condition to check

Built-in actions:
- `log` - Log a message
- `wait` - Wait for duration
- `set_variable` - Set a variable
- `render_template` - Render a template

## Quick Actions

- `generate_uuid` - Generate a UUID
- `generate_timestamp` - Get current timestamp
- `format_date` - Format current date
- `json_format` - Format JSON data
- `base64_encode` - Encode to base64
- `base64_decode` - Decode from base64

## Resources

| Resource | Description |
|----------|-------------|
| `automator://workflows` | All workflows |
| `automator://templates` | All templates |

## Example Usage

```python
# Create a template
template = create_template(
    name="Report Template",
    content="Report for {{date}}:\n{{content}}",
    variables=["date", "content"]
)

# Create a workflow
workflow = create_workflow(
    name="Daily Report",
    description="Generate daily report",
    steps=[
        {"action": "set_variable", "params": {"name": "date", "value": "today"}},
        {"action": "render_template", "params": {"template_id": 1}},
        {"action": "log", "params": {"message": "Report generated"}}
    ]
)

# Execute workflow
execution = execute_workflow(workflow_id=1, context={"content": "All systems operational"})

# Quick action
result = quick_action("generate_uuid")
# Returns: {"action": "generate_uuid", "output": "a1b2c3d4-..."}

# Create snippet
snippet = create_snippet(
    name="API Call",
    code="import requests\nresponse = requests.get(url)",
    language="python"
)
```

## Statistics

```python
stats = get_automation_stats()
# Returns: total_workflows, enabled_workflows, total_templates,
#          total_triggers, total_executions, executions_today
```

## Storage

This server uses in-memory storage. Data is not persisted between restarts.