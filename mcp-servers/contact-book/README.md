# Contact Book MCP Server

A FastMCP server for managing contacts with add, search, update, and delete operations.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

Or with FastMCP CLI:
```bash
fastmcp run server.py
```

## Available Tools

### Contact Management

| Tool | Description |
|------|-------------|
| `add_contact` | Add a new contact with name, email, phone, company, notes |
| `get_contact` | Retrieve a contact by ID |
| `search_contacts` | Search contacts by name, email, phone, or company |
| `update_contact` | Update an existing contact's information |
| `delete_contact` | Delete a contact by ID |
| `list_contacts` | List all contacts with pagination |
| `get_contact_count` | Get total number of contacts |

## Tool Parameters

### add_contact
```python
add_contact(
    name: str,              # Required: Contact's full name
    email: str = None,      # Optional: Email address
    phone: str = None,      # Optional: Phone number
    company: str = None,    # Optional: Company/organization
    notes: str = None       # Optional: Additional notes
)
```

### search_contacts
```python
search_contacts(
    query: str  # Search term to match against contact fields
)
```

### list_contacts
```python
list_contacts(
    limit: int = 50,   # Maximum contacts to return
    offset: int = 0    # Number of contacts to skip
)
```

## Resources

| Resource | Description |
|----------|-------------|
| `contacts://all` | All contacts formatted as a markdown list |

## Example Usage

```python
# Add a contact
contact = add_contact(
    name="John Doe",
    email="john@example.com",
    phone="+1-555-1234",
    company="Acme Corp"
)

# Search for contacts
results = search_contacts("john")

# Get all contacts
all_contacts = list_contacts()
```

## Storage

This server uses in-memory storage by default. Contacts are not persisted between restarts. For production use, consider integrating with a database.