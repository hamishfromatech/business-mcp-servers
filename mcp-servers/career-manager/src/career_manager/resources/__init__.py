"""
MCP Resources for Career Manager.
"""

from typing import Annotated
from fastmcp import FastMCP

from ..storage import load_data, get_stats


def register_resources(mcp: FastMCP) -> None:
    """Register MCP resources."""

    @mcp.resource("career://profile")
    def get_profile_resource() -> str:
        """User profile and personal information."""
        import json
        profile = load_data("profile")
        return json.dumps(profile, indent=2)

    @mcp.resource("career://resume")
    def get_resume_resource() -> str:
        """Current resume data."""
        import json
        resume = load_data("resume")
        return json.dumps(resume, indent=2)

    @mcp.resource("career://applications")
    def get_applications_resource() -> str:
        """Job applications tracking data."""
        import json
        applications = load_data("applications")
        return json.dumps(applications, indent=2)

    @mcp.resource("career://interviews")
    def get_interviews_resource() -> str:
        """Interview preparation and history data."""
        import json
        interviews = load_data("interviews")
        return json.dumps(interviews, indent=2)

    @mcp.resource("career://skills")
    def get_skills_resource() -> str:
        """Skills inventory data."""
        import json
        skills = load_data("skills")
        return json.dumps(skills, indent=2)

    @mcp.resource("career://goals")
    def get_goals_resource() -> str:
        """Career goals and milestones data."""
        import json
        goals = load_data("goals")
        return json.dumps(goals, indent=2)

    @mcp.resource("career://network")
    def get_network_resource() -> str:
        """Networking contacts and interactions data."""
        import json
        network = load_data("network")
        return json.dumps(network, indent=2)

    @mcp.resource("career://stats")
    def get_stats_resource() -> str:
        """Career management statistics and summary."""
        import json
        stats = get_stats()
        return json.dumps(stats, indent=2)

    # Resource templates for dynamic access

    @mcp.resource("career://application/{application_id}")
    def get_application_by_id(application_id: str) -> str:
        """Get a specific job application by ID."""
        import json
        applications = load_data("applications")
        apps = applications.get("applications", [])
        for app in apps:
            if app.get("id") == application_id:
                return json.dumps(app, indent=2)
        return json.dumps({"error": f"Application {application_id} not found"})

    @mcp.resource("career://contact/{contact_id}")
    def get_contact_by_id(contact_id: str) -> str:
        """Get a specific contact by ID."""
        import json
        network = load_data("network")
        contacts = network.get("contacts", [])
        for contact in contacts:
            if contact.get("id") == contact_id:
                return json.dumps(contact, indent=2)
        return json.dumps({"error": f"Contact {contact_id} not found"})

    @mcp.resource("career://company/{company_name}")
    def get_company_by_name(company_name: str) -> str:
        """Get company information including contacts and notes."""
        import json
        network = load_data("network")
        companies = network.get("companies", [])
        contacts = network.get("contacts", [])

        company_info = {"name": company_name, "notes": [], "contacts": []}

        for company in companies:
            if company.get("name", "").lower() == company_name.lower():
                company_info = company
                break

        # Add contacts from this company
        company_info["contacts"] = [
            c for c in contacts
            if c.get("company", "").lower() == company_name.lower()
        ]

        return json.dumps(company_info, indent=2)