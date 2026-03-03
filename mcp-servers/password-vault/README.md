# Password Vault MCP Server

A FastMCP server for securely storing and managing credentials.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Security Note

This server uses a simple XOR encryption for demonstration. For production use, integrate with a proper encryption library like `cryptography` and use secure key derivation.

## Available Tools

### Vault Setup

| Tool | Description |
|------|-------------|
| `setup_vault` | Initialize vault with master password |
| `is_vault_setup` | Check if vault is initialized |
| `verify_master_password` | Verify master password |

### Category Management

| Tool | Description |
|------|-------------|
| `create_category` | Create a category for organizing entries |
| `list_categories` | List all categories |

### Entry Management

| Tool | Description |
|------|-------------|
| `create_entry` | Create a new vault entry |
| `get_entry` | Get entry with decrypted password |
| `list_entries` | List entries (passwords masked) |
| `update_entry` | Update an entry |
| `delete_entry` | Delete an entry |
| `search_entries` | Search entries by site/username |

### Password Tools

| Tool | Description |
|------|-------------|
| `generate_password` | Generate a secure random password |
| `check_password_strength` | Check password strength |

## Resources

| Resource | Description |
|----------|-------------|
| `vault://stats` | Vault statistics |
| `vault://entries` | All entries (passwords masked) |

## Example Usage

```python
# Initialize vault
setup_vault(master_password="your-secure-master-password")

# Create categories
social = create_category(name="Social Media", icon="share")
work = create_category(name="Work", icon="briefcase")

# Create entry
entry = create_entry(
    site="GitHub",
    username="developer",
    password="my-secret-password",
    master_password="your-master-password",
    url="https://github.com",
    category_id=2,
    notes="Work account"
)

# Retrieve entry (with decrypted password)
entry = get_entry(entry_id=1, master_password="your-master-password")
print(entry["password"])  # Decrypted password

# List entries (passwords hidden)
entries = list_entries()

# Generate secure password
password = generate_password(
    length=20,
    include_uppercase=True,
    include_lowercase=True,
    include_numbers=True,
    include_symbols=True
)

# Check password strength
strength = check_password_strength("MyP@ssw0rd!")
# Returns: score, strength, feedback
```

## Password Generation Options

- `length` - Password length (default: 16)
- `include_uppercase` - Include A-Z
- `include_lowercase` - Include a-z
- `include_numbers` - Include 0-9
- `include_symbols` - Include special characters

## Storage

This server uses in-memory storage. For production, integrate with encrypted file storage or a secure database.