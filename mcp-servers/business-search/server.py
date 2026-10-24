"""
Business Search MCP Server
A FastMCP server that indexes the JSON data files of every other MCP server in
this repository and exposes cross-server search.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import os
import threading
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Business Search",
    instructions=(
        "A cross-server search hub. Indexes the JSON data files of the other "
        "business MCP servers (CRM, invoices, tickets, notes, OKRs, ...) and "
        "answers one query across all of them."
    ),
)


class SearchHit(BaseModel):
    """A single search result."""
    source: str
    entity_type: str
    record_id: int
    score: int
    matched_terms: int
    snippet: str
    record: dict


class DataSource(BaseModel):
    """An indexed data file."""
    source: str
    path: str
    records: int
    modified_at: str


# Root directories to scan. Defaults to the mcp-servers directory that contains
# this server. Override with MCP_DATA_ROOTS (os.pathsep separated) for tests or
# custom deployments.
def _data_roots() -> list[Path]:
    env = os.environ.get("MCP_DATA_ROOTS")
    if env:
        return [Path(p).expanduser() for p in env.split(os.pathsep) if p.strip()]
    return [Path(__file__).resolve().parent.parent]


_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()


# --- scanning ----------------------------------------------------------------
def _iter_data_files() -> list[Path]:
    """Find JSON data files belonging to sibling servers."""
    files: list[Path] = []
    seen: set[str] = set()
    for root in _data_roots():
        if not root.exists():
            continue
        patterns = ("*/data/*.json", "*/kanban_data.json", "*_data.json")
        for pattern in patterns:
            for path in root.glob(pattern):
                if any(part in {".venv", "node_modules", "__pycache__"} for part in path.parts):
                    continue
                resolved = str(path.resolve())
                if resolved not in seen:
                    seen.add(resolved)
                    files.append(path)
    return sorted(files)


def _source_name(path: Path) -> str:
    """Best-effort server name for a data file."""
    parts = path.parts
    if "data" in parts:
        index = len(parts) - 1 - list(reversed(parts)).index("data")
        if index > 0:
            return parts[index - 1]
    if path.name == "kanban_data.json":
        return path.parent.name
    return path.stem.replace("_data", "") or path.stem


def _collect_nested(record: dict, prefix: str, out: list[tuple[str, dict]]) -> None:
    """Collect nested records such as a board's tasks."""
    for key, value in record.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "id" in item:
                    out.append((f"{prefix}.{key}", item))
        elif isinstance(value, dict) and "id" in value:
            out.append((f"{prefix}.{key}", value))


def _collect_records(obj, prefix: str, out: list[tuple[str, dict]]) -> None:
    """Recursively extract records (dicts with an 'id') from a document."""
    if isinstance(obj, dict):
        child_dicts = {k: v for k, v in obj.items() if isinstance(v, dict)}
        if child_dicts and all("id" in v for v in child_dicts.values()):
            for value in child_dicts.values():
                out.append((prefix or "records", value))
                _collect_nested(value, prefix or "records", out)
            return
        if "id" in obj:
            out.append((prefix or "records", obj))
            _collect_nested(obj, prefix or "records", out)
            return
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                _collect_records(value, f"{prefix}.{key}" if prefix else key, out)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict) and "id" in item:
                out.append((prefix or "records", item))
            elif isinstance(item, (dict, list)):
                _collect_records(item, prefix, out)


def _record_text(record: dict) -> str:
    """Flatten a record into a lower-case searchable string.

    Nested record collections (a board's tasks, an invoice's comments) are
    indexed as their own records, so they are deliberately not folded into the
    parent's text to avoid duplicate hits.
    """
    parts: list[str] = []

    def is_nested_record(value) -> bool:
        return isinstance(value, dict) and "id" in value

    def is_nested_collection(value) -> bool:
        return (isinstance(value, list) and bool(value)
                and all(isinstance(item, dict) and "id" in item for item in value))

    def walk(value) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                parts.append(key)
                if is_nested_record(item) or is_nested_collection(item):
                    continue
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif value is not None:
            parts.append(str(value))

    walk(record)
    return " ".join(parts).lower()


def _index_file(path: Path) -> dict:
    """Parse a data file into indexed records."""
    stat = path.stat()
    source = _source_name(path)
    records: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {"mtime": stat.st_mtime, "size": stat.st_size, "source": source,
                "records": [], "error": "unreadable"}
    collected: list[tuple[str, dict]] = []
    _collect_records(document, "", collected)
    for entity_type, record in collected:
        if "id" not in record:
            continue
        records.append({
            "entity_type": entity_type,
            "id": record["id"],
            "record": record,
            "text": _record_text(record),
        })
    return {
        "mtime": stat.st_mtime, "size": stat.st_size, "source": source,
        "records": records,
    }


def _refresh_index(force: bool = False) -> None:
    """Incrementally refresh the index, re-parsing only changed files."""
    with _cache_lock:
        paths = _iter_data_files()
        live = {str(p.resolve()) for p in paths}
        for stale in set(_cache) - live:
            del _cache[stale]
        for path in paths:
            key = str(path.resolve())
            cached = _cache.get(key)
            try:
                stat = path.stat()
            except OSError:
                continue
            if (force or cached is None
                    or cached["mtime"] != stat.st_mtime
                    or cached["size"] != stat.st_size):
                _cache[key] = {**_index_file(path), "path": key}


# --- tools -------------------------------------------------------------------
@mcp.tool
def search_business(query: str, entity_type: Optional[str] = None,
                    source: Optional[str] = None, limit: int = 20) -> list[SearchHit]:
    """Search across every indexed business server.

    Args:
        query: Free-text terms, e.g. "acme overdue invoice"
        entity_type: Optional filter, e.g. "leads", "invoices", "tickets"
        source: Optional server filter, e.g. "crm", "invoice-manager"
        limit: Maximum results (default 20)
    """
    _refresh_index()
    terms = [t for t in query.lower().split() if t]
    if not terms:
        return []
    hits: list[dict] = []
    for meta in _cache.values():
        if source is not None and meta["source"] != source:
            continue
        for item in meta["records"]:
            if entity_type is not None and item["entity_type"] != entity_type:
                continue
            text = item["text"]
            matched = sum(1 for t in terms if t in text)
            if matched == 0:
                continue
            score = sum(text.count(t) for t in terms)
            snippet = text[:240]
            hits.append({
                "source": meta["source"], "entity_type": item["entity_type"],
                "record_id": item["id"], "score": score, "matched_terms": matched,
                "snippet": snippet, "record": item["record"],
            })
    hits.sort(key=lambda h: (h["matched_terms"], h["score"]), reverse=True)
    return [SearchHit(**hit) for hit in hits[:max(1, limit)]]


@mcp.tool
def list_data_sources() -> list[DataSource]:
    """List every indexed data file with its record count."""
    _refresh_index()
    result = []
    for meta in _cache.values():
        result.append(DataSource(
            source=meta["source"], path=meta["path"],
            records=len(meta["records"]),
            modified_at=datetime.fromtimestamp(meta["mtime"]).isoformat(),
        ))
    result.sort(key=lambda d: (d.source, d.path))
    return result


@mcp.tool
def get_index_stats() -> dict:
    """Totals across the whole index."""
    _refresh_index()
    by_source: dict[str, int] = {}
    by_entity: dict[str, int] = {}
    for meta in _cache.values():
        by_source[meta["source"]] = by_source.get(meta["source"], 0) + len(meta["records"])
        for item in meta["records"]:
            by_entity[item["entity_type"]] = by_entity.get(item["entity_type"], 0) + 1
    return {
        "sources": len(_cache),
        "records": sum(len(m["records"]) for m in _cache.values()),
        "by_source": by_source,
        "by_entity_type": by_entity,
        "roots": [str(r) for r in _data_roots()],
    }


@mcp.tool
def rebuild_index() -> dict:
    """Force a full re-index of all data files."""
    _refresh_index(force=True)
    return get_index_stats()


@mcp.tool
def get_record(source: str, entity_type: str, record_id: int) -> Optional[dict]:
    """Fetch a single record by its source, entity type, and id."""
    _refresh_index()
    for meta in _cache.values():
        if meta["source"] != source:
            continue
        for item in meta["records"]:
            if item["entity_type"] == entity_type and int(item["id"]) == record_id:
                return item["record"]
    return None


# --- resources ---------------------------------------------------------------
@mcp.resource("business://sources")
def get_sources_resource() -> str:
    """Indexed data sources as formatted text."""
    sources = list_data_sources()
    if not sources:
        return "# Business Data Sources\n\nNo data files found yet."
    lines = [f"# Business Data Sources ({len(sources)})\n"]
    for item in sources:
        lines.append(f"- **{item.source}** - {item.records} records ({item.path})")
    return "\n".join(lines)


@mcp.resource("business://stats")
def get_stats_resource() -> str:
    """Index statistics as formatted text."""
    stats = get_index_stats()
    lines = [
        "# Business Search Index\n",
        f"- **Sources:** {stats['sources']}",
        f"- **Records:** {stats['records']}",
        "\n## Records by source\n",
    ]
    for source, count in sorted(stats["by_source"].items()):
        lines.append(f"- {source}: {count}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
