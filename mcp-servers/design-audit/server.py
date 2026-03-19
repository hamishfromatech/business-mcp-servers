"""
Design Audit MCP Server
A FastMCP server for auditing web designs, tracking UI/UX issues, managing design systems, and accessibility checks.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
from enum import Enum
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Design Audit",
    instructions="A design audit server for tracking UI/UX issues, managing design systems, accessibility compliance, and maintaining design consistency."
)


class AuditStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class IssuePriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SUGGESTION = "suggestion"


class IssueStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"


class IssueType(str, Enum):
    ACCESSIBILITY = "accessibility"
    VISUAL = "visual"
    USABILITY = "usability"
    RESPONSIVE = "responsive"
    PERFORMANCE = "performance"
    BRANDING = "branding"
    CONTENT = "content"
    INTERACTION = "interaction"


class WCAGLevel(str, Enum):
    A = "A"
    AA = "AA"
    AAA = "AAA"


class Audit(BaseModel):
    """A design audit session."""
    id: int
    name: str
    description: Optional[str] = None
    scope: list[str] = []
    status: str
    created_at: str
    updated_at: str


class DesignIssue(BaseModel):
    """A design issue found in an audit."""
    id: int
    audit_id: Optional[int] = None
    type: str
    priority: str
    title: str
    description: str
    component: Optional[str] = None
    page_url: Optional[str] = None
    screenshot_path: Optional[str] = None
    status: str
    created_at: str
    updated_at: str


class DesignSystem(BaseModel):
    """A design system reference."""
    id: int
    name: str
    version: str
    colors: dict = {}
    typography: dict = {}
    spacing: dict = {}
    components: list = []
    created_at: str


class Component(BaseModel):
    """A UI component in the design system."""
    id: int
    name: str
    category: str
    description: Optional[str] = None
    properties: dict = {}
    variants: list = []
    created_at: str


class AccessibilityCheck(BaseModel):
    """An accessibility checklist item."""
    id: int
    category: str
    criterion: str
    description: str
    wcag_level: str
    status: str
    notes: Optional[str] = None
    created_at: str


# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "design.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "audits": {},
        "issues": {},
        "design_systems": {},
        "components": {},
        "accessibility_checks": {},
        "next_audit_id": 1,
        "next_issue_id": 1,
        "next_system_id": 1,
        "next_component_id": 1,
        "next_check_id": 1,
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
audits: dict[int, dict] = {int(k): v for k, v in _data.get("audits", {}).items()}
issues: dict[int, dict] = {int(k): v for k, v in _data.get("issues", {}).items()}
design_systems: dict[int, dict] = {int(k): v for k, v in _data.get("design_systems", {}).items()}
components: dict[int, dict] = {int(k): v for k, v in _data.get("components", {}).items()}
accessibility_checks: dict[int, dict] = {int(k): v for k, v in _data.get("accessibility_checks", {}).items()}
_next_audit_id = _data.get("next_audit_id", 1)
_next_issue_id = _data.get("next_issue_id", 1)
_next_system_id = _data.get("next_system_id", 1)
_next_component_id = _data.get("next_component_id", 1)
_next_check_id = _data.get("next_check_id", 1)


def _get_next_audit_id() -> int:
    global _next_audit_id
    id_ = _next_audit_id
    _next_audit_id += 1
    return id_


def _get_next_issue_id() -> int:
    global _next_issue_id
    id_ = _next_issue_id
    _next_issue_id += 1
    return id_


def _get_next_system_id() -> int:
    global _next_system_id
    id_ = _next_system_id
    _next_system_id += 1
    return id_


def _get_next_component_id() -> int:
    global _next_component_id
    id_ = _next_component_id
    _next_component_id += 1
    return id_


def _get_next_check_id() -> int:
    global _next_check_id
    id_ = _next_check_id
    _next_check_id += 1
    return id_


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "audits": audits,
        "issues": issues,
        "design_systems": design_systems,
        "components": components,
        "accessibility_checks": accessibility_checks,
        "next_audit_id": _next_audit_id,
        "next_issue_id": _next_issue_id,
        "next_system_id": _next_system_id,
        "next_component_id": _next_component_id,
        "next_check_id": _next_check_id,
    })


# === AUDIT SESSION TOOLS ===

@mcp.tool
def create_audit(
    name: str,
    project: str,
    url: Optional[str] = None,
    auditor: Optional[str] = None,
    scope: Optional[list[str]] = None,
    wcag_level: str = WCAGLevel.AA.value,
) -> dict:
    """Create a new design audit session.

    Args:
        name: Name of the audit
        project: Project name
        url: URL of the design/site being audited
        auditor: Person conducting the audit
        scope: List of pages or components to audit
        wcag_level: Target WCAG compliance level (A, AA, AAA)

    Returns:
        The created audit session
    """
    audit_id = _get_next_audit_id()
    audit = {
        "id": audit_id,
        "name": name,
        "project": project,
        "url": url,
        "auditor": auditor,
        "scope": scope or [],
        "wcag_level": wcag_level,
        "status": AuditStatus.PENDING.value,
        "issues": [],
        "accessibility_score": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "completed_at": None,
    }
    audits[audit_id] = audit
    _save()
    return audit


@mcp.tool
def get_audit(audit_id: int) -> Optional[dict]:
    """Get an audit session by ID.

    Args:
        audit_id: The audit ID

    Returns:
        The audit details or None if not found
    """
    return audits.get(audit_id)


@mcp.tool
def list_audits(
    status: Optional[str] = None,
    project: Optional[str] = None,
    auditor: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List audit sessions with optional filters.

    Args:
        status: Filter by status
        project: Filter by project name
        auditor: Filter by auditor
        limit: Maximum number of results

    Returns:
        List of matching audits
    """
    result = list(audits.values())

    if status:
        result = [a for a in result if a.get("status") == status]
    if project:
        result = [a for a in result if project.lower() in a.get("project", "").lower()]
    if auditor:
        result = [a for a in result if auditor.lower() in (a.get("auditor") or "").lower()]

    result.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    return result[:limit]


@mcp.tool
def update_audit_status(
    audit_id: int,
    status: str,
    accessibility_score: Optional[float] = None,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Update the status of an audit.

    Args:
        audit_id: The audit ID
        status: New status (pending, in_progress, completed, archived)
        accessibility_score: Overall accessibility score (0-100)
        notes: Notes about the status change

    Returns:
        The updated audit or None if not found
    """
    if audit_id not in audits:
        return None

    audit = audits[audit_id]
    audit["status"] = status
    audit["updated_at"] = datetime.now().isoformat()

    if accessibility_score is not None:
        audit["accessibility_score"] = accessibility_score

    if status == AuditStatus.COMPLETED.value:
        audit["completed_at"] = datetime.now().isoformat()

    if notes:
        audit.setdefault("notes", []).append({
            "note": notes,
            "timestamp": datetime.now().isoformat(),
        })

    _save()
    return audit


@mcp.tool
def delete_audit(audit_id: int) -> bool:
    """Delete an audit session.

    Args:
        audit_id: The audit ID

    Returns:
        True if deleted, False if not found
    """
    if audit_id in audits:
        del audits[audit_id]
        _save()
        return True
    return False


# === DESIGN ISSUE TOOLS ===

@mcp.tool
def create_design_issue(
    audit_id: int,
    page: str,
    issue_type: str,
    priority: str = IssuePriority.MEDIUM.value,
    title: str = "",
    description: str = "",
    element_selector: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    recommendation: Optional[str] = None,
    wcag_criterion: Optional[str] = None,
) -> dict:
    """Create a design audit issue.

    Args:
        audit_id: Associated audit ID
        page: Page or screen where the issue was found
        issue_type: Type of issue (accessibility, visual, usability, responsive, performance, branding, content, interaction)
        priority: Issue priority (critical, high, medium, low, suggestion)
        title: Brief issue title
        description: Detailed description
        element_selector: CSS selector or element description
        screenshot_path: Path to screenshot
        recommendation: Recommended fix
        wcag_criterion: Related WCAG criterion (e.g., "1.4.3", "2.1.1")

    Returns:
        The created issue
    """
    issue_id = _get_next_issue_id()
    issue = {
        "id": issue_id,
        "audit_id": audit_id,
        "page": page,
        "issue_type": issue_type,
        "priority": priority,
        "title": title,
        "description": description,
        "element_selector": element_selector,
        "screenshot_path": screenshot_path,
        "recommendation": recommendation,
        "wcag_criterion": wcag_criterion,
        "status": IssueStatus.OPEN.value,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    issues[issue_id] = issue

    # Link to audit
    if audit_id in audits:
        audits[audit_id].setdefault("issues", []).append(issue_id)
        audits[audit_id]["updated_at"] = datetime.now().isoformat()

    _save()
    return issue


@mcp.tool
def get_design_issue(issue_id: int) -> Optional[dict]:
    """Get a design issue by ID.

    Args:
        issue_id: The issue ID

    Returns:
        The issue details or None if not found
    """
    return issues.get(issue_id)


@mcp.tool
def list_design_issues(
    audit_id: Optional[int] = None,
    issue_type: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    page: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List design issues with optional filters.

    Args:
        audit_id: Filter by audit ID
        issue_type: Filter by issue type
        priority: Filter by priority
        status: Filter by status
        page: Filter by page
        limit: Maximum number of results

    Returns:
        List of matching issues
    """
    result = list(issues.values())

    if audit_id is not None:
        result = [i for i in result if i.get("audit_id") == audit_id]
    if issue_type:
        result = [i for i in result if i.get("issue_type") == issue_type]
    if priority:
        result = [i for i in result if i.get("priority") == priority]
    if status:
        result = [i for i in result if i.get("status") == status]
    if page:
        result = [i for i in result if page.lower() in i.get("page", "").lower()]

    result.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return result[:limit]


@mcp.tool
def update_design_issue(
    issue_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    description: Optional[str] = None,
    recommendation: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> Optional[dict]:
    """Update a design issue.

    Args:
        issue_id: The issue ID
        status: New status
        priority: New priority
        description: Updated description
        recommendation: Updated recommendation
        assigned_to: Person assigned to fix

    Returns:
        The updated issue or None if not found
    """
    if issue_id not in issues:
        return None

    issue = issues[issue_id]
    if status is not None:
        issue["status"] = status
    if priority is not None:
        issue["priority"] = priority
    if description is not None:
        issue["description"] = description
    if recommendation is not None:
        issue["recommendation"] = recommendation
    if assigned_to is not None:
        issue["assigned_to"] = assigned_to
    issue["updated_at"] = datetime.now().isoformat()
    _save()
    return issue


@mcp.tool
def resolve_design_issue(
    issue_id: int,
    resolution: str,
    resolved_by: Optional[str] = None,
) -> Optional[dict]:
    """Mark a design issue as fixed.

    Args:
        issue_id: The issue ID
        resolution: Description of how it was fixed
        resolved_by: Person who fixed it

    Returns:
        The resolved issue or None if not found
    """
    if issue_id not in issues:
        return None

    issue = issues[issue_id]
    issue["status"] = IssueStatus.FIXED.value
    issue["resolution"] = resolution
    issue["resolved_by"] = resolved_by
    issue["resolved_at"] = datetime.now().isoformat()
    issue["updated_at"] = datetime.now().isoformat()
    _save()
    return issue


@mcp.tool
def delete_design_issue(issue_id: int) -> bool:
    """Delete a design issue.

    Args:
        issue_id: The issue ID

    Returns:
        True if deleted, False if not found
    """
    if issue_id in issues:
        issue = issues[issue_id]
        audit_id = issue.get("audit_id")
        if audit_id and audit_id in audits:
            if issue_id in audits[audit_id].get("issues", []):
                audits[audit_id]["issues"].remove(issue_id)

        del issues[issue_id]
        _save()
        return True
    return False


# === DESIGN SYSTEM TOOLS ===

@mcp.tool
def create_design_system(
    name: str,
    brand: str,
    colors: Optional[list[dict]] = None,
    typography: Optional[dict] = None,
    spacing: Optional[dict] = None,
    description: Optional[str] = None,
) -> dict:
    """Create a design system definition.

    Args:
        name: Design system name
        brand: Brand/company name
        colors: List of color definitions (name, hex, usage)
        typography: Typography settings (fonts, sizes, weights)
        spacing: Spacing scale definitions
        description: Description of the design system

    Returns:
        The created design system
    """
    system_id = _get_next_system_id()
    system = {
        "id": system_id,
        "name": name,
        "brand": brand,
        "description": description,
        "colors": colors or [],
        "typography": typography or {},
        "spacing": spacing or {},
        "components": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    design_systems[system_id] = system
    _save()
    return system


@mcp.tool
def get_design_system(system_id: int) -> Optional[dict]:
    """Get a design system by ID.

    Args:
        system_id: The design system ID

    Returns:
        The design system details or None if not found
    """
    return design_systems.get(system_id)


@mcp.tool
def list_design_systems(limit: int = 50) -> list[dict]:
    """List all design systems.

    Args:
        limit: Maximum number of results

    Returns:
        List of design systems
    """
    result = list(design_systems.values())
    result.sort(key=lambda s: s.get("name", ""))
    return result[:limit]


@mcp.tool
def update_design_system(
    system_id: int,
    name: Optional[str] = None,
    colors: Optional[list[dict]] = None,
    typography: Optional[dict] = None,
    spacing: Optional[dict] = None,
) -> Optional[dict]:
    """Update a design system.

    Args:
        system_id: The design system ID
        name: New name
        colors: Updated color definitions
        typography: Updated typography settings
        spacing: Updated spacing scale

    Returns:
        The updated design system or None if not found
    """
    if system_id not in design_systems:
        return None

    system = design_systems[system_id]
    if name is not None:
        system["name"] = name
    if colors is not None:
        system["colors"] = colors
    if typography is not None:
        system["typography"] = typography
    if spacing is not None:
        system["spacing"] = spacing
    system["updated_at"] = datetime.now().isoformat()
    _save()
    return system


@mcp.tool
def add_color_to_system(
    system_id: int,
    name: str,
    hex_value: str,
    usage: Optional[str] = None,
) -> Optional[dict]:
    """Add a color to a design system.

    Args:
        system_id: The design system ID
        name: Color name (e.g., "primary", "secondary")
        hex_value: Hex color value (e.g., "#FF5733")
        usage: Usage description

    Returns:
        The updated design system or None if not found
    """
    if system_id not in design_systems:
        return None

    system = design_systems[system_id]
    color = {
        "name": name,
        "hex": hex_value,
        "usage": usage,
    }
    system.setdefault("colors", []).append(color)
    system["updated_at"] = datetime.now().isoformat()
    _save()
    return system


@mcp.tool
def delete_design_system(system_id: int) -> bool:
    """Delete a design system.

    Args:
        system_id: The design system ID

    Returns:
        True if deleted, False if not found
    """
    if system_id in design_systems:
        del design_systems[system_id]
        _save()
        return True
    return False


# === COMPONENT TOOLS ===

@mcp.tool
def create_component(
    system_id: int,
    name: str,
    category: str,
    description: str,
    variants: Optional[list[dict]] = None,
    props: Optional[dict] = None,
    usage_notes: Optional[str] = None,
) -> dict:
    """Create a design system component.

    Args:
        system_id: Parent design system ID
        name: Component name
        category: Category (e.g., "buttons", "inputs", "navigation")
        description: Component description
        variants: List of component variants
        props: Component properties/props
        usage_notes: Usage guidelines

    Returns:
        The created component
    """
    component_id = _get_next_component_id()
    component = {
        "id": component_id,
        "system_id": system_id,
        "name": name,
        "category": category,
        "description": description,
        "variants": variants or [],
        "props": props or {},
        "usage_notes": usage_notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    components[component_id] = component

    # Link to design system
    if system_id in design_systems:
        design_systems[system_id].setdefault("components", []).append(component_id)
        design_systems[system_id]["updated_at"] = datetime.now().isoformat()

    _save()
    return component


@mcp.tool
def get_component(component_id: int) -> Optional[dict]:
    """Get a component by ID.

    Args:
        component_id: The component ID

    Returns:
        The component details or None if not found
    """
    return components.get(component_id)


@mcp.tool
def list_components(
    system_id: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List components with optional filters.

    Args:
        system_id: Filter by design system ID
        category: Filter by category
        limit: Maximum number of results

    Returns:
        List of matching components
    """
    result = list(components.values())

    if system_id is not None:
        result = [c for c in result if c.get("system_id") == system_id]
    if category:
        result = [c for c in result if c.get("category") == category]

    result.sort(key=lambda c: c.get("name", ""))
    return result[:limit]


@mcp.tool
def update_component(
    component_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    variants: Optional[list[dict]] = None,
    props: Optional[dict] = None,
    usage_notes: Optional[str] = None,
) -> Optional[dict]:
    """Update a component.

    Args:
        component_id: The component ID
        name: New name
        description: Updated description
        variants: Updated variants
        props: Updated props
        usage_notes: Updated usage notes

    Returns:
        The updated component or None if not found
    """
    if component_id not in components:
        return None

    component = components[component_id]
    if name is not None:
        component["name"] = name
    if description is not None:
        component["description"] = description
    if variants is not None:
        component["variants"] = variants
    if props is not None:
        component["props"] = props
    if usage_notes is not None:
        component["usage_notes"] = usage_notes
    component["updated_at"] = datetime.now().isoformat()
    _save()
    return component


@mcp.tool
def delete_component(component_id: int) -> bool:
    """Delete a component.

    Args:
        component_id: The component ID

    Returns:
        True if deleted, False if not found
    """
    if component_id in components:
        component = components[component_id]
        system_id = component.get("system_id")
        if system_id and system_id in design_systems:
            if component_id in design_systems[system_id].get("components", []):
                design_systems[system_id]["components"].remove(component_id)

        del components[component_id]
        _save()
        return True
    return False


# === ACCESSIBILITY CHECK TOOLS ===

@mcp.tool
def create_accessibility_check(
    audit_id: int,
    page: str,
    criterion: str,
    wcag_level: str,
    status: str = "not_tested",
    result: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Create an accessibility compliance check.

    Args:
        audit_id: Associated audit ID
        page: Page being tested
        criterion: WCAG criterion (e.g., "1.4.3 Contrast")
        wcag_level: WCAG level (A, AA, AAA)
        status: Status (not_tested, pass, fail, not_applicable)
        result: Detailed result description
        notes: Additional notes

    Returns:
        The created check
    """
    check_id = _get_next_check_id()
    check = {
        "id": check_id,
        "audit_id": audit_id,
        "page": page,
        "criterion": criterion,
        "wcag_level": wcag_level,
        "status": status,
        "result": result,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    accessibility_checks[check_id] = check

    # Link to audit
    if audit_id in audits:
        audits[audit_id].setdefault("accessibility_checks", []).append(check_id)

    _save()
    return check


@mcp.tool
def get_accessibility_check(check_id: int) -> Optional[dict]:
    """Get an accessibility check by ID.

    Args:
        check_id: The check ID

    Returns:
        The check details or None if not found
    """
    return accessibility_checks.get(check_id)


@mcp.tool
def list_accessibility_checks(
    audit_id: Optional[int] = None,
    wcag_level: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """List accessibility checks with optional filters.

    Args:
        audit_id: Filter by audit ID
        wcag_level: Filter by WCAG level
        status: Filter by status
        limit: Maximum number of results

    Returns:
        List of matching checks
    """
    result = list(accessibility_checks.values())

    if audit_id is not None:
        result = [c for c in result if c.get("audit_id") == audit_id]
    if wcag_level:
        result = [c for c in result if c.get("wcag_level") == wcag_level]
    if status:
        result = [c for c in result if c.get("status") == status]

    result.sort(key=lambda c: (c.get("wcag_level", ""), c.get("criterion", "")))
    return result[:limit]


@mcp.tool
def update_accessibility_check(
    check_id: int,
    status: Optional[str] = None,
    result: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Update an accessibility check.

    Args:
        check_id: The check ID
        status: New status
        result: Updated result
        notes: Updated notes

    Returns:
        The updated check or None if not found
    """
    if check_id not in accessibility_checks:
        return None

    check = accessibility_checks[check_id]
    if status is not None:
        check["status"] = status
    if result is not None:
        check["result"] = result
    if notes is not None:
        check["notes"] = notes
    check["updated_at"] = datetime.now().isoformat()
    _save()
    return check


@mcp.tool
def delete_accessibility_check(check_id: int) -> bool:
    """Delete an accessibility check.

    Args:
        check_id: The check ID

    Returns:
        True if deleted, False if not found
    """
    if check_id in accessibility_checks:
        check = accessibility_checks[check_id]
        audit_id = check.get("audit_id")
        if audit_id and audit_id in audits:
            if check_id in audits[audit_id].get("accessibility_checks", []):
                audits[audit_id]["accessibility_checks"].remove(check_id)

        del accessibility_checks[check_id]
        _save()
        return True
    return False


# === ANALYTICS TOOLS ===

@mcp.tool
def get_audit_summary(audit_id: int) -> Optional[dict]:
    """Get a summary of an audit session.

    Args:
        audit_id: The audit ID

    Returns:
        Summary with issue counts and accessibility score
    """
    if audit_id not in audits:
        return None

    audit = audits[audit_id]
    audit_issues = [issues[i] for i in audit.get("issues", []) if i in issues]
    audit_checks = [accessibility_checks[i] for i in audit.get("accessibility_checks", []) if i in accessibility_checks]

    summary = {
        "audit_id": audit_id,
        "name": audit.get("name"),
        "status": audit.get("status"),
        "total_issues": len(audit_issues),
        "by_type": {},
        "by_priority": {},
        "by_status": {},
        "accessibility": {
            "total_checks": len(audit_checks),
            "passed": 0,
            "failed": 0,
            "not_tested": 0,
            "not_applicable": 0,
        },
        "critical_open": 0,
    }

    for issue in audit_issues:
        issue_type = issue.get("issue_type", "unknown")
        priority = issue.get("priority", "medium")
        status = issue.get("status", "open")

        summary["by_type"][issue_type] = summary["by_type"].get(issue_type, 0) + 1
        summary["by_priority"][priority] = summary["by_priority"].get(priority, 0) + 1
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

        if issue.get("status") == IssueStatus.OPEN.value and issue.get("priority") == IssuePriority.CRITICAL.value:
            summary["critical_open"] += 1

    for check in audit_checks:
        check_status = check.get("status", "not_tested")
        if check_status in summary["accessibility"]:
            summary["accessibility"][check_status] += 1

    # Calculate accessibility score
    if audit_checks:
        passed = summary["accessibility"]["passed"]
        total_applicable = summary["accessibility"]["total_checks"] - summary["accessibility"]["not_applicable"]
        if total_applicable > 0:
            summary["accessibility"]["score"] = round((passed / total_applicable) * 100, 1)

    return summary


@mcp.tool
def get_overall_design_stats() -> dict:
    """Get overall statistics across all audits and design systems.

    Returns:
        Statistics about audits, issues, and design systems
    """
    all_issues = list(issues.values())
    all_audits = list(audits.values())
    all_checks = list(accessibility_checks.values())

    stats = {
        "total_audits": len(audits),
        "total_issues": len(issues),
        "total_design_systems": len(design_systems),
        "total_components": len(components),
        "total_accessibility_checks": len(accessibility_checks),
        "audits_by_status": {},
        "issues_by_type": {},
        "issues_by_priority": {},
        "issues_by_status": {},
        "open_issues": 0,
        "critical_open": 0,
        "accessibility_pass_rate": 0,
    }

    for audit in all_audits:
        status = audit.get("status", "unknown")
        stats["audits_by_status"][status] = stats["audits_by_status"].get(status, 0) + 1

    for issue in all_issues:
        issue_type = issue.get("issue_type", "unknown")
        priority = issue.get("priority", "medium")
        status = issue.get("status", "open")

        stats["issues_by_type"][issue_type] = stats["issues_by_type"].get(issue_type, 0) + 1
        stats["issues_by_priority"][priority] = stats["issues_by_priority"].get(priority, 0) + 1
        stats["issues_by_status"][status] = stats["issues_by_status"].get(status, 0) + 1

        if status == IssueStatus.OPEN.value:
            stats["open_issues"] += 1
            if priority == IssuePriority.CRITICAL.value:
                stats["critical_open"] += 1

    # Calculate accessibility pass rate
    if all_checks:
        passed = sum(1 for c in all_checks if c.get("status") == "pass")
        total_applicable = sum(1 for c in all_checks if c.get("status") != "not_applicable")
        if total_applicable > 0:
            stats["accessibility_pass_rate"] = round((passed / total_applicable) * 100, 1)

    return stats


@mcp.tool
def search_design_issues(query: str) -> list[dict]:
    """Search design issues by title, description, or page.

    Args:
        query: Search term

    Returns:
        List of matching issues
    """
    query_lower = query.lower()
    results = []

    for issue in issues.values():
        if (
            query_lower in issue.get("title", "").lower() or
            query_lower in issue.get("description", "").lower() or
            query_lower in issue.get("page", "").lower() or
            query_lower in (issue.get("recommendation") or "").lower()
        ):
            results.append(issue)

    return results[:20]


# === RESOURCES ===

@mcp.resource("audits://all")
def get_all_audits_resource() -> str:
    """Resource providing all audits as a formatted list."""
    if not audits:
        return "No audits found."

    lines = ["# All Design Audits\n"]
    for audit in sorted(audits.values(), key=lambda a: a.get("created_at", ""), reverse=True):
        status_emoji = {
            AuditStatus.PENDING.value: "⏳",
            AuditStatus.IN_PROGRESS.value: "🔍",
            AuditStatus.COMPLETED.value: "✅",
            AuditStatus.ARCHIVED.value: "📦",
        }.get(audit.get("status"), "❓")

        lines.append(f"## {status_emoji} {audit.get('name', 'Untitled')} (ID: {audit['id']})")
        lines.append(f"- **Project:** {audit.get('project', 'N/A')}")
        lines.append(f"- **Status:** {audit.get('status', 'unknown')}")
        if audit.get("url"):
            lines.append(f"- **URL:** {audit['url']}")
        if audit.get("auditor"):
            lines.append(f"- **Auditor:** {audit['auditor']}")
        lines.append(f"- **Issues:** {len(audit.get('issues', []))}")
        if audit.get("accessibility_score") is not None:
            lines.append(f"- **Accessibility Score:** {audit['accessibility_score']}%")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("issues://open")
def get_open_design_issues_resource() -> str:
    """Resource providing all open design issues."""
    open_issues = [i for i in issues.values() if i.get("status") == IssueStatus.OPEN.value]

    if not open_issues:
        return "No open design issues."

    lines = ["# Open Design Issues\n"]

    priority_order = {
        IssuePriority.CRITICAL.value: 0,
        IssuePriority.HIGH.value: 1,
        IssuePriority.MEDIUM.value: 2,
        IssuePriority.LOW.value: 3,
        IssuePriority.SUGGESTION.value: 4,
    }
    open_issues.sort(key=lambda i: priority_order.get(i.get("priority", "medium"), 2))

    for issue in open_issues:
        priority_emoji = {
            IssuePriority.CRITICAL.value: "🔴",
            IssuePriority.HIGH.value: "🟠",
            IssuePriority.MEDIUM.value: "🟡",
            IssuePriority.LOW.value: "🟢",
            IssuePriority.SUGGESTION.value: "💡",
        }.get(issue.get("priority", "medium"), "❓")

        type_emoji = {
            IssueType.ACCESSIBILITY.value: "♿",
            IssueType.VISUAL.value: "🎨",
            IssueType.USABILITY.value: "👆",
            IssueType.RESPONSIVE.value: "📱",
            IssueType.PERFORMANCE.value: "⚡",
            IssueType.BRANDING.value: "🏷️",
            IssueType.CONTENT.value: "📝",
            IssueType.INTERACTION.value: "🖱️",
        }.get(issue.get("issue_type", "unknown"), "❓")

        lines.append(f"## {priority_emoji} {type_emoji} {issue.get('title', 'Untitled')} (ID: {issue['id']})")
        lines.append(f"- **Page:** {issue.get('page', 'N/A')}")
        lines.append(f"- **Type:** {issue.get('issue_type', 'unknown')}")
        lines.append(f"- **Priority:** {issue.get('priority', 'medium')}")
        lines.append(f"- **Description:** {issue.get('description', 'N/A')}")
        if issue.get("recommendation"):
            lines.append(f"- **Recommendation:** {issue['recommendation']}")
        if issue.get("wcag_criterion"):
            lines.append(f"- **WCAG:** {issue['wcag_criterion']}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("design-systems://all")
def get_all_design_systems_resource() -> str:
    """Resource providing all design systems."""
    if not design_systems:
        return "No design systems defined."

    lines = ["# Design Systems\n"]

    for system in sorted(design_systems.values(), key=lambda s: s.get("name", "")):
        lines.append(f"## {system.get('name', 'Unnamed')} (ID: {system['id']})")
        lines.append(f"- **Brand:** {system.get('brand', 'N/A')}")
        if system.get("description"):
            lines.append(f"- **Description:** {system['description']}")

        if system.get("colors"):
            lines.append("\n### Colors\n")
            for color in system["colors"]:
                lines.append(f"- **{color.get('name', 'Unknown')}:** `{color.get('hex', 'N/A')}` - {color.get('usage', '')}")

        if system.get("typography"):
            lines.append("\n### Typography\n")
            typo = system["typography"]
            if typo.get("primary_font"):
                lines.append(f"- **Primary Font:** {typo['primary_font']}")
            if typo.get("secondary_font"):
                lines.append(f"- **Secondary Font:** {typo['secondary_font']}")

        lines.append(f"\n- **Components:** {len(system.get('components', []))}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("accessibility://summary")
def get_accessibility_summary_resource() -> str:
    """Resource providing accessibility check summary."""
    all_checks = list(accessibility_checks.values())

    if not all_checks:
        return "No accessibility checks recorded."

    lines = ["# Accessibility Compliance Summary\n"]

    # Group by WCAG level
    by_level = {"A": [], "AA": [], "AAA": []}
    for check in all_checks:
        level = check.get("wcag_level", "AA")
        if level in by_level:
            by_level[level].append(check)

    for level in ["A", "AA", "AAA"]:
        checks = by_level[level]
        if not checks:
            continue

        passed = sum(1 for c in checks if c.get("status") == "pass")
        failed = sum(1 for c in checks if c.get("status") == "fail")
        not_tested = sum(1 for c in checks if c.get("status") == "not_tested")

        lines.append(f"## WCAG Level {level}\n")
        lines.append(f"- **Passed:** {passed}")
        lines.append(f"- **Failed:** {failed}")
        lines.append(f"- **Not Tested:** {not_tested}")

        if failed > 0:
            lines.append("\n### Failed Criteria\n")
            for check in checks:
                if check.get("status") == "fail":
                    lines.append(f"- {check.get('criterion', 'Unknown')} (Page: {check.get('page', 'N/A')})")

        lines.append("")

    return "\n".join(lines)


@mcp.resource("stats://design")
def get_design_stats_resource() -> str:
    """Resource providing overall design statistics."""
    stats = get_overall_design_stats()

    lines = ["# Design Audit Statistics\n"]
    lines.append(f"- **Total Audits:** {stats['total_audits']}")
    lines.append(f"- **Total Issues:** {stats['total_issues']}")
    lines.append(f"- **Design Systems:** {stats['total_design_systems']}")
    lines.append(f"- **Components:** {stats['total_components']}")
    lines.append(f"- **Accessibility Checks:** {stats['total_accessibility_checks']}")
    lines.append(f"- **Open Issues:** {stats['open_issues']}")
    lines.append(f"- **Critical Open Issues:** {stats['critical_open']}")

    if stats["accessibility_pass_rate"] > 0:
        lines.append(f"- **Accessibility Pass Rate:** {stats['accessibility_pass_rate']}%")

    if stats["issues_by_type"]:
        lines.append("\n## Issues by Type\n")
        for issue_type, count in sorted(stats["issues_by_type"].items()):
            lines.append(f"- {issue_type}: {count}")

    if stats["issues_by_priority"]:
        lines.append("\n## Issues by Priority\n")
        for priority, count in sorted(stats["issues_by_priority"].items()):
            lines.append(f"- {priority}: {count}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
