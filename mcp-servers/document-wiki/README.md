# Document Wiki MCP Server

A FastMCP server for managing wiki documents and a knowledge base with bi-directional linking.

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Available Tools

### Category Management

| Tool | Description |
|------|-------------|
| `create_category` | Create a category for organizing documents |
| `list_categories` | List all categories |

### Document Management

| Tool | Description |
|------|-------------|
| `create_document` | Create a new wiki document |
| `get_document` | Get a document by ID |
| `get_document_by_title` | Get a document by title |
| `update_document` | Update an existing document |
| `delete_document` | Delete a document |
| `search_documents` | Search documents by title, content, or tags |
| `get_documents_by_category` | Get all documents in a category |
| `get_documents_by_tag` | Get all documents with a tag |
| `get_all_tags` | Get all unique tags |

### Linking

| Tool | Description |
|------|-------------|
| `get_linked_documents` | Get documents linked via [[wikilinks]] |
| `get_backlinks` | Get documents that link to this document |

## Wiki Links

Documents support `[[title]]` syntax for linking to other documents:

```markdown
# My Document

This links to [[Another Document]] and [[Some Other Page]].

Tags are also supported: #documentation #important
```

## Resources

| Resource | Description |
|----------|-------------|
| `wiki://index` | Wiki index with all documents |
| `wiki://recent` | Recently updated documents |
| `wiki://tags` | All tags with document counts |

## Example Usage

```python
# Create a category
cat = create_category(name="Documentation", description="Technical docs")

# Create a document
doc = create_document(
    title="Getting Started",
    content="# Getting Started\n\nSee [[Installation]] for setup.\n#beginners",
    category_id=1,
    tags=["tutorial", "basics"]
)

# Create another linked document
doc2 = create_document(
    title="Installation",
    content="# Installation\n\nPrerequisites: Python 3.8+\n#guide"
)

# Get backlinks
backlinks = get_backlinks(doc2["id"])  # Returns Getting Started doc

# Search documents
results = search_documents("python")
```

## Storage

This server uses in-memory storage. For production, integrate with a file system or database.