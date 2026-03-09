"""
Profile management tools.
"""

from typing import Annotated
from datetime import datetime
from fastmcp import FastMCP

from ..storage import load_data, save_data, update_data, merge_nested


def register_profile_tools(mcp: FastMCP) -> None:
    """Register profile management tools."""

    @mcp.tool
    def get_profile() -> dict:
        """Get the current user profile with all personal and career information.

        Returns the complete profile including personal info, social links,
        preferences, and metadata.
        """
        return load_data("profile")

    @mcp.tool
    def update_personal_info(
        name: Annotated[str | None, "Full name"] = None,
        email: Annotated[str | None, "Email address"] = None,
        phone: Annotated[str | None, "Phone number"] = None,
        location: Annotated[str | None, "Current location/city"] = None,
        linkedin: Annotated[str | None, "LinkedIn URL or username"] = None,
        github: Annotated[str | None, "GitHub URL or username"] = None,
        portfolio: Annotated[str | None, "Portfolio website URL"] = None,
        website: Annotated[str | None, "Personal website URL"] = None,
        summary: Annotated[str | None, "Professional summary/tagline"] = None,
        title: Annotated[str | None, "Current job title"] = None,
    ) -> dict:
        """Update personal information in the profile.

        Only provide fields you want to update. Other fields remain unchanged.

        Args:
            name: Full name
            email: Email address
            phone: Phone number
            location: Current location/city
            linkedin: LinkedIn URL or username
            github: GitHub URL or username
            portfolio: Portfolio website URL
            website: Personal website URL
            summary: Professional summary/tagline
            title: Current job title

        Returns:
            Updated profile data
        """
        profile = load_data("profile")

        # Update personal info
        personal_info = profile.get("personal_info", {})
        if name is not None:
            personal_info["name"] = name
        if email is not None:
            personal_info["email"] = email
        if phone is not None:
            personal_info["phone"] = phone
        if location is not None:
            personal_info["location"] = location
        if summary is not None:
            personal_info["summary"] = summary
        if title is not None:
            personal_info["title"] = title

        profile["personal_info"] = personal_info

        # Update social links
        social_links = profile.get("social_links", {})
        if linkedin is not None:
            social_links["linkedin"] = linkedin
        if github is not None:
            social_links["github"] = github
        if portfolio is not None:
            social_links["portfolio"] = portfolio
        if website is not None:
            social_links["website"] = website

        profile["social_links"] = social_links
        save_data("profile", profile)

        return profile

    @mcp.tool
    def update_preferences(
        job_search_status: Annotated[
            str | None, "Job search status: 'open', 'casually_looking', 'not_looking'"
        ] = None,
        preferred_locations: Annotated[list[str] | None, "List of preferred work locations"] = None,
        preferred_work_type: Annotated[
            str | None, "Work type preference: 'remote', 'hybrid', 'onsite'"
        ] = None,
        salary_min: Annotated[int | None, "Minimum salary expectation"] = None,
        salary_max: Annotated[int | None, "Maximum salary expectation"] = None,
        salary_currency: Annotated[str | None, "Salary currency (e.g., USD, EUR)"] = None,
    ) -> dict:
        """Update job search preferences and settings.

        Args:
            job_search_status: Current job search status
            preferred_locations: List of preferred work locations
            preferred_work_type: Work type preference
            salary_min: Minimum salary expectation
            salary_max: Maximum salary expectation
            salary_currency: Salary currency

        Returns:
            Updated profile with preferences
        """
        profile = load_data("profile")
        preferences = profile.get("preferences", {})

        if job_search_status is not None:
            valid_statuses = ["open", "casually_looking", "not_looking"]
            if job_search_status in valid_statuses:
                preferences["job_search_status"] = job_search_status

        if preferred_locations is not None:
            preferences["preferred_locations"] = preferred_locations

        if preferred_work_type is not None:
            valid_types = ["remote", "hybrid", "onsite"]
            if preferred_work_type in valid_types:
                preferences["preferred_work_type"] = preferred_work_type

        salary_range = preferences.get("salary_range", {})
        if salary_min is not None:
            salary_range["min"] = salary_min
        if salary_max is not None:
            salary_range["max"] = salary_max
        if salary_currency is not None:
            salary_range["currency"] = salary_currency
        preferences["salary_range"] = salary_range

        profile["preferences"] = preferences
        save_data("profile", profile)

        return profile

    @mcp.tool
    def add_social_link(
        platform: Annotated[str, "Platform name (e.g., 'twitter', 'instagram')"],
        url: Annotated[str, "URL or username for the platform"],
    ) -> dict:
        """Add a social media or professional platform link.

        Args:
            platform: Name of the platform
            url: URL or username

        Returns:
            Updated profile with social links
        """
        return merge_nested("profile", f"social_links.{platform}", url)

    @mcp.tool
    def get_job_search_status() -> dict:
        """Get current job search status and preferences.

        Returns job search status, preferred locations, work type,
        and salary expectations.
        """
        profile = load_data("profile")
        preferences = profile.get("preferences", {})

        return {
            "status": preferences.get("job_search_status", "open"),
            "preferred_locations": preferences.get("preferred_locations", []),
            "work_type": preferences.get("preferred_work_type", "hybrid"),
            "salary_range": preferences.get("salary_range", {}),
        }