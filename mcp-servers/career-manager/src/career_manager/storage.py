"""
Data storage layer for Career Manager.
Uses JSON files for simple, dependency-free persistence.
"""

import json
from pathlib import Path
from typing import Any
from datetime import datetime
import threading
import uuid

# Default data directory
DATA_DIR = Path.home() / ".career-manager"

# File paths for each data type
DATA_FILES = {
    "profile": DATA_DIR / "profile.json",
    "resume": DATA_DIR / "resume.json",
    "applications": DATA_DIR / "applications.json",
    "interviews": DATA_DIR / "interviews.json",
    "skills": DATA_DIR / "skills.json",
    "goals": DATA_DIR / "goals.json",
    "network": DATA_DIR / "network.json",
}

# File locks for thread-safe access
_locks = {name: threading.RLock() for name in DATA_FILES}  # Use RLock for reentrant locking


def ensure_data_dir() -> None:
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _default_data(name: str) -> dict:
    """Get default data structure for each data type."""
    now = datetime.now().isoformat()
    defaults = {
        "profile": {
            "personal_info": {},
            "social_links": {},
            "preferences": {
                "job_search_status": "open",
                "preferred_locations": [],
                "preferred_work_type": "hybrid",
                "salary_range": {"min": None, "max": None, "currency": "USD"},
            },
            "created_at": now,
            "updated_at": now,
        },
        "resume": {
            "versions": [],
            "current_version": None,
            "sections": {
                "summary": "",
                "experience": [],
                "education": [],
                "skills": [],
                "certifications": [],
                "projects": [],
            },
            "created_at": now,
            "updated_at": now,
        },
        "applications": {
            "applications": [],
            "stats": {
                "total": 0,
                "applied": 0,
                "screening": 0,
                "interview": 0,
                "offer": 0,
                "rejected": 0,
                "withdrawn": 0,
            },
            "created_at": now,
            "updated_at": now,
        },
        "interviews": {
            "sessions": [],
            "questions_bank": [],
            "feedback_history": [],
            "preparation_materials": {},
            "created_at": now,
            "updated_at": now,
        },
        "skills": {
            "technical": [],
            "soft": [],
            "learning": [],
            "target_skills": [],
            "created_at": now,
            "updated_at": now,
        },
        "goals": {
            "short_term": [],
            "long_term": [],
            "milestones": [],
            "achievements": [],
            "created_at": now,
            "updated_at": now,
        },
        "network": {
            "contacts": [],
            "interactions": [],
            "companies": [],
            "created_at": now,
            "updated_at": now,
        },
    }
    return defaults.get(name, {})


def load_data(name: str) -> dict:
    """Load data from JSON file."""
    ensure_data_dir()
    file_path = DATA_FILES.get(name)
    if not file_path:
        return {}

    with _locks[name]:
        if not file_path.exists():
            default = _default_data(name)
            # Write directly without calling save_data to avoid nested lock issues
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2, ensure_ascii=False, default=str)
            return default

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return _default_data(name)


def save_data(name: str, data: dict) -> None:
    """Save data to JSON file."""
    ensure_data_dir()
    file_path = DATA_FILES.get(name)
    if not file_path:
        return

    data["updated_at"] = datetime.now().isoformat()

    with _locks[name]:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def update_data(name: str, updates: dict) -> dict:
    """Update data with partial updates."""
    data = load_data(name)
    data.update(updates)
    save_data(name, data)
    return data


def merge_nested(name: str, path: str, value: Any) -> dict:
    """Merge a value into a nested path in the data.

    Args:
        name: Data type name (profile, resume, etc.)
        path: Dot-separated path (e.g., "personal_info.name")
        value: Value to set

    Returns:
        Updated data dict
    """
    data = load_data(name)
    parts = path.split(".")
    current = data

    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    current[parts[-1]] = value
    save_data(name, data)
    return data


def get_nested(name: str, path: str, default: Any = None) -> Any:
    """Get a value from a nested path in the data.

    Args:
        name: Data type name
        path: Dot-separated path
        default: Default value if path not found

    Returns:
        Value at path or default
    """
    data = load_data(name)
    parts = path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default

    return current


def append_to_list(name: str, path: str, item: dict) -> dict:
    """Append an item to a list in the data.

    Args:
        name: Data type name
        path: Dot-separated path to list
        item: Item to append

    Returns:
        Updated data dict
    """
    data = load_data(name)
    parts = path.split(".")
    current = data

    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    last_part = parts[-1]
    if last_part not in current:
        current[last_part] = []

    # Add ID and timestamp if not present
    if "id" not in item:
        item["id"] = str(uuid.uuid4())[:8]
    if "created_at" not in item:
        item["created_at"] = datetime.now().isoformat()

    current[last_part].append(item)
    save_data(name, data)
    return data


def list_items(name: str, path: str, limit: int = 50, offset: int = 0) -> list:
    """List items from a list in the data with pagination."""
    data = load_data(name)
    parts = path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return []

    if isinstance(current, list):
        return current[offset : offset + limit]
    return []


def delete_item(name: str, path: str, item_id: str) -> bool:
    """Delete an item from a list by ID."""
    data = load_data(name)
    parts = path.split(".")
    current = data

    for part in parts[:-1]:
        if part not in current:
            return False
        current = current[part]

    last_part = parts[-1]
    if last_part not in current or not isinstance(current[last_part], list):
        return False

    original_len = len(current[last_part])
    current[last_part] = [item for item in current[last_part] if item.get("id") != item_id]

    if len(current[last_part]) < original_len:
        save_data(name, data)
        return True
    return False


def update_item(name: str, path: str, item_id: str, updates: dict) -> dict | None:
    """Update an item in a list by ID."""
    data = load_data(name)
    parts = path.split(".")
    current = data

    for part in parts[:-1]:
        if part not in current:
            return None
        current = current[part]

    last_part = parts[-1]
    if last_part not in current or not isinstance(current[last_part], list):
        return None

    for item in current[last_part]:
        if item.get("id") == item_id:
            item.update(updates)
            item["updated_at"] = datetime.now().isoformat()
            save_data(name, data)
            return item
    return None


def get_stats() -> dict:
    """Get overall career management statistics."""
    profile = load_data("profile")
    applications = load_data("applications")
    interviews = load_data("interviews")
    skills = load_data("skills")
    goals = load_data("goals")
    network = load_data("network")

    return {
        "profile_complete": bool(profile.get("personal_info", {}).get("name")),
        "total_applications": len(applications.get("applications", [])),
        "application_stats": applications.get("stats", {}),
        "total_interviews": len(interviews.get("sessions", [])),
        "total_skills": len(skills.get("technical", [])) + len(skills.get("soft", [])),
        "active_goals": len([g for g in goals.get("short_term", []) if g.get("status") == "active"]),
        "network_contacts": len(network.get("contacts", [])),
        "last_updated": profile.get("updated_at"),
    }