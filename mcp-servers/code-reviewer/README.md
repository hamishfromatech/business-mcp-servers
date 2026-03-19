# Code Reviewer MCP Server

A FastMCP server for managing code reviews, tracking issues, and maintaining code quality standards.

## Features

- **Review Sessions**: Create and manage code review sessions for branches and pull requests
- **Issue Tracking**: Track code review issues with categories, severity levels, and status
- **Code Standards**: Define and maintain code quality standards and best practices
- **Analytics**: Get summaries and statistics on reviews and issues

## Installation

```bash
pip install fastmcp
```

## Usage

### Running the Server

```bash
cd mcp-servers/code-reviewer
python server.py
```

### With FastMCP CLI

```bash
fastmcp run server.py
# or with hot reload
fastmcp dev server.py
```

## Tools

### Review Sessions

| Tool | Description |
|------|-------------|
| `create_review` | Create a new code review session |
| `get_review` | Get a review session by ID |
| `list_reviews` | List reviews with filters (status, reviewer, repository) |
| `update_review_status` | Update review status (pending, in_review, approved, changes_requested) |
| `add_files_to_review` | Add files to a review session |
| `delete_review` | Delete a review session |

### Issues

| Tool | Description |
|------|-------------|
| `create_issue` | Create a code review issue |
| `get_issue` | Get an issue by ID |
| `list_issues` | List issues with filters (status, category, severity, file) |
| `update_issue` | Update an issue |
| `resolve_issue` | Mark an issue as resolved |
| `delete_issue` | Delete an issue |

### Code Standards

| Tool | Description |
|------|-------------|
| `create_standard` | Create a code quality standard |
| `get_standard` | Get a standard by ID |
| `list_standards` | List standards with filters |
| `update_standard` | Update a standard |
| `delete_standard` | Delete a standard |

### Analytics

| Tool | Description |
|------|-------------|
| `get_review_summary` | Get summary of a review session |
| `get_overall_stats` | Get overall statistics |
| `search_issues` | Search issues by title, description, or file |

## Issue Categories

- `bug` - Bugs and errors
- `security` - Security vulnerabilities
- `performance` - Performance issues
- `style` - Code style issues
- `maintainability` - Maintainability concerns
- `documentation` - Documentation issues
- `testing` - Testing issues
- `architecture` - Architecture concerns

## Severity Levels

- `critical` - Must fix immediately
- `high` - Important, fix soon
- `medium` - Should fix
- `low` - Nice to fix
- `info` - Informational

## Resources

| Resource | Description |
|----------|-------------|
| `reviews://all` | All reviews as formatted list |
| `issues://open` | All open issues |
| `standards://all` | All code standards |
| `stats://summary` | Overall statistics |

## Data Storage

Data is stored in `data/code_reviewer.json` in the server directory.

## Example Usage

```python
# Create a review session
create_review(
    title="Feature: User Authentication",
    repository="myapp",
    branch="feature/auth",
    reviewer="john@example.com"
)

# Create an issue
create_issue(
    review_id=1,
    file_path="src/auth/login.py",
    line_start=42,
    line_end=45,
    category="security",
    severity="high",
    title="Potential SQL injection vulnerability",
    description="User input not properly sanitized before database query",
    suggestion="Use parameterized queries"
)

# Resolve an issue
resolve_issue(
    issue_id=1,
    resolution="Fixed by implementing parameterized queries",
    resolved_by="john@example.com"
)
```

## License

MIT License