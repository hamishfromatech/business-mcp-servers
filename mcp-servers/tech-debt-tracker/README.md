# Tech Debt Tracker MCP Server

A FastMCP server for tracking technical debt, managing refactoring tasks, and monitoring code quality metrics.

## Features

- **Debt Items**: Track technical debt with categories, priorities, and impact assessments
- **Interest Tracking**: Record "interest" (extra work) accrued by debt over time
- **Refactoring Tasks**: Plan and track refactoring efforts
- **Quality Metrics**: Record and monitor code quality metrics over time
- **Snapshots**: Capture debt state at points in time for comparison
- **Analytics**: Get summaries, priority items, and component-level debt analysis

## Installation

```bash
pip install fastmcp
```

## Usage

### Running the Server

```bash
cd mcp-servers/tech-debt-tracker
python server.py
```

### With FastMCP CLI

```bash
fastmcp run server.py
# or with hot reload
fastmcp dev server.py
```

## Tools

### Debt Items

| Tool | Description |
|------|-------------|
| `create_debt_item` | Create a new technical debt item |
| `get_debt_item` | Get a debt item by ID |
| `list_debt_items` | List debt items with filters |
| `update_debt_item` | Update a debt item |
| `resolve_debt_item` | Mark a debt item as resolved |
| `accrue_interest` | Record interest (extra work) on debt |
| `delete_debt_item` | Delete a debt item |

### Refactoring Tasks

| Tool | Description |
|------|-------------|
| `create_refactoring_task` | Create a refactoring task |
| `get_refactoring_task` | Get a task by ID |
| `list_refactoring_tasks` | List tasks with filters |
| `update_refactoring_task` | Update a task |
| `complete_refactoring_task` | Mark a task as completed |
| `delete_refactoring_task` | Delete a task |

### Quality Metrics

| Tool | Description |
|------|-------------|
| `record_quality_metric` | Record a code quality metric |
| `get_quality_metric` | Get a metric by ID |
| `list_quality_metrics` | List metrics with filters |
| `get_metric_history` | Get historical values for a metric |
| `delete_quality_metric` | Delete a metric |

### Snapshots

| Tool | Description |
|------|-------------|
| `create_debt_snapshot` | Create a snapshot of current debt state |
| `get_debt_snapshot` | Get a snapshot by ID |
| `list_debt_snapshots` | List all snapshots |
| `compare_snapshots` | Compare two snapshots |
| `delete_debt_snapshot` | Delete a snapshot |

### Analytics

| Tool | Description |
|------|-------------|
| `get_debt_summary` | Get summary of technical debt |
| `get_priority_items` | Get highest priority debt items |
| `search_debt_items` | Search debt items |
| `get_component_debt` | Get debt summary for a component |

## Debt Categories

- `architecture` - Architectural issues
- `code_quality` - Code quality problems
- `documentation` - Missing/outdated documentation
- `testing` - Test coverage issues
- `performance` - Performance problems
- `security` - Security vulnerabilities
- `dependencies` - Dependency issues
- `infrastructure` - Infrastructure debt
- `maintainability` - Maintainability concerns

## Priority Levels

- `critical` - Blocking, must fix immediately
- `high` - Important, fix soon
- `medium` - Should fix
- `low` - Nice to fix
- `nice_to_have` - Optional improvements

## Effort Estimates

- `trivial` - Less than 1 hour
- `small` - 1-4 hours
- `medium` - 1-2 days
- `large` - 3-5 days
- `very_large` - 1-2 weeks
- `epic` - 2+ weeks

## Impact Levels

- `critical` - Blocking production
- `high` - Significant user impact
- `medium` - Moderate user impact
- `low` - Minor inconvenience
- `minimal` - Internal only

## Resources

| Resource | Description |
|----------|-------------|
| `debt://summary` | Technical debt summary |
| `debt://priority` | Priority debt items |
| `debt://open` | All open debt items |
| `tasks://active` | Active refactoring tasks |
| `metrics://latest` | Latest quality metrics |
| `snapshots://all` | All debt snapshots |

## Data Storage

Data is stored in `data/tech_debt.json` in the server directory.

## Example Usage

```python
# Create a debt item
create_debt_item(
    title="Legacy authentication module needs refactoring",
    category="code_quality",
    description="The auth module uses deprecated patterns and has high cyclomatic complexity",
    priority="high",
    impact="medium",
    effort="large",
    component="authentication",
    file_path="src/auth/legacy_auth.py",
    business_value="Reduces maintenance time and improves security"
)

# Accrue interest when debt causes extra work
accrue_interest(
    debt_id=1,
    hours=2.5,
    description="Spent extra time debugging auth issue caused by legacy code"
)

# Create a refactoring task
create_refactoring_task(
    title="Refactor authentication module",
    description="Modernize auth module using current patterns",
    debt_ids=[1],
    effort="large",
    benefits=["Improved maintainability", "Better security", "Faster onboarding"],
    risks=["Potential regression in auth flows"]
)

# Record quality metrics
record_quality_metric(
    name="code_coverage",
    value=72.5,
    unit="%",
    component="authentication",
    threshold=80,
    notes="Needs improvement to meet threshold"
)

# Create a snapshot for comparison
create_debt_snapshot(
    name="Q1 2024 Baseline",
    description="Starting point for debt reduction initiative"
)

# Compare snapshots to track progress
compare_snapshots(snapshot_id_1=1, snapshot_id_2=2)
```

## License

MIT License