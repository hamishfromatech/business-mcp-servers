"""
Skills MCP Server
A FastMCP server that exposes Claude Code skills as MCP resources.
Skills are loaded from configured directories and can be queried/listed by AI assistants.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import json
import re
from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP(
    name="Skills Server",
    instructions="A server that exposes Claude Code skills as MCP resources. Skills are loaded from configured directories and can be discovered, listed, and loaded dynamically."
)

# Configuration - skill directories to scan
# Users can add their own directories here or via environment variable
SKILL_DIRS = [
    Path(__file__).parent / "skills",  # Local skills directory
    Path.home() / ".claude" / "skills",  # User's global skills
]

# Try to load additional paths from environment
import os
if os.environ.get("SKILLS_PATH"):
    for p in os.environ.get("SKILLS_PATH", "").split(os.pathsep):
        SKILL_DIRS.append(Path(p))


class Skill(BaseModel):
    """Represents a Claude Code skill."""
    name: str
    description: str
    version: str
    path: str
    content: str
    has_scripts: bool
    has_references: bool
    has_assets: bool
    loaded_at: str


# In-memory storage for loaded skills
skills: dict[str, Skill] = {}


def parse_skill_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from SKILL.md content.

    Args:
        content: Raw SKILL.md content

    Returns:
        Dictionary with frontmatter fields and body content
    """
    frontmatter = {
        "name": "",
        "description": "",
        "version": "1.0.0",
    }

    # Match frontmatter between --- markers
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if match:
        fm_text = match.group(1)
        body = match.group(2)

        # Parse simple YAML key: value pairs
        for line in fm_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                frontmatter[key] = value

        frontmatter["_body"] = body
    else:
        frontmatter["_body"] = content

    return frontmatter


def discover_skills() -> dict[str, Skill]:
    """Discover all skills from configured directories.

    Returns:
        Dictionary of skill name -> Skill object
    """
    discovered = {}

    for skill_dir in SKILL_DIRS:
        if not skill_dir.exists():
            continue

        for skill_path in skill_dir.iterdir():
            if not skill_path.is_dir():
                continue

            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                content = skill_md.read_text(encoding="utf-8")
                parsed = parse_skill_frontmatter(content)

                # Use directory name as skill name if not in frontmatter
                skill_name = parsed.get("name") or skill_path.name
                skill_name = skill_name.lower().replace(" ", "-")

                # Check for supporting directories
                has_scripts = (skill_path / "scripts").exists()
                has_references = (skill_path / "references").exists()
                has_assets = (skill_path / "assets").exists()

                discovered[skill_name] = Skill(
                    name=skill_name,
                    description=parsed.get("description", ""),
                    version=parsed.get("version", "1.0.0"),
                    path=str(skill_path),
                    content=parsed.get("_body", content),
                    has_scripts=has_scripts,
                    has_references=has_references,
                    has_assets=has_assets,
                    loaded_at=datetime.now().isoformat()
                )
            except Exception as e:
                print(f"Error loading skill from {skill_path}: {e}")

    return discovered


def _reload_skills() -> None:
    """Reload skills from disk."""
    global skills
    skills = discover_skills()


# Initialize skills on startup
skills = discover_skills()


# === TOOLS ===

@mcp.tool
def list_skills(
    category: Optional[str] = None,
    has_scripts: Optional[bool] = None
) -> list[Skill]:
    """List all available skills.

    Args:
        category: Filter by category (optional, for future use)
        has_scripts: Filter to skills with/without scripts

    Returns:
        List of skill metadata
    """
    result = []
    for skill in skills.values():
        if has_scripts is not None and skill.has_scripts != has_scripts:
            continue
        result.append(skill)
    return result


@mcp.tool
def get_skill(name: str) -> Optional[Skill]:
    """Get full details of a specific skill.

    Args:
        name: The skill name (case-insensitive)

    Returns:
        Full skill details including content, or None if not found
    """
    name_lower = name.lower().replace(" ", "-")
    skill = skills.get(name_lower)
    if skill:
        return skill
    return None


@mcp.tool
def search_skills(query: str) -> list[Skill]:
    """Search skills by name or description.

    Args:
        query: Search term to match against skill name and description

    Returns:
        List of matching skills
    """
    query_lower = query.lower()
    results = []

    for skill in skills.values():
        if (
            query_lower in skill.name.lower() or
            query_lower in skill.description.lower() or
            query_lower in skill.content.lower()
        ):
            results.append(skill)

    return results


@mcp.tool
def reload_skills() -> dict:
    """Reload all skills from disk.

    Use this after adding/modifying skill files.

    Returns:
        Summary of loaded skills
    """
    _reload_skills()
    return {
        "total_skills": len(skills),
        "skill_names": list(skills.keys()),
        "loaded_at": datetime.now().isoformat()
    }


@mcp.tool
def get_skill_scripts(name: str) -> Optional[list[dict]]:
    """List scripts available in a skill's scripts directory.

    Args:
        name: The skill name

    Returns:
        List of script files with their paths, or None if skill not found
    """
    name_lower = name.lower().replace(" ", "-")
    skill = skills.get(name_lower)

    if not skill:
        return None

    skill_path = Path(skill.path)
    scripts_dir = skill_path / "scripts"

    if not scripts_dir.exists():
        return []

    scripts = []
    for script_file in scripts_dir.iterdir():
        if script_file.is_file():
            scripts.append({
                "name": script_file.name,
                "path": str(script_file),
                "extension": script_file.suffix,
            })

    return scripts


@mcp.tool
def get_skill_references(name: str) -> Optional[list[dict]]:
    """List reference files available in a skill's references directory.

    Args:
        name: The skill name

    Returns:
        List of reference files, or None if skill not found
    """
    name_lower = name.lower().replace(" ", "-")
    skill = skills.get(name_lower)

    if not skill:
        return None

    skill_path = Path(skill.path)
    refs_dir = skill_path / "references"

    if not refs_dir.exists():
        return []

    refs = []
    for ref_file in refs_dir.iterdir():
        if ref_file.is_file():
            refs.append({
                "name": ref_file.name,
                "path": str(ref_file),
                "extension": ref_file.suffix,
            })

    return refs


@mcp.tool
def add_skill_directory(path: str) -> dict:
    """Add a new directory to scan for skills.

    Args:
        path: Absolute path to the directory containing skills

    Returns:
        Result of the operation
    """
    new_dir = Path(path)

    if not new_dir.exists():
        return {"success": False, "error": "Directory does not exist"}

    if not new_dir.is_dir():
        return {"success": False, "error": "Path is not a directory"}

    if new_dir not in SKILL_DIRS:
        SKILL_DIRS.append(new_dir)

    # Reload to pick up new skills
    _reload_skills()

    return {
        "success": True,
        "path": str(new_dir),
        "total_skills": len(skills)
    }


@mcp.tool
def get_skill_count() -> dict:
    """Get the total number of loaded skills.

    Returns:
        Count of skills and skill directories
    """
    return {
        "total_skills": len(skills),
        "skill_directories": [str(d) for d in SKILL_DIRS if d.exists()],
        "skill_names": list(skills.keys())
    }


# === RESOURCES ===

@mcp.resource("skills://index")
def get_skills_index() -> str:
    """Resource providing an index of all available skills."""
    if not skills:
        return "# Skills Index\n\nNo skills loaded."

    lines = ["# Skills Index\n"]
    lines.append(f"**Total Skills:** {len(skills)}\n")

    for skill in sorted(skills.values(), key=lambda s: s.name):
        lines.append(f"## {skill.name}")
        lines.append(f"- **Description:** {skill.description}")
        lines.append(f"- **Version:** {skill.version}")
        if skill.has_scripts:
            lines.append("- Has scripts: Yes")
        if skill.has_references:
            lines.append("- Has references: Yes")
        lines.append("")

    return "\n".join(lines)


@mcp.resource("skills://{name}")
def get_skill_resource(name: str) -> str:
    """Resource providing full skill content.

    Load any skill by name using: skills://skill-name
    """
    name_lower = name.lower().replace(" ", "-")
    skill = skills.get(name_lower)

    if not skill:
        return f"# Skill Not Found\n\nSkill '{name}' was not found.\n\nAvailable skills: {', '.join(skills.keys())}"

    lines = [
        f"# {skill.name}",
        "",
        f"**Description:** {skill.description}",
        f"**Version:** {skill.version}",
        f"**Path:** {skill.path}",
        "",
        "---",
        "",
        "# Skill Instructions",
        "",
        skill.content,
    ]

    if skill.has_scripts:
        lines.append("\n---\n\n**Note:** This skill has accompanying scripts.")

    if skill.has_references:
        lines.append("\n**Note:** This skill has reference documentation.")

    return "\n".join(lines)


@mcp.resource("skills://directories")
def get_skill_directories() -> str:
    """Resource showing all configured skill directories."""
    lines = ["# Skill Directories\n"]

    for i, dir_path in enumerate(SKILL_DIRS, 1):
        exists = dir_path.exists()
        status = "Active" if exists else "Not Found"
        lines.append(f"{i}. `{dir_path}` - {status}")

    return "\n".join(lines)


@mcp.resource("skills://stats")
def get_skills_stats() -> str:
    """Resource showing skill statistics."""
    total = len(skills)
    with_scripts = sum(1 for s in skills.values() if s.has_scripts)
    with_refs = sum(1 for s in skills.values() if s.has_references)
    with_assets = sum(1 for s in skills.values() if s.has_assets)

    lines = [
        "# Skills Statistics\n",
        f"- **Total Skills:** {total}",
        f"- **Skills with Scripts:** {with_scripts}",
        f"- **Skills with References:** {with_refs}",
        f"- **Skills with Assets:** {with_assets}",
        f"- **Configured Directories:** {len(SKILL_DIRS)}",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()