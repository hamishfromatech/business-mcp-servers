# REMOTE WORK PERKS MCP Server

A FastMCP server for remote work benefits, tool access, reimbursements,
and policy compliance — all in one place.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
cd mcp-servers/remote-perks
python server.py
```

## Available Tools

### Remote Worker Management

| Tool | Description |
|------|-------------|
| `add_remote_worker` | Register a remote worker with equipment allowances |
| `get_remote_worker` | Lookup a worker by employee ID |
| `list_remote_workers` | List workers, filtered by department or status |
| `get_remote_worker_summary` | Summary: total, active, equipment stats |

### Benefits Plans & Enrollments

| Tool | Description |
|------|-------------|
| `add_benefit_plan` | Create a benefits plan (travel, wellness, learning) |
| `get_benefit_plan` | Retrieve a plan by ID |
| `add_benefit_enrollment` | Enroll an employee in a benefit plan |
| `get_benefit_enrollment` | Retrieve enrollment by ID |
| `list_benefit_enrollments` | List enrollments, filtered by employee or status |

### Reimbursements

| Tool | Description |
|------|-------------|
| `submit_remote_reimbursement` | Submit a reimbursement request |
| `get_reimbursement_request` | Retrieve request by ID |
| `list_reimbursement_requests` | List requests, filtered by status or employee |
| `approve_reimbursement` | Approve a reimbursement request |
| `reject_reimbursement` | Reject a reimbursement with reason |

### Access Requests

| Tool | Description |
|------|-------------|
| `submit_access_request` | Request access to tools, software, or resources |
| `get_access_request` | Retrieve request by ID |
| `list_access_requests` | List requests, filtered by status, employee, or type |
| `grant_access` | Grant approval to an access request |
| `revoke_access` | Revoke access with a reason |

### Policy Management

| Tool | Description |
|------|-------------|
| `add_policy` | Create a remote work policy |
| `get_policy` | Retrieve a policy by ID |
| `list_policies` | List active policies |

### Analytics

| Tool | Description |
|------|-------------|
| `get_reimbursement_summary` | Spend totals by category, type, status |
| `get_access_summary` | Access request counts, active grants |
| `get_benefit_enrollment_summary` | Enrollment totals by designation |
| `get_policy_compliance_summary` | Policy review compliance status |

### Data Integrity

| Tool | Description |
|------|-------------|
| `flush_data` | Force pending writes to disk |
| `backup_data` | Create timestamped backup |
| `list_backups` | List backups, newest first |
| `restore_backup` | Restore from a named backup |

---

Created by **hamishfromatech** - [YouTube](https://youtube.com/@hamishfromatech)
---

## Feedback & Community

[hamish@atech.industries](mailto:hamish@atech.industries)