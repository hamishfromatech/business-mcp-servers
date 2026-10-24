"""
Contact Book MCP Server
A FastMCP server for managing contacts with add, search, update, and delete operations.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import os
import shutil
import atexit
import tempfile
import threading
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Contact Book",
    instructions="A contact management server for storing, searching, and organizing contacts."
)


class Contact(BaseModel):
    """A contact in the contact book."""
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str

# Data persistence setup
DATA_DIR = Path(os.environ.get("MCP_DATA_DIR") or (Path(__file__).parent / "data"))
DATA_FILE = DATA_DIR / "contacts.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"contacts": {}, "next_id": 1}


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
contacts: dict[int, dict] = {int(k): v for k, v in _data.get("contacts", {}).items()}
_next_id = _data.get("next_id", 1)


def _get_next_id() -> int:
    global _next_id
    id_ = _next_id
    _next_id += 1
    return id_


def _save() -> None:
    """Save current state to disk."""
    _save_data({"contacts": contacts, "next_id": _next_id})


@mcp.tool
def add_contact(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    notes: Optional[str] = None
) -> Contact:
    """Add a new contact to the contact book.

    Args:
        name: The contact's full name (required)
        email: The contact's email address
        phone: The contact's phone number
        company: The contact's company/organization
        notes: Additional notes about the contact

    Returns:
        The created contact with its assigned ID
    """
    contact_id = _get_next_id()
    contact = Contact(
        id=contact_id,
        name=name,
        email=email,
        phone=phone,
        company=company,
        notes=notes,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    contacts[contact_id] = contact.model_dump()
    _save()
    return contact


@mcp.tool
def get_contact(contact_id: int) -> Optional[Contact]:
    """Retrieve a contact by ID.

    Args:
        contact_id: The unique ID of the contact

    Returns:
        The contact details or None if not found
    """
    data = contacts.get(contact_id)
    if data is None:
        return None
    return Contact(**data)


@mcp.tool
def search_contacts(query: str) -> list[Contact]:
    """Search contacts by name, email, phone, or company.

    Args:
        query: Search term to match against contact fields

    Returns:
        List of matching contacts
    """
    query_lower = query.lower()
    results = []
    for contact_data in contacts.values():
        if any(
            query_lower in str(v).lower()
            for k, v in contact_data.items()
            if v is not None and k != "id"
        ):
            results.append(Contact(**contact_data))
    return results


@mcp.tool
def update_contact(
    contact_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[Contact]:
    """Update an existing contact.

    Args:
        contact_id: The ID of the contact to update
        name: New name for the contact
        email: New email address
        phone: New phone number
        company: New company name
        notes: New notes

    Returns:
        The updated contact or None if not found
    """
    if contact_id not in contacts:
        return None

    contact = contacts[contact_id]
    if name is not None:
        contact["name"] = name
    if email is not None:
        contact["email"] = email
    if phone is not None:
        contact["phone"] = phone
    if company is not None:
        contact["company"] = company
    if notes is not None:
        contact["notes"] = notes
    contact["updated_at"] = datetime.now().isoformat()
    _save()

    return Contact(**contact)


@mcp.tool
def delete_contact(contact_id: int) -> bool:
    """Delete a contact by ID.

    Args:
        contact_id: The ID of the contact to delete

    Returns:
        True if deleted, False if not found
    """
    if contact_id in contacts:
        del contacts[contact_id]
        _save()
        return True
    return False


@mcp.tool
def list_contacts(limit: int = 50, offset: int = 0) -> list[Contact]:
    """List all contacts with pagination.

    Args:
        limit: Maximum number of contacts to return (default 50)
        offset: Number of contacts to skip (default 0)

    Returns:
        List of contacts
    """
    all_contacts = sorted(contacts.values(), key=lambda c: c.get("name", ""))
    return [Contact(**c) for c in all_contacts[offset:offset + limit]]


@mcp.tool
def get_contact_count() -> int:
    """Get the total number of contacts.

    Returns:
        Total count of contacts in the book
    """
    return len(contacts)


@mcp.resource("contacts://all")
def get_all_contacts_resource() -> str:
    """Resource providing all contacts as a formatted list."""
    if not contacts:
        return "No contacts found."

    lines = ["# All Contacts\n"]
    for contact in sorted(contacts.values(), key=lambda c: c.get("name", "")):
        lines.append(f"## {contact['name']} (ID: {contact['id']})")
        if contact.get("email"):
            lines.append(f"- Email: {contact['email']}")
        if contact.get("phone"):
            lines.append(f"- Phone: {contact['phone']}")
        if contact.get("company"):
            lines.append(f"- Company: {contact['company']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()