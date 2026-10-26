# Employee Directory MCP Server

A FastMCP server for managing employees with roles, departments, positions,
employment types, onboarding/offboarding, and org charts.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
cd mcp-servers/employee-directory
python server.py
```

## Available Tools

### Employee Management

| Tool | Description |
|------|-------------|
| `add_employee` | Add a new employee with role, department, position |
| `get_employee` | Retrieve an employee by ID |
| `search_employees` | Search by name, email, or role |
| `update_employee` | Update employee details |
| `delete_employee` | Delete an employee by ID |
| `list_employees` | List all employees, sorted by name |
| `get_employee_count` | Total employee count |

### Department Management

| Tool | Description |
|------|-------------|
| `add_department` | Add a new department with slug and optional manager |
| `get_department` | Retrieve a department by ID |
| `list_departments` | List all departments |
| `get_department_count` | Total department count |

### Role & Position Management

| Tool | Description |
|------|-------------|
| `add_role` | Add a job role/title |
| `get_role` | Retrieve a role by ID |
| `list_roles` | List all roles |
| `add_position` | Add a position level (senior/junior/mid) |
| `get_position` | Retrieve a position by ID |
| `list_positions` | List all positions |

### Data Integrity

| Tool | Description |
|------|-------------|
| `flush_data` | Force any pending writes to disk |
| `backup_data` | Copy current data to `backups/` with timestamp |
| `list_backups` | List snapshots, newest first |
| `restore_backup` | Restore from a named backup (restart server to load) |

## Employee Fields

- `id` — Auto-generated integer
- `first_name` / `last_name` — Name fields
- `email` — Email address
- `phone` — Optional phone number
- `role_id` — Reference to a role/title
- `department_id` — Reference to a department
- `position_id` — Optional reference to a position level
- `employment_type` — Full-time, part-time, contractor, or intern
- `start_date` — ISO date string (auto-filled on creation)
- `status` — Active, onboarding, offboarding, or terminated
- `manager_id` — Optional employee ID (reports to)
- `notes` — Optional notes
- `created_at` / `updated_at` — ISO timestamps

## Sorting

Employees are sorted by first name in list operations.

---

Created by **hamishfromatech** - [YouTube](https://youtube.com/@hamishfromatech)
---

## Feedback & Community

Found this MCP server genuinely useful? I'd love to hear from you.

- **Email**: [hamish@atech.industries](mailto:hamish@atech.industries)
- **Join our free Open Source AI Builders Club on Skool**: [https://www.skool.com/open-source-ai-builders-club](https://www.skool.com/open-source-ai-builders-club)
