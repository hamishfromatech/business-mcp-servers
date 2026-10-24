"""
File Organizer MCP Server
A FastMCP server for organizing, categorizing, and managing files.
"""

import os
import atexit
import shutil
import hashlib
from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import tempfile
import threading
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="File Organizer",
    instructions="A file organization server for categorizing, moving, and managing files."
)


class OrganizationRule(BaseModel):
    """A file organization rule."""
    id: int
    name: str
    source_pattern: str
    target_directory: str
    file_types: list[str] = []
    created_at: str


class FileInfo(BaseModel):
    """Information about a file."""
    path: str
    name: str
    extension: str
    size: int
    modified: str


class DuplicateFile(BaseModel):
    """A file within a duplicate group."""
    path: str
    size: int
    modified: str


class DuplicateGroup(BaseModel):
    """A group of duplicate files."""
    hash: str
    size_bytes: int
    files: list[DuplicateFile]

# Data persistence setup
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "organizer.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"organization_rules": {}, "file_registry": {}, "next_rule_id": 1}


_write_lock = threading.Lock()
_last_payload: Optional[str] = None
_pending_payload: Optional[str] = None
_flush_timer: Optional[threading.Timer] = None
_WRITE_DEBOUNCE_MS = int(os.environ.get("MCP_WRITE_DEBOUNCE_MS", "0") or 0)


def _write_payload(payload: str) -> None:
    """Atomically replace the data file with serialized JSON."""
    global _last_payload
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, DATA_FILE)
        _last_payload = payload
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _flush_pending() -> None:
    """Write any deferred payload to disk immediately."""
    global _pending_payload
    with _write_lock:
        if _pending_payload is not None:
            payload, _pending_payload = _pending_payload, None
            _write_payload(payload)


def _save_data(data: dict) -> None:
    """Save data atomically, skipping unchanged writes.

    Writes to a temp file in the same directory then os.replace()s it into
    place, so an interrupted write can never leave a truncated/corrupt file.
    Set MCP_WRITE_DEBOUNCE_MS>0 to defer disk I/O; pending writes are flushed
    on exit and by the flush_data tool.
    """
    global _pending_payload, _flush_timer
    payload = json.dumps(data, indent=2, default=str)
    if _WRITE_DEBOUNCE_MS <= 0:
        with _write_lock:
            if payload != _last_payload:
                _write_payload(payload)
        return
    with _write_lock:
        if payload == _last_payload:
            return
        _pending_payload = payload
        if _flush_timer is not None:
            _flush_timer.cancel()
        _flush_timer = threading.Timer(_WRITE_DEBOUNCE_MS / 1000.0, _flush_pending)
        _flush_timer.daemon = True
        _flush_timer.start()


atexit.register(_flush_pending)


@mcp.tool
def flush_data() -> dict:
    """Flush any deferred writes to disk immediately."""
    _flush_pending()
    return {"flushed": True, "path": str(DATA_FILE), "debounce_ms": _WRITE_DEBOUNCE_MS}


@mcp.tool
def backup_data() -> dict:
    """Copy the current data file into data/backups/ with a timestamp."""
    _flush_pending()
    if not DATA_FILE.exists():
        raise ValueError("No data file to back up yet")
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = backup_dir / f"{DATA_FILE.stem}-{stamp}.json"
    shutil.copy2(DATA_FILE, target)
    return {"backup": str(target), "bytes": target.stat().st_size}


@mcp.tool
def list_backups() -> list[dict]:
    """List available data backups, newest first."""
    backup_dir = DATA_DIR / "backups"
    if not backup_dir.exists():
        return []
    items = []
    for path in sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        items.append({
            "name": path.name,
            "bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        })
    return items


@mcp.tool
def restore_backup(name: str) -> dict:
    """Restore a backup, replacing current data. Restart the server to load it."""
    source = DATA_DIR / "backups" / name
    if not source.exists():
        raise ValueError(f"Unknown backup: {name}")
    with _write_lock:
        _write_payload(source.read_text(encoding="utf-8"))
    return {"restored": name, "note": "Restart the MCP server to load the restored data"}


# Initialize data
_data = _load_data()
organization_rules: dict[int, dict] = {int(k): v for k, v in _data.get("organization_rules", {}).items()}
file_registry: dict[str, dict] = _data.get("file_registry", {})
_next_rule_id = _data.get("next_rule_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "organization_rules": organization_rules,
        "file_registry": file_registry,
        "next_rule_id": _next_rule_id
    })


# Category definitions with extensions
DEFAULT_CATEGORIES = {
    "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"],
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
    "videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".rb"],
    "data": [".json", ".xml", ".csv", ".yaml", ".yml", ".sql", ".db"],
}


def _get_next_rule_id() -> int:
    global _next_rule_id
    id_ = _next_rule_id
    _next_rule_id += 1
    return id_


def _get_file_hash(filepath: str) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def _get_category_for_extension(extension: str) -> str:
    """Get the category for a file extension."""
    ext = extension.lower()
    for category, extensions in DEFAULT_CATEGORIES.items():
        if ext in extensions:
            return category
    return "other"


# File Analysis Tools
@mcp.tool
def analyze_directory(directory: str, recursive: bool = True) -> dict:
    """Analyze a directory and return file statistics.

    Args:
        directory: Path to the directory to analyze
        recursive: Whether to analyze subdirectories

    Returns:
        Statistics about files in the directory
    """
    path = Path(directory)
    if not path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    stats = {
        "total_files": 0,
        "total_size": 0,
        "by_category": {},
        "by_extension": {},
        "large_files": [],
        "duplicate_candidates": []
    }

    file_hashes: dict[str, list[str]] = {}

    if recursive:
        pattern = "**/*"
    else:
        pattern = "*"

    for filepath in path.glob(pattern):
        if filepath.is_file():
            stats["total_files"] += 1
            size = filepath.stat().st_size
            stats["total_size"] += size

            # Track by extension
            ext = filepath.suffix.lower() or ".no_extension"
            stats["by_extension"][ext] = stats["by_extension"].get(ext, 0) + 1

            # Track by category
            category = _get_category_for_extension(ext)
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

            # Track large files (> 10MB)
            if size > 10 * 1024 * 1024:
                stats["large_files"].append({
                    "path": str(filepath),
                    "size_mb": round(size / (1024 * 1024), 2)
                })

            # Track potential duplicates by size
            try:
                file_hash = _get_file_hash(str(filepath))
                if file_hash in file_hashes:
                    file_hashes[file_hash].append(str(filepath))
                else:
                    file_hashes[file_hash] = [str(filepath)]
            except Exception:
                pass

    # Find duplicates
    stats["duplicate_candidates"] = [
        {"files": files, "hash": h}
        for h, files in file_hashes.items()
        if len(files) > 1
    ]

    stats["total_size_mb"] = round(stats["total_size"] / (1024 * 1024), 2)
    return stats


@mcp.tool
def categorize_file(filepath: str) -> dict:
    """Determine the category for a specific file.

    Args:
        filepath: Path to the file

    Returns:
        File category and metadata
    """
    path = Path(filepath)
    if not path.exists():
        raise ValueError(f"File does not exist: {filepath}")

    ext = path.suffix.lower()
    category = _get_category_for_extension(ext)

    stat = path.stat()

    return {
        "path": str(path),
        "name": path.name,
        "extension": ext,
        "category": category,
        "size": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
    }


@mcp.tool
def list_files_by_category(directory: str, category: str) -> list[FileInfo]:
    """List all files in a directory that belong to a category.

    Args:
        directory: Path to the directory
        category: Category name (documents, images, videos, audio, archives, code, data, other)

    Returns:
        List of files in the category
    """
    path = Path(directory)
    if not path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    extensions = DEFAULT_CATEGORIES.get(category, [])
    files = []

    for filepath in path.glob("**/*"):
        if filepath.is_file():
            ext = filepath.suffix.lower()
            if ext in extensions:
                stat = filepath.stat()
                files.append(FileInfo(
                    path=str(filepath),
                    name=filepath.name,
                    extension=ext,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
                ))

    return files


# Organization Tools
@mcp.tool
def create_organization_rule(
    name: str,
    source_pattern: str,
    target_directory: str,
    file_types: Optional[list[str]] = None
) -> OrganizationRule:
    """Create a rule for organizing files.

    Args:
        name: Rule name
        source_pattern: Glob pattern for source files
        target_directory: Where to move matching files
        file_types: Optional list of extensions to match

    Returns:
        The created rule
    """
    rule_id = _get_next_rule_id()
    rule = OrganizationRule(
        id=rule_id,
        name=name,
        source_pattern=source_pattern,
        target_directory=target_directory,
        file_types=file_types or [],
        created_at=datetime.now().isoformat()
    )
    organization_rules[rule_id] = rule.model_dump()
    _save()
    return rule


@mcp.tool
def list_organization_rules() -> list[OrganizationRule]:
    """List all organization rules.

    Returns:
        List of rules
    """
    return [OrganizationRule(**r) for r in organization_rules.values()]


@mcp.tool
def delete_organization_rule(rule_id: int) -> bool:
    """Delete an organization rule.

    Args:
        rule_id: The rule ID to delete

    Returns:
        True if deleted, False if not found
    """
    if rule_id in organization_rules:
        del organization_rules[rule_id]
        _save()
        return True
    return False


@mcp.tool
def organize_directory(
    directory: str,
    dry_run: bool = True,
    create_folders: bool = True
) -> dict:
    """Organize files in a directory by category.

    Args:
        directory: Path to the directory to organize
        dry_run: If True, only show what would be done without moving files
        create_folders: If True, create category folders if they don't exist

    Returns:
        Summary of organization actions
    """
    path = Path(directory)
    if not path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    actions = {
        "moved": [],
        "skipped": [],
        "errors": [],
        "dry_run": dry_run
    }

    for filepath in path.glob("*"):
        if filepath.is_file():
            ext = filepath.suffix.lower()
            category = _get_category_for_extension(ext)

            target_dir = path / category
            target_path = target_dir / filepath.name

            if target_path.exists():
                actions["skipped"].append({
                    "file": str(filepath),
                    "reason": "Target already exists"
                })
                continue

            if dry_run:
                actions["moved"].append({
                    "source": str(filepath),
                    "target": str(target_path),
                    "category": category,
                    "simulated": True
                })
            else:
                try:
                    if create_folders:
                        target_dir.mkdir(exist_ok=True)
                    shutil.move(str(filepath), str(target_path))
                    actions["moved"].append({
                        "source": str(filepath),
                        "target": str(target_path),
                        "category": category,
                        "simulated": False
                    })
                except Exception as e:
                    actions["errors"].append({
                        "file": str(filepath),
                        "error": str(e)
                    })

    return actions


@mcp.tool
def find_duplicates(directory: str) -> list[DuplicateGroup]:
    """Find duplicate files in a directory.

    Args:
        directory: Path to search for duplicates

    Returns:
        List of duplicate file groups
    """
    path = Path(directory)
    if not path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    file_hashes: dict[str, list[DuplicateFile]] = {}

    for filepath in path.glob("**/*"):
        if filepath.is_file():
            try:
                file_hash = _get_file_hash(str(filepath))
                stat = filepath.stat()
                file_info = DuplicateFile(
                    path=str(filepath),
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
                )

                if file_hash in file_hashes:
                    file_hashes[file_hash].append(file_info)
                else:
                    file_hashes[file_hash] = [file_info]
            except Exception:
                pass

    return [
        DuplicateGroup(
            hash=h,
            size_bytes=files[0].size,
            files=files
        )
        for h, files in file_hashes.items()
        if len(files) > 1
    ]


@mcp.tool
def create_folder_structure(base_directory: str, structure: dict) -> dict:
    """Create a folder structure from a template.

    Args:
        base_directory: Base path where folders will be created
        structure: Dictionary defining folder structure (keys are folder names, values are sub-folders)

    Returns:
        Summary of created folders
    """
    base_path = Path(base_directory)
    created = []
    errors = []

    def create_recursive(current_path: Path, struct: dict):
        for name, subdirs in struct.items():
            folder_path = current_path / name
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                created.append(str(folder_path))
                if subdirs:
                    create_recursive(folder_path, subdirs)
            except Exception as e:
                errors.append({"path": str(folder_path), "error": str(e)})

    create_recursive(base_path, structure)

    return {"created": created, "errors": errors}


# Resources
@mcp.resource("organizer://categories")
def get_categories_resource() -> str:
    """Resource showing file categories and their extensions."""
    lines = ["# File Categories\n"]

    for category, extensions in DEFAULT_CATEGORIES.items():
        lines.append(f"## {category.title()}")
        lines.append(", ".join(extensions))
        lines.append("")

    return "\n".join(lines)


@mcp.resource("organizer://rules")
def get_rules_resource() -> str:
    """Resource showing all organization rules."""
    if not organization_rules:
        return "# Organization Rules\n\nNo rules defined yet."

    lines = ["# Organization Rules\n"]

    for rule in organization_rules.values():
        lines.append(f"## {rule['name']} (ID: {rule['id']})")
        lines.append(f"- Source Pattern: {rule['source_pattern']}")
        lines.append(f"- Target Directory: {rule['target_directory']}")
        if rule['file_types']:
            lines.append(f"- File Types: {', '.join(rule['file_types'])}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()