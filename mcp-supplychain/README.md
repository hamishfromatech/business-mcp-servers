# MCP Supply Chain Guard MCP Server

A FastMCP server for repo verification, signature verification,
registry integrity checks, typosquatting detection, and package signing.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
cd mcp-servers/mcp-supplychain
python server.py
```

## Available Tools

### Repo Verification
- `verify_repo_signature(repo_url, commit_hash, signature_file, public_key)` — Verify GPG signature
- `check_typosquat(package_name, reported_name, source_url)` — Detect typosquatting packages
- `verify_registry_integrity(repo_url, expected_commit, actual_commit)` — Verify registry commit
- `check_policy(repo_url, cert_expires, signing_key_matches)` — Check signing policy

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