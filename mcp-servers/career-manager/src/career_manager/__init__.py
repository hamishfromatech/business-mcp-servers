"""
Career Manager - All-in-one career management MCP server.
"""

__version__ = "0.1.0"

from .server import main, mcp
from .storage import (
    load_data,
    save_data,
    update_data,
    get_stats,
    ensure_data_dir,
)

__all__ = [
    "main",
    "mcp",
    "load_data",
    "save_data",
    "update_data",
    "get_stats",
    "ensure_data_dir",
]