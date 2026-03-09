# Career Manager MCP Server

An all-in-one career management MCP server built with FastMCP. Manage your entire career from resume creation to interview practice, job application tracking, and networking.

## Features

### 🔧 Tools (70+)

**Profile Management**
- `get_profile` - Get current profile
- `update_personal_info` - Update name, email, phone, location, title
- `update_preferences` - Job search status, work type, salary range
- `add_social_link` - Add social/professional platform links
- `get_job_search_status` - Get current job search preferences

**Resume Management**
- `get_resume` / `update_resume_summary` - Manage resume sections
- `add_experience` / `update_experience` / `delete_experience` - Work history
- `add_education` - Education entries
- `add_skill` - Skills with levels
- `add_certification` / `add_project` - Certifications and projects
- `save_resume_version` / `load_resume_version` / `list_resume_versions` - Version control

**Resume Document Generation**
- `generate_resume_files` - Generate PDF, DOCX, and MD files at once
- `generate_resume_pdf` - Generate professionally formatted PDF
- `generate_resume_docx` - Generate Word document
- `generate_resume_md` - Generate Markdown file
- `list_resume_files` / `delete_resume_file` - Manage generated files
- `get_resume_output_directory` - Get output folder path

**Interview Practice**
- `get_interview_questions` - Get practice questions by category
- `add_custom_question` - Add custom questions
- `log_interview_session` - Track real interviews
- `get_interview_history` - Review past interviews
- `analyze_interview_performance` - Get insights
- `add_preparation_material` / `get_preparation_materials` - Company prep
- `generate_interview_prep` - Create prep checklist

**Job Applications**
- `add_application` / `update_application_status` - Track applications
- `add_application_note` / `add_timeline_event` - Notes and timeline
- `get_applications` / `get_application` - Query applications
- `delete_application` - Remove applications
- `get_application_stats` - Pipeline statistics
- `get_upcoming_events` - Calendar view
- `add_application_contact` - Track recruiters/hiring managers

**Skills Inventory**
- `get_skills_inventory` - View all skills
- `add_technical_skill` / `add_soft_skill` - Add skills
- `add_learning_goal` / `update_learning_progress` - Track learning
- `add_target_skill` - Target skills for roles
- `analyze_skill_gaps` - Compare against job requirements
- `get_skills_by_level` - Filter skills
- `generate_skills_section` - Resume export

**Networking**
- `add_contact` / `update_contact` / `delete_contact` - Contact management
- `get_contacts` - Search and filter
- `log_interaction` / `get_interaction_history` - Track conversations
- `add_company_note` / `get_company_info` - Company research
- `get_network_stats` - Network analytics
- `add_tag_to_contact` - Organize contacts

**Career Goals**
- `add_short_term_goal` / `add_long_term_goal` - Set goals
- `update_goal_progress` / `complete_milestone` - Track progress
- `get_active_goals` / `get_achievements` - View goals
- `delete_goal` - Remove goals
- `get_goal_summary` - Overview
- `link_goals` - Connect short/long-term goals

**Cover Letters**
- `create_cover_letter` - Create from template
- `update_cover_letter_section` - Edit sections
- `get_cover_letter` / `list_cover_letters` - View letters
- `generate_cover_letter_text` - Export as text
- `finalize_cover_letter` / `delete_cover_letter` - Manage
- `get_cover_letter_tips` - Best practices

### 🔍 Tool Discovery (FastMCP 3.1.0+)

Career Manager uses **BM25 Search Transform** to efficiently handle 70+ tools. Instead of loading all tools into context, the LLM uses:

```
search_tools("resume experience") → Returns: add_experience, update_experience, generate_resume_pdf, ...
call_tool("add_experience", {"company": "Google"}) → Executes the tool
```

**Always visible:**
- `get_career_overview()` - Quick status snapshot
- `search_career_data(query)` - Search across all your data

### 📚 Resources

Access your career data directly:
- `career://profile` - User profile
- `career://resume` - Resume data
- `career://applications` - Job applications
- `career://interviews` - Interview data
- `career://skills` - Skills inventory
- `career://goals` - Career goals
- `career://network` - Network contacts
- `career://stats` - Overview statistics

Dynamic resources:
- `career://application/{id}` - Specific application
- `career://contact/{id}` - Specific contact
- `career://company/{name}` - Company info

### 📝 Prompts

Pre-built prompts for common tasks:
- `resume_review_prompt` - Review and improve resume
- `interview_prep_prompt` - Prepare for interviews
- `job_search_strategy_prompt` - Develop job search strategy
- `cover_letter_prompt` - Write cover letters
- `career_development_prompt` - Career planning
- `salary_negotiation_prompt` - Prepare for negotiations

## Installation

```bash
# Clone or download the repository
cd career-manager

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

### Optional: Document Generation

To generate PDF and DOCX resume files, install the optional dependencies:

```bash
# For PDF generation
pip install reportlab

# For DOCX (Word) generation
pip install python-docx

# Or install both at once
pip install -e ".[docs]"
```

> **Note:** Markdown generation works out of the box with no extra dependencies.

## Usage

### As MCP Server (stdio) - Default

```bash
career-manager
# or
python -m career_manager.server
```

### As HTTP Server

```bash
career-manager --transport http --port 8000
```

### As SSE Server

```bash
career-manager --transport sse --port 8000
```

### Web UI

```bash
career-manager-webui
# Opens browser at http://localhost:8080
```

### Disable Tool Search

To show all tools instead of using search transform:

```bash
career-manager --no-search
```

## Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "career-manager": {
      "command": "uv",
      "args": ["run", "career-manager"],
      "cwd": "/path/to/career-manager"
    }
  }
}
```

Or with Python directly:

```json
{
  "mcpServers": {
    "career-manager": {
      "command": "python",
      "args": ["-m", "career_manager.server"],
      "cwd": "/path/to/career-manager"
    }
  }
}
```

## Data Storage

All data is stored locally in JSON format at `~/.career-manager/`:

```
~/.career-manager/
├── profile.json        # Personal info, preferences
├── resume.json         # Resume data, versions
├── applications.json   # Job applications, cover letters
├── interviews.json     # Interview sessions, prep
├── skills.json         # Skills inventory
├── goals.json          # Career goals, achievements
├── network.json        # Contacts, interactions
└── output/             # Generated resume files
    ├── resume_*.pdf
    ├── resume_*.docx
    └── resume_*.md
```

## Example Workflows

### Starting Fresh

```python
# 1. Set up your profile
update_personal_info(
    name="John Doe",
    email="john@example.com",
    title="Software Engineer"
)

# 2. Add your experience
add_experience(
    company="Tech Corp",
    title="Senior Engineer",
    start_date="2020-01",
    end_date="Present",
    achievements=["Built microservices", "Led team of 5"]
)

# 3. Track a job application
add_application(
    company="Dream Company",
    position="Staff Engineer",
    url="https://jobs.dreamcompany.com/123",
    status="applied"
)

# 4. Generate resume files
generate_resume_files(formats=["pdf", "docx", "md"])
```

### Interview Preparation

```python
# 1. Generate prep materials
generate_interview_prep(company="Dream Company", position="Staff Engineer")

# 2. Get practice questions
questions = get_interview_questions(category="behavioral", count=5)

# 3. After the interview, log it
log_interview_session(
    company="Dream Company",
    position="Staff Engineer",
    date="2024-01-15",
    round_type="technical",
    questions_asked=["Tell me about...", "How do you..."],
    went_well=["System design"],
    needs_improvement=["Behavioral examples"]
)

# 4. Analyze your performance
analyze_interview_performance()
```

### Skill Gap Analysis

```python
# Add your skills
add_technical_skill(skill="Python", level="expert", years=8)
add_technical_skill(skill="Kubernetes", level="intermediate", years=2)
add_soft_skill(skill="Leadership", level="proficient")

# Analyze gaps for a target role
analyze_skill_gaps(required_skills=[
    "Python", "Kubernetes", "AWS", "System Design", "Leadership"
])
# Returns: matched skills, gaps, recommendations
```

## Project Structure

```
career-manager/
├── pyproject.toml          # Package config
├── README.md               # This file
├── system-prompt.md        # LLM system prompt
└── src/
    └── career_manager/
        ├── __init__.py     # Package exports
        ├── server.py       # MCP server + prompts
        ├── storage.py      # Data layer
        ├── documents.py    # Document generation
        ├── webui.py        # Web interface
        ├── tools/
        │   ├── __init__.py
        │   ├── profile.py      # Profile tools
        │   ├── resume.py       # Resume tools
        │   ├── interview.py    # Interview tools
        │   ├── applications.py # Job tracking
        │   ├── skills.py       # Skills tools
        │   ├── network.py      # Networking tools
        │   ├── goals.py        # Goals tools
        │   └── cover_letter.py # Cover letters
        └── resources/
            └── __init__.py     # MCP resources
```

## License

MIT License - feel free to use and modify for your needs!