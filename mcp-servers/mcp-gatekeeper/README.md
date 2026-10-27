# MCP Gatekeeper MCP Server

A FastMCP server for identity-aware MCP middleware, OAuth enforcement,
access auditing, and secure MCP routing.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
cd mcp-servers/mcp-gatekeeper
python server.py
```

## Available Tools

### Policy & Access Control
- `create_policy(service_name, allowed_origins, allowed_roles)` — Create access policy
- `get_policy(service_name)` — Retrieve policy by service
- `list_policies()` — List all policies
- `check_access(service_name, user, action, resource, origin)` — Check if access is allowed
- `audit_request(service_name, user, action, resource, origin, result)` — Log access request
- `list_audit_logs()` — List audit logs
- `get_audit_log_count()` — Count audit logs

### Token Management
- `issue_token(service_name, user, token_type)` — Issue OAuth token

### Data Integrity
- `flush_data()` — Force pending writes
- `backup_data()` — Create timestamped backup
- `list_backups()` — List backups, newest first
- `restore_backup(name)` — Restore from backup

---
Created by hamishfromatech - YouTube
---
## Feedback & Community
[hamish@atech.industries](mailto:hamish@atech.industries)