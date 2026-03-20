"""
Code Reviewer MCP Server
A FastMCP server for managing code reviews, tracking issues, and maintaining code quality standards.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
from enum import Enum
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Code Reviewer",
    instructions="A code review management server for tracking review sessions, issues, and maintaining code quality standards."
)


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class IssueCategory(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ARCHITECTURE = "architecture"


class Review(BaseModel):
    """A code review session."""
    id: int
    title: str
    description: Optional[str] = None
    repository: Optional[str] = None
    branch: Optional[str] = None
    files: list[str] = []
    status: str
    reviewer: Optional[str] = None
    issues: list[int] = []
    created_at: str
    updated_at: str


class Issue(BaseModel):
    """A code review issue."""
    id: int
    review_id: Optional[int] = None
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    category: str
    severity: str
    title: str = ""
    description: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    status: str
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: str
    updated_at: str


class Standard(BaseModel):
    """A coding standard or best practice."""
    id: int
    name: str
    category: str
    description: str
    rules: list[str] = []
    examples: list[dict] = []
    references: list[str] = []
    created_at: str
    updated_at: Optional[str] = None


# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "reviews.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "reviews": {},
        "issues": {},
        "standards": {},
        "next_review_id": 1,
        "next_issue_id": 1,
        "next_standard_id": 1,
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
reviews: dict[int, dict] = {int(k): v for k, v in _data.get("reviews", {}).items()}
issues: dict[int, dict] = {int(k): v for k, v in _data.get("issues", {}).items()}
standards: dict[int, dict] = {int(k): v for k, v in _data.get("standards", {}).items()}
_next_review_id = _data.get("next_review_id", 1)
_next_issue_id = _data.get("next_issue_id", 1)
_next_standard_id = _data.get("next_standard_id", 1)


def _get_next_review_id() -> int:
    global _next_review_id
    id_ = _next_review_id
    _next_review_id += 1
    return id_


def _get_next_issue_id() -> int:
    global _next_issue_id
    id_ = _next_issue_id
    _next_issue_id += 1
    return id_


def _get_next_standard_id() -> int:
    global _next_standard_id
    id_ = _next_standard_id
    _next_standard_id += 1
    return id_


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "reviews": reviews,
        "issues": issues,
        "standards": standards,
        "next_review_id": _next_review_id,
        "next_issue_id": _next_issue_id,
        "next_standard_id": _next_standard_id,
    })


# === REVIEW SESSION TOOLS ===

@mcp.tool
def create_review(
    title: str,
    repository: str,
    branch: str,
    reviewer: Optional[str] = None,
    description: Optional[str] = None,
    files: Optional[list[str]] = None,
) -> Review:
    """Create a new code review session.

    Args:
        title: Title of the review
        repository: Repository or project name
        branch: Branch being reviewed
        reviewer: Person assigned to review
        description: Description of what's being reviewed
        files: List of files to review

    Returns:
        The created review session
    """
    review_id = _get_next_review_id()
    review = {
        "id": review_id,
        "title": title,
        "repository": repository,
        "branch": branch,
        "reviewer": reviewer,
        "description": description,
        "files": files or [],
        "status": ReviewStatus.PENDING.value,
        "issues": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    reviews[review_id] = review
    _save()
    return Review(**review)


@mcp.tool
def get_review(review_id: int) -> Optional[Review]:
    """Get a review session by ID.

    Args:
        review_id: The review ID

    Returns:
        The review details or None if not found
    """
    review = reviews.get(review_id)
    return Review(**review) if review else None


@mcp.tool
def list_reviews(
    status: Optional[str] = None,
    reviewer: Optional[str] = None,
    repository: Optional[str] = None,
    limit: int = 50,
) -> list[Review]:
    """List review sessions with optional filters.

    Args:
        status: Filter by status (pending, in_review, approved, changes_requested)
        reviewer: Filter by reviewer name
        repository: Filter by repository
        limit: Maximum number of results

    Returns:
        List of matching reviews
    """
    result = list(reviews.values())

    if status:
        result = [r for r in result if r.get("status") == status]
    if reviewer:
        result = [r for r in result if reviewer.lower() in (r.get("reviewer") or "").lower()]
    if repository:
        result = [r for r in result if repository.lower() in r.get("repository", "").lower()]

    result.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return [Review(**r) for r in result[:limit]]


@mcp.tool
def update_review_status(
    review_id: int,
    status: str,
    notes: Optional[str] = None,
) -> Optional[Review]:
    """Update the status of a review session.

    Args:
        review_id: The review ID
        status: New status (pending, in_review, approved, changes_requested)
        notes: Optional notes about the status change

    Returns:
        The updated review or None if not found
    """
    if review_id not in reviews:
        return None

    review = reviews[review_id]
    review["status"] = status
    review["updated_at"] = datetime.now().isoformat()
    if notes:
        review.setdefault("status_history", []).append({
            "status": status,
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
        })
    _save()
    return Review(**review)


@mcp.tool
def add_files_to_review(
    review_id: int,
    files: list[str],
) -> Optional[Review]:
    """Add files to a review session.

    Args:
        review_id: The review ID
        files: List of file paths to add

    Returns:
        The updated review or None if not found
    """
    if review_id not in reviews:
        return None

    review = reviews[review_id]
    existing_files = set(review.get("files", []))
    review["files"] = list(existing_files.union(set(files)))
    review["updated_at"] = datetime.now().isoformat()
    _save()
    return Review(**review)


@mcp.tool
def delete_review(review_id: int) -> bool:
    """Delete a review session.

    Args:
        review_id: The review ID

    Returns:
        True if deleted, False if not found
    """
    if review_id in reviews:
        del reviews[review_id]
        _save()
        return True
    return False


# === ISSUE TOOLS ===

@mcp.tool
def create_issue(
    review_id: Optional[int],
    file_path: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
    category: str = IssueCategory.BUG.value,
    severity: str = Severity.MEDIUM.value,
    title: str = "",
    description: str = "",
    suggestion: Optional[str] = None,
    code_snippet: Optional[str] = None,
) -> Issue:
    """Create a code review issue.

    Args:
        review_id: Associated review ID (optional)
        file_path: Path to the file with the issue
        line_start: Starting line number
        line_end: Ending line number
        category: Issue category (bug, security, performance, style, maintainability, documentation, testing, architecture)
        severity: Issue severity (critical, high, medium, low, info)
        title: Brief issue title
        description: Detailed description of the issue
        suggestion: Suggested fix
        code_snippet: Relevant code snippet

    Returns:
        The created issue
    """
    issue_id = _get_next_issue_id()
    issue = {
        "id": issue_id,
        "review_id": review_id,
        "file_path": file_path,
        "line_start": line_start,
        "line_end": line_end,
        "category": category,
        "severity": severity,
        "title": title,
        "description": description,
        "suggestion": suggestion,
        "code_snippet": code_snippet,
        "status": IssueStatus.OPEN.value,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    issues[issue_id] = issue

    # Link to review if provided
    if review_id and review_id in reviews:
        reviews[review_id].setdefault("issues", []).append(issue_id)
        reviews[review_id]["updated_at"] = datetime.now().isoformat()

    _save()
    return Issue(**issue)


@mcp.tool
def get_issue(issue_id: int) -> Optional[Issue]:
    """Get an issue by ID.

    Args:
        issue_id: The issue ID

    Returns:
        The issue details or None if not found
    """
    issue = issues.get(issue_id)
    return Issue(**issue) if issue else None


@mcp.tool
def list_issues(
    status: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    review_id: Optional[int] = None,
    file_path: Optional[str] = None,
    limit: int = 50,
) -> list[Issue]:
    """List issues with optional filters.

    Args:
        status: Filter by status
        category: Filter by category
        severity: Filter by severity
        review_id: Filter by review ID
        file_path: Filter by file path
        limit: Maximum number of results

    Returns:
        List of matching issues
    """
    result = list(issues.values())

    if status:
        result = [i for i in result if i.get("status") == status]
    if category:
        result = [i for i in result if i.get("category") == category]
    if severity:
        result = [i for i in result if i.get("severity") == severity]
    if review_id is not None:
        result = [i for i in result if i.get("review_id") == review_id]
    if file_path:
        result = [i for i in result if file_path.lower() in i.get("file_path", "").lower()]

    result.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return [Issue(**i) for i in result[:limit]]


@mcp.tool
def update_issue(
    issue_id: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    description: Optional[str] = None,
    suggestion: Optional[str] = None,
    resolution_notes: Optional[str] = None,
) -> Optional[Issue]:
    """Update an issue.

    Args:
        issue_id: The issue ID
        status: New status
        severity: New severity
        description: Updated description
        suggestion: Updated suggestion
        resolution_notes: Notes about resolution

    Returns:
        The updated issue or None if not found
    """
    if issue_id not in issues:
        return None

    issue = issues[issue_id]
    if status is not None:
        issue["status"] = status
    if severity is not None:
        issue["severity"] = severity
    if description is not None:
        issue["description"] = description
    if suggestion is not None:
        issue["suggestion"] = suggestion
    if resolution_notes is not None:
        issue["resolution_notes"] = resolution_notes
    issue["updated_at"] = datetime.now().isoformat()
    _save()
    return Issue(**issue)


@mcp.tool
def resolve_issue(
    issue_id: int,
    resolution: str,
    resolved_by: Optional[str] = None,
) -> Optional[Issue]:
    """Mark an issue as resolved.

    Args:
        issue_id: The issue ID
        resolution: Description of how it was resolved
        resolved_by: Person who resolved it

    Returns:
        The resolved issue or None if not found
    """
    if issue_id not in issues:
        return None

    issue = issues[issue_id]
    issue["status"] = IssueStatus.RESOLVED.value
    issue["resolution"] = resolution
    issue["resolved_by"] = resolved_by
    issue["resolved_at"] = datetime.now().isoformat()
    issue["updated_at"] = datetime.now().isoformat()
    _save()
    return Issue(**issue)


@mcp.tool
def delete_issue(issue_id: int) -> bool:
    """Delete an issue.

    Args:
        issue_id: The issue ID

    Returns:
        True if deleted, False if not found
    """
    if issue_id in issues:
        # Remove from review if linked
        issue = issues[issue_id]
        review_id = issue.get("review_id")
        if review_id and review_id in reviews:
            reviews[review_id].setdefault("issues", [])
            if issue_id in reviews[review_id]["issues"]:
                reviews[review_id]["issues"].remove(issue_id)

        del issues[issue_id]
        _save()
        return True
    return False


# === CODE STANDARDS TOOLS ===

@mcp.tool
def create_standard(
    name: str,
    category: str,
    description: str,
    rules: list[str],
    examples: Optional[list[dict]] = None,
    references: Optional[list[str]] = None,
) -> Standard:
    """Create a code quality standard.

    Args:
        name: Standard name
        category: Category (style, security, performance, etc.)
        description: Description of the standard
        rules: List of rules that define this standard
        examples: Example code snippets (good/bad examples)
        references: Reference links or documentation

    Returns:
        The created standard
    """
    standard_id = _get_next_standard_id()
    standard = {
        "id": standard_id,
        "name": name,
        "category": category,
        "description": description,
        "rules": rules,
        "examples": examples or [],
        "references": references or [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    standards[standard_id] = standard
    _save()
    return Standard(**standard)


@mcp.tool
def get_standard(standard_id: int) -> Optional[Standard]:
    """Get a code standard by ID.

    Args:
        standard_id: The standard ID

    Returns:
        The standard details or None if not found
    """
    standard = standards.get(standard_id)
    return Standard(**standard) if standard else None


@mcp.tool
def list_standards(
    category: Optional[str] = None,
    limit: int = 50,
) -> list[Standard]:
    """List code standards with optional filters.

    Args:
        category: Filter by category
        limit: Maximum number of results

    Returns:
        List of matching standards
    """
    result = list(standards.values())

    if category:
        result = [s for s in result if s.get("category") == category]

    result.sort(key=lambda s: s.get("name", ""))
    return [Standard(**s) for s in result[:limit]]


@mcp.tool
def update_standard(
    standard_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    rules: Optional[list[str]] = None,
    examples: Optional[list[dict]] = None,
) -> Optional[Standard]:
    """Update a code standard.

    Args:
        standard_id: The standard ID
        name: New name
        description: New description
        rules: New rules list
        examples: New examples

    Returns:
        The updated standard or None if not found
    """
    if standard_id not in standards:
        return None

    standard = standards[standard_id]
    if name is not None:
        standard["name"] = name
    if description is not None:
        standard["description"] = description
    if rules is not None:
        standard["rules"] = rules
    if examples is not None:
        standard["examples"] = examples
    standard["updated_at"] = datetime.now().isoformat()
    _save()
    return Standard(**standard)


@mcp.tool
def delete_standard(standard_id: int) -> bool:
    """Delete a code standard.

    Args:
        standard_id: The standard ID

    Returns:
        True if deleted, False if not found
    """
    if standard_id in standards:
        del standards[standard_id]
        _save()
        return True
    return False


# === ANALYTICS TOOLS ===

@mcp.tool
def get_review_summary(review_id: int) -> Optional[dict]:
    """Get a summary of a review session.

    Args:
        review_id: The review ID

    Returns:
        Summary with issue counts by category and severity
    """
    if review_id not in reviews:
        return None

    review = reviews[review_id]
    review_issues = [issues[i] for i in review.get("issues", []) if i in issues]

    summary = {
        "review_id": review_id,
        "title": review.get("title"),
        "status": review.get("status"),
        "total_issues": len(review_issues),
        "by_category": {},
        "by_severity": {},
        "by_status": {},
        "open_critical": 0,
    }

    for issue in review_issues:
        cat = issue.get("category", "unknown")
        sev = issue.get("severity", "medium")
        stat = issue.get("status", "open")

        summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1
        summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
        summary["by_status"][stat] = summary["by_status"].get(stat, 0) + 1

        if issue.get("status") == IssueStatus.OPEN.value and issue.get("severity") == Severity.CRITICAL.value:
            summary["open_critical"] += 1

    return summary


@mcp.tool
def get_overall_stats() -> dict:
    """Get overall statistics across all reviews and issues.

    Returns:
        Statistics about reviews, issues, and standards
    """
    all_issues = list(issues.values())
    all_reviews = list(reviews.values())

    stats = {
        "total_reviews": len(reviews),
        "total_issues": len(issues),
        "total_standards": len(standards),
        "reviews_by_status": {},
        "issues_by_status": {},
        "issues_by_category": {},
        "issues_by_severity": {},
        "open_issues": 0,
        "critical_open": 0,
    }

    for review in all_reviews:
        status = review.get("status", "unknown")
        stats["reviews_by_status"][status] = stats["reviews_by_status"].get(status, 0) + 1

    for issue in all_issues:
        status = issue.get("status", "unknown")
        category = issue.get("category", "unknown")
        severity = issue.get("severity", "medium")

        stats["issues_by_status"][status] = stats["issues_by_status"].get(status, 0) + 1
        stats["issues_by_category"][category] = stats["issues_by_category"].get(category, 0) + 1
        stats["issues_by_severity"][severity] = stats["issues_by_severity"].get(severity, 0) + 1

        if status == IssueStatus.OPEN.value:
            stats["open_issues"] += 1
            if severity == Severity.CRITICAL.value:
                stats["critical_open"] += 1

    return stats


@mcp.tool
def search_issues(query: str) -> list[Issue]:
    """Search issues by title, description, or file path.

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
            query_lower in issue.get("file_path", "").lower() or
            query_lower in issue.get("suggestion", "").lower()
        ):
            results.append(issue)

    return [Issue(**i) for i in results[:20]]


# === RESOURCES ===

@mcp.resource("reviews://all")
def get_all_reviews_resource() -> str:
    """Resource providing all reviews as a formatted list."""
    if not reviews:
        return "No reviews found."

    lines = ["# All Code Reviews\n"]
    for review in sorted(reviews.values(), key=lambda r: r.get("created_at", ""), reverse=True):
        status_emoji = {
            ReviewStatus.PENDING.value: "⏳",
            ReviewStatus.IN_REVIEW.value: "🔍",
            ReviewStatus.APPROVED.value: "✅",
            ReviewStatus.CHANGES_REQUESTED.value: "❌",
        }.get(review.get("status"), "❓")

        lines.append(f"## {status_emoji} {review.get('title', 'Untitled')} (ID: {review['id']})")
        lines.append(f"- **Repository:** {review.get('repository', 'N/A')}")
        lines.append(f"- **Branch:** {review.get('branch', 'N/A')}")
        lines.append(f"- **Status:** {review.get('status', 'unknown')}")
        if review.get("reviewer"):
            lines.append(f"- **Reviewer:** {review['reviewer']}")
        lines.append(f"- **Issues:** {len(review.get('issues', []))}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("issues://open")
def get_open_issues_resource() -> str:
    """Resource providing all open issues."""
    open_issues = [i for i in issues.values() if i.get("status") == IssueStatus.OPEN.value]

    if not open_issues:
        return "No open issues."

    lines = ["# Open Issues\n"]

    # Sort by severity
    severity_order = {
        Severity.CRITICAL.value: 0,
        Severity.HIGH.value: 1,
        Severity.MEDIUM.value: 2,
        Severity.LOW.value: 3,
        Severity.INFO.value: 4,
    }
    open_issues.sort(key=lambda i: severity_order.get(i.get("severity", "medium"), 2))

    for issue in open_issues:
        sev_emoji = {
            Severity.CRITICAL.value: "🔴",
            Severity.HIGH.value: "🟠",
            Severity.MEDIUM.value: "🟡",
            Severity.LOW.value: "🟢",
            Severity.INFO.value: "ℹ️",
        }.get(issue.get("severity", "medium"), "❓")

        lines.append(f"## {sev_emoji} {issue.get('title', 'Untitled')} (ID: {issue['id']})")
        lines.append(f"- **File:** {issue.get('file_path', 'N/A')}")
        if issue.get("line_start"):
            line_info = f"Line {issue['line_start']}"
            if issue.get("line_end") and issue["line_end"] != issue["line_start"]:
                line_info += f"-{issue['line_end']}"
            lines.append(f"- **Location:** {line_info}")
        lines.append(f"- **Category:** {issue.get('category', 'unknown')}")
        lines.append(f"- **Description:** {issue.get('description', 'N/A')}")
        if issue.get("suggestion"):
            lines.append(f"- **Suggestion:** {issue['suggestion']}")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("standards://all")
def get_all_standards_resource() -> str:
    """Resource providing all code standards."""
    if not standards:
        return "No code standards defined."

    lines = ["# Code Quality Standards\n"]

    # Group by category
    by_category = {}
    for standard in standards.values():
        cat = standard.get("category", "general")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(standard)

    for category, cat_standards in sorted(by_category.items()):
        lines.append(f"\n## {category.title()}\n")
        for standard in cat_standards:
            lines.append(f"### {standard.get('name', 'Unnamed')} (ID: {standard['id']})")
            lines.append(f"{standard.get('description', 'No description')}")
            if standard.get("rules"):
                lines.append("\n**Rules:**")
                for rule in standard["rules"]:
                    lines.append(f"- {rule}")
            lines.append("")

    return "\n".join(lines)


@mcp.resource("stats://summary")
def get_stats_resource() -> str:
    """Resource providing overall statistics."""
    stats = get_overall_stats()

    lines = ["# Code Review Statistics\n"]
    lines.append(f"- **Total Reviews:** {stats['total_reviews']}")
    lines.append(f"- **Total Issues:** {stats['total_issues']}")
    lines.append(f"- **Code Standards:** {stats['total_standards']}")
    lines.append(f"- **Open Issues:** {stats['open_issues']}")
    lines.append(f"- **Critical Open Issues:** {stats['critical_open']}")

    if stats["issues_by_category"]:
        lines.append("\n## Issues by Category\n")
        for cat, count in sorted(stats["issues_by_category"].items()):
            lines.append(f"- {cat}: {count}")

    if stats["issues_by_severity"]:
        lines.append("\n## Issues by Severity\n")
        for sev, count in sorted(stats["issues_by_severity"].items()):
            lines.append(f"- {sev}: {count}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
