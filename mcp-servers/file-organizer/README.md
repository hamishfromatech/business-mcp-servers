# File Organizer MCP Server

A FastMCP server for organizing, categorizing, and managing files.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### File Analysis

| Tool | Description |
|------|-------------|
| `analyze_directory` | Analyze directory for file statistics |
| `categorize_file` | Determine category for a specific file |
| `list_files_by_category` | List files in a category |
| `find_duplicates` | Find duplicate files by hash |

### Organization

| Tool | Description |
|------|-------------|
| `create_organization_rule` | Create a rule for organizing files |
| `list_organization_rules` | List all organization rules |
| `delete_organization_rule` | Delete an organization rule |
| `organize_directory` | Organize files by category |
| `create_folder_structure` | Create folders from template |

## File Categories

| Category | Extensions |
|----------|------------|
| `documents` | .pdf, .doc, .docx, .txt, .rtf, .odt, .xls, .xlsx, .ppt, .pptx |
| `images` | .jpg, .jpeg, .png, .gif, .bmp, .svg, .webp, .ico |
| `videos` | .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm |
| `audio` | .mp3, .wav, .flac, .aac, .ogg, .wma, .m4a |
| `archives` | .zip, .rar, .7z, .tar, .gz, .bz2 |
| `code` | .py, .js, .ts, .java, .cpp, .c, .h, .cs, .go, .rs, .rb |
| `data` | .json, .xml, .csv, .yaml, .yml, .sql, .db |

## Resources

| Resource | Description |
|----------|-------------|
| `organizer://categories` | File categories and their extensions |
| `organizer://rules` | All organization rules |

## Example Usage

```python
# Analyze a directory
stats = analyze_directory("/path/to/folder", recursive=True)
# Returns: total_files, total_size, by_category, by_extension, large_files, duplicate_candidates

# Get file category
info = categorize_file("/path/to/file.pdf")
# Returns: path, name, extension, category, size, modified

# Organize directory (dry run)
actions = organize_directory("/path/to/folder", dry_run=True)
# Returns: moved, skipped, errors

# Organize directory (actually move files)
actions = organize_directory("/path/to/folder", dry_run=False, create_folders=True)

# Find duplicates
duplicates = find_duplicates("/path/to/folder")
# Returns groups of duplicate files

# Create folder structure
structure = {
    "Documents": {"Work": None, "Personal": None},
    "Media": {"Photos": None, "Videos": None}
}
result = create_folder_structure("/base/path", structure)
```

## Safety Features

- `organize_directory` has `dry_run=True` by default
- File hashes are calculated using MD5 for duplicate detection
- Large files (>10MB) are flagged in analysis

## Storage

This server uses in-memory storage. Organization rules are not persisted between restarts.