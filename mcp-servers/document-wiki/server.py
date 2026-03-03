"""
Document Wiki MCP Server
A FastMCP server for managing wiki documents and a knowledge base.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import re
from fastmcp import FastMCP

mcp = FastMCP(
    name="Document Wiki",
    instructions="A wiki server for creating, organizing, and linking knowledge base documents."
)

# Data persistence setup
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "wiki.json"


def _load_data() -> dict:
    """Load data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"documents": {}, "categories": {}, "next_doc_id": 1, "next_cat_id": 1}


def _save_data(data: dict) -> None:
    """Save data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Initialize data
_data = _load_data()
documents: dict[int, dict] = {int(k): v for k, v in _data.get("documents", {}).items()}
categories: dict[int, dict] = {int(k): v for k, v in _data.get("categories", {}).items()}
_next_doc_id = _data.get("next_doc_id", 1)
_next_cat_id = _data.get("next_cat_id", 1)


def _save() -> None:
    """Save current state to disk."""
    _save_data({
        "documents": documents, "categories": categories,
        "next_doc_id": _next_doc_id, "next_cat_id": _next_cat_id
    })


def _get_next_doc_id() -> int:
    global _next_doc_id
    id_ = _next_doc_id
    _next_doc_id += 1
    return id_


def _get_next_cat_id() -> int:
    global _next_cat_id
    id_ = _next_cat_id
    _next_cat_id += 1
    return id_


def _extract_wikilinks(content: str) -> list[str]:
    """Extract [[wiki links]] from content."""
    return re.findall(r'\[\[([^\]]+)\]\]', content)


# Category Management
@mcp.tool
def create_category(name: str, description: Optional[str] = None) -> dict:
    """Create a new category for organizing documents.

    Args:
        name: Category name
        description: Category description

    Returns:
        The created category
    """
    category_id = _get_next_cat_id()
    category = {
        "id": category_id,
        "name": name,
        "description": description,
        "created_at": datetime.now().isoformat()
    }
    categories[category_id] = category
    _save()
    return category


@mcp.tool
def list_categories() -> list[dict]:
    """List all categories.

    Returns:
        List of all categories
    """
    return list(categories.values())


# Document Management
@mcp.tool
def create_document(
    title: str,
    content: str,
    category_id: Optional[int] = None,
    tags: Optional[list[str]] = None
) -> dict:
    """Create a new wiki document.

    Args:
        title: Document title
        content: Document content (supports markdown and [[wiki links]])
        category_id: Optional category ID
        tags: Optional list of tags

    Returns:
        The created document
    """
    doc_id = _get_next_doc_id()
    doc = {
        "id": doc_id,
        "title": title,
        "content": content,
        "category_id": category_id,
        "tags": tags or [],
        "links_to": _extract_wikilinks(content),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    documents[doc_id] = doc
    _save()
    return doc


@mcp.tool
def get_document(document_id: int) -> Optional[dict]:
    """Get a document by ID.

    Args:
        document_id: The document ID

    Returns:
        Document details or None
    """
    return documents.get(document_id)


@mcp.tool
def get_document_by_title(title: str) -> Optional[dict]:
    """Get a document by its title.

    Args:
        title: The document title (exact match)

    Returns:
        Document details or None
    """
    for doc in documents.values():
        if doc["title"].lower() == title.lower():
            return doc
    return None


@mcp.tool
def update_document(
    document_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category_id: Optional[int] = None,
    tags: Optional[list[str]] = None
) -> Optional[dict]:
    """Update an existing document.

    Args:
        document_id: The document ID
        title: New title
        content: New content
        category_id: New category ID
        tags: New tags

    Returns:
        Updated document or None
    """
    if document_id not in documents:
        return None

    doc = documents[document_id]
    if title is not None:
        doc["title"] = title
    if content is not None:
        doc["content"] = content
        doc["links_to"] = _extract_wikilinks(content)
    if category_id is not None:
        doc["category_id"] = category_id
    if tags is not None:
        doc["tags"] = tags
    doc["updated_at"] = datetime.now().isoformat()
    _save()

    return doc


@mcp.tool
def delete_document(document_id: int) -> bool:
    """Delete a document.

    Args:
        document_id: The document ID

    Returns:
        True if deleted, False if not found
    """
    if document_id in documents:
        del documents[document_id]
        _save()
        return True
    return False


@mcp.tool
def search_documents(query: str) -> list[dict]:
    """Search documents by title, content, or tags.

    Args:
        query: Search term

    Returns:
        List of matching documents
    """
    query_lower = query.lower()
    results = []

    for doc in documents.values():
        if (
            query_lower in doc["title"].lower() or
            query_lower in doc["content"].lower() or
            any(query_lower in tag.lower() for tag in doc.get("tags", []))
        ):
            results.append(doc)

    return results


@mcp.tool
def get_documents_by_category(category_id: int) -> list[dict]:
    """Get all documents in a category.

    Args:
        category_id: The category ID

    Returns:
        List of documents in the category
    """
    return [
        doc for doc in documents.values()
        if doc.get("category_id") == category_id
    ]


@mcp.tool
def get_documents_by_tag(tag: str) -> list[dict]:
    """Get all documents with a specific tag.

    Args:
        tag: The tag to search for

    Returns:
        List of documents with the tag
    """
    tag_lower = tag.lower()
    return [
        doc for doc in documents.values()
        if any(t.lower() == tag_lower for t in doc.get("tags", []))
    ]


@mcp.tool
def get_linked_documents(document_id: int) -> list[dict]:
    """Get documents that this document links to (via [[wiki links]]).

    Args:
        document_id: The source document ID

    Returns:
        List of linked documents
    """
    if document_id not in documents:
        return []

    doc = documents[document_id]
    linked = []

    for link_title in doc.get("links_to", []):
        linked_doc = get_document_by_title(link_title)
        if linked_doc:
            linked.append(linked_doc)

    return linked


@mcp.tool
def get_backlinks(document_id: int) -> list[dict]:
    """Get documents that link to this document.

    Args:
        document_id: The target document ID

    Returns:
        List of documents with backlinks
    """
    if document_id not in documents:
        return []

    doc = documents[document_id]
    title = doc["title"].lower()
    backlinks = []

    for other_doc in documents.values():
        if other_doc["id"] == document_id:
            continue
        if any(title == link.lower() for link in other_doc.get("links_to", [])):
            backlinks.append(other_doc)

    return backlinks


@mcp.tool
def get_all_tags() -> list[str]:
    """Get all unique tags used across documents.

    Returns:
        List of unique tags
    """
    tags = set()
    for doc in documents.values():
        tags.update(doc.get("tags", []))
    return sorted(list(tags))


# Resources
@mcp.resource("wiki://index")
def get_wiki_index() -> str:
    """Resource showing the wiki index with all documents."""
    if not documents:
        return "# Wiki Index\n\nNo documents yet."

    lines = ["# Wiki Index\n"]

    # Group by category
    cats = {c["id"]: c for c in categories.values()}
    by_category: dict[int | None, list[dict]] = {}

    for doc in sorted(documents.values(), key=lambda d: d["title"]):
        cat_id = doc.get("category_id")
        if cat_id not in by_category:
            by_category[cat_id] = []
        by_category[cat_id].append(doc)

    for cat_id, docs in by_category.items():
        if cat_id is None:
            lines.append("## Uncategorized")
        else:
            cat_name = cats.get(cat_id, {}).get("name", "Unknown")
            lines.append(f"## {cat_name}")

        for doc in docs:
            lines.append(f"- [[{doc['title']}]] (ID: {doc['id']})")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("wiki://recent")
def get_recent_documents() -> str:
    """Resource showing recently updated documents."""
    if not documents:
        return "# Recent Documents\n\nNo documents yet."

    lines = ["# Recently Updated Documents\n"]

    recent = sorted(
        documents.values(),
        key=lambda d: d.get("updated_at", ""),
        reverse=True
    )[:10]

    for doc in recent:
        lines.append(f"- [[{doc['title']}]] - Updated: {doc['updated_at'][:10]}")

    return "\n".join(lines)


@mcp.resource("wiki://tags")
def get_tags_resource() -> str:
    """Resource showing all tags and document counts."""
    tags = get_all_tags()
    if not tags:
        return "# Tags\n\nNo tags yet."

    lines = ["# Tags\n"]

    for tag in tags:
        count = len(get_documents_by_tag(tag))
        lines.append(f"- **{tag}** ({count} documents)")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()