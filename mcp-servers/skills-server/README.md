# Skills MCP Server

A FastMCP server that exposes Claude Code skills as MCP resources, making them universally accessible to any AI assistant that supports MCP.

## The Universal Approach

Claude Code uses a "skills" system where skills are defined in `SKILL.md` files with YAML frontmatter. This server bridges that system to MCP, allowing:

- **Any MCP-compatible AI** to load and use skills
- **Dynamic discovery** of available skills
- **Resource-based access** via standard MCP resource URIs
- **No lock-in** - skills become portable across AI systems

## Installation

```bash
pip install fastmcp
```

## Running the Server

```bash
python server.py
```

## Configuration

### Default Skill Directories

The server scans these directories by default:

1. `./skills/` - Local skills directory (relative to server)
2. `~/.claude/skills/` - User's global Claude skills

### Adding Custom Directories

**Via Environment Variable:**
```bash
export SKILLS_PATH="/path/to/skills:/another/path"
python server.py
```

**Via Tool Call:**
```python
add_skill_directory("/path/to/my/skills")
```

## Skill Format

Skills should be in the Claude Code format:

```
my-skill/
├── SKILL.md          # Required: Skill definition
├── scripts/          # Optional: Executable scripts
├── references/       # Optional: Reference documentation
└── assets/           # Optional: Static assets
```

### SKILL.md Format

```markdown
---
name: My Skill
description: What this skill does and when to use it
version: 1.0.0
---

# Skill Instructions

Detailed instructions for the AI to follow when this skill is invoked.

This content becomes the skill's guidance.
```

## Available Tools

### Discovery

| Tool | Description |
|------|-------------|
| `list_skills` | List all available skills with metadata |
| `get_skill` | Get full details of a specific skill |
| `search_skills` | Search skills by name, description, or content |
| `get_skill_count` | Get total count of loaded skills |

### Management

| Tool | Description |
|------|-------------|
| `reload_skills` | Reload all skills from disk |
| `add_skill_directory` | Add a new directory to scan |
| `get_skill_scripts` | List scripts in a skill's scripts/ directory |
| `get_skill_references` | List reference files in a skill's references/ directory |

## Available Resources

### Static Resources

| Resource | Description |
|----------|-------------|
| `skills://index` | Index of all available skills |
| `skills://directories` | Configured skill directories |
| `skills://stats` | Statistics about loaded skills |

### Dynamic Resources

| Resource | Description |
|----------|-------------|
| `skills://{name}` | Full content of a specific skill |

## Example Usage

### List all skills
```python
skills = list_skills()
# Returns: [{"name": "code-review", "description": "...", "version": "1.0.0"}, ...]
```

### Load a skill
```python
skill = get_skill("code-review")
# Returns full skill with content, path, scripts, etc.
```

### Search skills
```python
results = search_skills("review")
# Returns skills matching in name, description, or content
```

### Access as Resource
```
# AI can read: skills://code-review
# Returns full skill content as markdown
```

### Reload after changes
```python
reload_skills()
# Re-scans all directories for new/modified skills
```

## Resource URIs in Action

The AI can load any skill as a resource:

```
skills://code-review      # Load the code-review skill
skills://deploy           # Load the deploy skill
skills://testing          # Load the testing skill
```

This makes skills universally accessible through the standard MCP resource system.

## Use Cases

1. **Portable Skills** - Use the same skills across Claude Code, Claude Desktop, or any MCP client
2. **Skill Libraries** - Share skill collections across teams
3. **Dynamic Loading** - AI discovers and loads relevant skills on demand
4. **Skill Development** - Test and iterate on skills without restarting

## Example Skill Structure

```
skills/
├── code-review/
│   ├── SKILL.md
│   └── references/
│       └── style-guide.md
├── deploy/
│   ├── SKILL.md
│   └── scripts/
│       └── deploy.sh
└── testing/
    └── SKILL.md
```

## Integration with Claude Code

This server is particularly useful when:

1. You want to use Claude Code skills in Claude Desktop
2. You want to share skills between different AI tools
3. You want to build a centralized skill library for your team
4. You want to test skills before adding them to Claude Code

## Storage

Skills are loaded from the filesystem and cached in memory. Call `reload_skills()` to pick up changes without restarting the server.

---

Part of [MCP Servers for Business](https://github.com/hamishfromatech/mcp-servers) by [hamishfromatech](https://youtube.com/@hamishfromatech)