# MCP Security Scanner MCP Server

A FastMCP server for CVE detection, tool-poisoning identification,
vulnerability tracking, and security alert generation.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
cd mcp-servers/mcp-security-scanner
python server.py
```

## Available Tools

### Security Scanning
- `run_cve_scan(selector, targets, severity_filter, exclude_patterns)` — Execute CVE pattern scan
- `get_scan(scan_id)` — Retrieve completed scan
- `complete_scan(scan_id, findings, tool_poisoned)` — Mark scan as complete
- `add_vulnerability(title, category, severity, target, cvss_score, cve_id, description, mitigation, references)` — Report vulnerability
- `get_vulnerability(vuln_id)` — Get vulnerability details
- `search_vulnerabilities(query)` — Search vulnerabilities
- `get_vulnerability_count()` — Count total vulnerabilities
- `list_scans()` — List all scans
- `get_scan_count()` — Count scans

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