"""
Password Vault MCP Server
A FastMCP server for securely storing and managing credentials.

Note: This is a basic implementation. For production use, implement proper
encryption at rest using libraries like cryptography or passlib.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import base64
import hashlib
import secrets
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Password Vault",
    instructions="A secure password vault server for storing and managing credentials with encryption."
)


class Category(BaseModel):
    """A category for organizing vault entries."""
    id: int
    name: str
    icon: Optional[str] = None
    created_at: str


class VaultEntry(BaseModel):
    """A vault entry (password masked)."""
    id: int
    site: str
    username: str
    url: Optional[str] = None
    category_id: Optional[int] = None
    notes: Optional[str] = None
    has_password: bool = True
    created_at: str
    updated_at: str

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "vault.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "vault_entries": {}, "categories": {}, "master_key_hash": None,
        "next_entry_id": 1, "next_category_id": 1
    }


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
vault_entries: dict[int, dict] = {int(k): v for k, v in _data.get("vault_entries", {}).items()}
categories: dict[int, dict] = {int(k): v for k, v in _data.get("categories", {}).items()}
master_key_hash: Optional[str] = _data.get("master_key_hash")

_next_entry_id = _data.get("next_entry_id", 1)
_next_category_id = _data.get("next_category_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "vault_entries": vault_entries, "categories": categories,
        "master_key_hash": master_key_hash,
        "next_entry_id": _next_entry_id, "next_category_id": _next_category_id
    })


def _get_next_entry_id() -> int:
    global _next_entry_id
    id_ = _next_entry_id
    _next_entry_id += 1
    return id_


def _get_next_category_id() -> int:
    global _next_category_id
    id_ = _next_category_id
    _next_category_id += 1
    return id_


def _simple_encrypt(data: str, key: str) -> str:
    """Simple XOR encryption for demo purposes.
    In production, use proper encryption like Fernet from cryptography library.
    """
    key_bytes = key.encode('utf-8')
    data_bytes = data.encode('utf-8')
    encrypted = bytes([data_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data_bytes))])
    return base64.b64encode(encrypted).decode('utf-8')


def _simple_decrypt(encrypted_data: str, key: str) -> str:
    """Simple XOR decryption for demo purposes."""
    key_bytes = key.encode('utf-8')
    data_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
    decrypted = bytes([data_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data_bytes))])
    return decrypted.decode('utf-8')


def _hash_key(key: str) -> str:
    """Hash a key using SHA-256."""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


# Master Key Management
@mcp.tool
def setup_vault(master_password: str) -> dict:
    """Initialize the vault with a master password.

    Args:
        master_password: The master password to secure the vault

    Returns:
        Setup confirmation
    """
    global master_key_hash
    master_key_hash = _hash_key(master_password)
    _save()
    return {"message": "Vault initialized successfully", "setup": True}


@mcp.tool
def is_vault_setup() -> bool:
    """Check if the vault has been initialized.

    Returns:
        True if vault is set up
    """
    return master_key_hash is not None


@mcp.tool
def verify_master_password(password: str) -> bool:
    """Verify the master password.

    Args:
        password: The password to verify

    Returns:
        True if correct
    """
    if master_key_hash is None:
        return False
    return _hash_key(password) == master_key_hash


# Category Management
@mcp.tool
def create_category(name: str, icon: Optional[str] = None) -> Category:
    """Create a category for organizing vault entries.

    Args:
        name: Category name
        icon: Optional icon identifier

    Returns:
        The created category
    """
    category_id = _get_next_category_id()
    category = Category(
        id=category_id,
        name=name,
        icon=icon,
        created_at=datetime.now().isoformat()
    )
    categories[category_id] = category.model_dump()
    _save()
    return category


@mcp.tool
def list_categories() -> list[Category]:
    """List all categories.

    Returns:
        List of categories
    """
    return [Category(**c) for c in categories.values()]


# Vault Entry Management
@mcp.tool
def create_entry(
    site: str,
    username: str,
    password: str,
    master_password: str,
    url: Optional[str] = None,
    category_id: Optional[int] = None,
    notes: Optional[str] = None
) -> VaultEntry:
    """Create a new vault entry.

    Args:
        site: Site/service name
        username: Username/email
        password: The password to store
        master_password: Master password for encryption
        url: Optional site URL
        category_id: Optional category ID
        notes: Optional notes

    Returns:
        The created entry (password masked)
    """
    if not verify_master_password(master_password):
        raise ValueError("Invalid master password")

    entry_id = _get_next_entry_id()
    encrypted_password = _simple_encrypt(password, master_password)

    entry = {
        "id": entry_id,
        "site": site,
        "username": username,
        "password_encrypted": encrypted_password,
        "url": url,
        "category_id": category_id,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    vault_entries[entry_id] = entry
    _save()

    return VaultEntry(
        id=entry_id,
        site=site,
        username=username,
        url=url,
        category_id=category_id,
        notes=notes,
        has_password=True,
        created_at=entry["created_at"],
        updated_at=entry["updated_at"]
    )


@mcp.tool
def get_entry(entry_id: int, master_password: str) -> Optional[dict]:
    """Get a vault entry with decrypted password.

    Args:
        entry_id: The entry ID
        master_password: Master password for decryption

    Returns:
        Entry with decrypted password or None
    """
    if entry_id not in vault_entries:
        return None

    if not verify_master_password(master_password):
        raise ValueError("Invalid master password")

    entry = vault_entries[entry_id]
    result = entry.copy()
    result["password"] = _simple_decrypt(entry["password_encrypted"], master_password)
    del result["password_encrypted"]
    return result


@mcp.tool
def list_entries(category_id: Optional[int] = None) -> list[VaultEntry]:
    """List all vault entries (passwords masked).

    Args:
        category_id: Optional filter by category

    Returns:
        List of entries without passwords
    """
    result = []
    for entry in vault_entries.values():
        if category_id is not None and entry.get("category_id") != category_id:
            continue
        result.append(VaultEntry(
            id=entry["id"],
            site=entry["site"],
            username=entry["username"],
            url=entry.get("url"),
            category_id=entry.get("category_id"),
            notes=entry.get("notes"),
            has_password=True,
            created_at=entry["created_at"],
            updated_at=entry["updated_at"]
        ))

    return result


@mcp.tool
def update_entry(
    entry_id: int,
    master_password: str,
    site: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    url: Optional[str] = None,
    category_id: Optional[int] = None,
    notes: Optional[str] = None
) -> Optional[VaultEntry]:
    """Update a vault entry.

    Args:
        entry_id: The entry ID
        master_password: Master password
        site: New site name
        username: New username
        password: New password
        url: New URL
        category_id: New category
        notes: New notes

    Returns:
        Updated entry or None
    """
    if entry_id not in vault_entries:
        return None

    if not verify_master_password(master_password):
        raise ValueError("Invalid master password")

    entry = vault_entries[entry_id]
    if site is not None:
        entry["site"] = site
    if username is not None:
        entry["username"] = username
    if password is not None:
        entry["password_encrypted"] = _simple_encrypt(password, master_password)
    if url is not None:
        entry["url"] = url
    if category_id is not None:
        entry["category_id"] = category_id
    if notes is not None:
        entry["notes"] = notes

    entry["updated_at"] = datetime.now().isoformat()
    _save()

    return VaultEntry(
        id=entry["id"],
        site=entry["site"],
        username=entry["username"],
        url=entry.get("url"),
        category_id=entry.get("category_id"),
        notes=entry.get("notes"),
        has_password=True,
        created_at=entry["created_at"],
        updated_at=entry["updated_at"]
    )


@mcp.tool
def delete_entry(entry_id: int, master_password: str) -> bool:
    """Delete a vault entry.

    Args:
        entry_id: The entry ID
        master_password: Master password for verification

    Returns:
        True if deleted, False if not found
    """
    if not verify_master_password(master_password):
        raise ValueError("Invalid master password")

    if entry_id in vault_entries:
        del vault_entries[entry_id]
        _save()
        return True
    return False


@mcp.tool
def search_entries(query: str) -> list[VaultEntry]:
    """Search vault entries by site, username, or URL.

    Args:
        query: Search term

    Returns:
        List of matching entries (passwords masked)
    """
    query_lower = query.lower()
    result = []

    for entry in vault_entries.values():
        if (query_lower in entry["site"].lower() or
            query_lower in entry["username"].lower() or
            (entry.get("url") and query_lower in entry["url"].lower())):
            result.append(VaultEntry(
                id=entry["id"],
                site=entry["site"],
                username=entry["username"],
                url=entry.get("url"),
                category_id=entry.get("category_id"),
                notes=entry.get("notes"),
                has_password=True,
                created_at=entry["created_at"],
                updated_at=entry["updated_at"]
            ))

    return result


# Password Generation
@mcp.tool
def generate_password(
    length: int = 16,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_numbers: bool = True,
    include_symbols: bool = True
) -> str:
    """Generate a secure random password.

    Args:
        length: Password length (default 16)
        include_uppercase: Include uppercase letters
        include_lowercase: Include lowercase letters
        include_numbers: Include numbers
        include_symbols: Include symbols

    Returns:
        Generated password
    """
    import string

    characters = ""
    if include_uppercase:
        characters += string.ascii_uppercase
    if include_lowercase:
        characters += string.ascii_lowercase
    if include_numbers:
        characters += string.digits
    if include_symbols:
        characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"

    if not characters:
        characters = string.ascii_letters + string.digits

    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password


@mcp.tool
def check_password_strength(password: str) -> dict:
    """Check the strength of a password.

    Args:
        password: The password to check

    Returns:
        Strength analysis and recommendations
    """
    import string

    score = 0
    feedback = []

    # Length check
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Use at least 8 characters")

    if len(password) >= 12:
        score += 1

    if len(password) >= 16:
        score += 1

    # Character variety
    has_upper = any(c in string.ascii_uppercase for c in password)
    has_lower = any(c in string.ascii_lowercase for c in password)
    has_number = any(c in string.digits for c in password)
    has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    variety_count = sum([has_upper, has_lower, has_number, has_symbol])
    score += variety_count

    if not has_upper:
        feedback.append("Add uppercase letters")
    if not has_lower:
        feedback.append("Add lowercase letters")
    if not has_number:
        feedback.append("Add numbers")
    if not has_symbol:
        feedback.append("Add special characters")

    # Common patterns
    common_patterns = ["123", "abc", "qwe", "password", "admin"]
    for pattern in common_patterns:
        if pattern in password.lower():
            score -= 1
            feedback.append(f"Avoid common patterns like '{pattern}'")

    # Determine strength level
    if score <= 2:
        strength = "weak"
    elif score <= 4:
        strength = "moderate"
    elif score <= 6:
        strength = "strong"
    else:
        strength = "very strong"

    return {
        "password": password[:3] + "*" * (len(password) - 3),
        "length": len(password),
        "score": max(0, score),
        "strength": strength,
        "feedback": feedback,
        "has_uppercase": has_upper,
        "has_lowercase": has_lower,
        "has_numbers": has_number,
        "has_symbols": has_symbol
    }


# Statistics
@mcp.tool
def get_vault_stats() -> dict:
    """Get vault statistics.

    Returns:
        Statistics about the vault
    """
    return {
        "total_entries": len(vault_entries),
        "total_categories": len(categories),
        "is_setup": master_key_hash is not None
    }


# Resources
@mcp.resource("vault://stats")
def get_vault_stats_resource() -> str:
    """Resource showing vault statistics."""
    stats = get_vault_stats()

    lines = ["# Password Vault Statistics\n"]
    lines.append(f"- **Status:** {'Set Up' if stats['is_setup'] else 'Not Initialized'}")
    lines.append(f"- **Total Entries:** {stats['total_entries']}")
    lines.append(f"- **Categories:** {stats['total_categories']}")

    return "\n".join(lines)


@mcp.resource("vault://entries")
def get_entries_resource() -> str:
    """Resource showing all vault entries (passwords masked)."""
    entries = list_entries()

    if not entries:
        return "# Vault Entries\n\nNo entries in vault."

    lines = ["# Vault Entries\n"]

    # Group by category
    by_category: dict[int | None, list] = {}
    for entry in entries:
        cat_id = entry.get("category_id")
        if cat_id not in by_category:
            by_category[cat_id] = []
        by_category[cat_id].append(entry)

    for cat_id, cat_entries in by_category.items():
        if cat_id is None:
            lines.append("## Uncategorized")
        else:
            cat = categories.get(cat_id, {})
            lines.append(f"## {cat.get('name', 'Unknown')}")

        for entry in cat_entries:
            lines.append(f"- **{entry['site']}**")
            lines.append(f"  - Username: {entry['username']}")
            if entry.get("url"):
                lines.append(f"  - URL: {entry['url']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()