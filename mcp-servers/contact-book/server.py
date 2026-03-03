"""
Contact Book MCP Server
A FastMCP server for managing contacts with add, search, update, and delete operations.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
from fastmcp import FastMCP

mcp = FastMCP(
    name="Contact Book",
    instructions="A contact management server for storing, searching, and organizing contacts."
)

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "contacts.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"contacts": {}, "next_id": 1}


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
contacts: dict[int, dict] = {int(k): v for k, v in _data.get("contacts", {}).items()}
_next_id = _data.get("next_id", 1)


def _get_next_id() -> int:
    global _next_id
    id_ = _next_id
    _next_id += 1
    _save_data({"contacts": contacts, "next_id": _next_id})
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
) -> dict:
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
    contact = {
        "id": contact_id,
        "name": name,
        "email": email,
        "phone": phone,
        "company": company,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    contacts[contact_id] = contact
    _save()
    return contact


@mcp.tool
def get_contact(contact_id: int) -> Optional[dict]:
    """Retrieve a contact by ID.

    Args:
        contact_id: The unique ID of the contact

    Returns:
        The contact details or None if not found
    """
    return contacts.get(contact_id)


@mcp.tool
def search_contacts(query: str) -> list[dict]:
    """Search contacts by name, email, phone, or company.

    Args:
        query: Search term to match against contact fields

    Returns:
        List of matching contacts
    """
    query_lower = query.lower()
    results = []
    for contact in contacts.values():
        if any(
            query_lower in str(v).lower()
            for k, v in contact.items()
            if v is not None and k != "id"
        ):
            results.append(contact)
    return results


@mcp.tool
def update_contact(
    contact_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[dict]:
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

    return contact


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
def list_contacts(limit: int = 50, offset: int = 0) -> list[dict]:
    """List all contacts with pagination.

    Args:
        limit: Maximum number of contacts to return (default 50)
        offset: Number of contacts to skip (default 0)

    Returns:
        List of contacts
    """
    all_contacts = sorted(contacts.values(), key=lambda c: c.get("name", ""))
    return all_contacts[offset:offset + limit]


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