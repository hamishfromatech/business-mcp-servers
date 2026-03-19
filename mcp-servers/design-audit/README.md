# Design Audit MCP Server

A FastMCP server for auditing web designs, tracking UI/UX issues, managing design systems, and accessibility compliance.

## Features

- **Design Audits**: Create and manage design audit sessions for websites and applications
- **Issue Tracking**: Track UI/UX issues with types, priorities, and WCAG criteria
- **Design Systems**: Define and manage design systems with colors, typography, and components
- **Accessibility Checks**: Track WCAG compliance with structured accessibility checks
- **Analytics**: Get summaries and statistics on audits and issues

## Installation

```bash
pip install fastmcp
```

## Usage

### Running the Server

```bash
cd mcp-servers/design-audit
python server.py
```

### With FastMCP CLI

```bash
fastmcp run server.py
# or with hot reload
fastmcp dev server.py
```

## Tools

### Audit Sessions

| Tool | Description |
|------|-------------|
| `create_audit` | Create a new design audit session |
| `get_audit` | Get an audit session by ID |
| `list_audits` | List audits with filters (status, project, auditor) |
| `update_audit_status` | Update audit status |
| `delete_audit` | Delete an audit session |

### Design Issues

| Tool | Description |
|------|-------------|
| `create_design_issue` | Create a design audit issue |
| `get_design_issue` | Get an issue by ID |
| `list_design_issues` | List issues with filters |
| `update_design_issue` | Update an issue |
| `resolve_design_issue` | Mark an issue as fixed |
| `delete_design_issue` | Delete an issue |

### Design Systems

| Tool | Description |
|------|-------------|
| `create_design_system` | Create a design system definition |
| `get_design_system` | Get a design system by ID |
| `list_design_systems` | List all design systems |
| `update_design_system` | Update a design system |
| `add_color_to_system` | Add a color to a design system |
| `delete_design_system` | Delete a design system |

### Components

| Tool | Description |
|------|-------------|
| `create_component` | Create a design system component |
| `get_component` | Get a component by ID |
| `list_components` | List components with filters |
| `update_component` | Update a component |
| `delete_component` | Delete a component |

### Accessibility Checks

| Tool | Description |
|------|-------------|
| `create_accessibility_check` | Create an accessibility compliance check |
| `get_accessibility_check` | Get a check by ID |
| `list_accessibility_checks` | List checks with filters |
| `update_accessibility_check` | Update a check |
| `delete_accessibility_check` | Delete a check |

### Analytics

| Tool | Description |
|------|-------------|
| `get_audit_summary` | Get summary of an audit session |
| `get_overall_design_stats` | Get overall statistics |
| `search_design_issues` | Search issues by title, description, or page |

## Issue Types

- `accessibility` - Accessibility issues
- `visual` - Visual design issues
- `usability` - Usability problems
- `responsive` - Responsive design issues
- `performance` - Performance issues
- `branding` - Brand consistency issues
- `content` - Content issues
- `interaction` - Interaction design issues

## Priority Levels

- `critical` - Blocking release
- `high` - Significant user impact
- `medium` - Moderate impact
- `low` - Minor issue
- `suggestion` - Nice to have improvement

## WCAG Levels

- `A` - Level A (minimum)
- `AA` - Level AA (recommended)
- `AAA` - Level AAA (enhanced)

## Resources

| Resource | Description |
|----------|-------------|
| `audits://all` | All audits as formatted list |
| `issues://open` | All open design issues |
| `design-systems://all` | All design systems |
| `accessibility://summary` | Accessibility compliance summary |
| `stats://design` | Overall design statistics |

## Data Storage

Data is stored in `data/design_audit.json` in the server directory.

## Example Usage

```python
# Create an audit session
create_audit(
    name="Homepage Redesign Audit",
    project="company-website",
    url="https://example.com",
    auditor="jane@example.com",
    wcag_level="AA"
)

# Create a design issue
create_design_issue(
    audit_id=1,
    page="Homepage",
    issue_type="accessibility",
    priority="high",
    title="Insufficient color contrast",
    description="Text contrast ratio is 3.2:1, needs to be at least 4.5:1",
    element_selector=".hero-section h1",
    recommendation="Use darker text color or lighter background",
    wcag_criterion="1.4.3"
)

# Create a design system
create_design_system(
    name="Brand Design System",
    brand="Acme Corp",
    colors=[
        {"name": "primary", "hex": "#0066CC", "usage": "Primary buttons, links"},
        {"name": "secondary", "hex": "#6C757D", "usage": "Secondary elements"},
    ],
    typography={
        "primary_font": "Inter",
        "secondary_font": "Roboto",
        "base_size": "16px"
    }
)

# Add accessibility check
create_accessibility_check(
    audit_id=1,
    page="Homepage",
    criterion="1.4.3 Contrast (Minimum)",
    wcag_level="AA",
    status="fail",
    result="3 text elements fail contrast requirements",
    notes="See issues #2, #3, #4"
)
```

## License

MIT License