"""
Career Manager MCP Server - All-in-one career management.
"""

import argparse
from fastmcp import FastMCP

from .tools import (
    register_profile_tools,
    register_resume_tools,
    register_interview_tools,
    register_application_tools,
    register_skills_tools,
    register_network_tools,
    register_goals_tools,
    register_cover_letter_tools,
)
from .resources import register_resources
from .storage import ensure_data_dir, get_stats, load_data

# Try to import search transform (requires FastMCP 3.1.0+)
_SEARCH_TRANSFORM_AVAILABLE = False
try:
    from fastmcp.server.transforms.search import BM25SearchTransform
    _SEARCH_TRANSFORM_AVAILABLE = True
except ImportError:
    pass


def create_server(use_search: bool = True) -> FastMCP:
    """Create the MCP server, optionally with search transform."""

    if use_search and _SEARCH_TRANSFORM_AVAILABLE:
        # Use search transform to handle 70+ tools efficiently
        # This replaces the full tool catalog with search_tools + call_tool
        # The LLM discovers tools on-demand instead of receiving all tools upfront
        server = FastMCP(
            name="Career Manager",
            instructions="""
    Career Manager is a comprehensive career management system with 70+ tools.

    DISCOVER TOOLS: Use search_tools(query) to find relevant tools by keyword.
    Example queries: "resume", "interview", "application", "skill", "goal"

    CORE TOOLS (always visible):
    - get_career_overview: Quick status of your career management
    - search_career_data: Search across all your data

    RESOURCES: Access your data directly via career:// URIs:
    - career://profile - Your profile and preferences
    - career://resume - Resume data and versions
    - career://applications - Job applications pipeline
    - career://interviews - Interview history and prep
    - career://skills - Skills inventory
    - career://goals - Career goals tracking
    - career://network - Professional contacts
    - career://stats - Quick statistics

    All data is stored locally in ~/.career-manager/
    """,
            transforms=[
                BM25SearchTransform(
                    max_results=10,  # Return top 10 most relevant tools
                    always_visible=[
                        "get_career_overview",
                        "search_career_data",
                    ],
                )
            ],
        )
    else:
        # Fallback: show all tools
        server = FastMCP(
            name="Career Manager",
            instructions="""
    Career Manager is a comprehensive career management system. Use it to:

    - Manage your profile and job search preferences
    - Create and manage resumes with multiple versions
    - Track job applications and their status
    - Practice for interviews with question banks and session logging
    - Manage your skills inventory and identify gaps
    - Build and maintain your professional network
    - Set and track career goals
    - Generate cover letters

    RESOURCES: Access your data directly via career:// URIs:
    - career://profile, career://resume, career://applications
    - career://interviews, career://skills, career://goals
    - career://network, career://stats

    All data is stored locally in ~/.career-manager/
    """,
        )

    return server


# Create the MCP server
mcp = create_server(use_search=True)


# Register all tools
register_profile_tools(mcp)
register_resume_tools(mcp)
register_interview_tools(mcp)
register_application_tools(mcp)
register_skills_tools(mcp)
register_network_tools(mcp)
register_goals_tools(mcp)
register_cover_letter_tools(mcp)

# Register resources
register_resources(mcp)


# Add prompts for common career tasks
@mcp.prompt
def resume_review_prompt() -> str:
    """Prompt for reviewing and improving a resume."""
    return """Please review my resume and provide suggestions for improvement.

Consider:
1. Overall structure and readability
2. Impact of bullet points (use action verbs, quantify results)
3. Skills representation
4. ATS optimization
5. Areas that could be strengthened

Use the career://resume resource to access my current resume data."""


@mcp.prompt
def interview_prep_prompt(
    company: str,
    position: str,
) -> str:
    """Prompt for interview preparation.

    Args:
        company: Company you're interviewing with
        position: Position you're applying for
    """
    return f"""Help me prepare for an interview at {company} for the {position} position.

Please:
1. Generate relevant interview questions based on my resume
2. Provide tips for answering common questions
3. Help me prepare questions to ask the interviewer
4. Identify key experiences from my resume to highlight
5. Research the company and role

Use career://profile and career://resume resources to access my information.
Use career://interviews to see any previous interview history."""


@mcp.prompt
def job_search_strategy_prompt() -> str:
    """Prompt for developing a job search strategy."""
    return """Help me develop a comprehensive job search strategy.

Based on my profile, skills, and goals:
1. Identify target roles and companies
2. Suggest job search channels and strategies
3. Help prioritize applications
4. Review networking opportunities
5. Track progress and optimize approach

Use career://profile, career://skills, career://goals, and career://applications
resources to understand my current situation."""


@mcp.prompt
def cover_letter_prompt(
    company: str,
    position: str,
) -> str:
    """Prompt for writing a cover letter.

    Args:
        company: Company you're applying to
        position: Position you're applying for
    """
    return f"""Help me write a compelling cover letter for {position} at {company}.

Please:
1. Review my relevant experience for this role
2. Identify key accomplishments to highlight
3. Research the company to personalize the letter
4. Create a compelling opening and closing
5. Ensure it's tailored and not generic

Use career://profile and career://resume resources to access my information."""


@mcp.prompt
def career_development_prompt() -> str:
    """Prompt for career development planning."""
    return """Help me plan my career development.

Based on my current skills, goals, and industry trends:
1. Identify skill gaps to address
2. Suggest learning resources and certifications
3. Recommend networking opportunities
4. Help set realistic career milestones
5. Create an action plan

Use career://skills, career://goals, and career://network resources
to understand my current situation."""


@mcp.prompt
def salary_negotiation_prompt(
    company: str,
    position: str,
    offer_amount: str = None,
) -> str:
    """Prompt for salary negotiation preparation.

    Args:
        company: Company name
        position: Position title
        offer_amount: Current offer amount (optional)
    """
    offer_context = f"\nThe current offer is: {offer_amount}" if offer_amount else ""
    return f"""Help me prepare for salary negotiation for {position} at {company}.{offer_context}

Please:
1. Help me determine market rate for this role
2. Identify my negotiating leverage points
3. Suggest negotiation strategies and scripts
4. Help me prepare responses to common objections
5. Consider total compensation (not just salary)

Use career://profile for my current salary expectations and career://applications
for context on this opportunity."""


# Core tools - always visible when search transform is active
@mcp.tool
def get_career_overview() -> dict:
    """Get a comprehensive overview of your career management status.

    Returns a summary of profile, applications, interviews, skills, and goals.
    This is a quick snapshot to understand your current career situation.
    """
    return get_stats()


@mcp.tool
def search_career_data(
    query: str,
    data_types: list[str] = None,
) -> dict:
    """Search across all your career data for matching entries.

    Args:
        query: Search query (searches company names, positions, skills, goals, etc.)
        data_types: Types to search: 'applications', 'contacts', 'goals', 'skills'
                   (default: all types)

    Returns:
        Matching entries from each data type

    Example:
        search_career_data("Google") - find all mentions of Google
        search_career_data("python", data_types=["skills"]) - find Python skills
    """
    if data_types is None:
        data_types = ["applications", "contacts", "goals", "skills"]

    query_lower = query.lower()
    results = {}

    if "applications" in data_types:
        applications = load_data("applications")
        apps = applications.get("applications", [])
        matches = [
            a for a in apps
            if query_lower in a.get("company", "").lower()
            or query_lower in a.get("position", "").lower()
            or query_lower in (a.get("description") or "").lower()
        ]
        results["applications"] = matches[:10]

    if "contacts" in data_types:
        network = load_data("network")
        contacts = network.get("contacts", [])
        matches = [
            c for c in contacts
            if query_lower in c.get("name", "").lower()
            or query_lower in (c.get("company") or "").lower()
            or query_lower in (c.get("title") or "").lower()
        ]
        results["contacts"] = matches[:10]

    if "goals" in data_types:
        goals = load_data("goals")
        all_goals = goals.get("short_term", []) + goals.get("long_term", [])
        matches = [
            g for g in all_goals
            if query_lower in g.get("goal", "").lower()
        ]
        results["goals"] = matches[:10]

    if "skills" in data_types:
        skills = load_data("skills")
        technical = skills.get("technical", [])
        matches = [
            s for s in technical
            if query_lower in s.get("name", "").lower()
        ]
        results["skills"] = matches[:10]

    return results


def main():
    """Run the Career Manager MCP server."""
    parser = argparse.ArgumentParser(description="Career Manager MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP/SSE transport (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for HTTP/SSE transport (default: localhost)",
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="Disable search transform (show all tools instead)",
    )

    args = parser.parse_args()

    # Ensure data directory exists
    ensure_data_dir()

    # Re-create server if --no-search flag is used
    global mcp
    if args.no_search:
        mcp = create_server(use_search=False)
        # Re-register tools
        register_profile_tools(mcp)
        register_resume_tools(mcp)
        register_interview_tools(mcp)
        register_application_tools(mcp)
        register_skills_tools(mcp)
        register_network_tools(mcp)
        register_goals_tools(mcp)
        register_cover_letter_tools(mcp)
        register_resources(mcp)

    # Run the server
    if args.transport == "stdio":
        mcp.run()
    elif args.transport == "http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()