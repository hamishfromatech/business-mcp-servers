"""
Job application tracking tools.
"""

from typing import Annotated
from datetime import datetime
import uuid
from fastmcp import FastMCP

from ..storage import load_data, save_data


# Application status flow
STATUS_FLOW = {
    "saved": "Job saved for later",
    "applied": "Application submitted",
    "screening": "Initial screening/recruiter call",
    "interview": "Interview scheduled/completed",
    "offer": "Received offer",
    "rejected": "Application rejected",
    "withdrawn": "Withdrew application",
    "accepted": "Accepted offer",
}


def register_application_tools(mcp: FastMCP) -> None:
    """Register job application tracking tools."""

    @mcp.tool
    def add_application(
        company: Annotated[str, "Company name"],
        position: Annotated[str, "Job title/position"],
        location: Annotated[str | None, "Job location"] = None,
        url: Annotated[str | None, "Job posting URL"] = None,
        salary: Annotated[str | None, "Salary range or amount"] = None,
        description: Annotated[str | None, "Job description"] = None,
        requirements: Annotated[list[str] | None, "Job requirements"] = None,
        source: Annotated[str | None, "Where you found the job"] = None,
        notes: Annotated[str | None, "Personal notes"] = None,
        status: Annotated[str, "Initial status (default: 'saved')"] = "saved",
    ) -> dict:
        """Add a new job application to track.

        Args:
            company: Company name
            position: Job title/position
            location: Job location
            url: Job posting URL
            salary: Salary range or amount
            description: Job description
            requirements: List of requirements
            source: Where you found the job
            notes: Personal notes
            status: Initial status

        Returns:
            Created application entry
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        app = {
            "id": str(uuid.uuid4())[:8],
            "company": company,
            "position": position,
            "location": location,
            "url": url,
            "salary": salary,
            "description": description,
            "requirements": requirements or [],
            "source": source,
            "notes": notes,
            "status": status,
            "status_history": [
                {"status": status, "date": datetime.now().isoformat(), "notes": "Initial status"}
            ],
            "timeline": [
                {"event": "Application created", "date": datetime.now().isoformat()}
            ],
            "contacts": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        apps.append(app)
        applications["applications"] = apps

        # Update stats
        applications["stats"]["total"] = len(apps)
        applications["stats"][status] = applications["stats"].get(status, 0) + 1

        save_data("applications", applications)

        return app

    @mcp.tool
    def update_application_status(
        application_id: Annotated[str, "Application ID"],
        status: Annotated[
            str, "New status: 'saved', 'applied', 'screening', 'interview', 'offer', 'rejected', 'withdrawn', 'accepted'"
        ],
        notes: Annotated[str | None, "Notes about status change"] = None,
    ) -> dict:
        """Update the status of a job application.

        Args:
            application_id: ID of the application
            status: New status
            notes: Optional notes about the change

        Returns:
            Updated application
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        for app in apps:
            if app.get("id") == application_id:
                old_status = app.get("status")

                # Update stats
                if old_status in applications["stats"]:
                    applications["stats"][old_status] = max(
                        0, applications["stats"].get(old_status, 0) - 1
                    )
                applications["stats"][status] = applications["stats"].get(status, 0) + 1

                # Update application
                app["status"] = status
                app["updated_at"] = datetime.now().isoformat()

                # Add to history
                app["status_history"].append(
                    {
                        "status": status,
                        "date": datetime.now().isoformat(),
                        "notes": notes,
                    }
                )

                app["timeline"].append(
                    {"event": f"Status changed to: {status}", "date": datetime.now().isoformat()}
                )

                save_data("applications", applications)
                return app

        return {"error": f"Application {application_id} not found"}

    @mcp.tool
    def add_application_note(
        application_id: Annotated[str, "Application ID"],
        note: Annotated[str, "Note content"],
        note_type: Annotated[str, "Note type: 'general', 'reminder', 'contact', 'prep'"] = "general",
    ) -> dict:
        """Add a note to a job application.

        Args:
            application_id: ID of the application
            note: Note content
            note_type: Type of note

        Returns:
            Updated application
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        for app in apps:
            if app.get("id") == application_id:
                if "notes_list" not in app:
                    app["notes_list"] = []

                app["notes_list"].append(
                    {
                        "id": str(uuid.uuid4())[:8],
                        "note": note,
                        "type": note_type,
                        "created_at": datetime.now().isoformat(),
                    }
                )

                save_data("applications", applications)
                return app

        return {"error": f"Application {application_id} not found"}

    @mcp.tool
    def add_timeline_event(
        application_id: Annotated[str, "Application ID"],
        event: Annotated[str, "Event description"],
        event_date: Annotated[str | None, "Event date (YYYY-MM-DD)"] = None,
    ) -> dict:
        """Add a timeline event to an application.

        Args:
            application_id: ID of the application
            event: Event description
            event_date: Event date (defaults to today)

        Returns:
            Updated application
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        for app in apps:
            if app.get("id") == application_id:
                app["timeline"].append(
                    {
                        "event": event,
                        "date": event_date or datetime.now().isoformat(),
                    }
                )
                app["updated_at"] = datetime.now().isoformat()
                save_data("applications", applications)
                return app

        return {"error": f"Application {application_id} not found"}

    @mcp.tool
    def get_applications(
        status: Annotated[
            str | None, "Filter by status"
        ] = None,
        company: Annotated[str | None, "Filter by company"] = None,
        limit: Annotated[int, "Maximum results"] = 20,
    ) -> list:
        """Get job applications with optional filtering.

        Args:
            status: Filter by status
            company: Filter by company
            limit: Maximum number of results

        Returns:
            List of matching applications
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        if status:
            apps = [a for a in apps if a.get("status") == status]
        if company:
            apps = [a for a in apps if company.lower() in a.get("company", "").lower()]

        # Sort by updated_at descending
        apps = sorted(apps, key=lambda x: x.get("updated_at", ""), reverse=True)

        return apps[:limit]

    @mcp.tool
    def get_application(application_id: Annotated[str, "Application ID"]) -> dict:
        """Get a specific job application by ID.

        Args:
            application_id: ID of the application

        Returns:
            Application details
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        for app in apps:
            if app.get("id") == application_id:
                return app

        return {"error": f"Application {application_id} not found"}

    @mcp.tool
    def delete_application(application_id: Annotated[str, "Application ID"]) -> dict:
        """Delete a job application.

        Args:
            application_id: ID of the application to delete

        Returns:
            Confirmation message
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        for i, app in enumerate(apps):
            if app.get("id") == application_id:
                # Update stats
                status = app.get("status")
                if status in applications["stats"]:
                    applications["stats"][status] = max(
                        0, applications["stats"].get(status, 0) - 1
                    )
                applications["stats"]["total"] = len(apps) - 1

                del apps[i]
                save_data("applications", applications)
                return {"deleted": True, "application_id": application_id}

        return {"error": f"Application {application_id} not found", "deleted": False}

    @mcp.tool
    def get_application_stats() -> dict:
        """Get statistics about job applications.

        Returns:
            Application statistics and funnel
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        stats = {
            "total": len(apps),
            "by_status": {},
            "by_source": {},
            "recent_activity": [],
            "conversion_rates": {},
        }

        for app in apps:
            # Count by status
            status = app.get("status", "unknown")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Count by source
            source = app.get("source", "unknown")
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

        # Calculate conversion rates
        if stats["total"] > 0:
            stats["conversion_rates"] = {
                "response_rate": (stats["by_status"].get("screening", 0) + stats["by_status"].get("interview", 0)) / stats["total"] * 100,
                "interview_rate": stats["by_status"].get("interview", 0) / stats["total"] * 100,
                "offer_rate": stats["by_status"].get("offer", 0) / stats["total"] * 100,
            }

        # Recent activity (last 10 updated)
        recent = sorted(apps, key=lambda x: x.get("updated_at", ""), reverse=True)[:10]
        stats["recent_activity"] = [
            {"company": a.get("company"), "position": a.get("position"), "status": a.get("status"), "updated": a.get("updated_at")}
            for a in recent
        ]

        return stats

    @mcp.tool
    def get_upcoming_events(
        days: Annotated[int, "Number of days to look ahead"] = 7
    ) -> list:
        """Get upcoming events/reminders from applications.

        Args:
            days: Number of days to look ahead

        Returns:
            List of upcoming events
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        from datetime import timedelta
        now = datetime.now()
        future = now + timedelta(days=days)

        events = []
        for app in apps:
            for event in app.get("timeline", []):
                event_date_str = event.get("date", "")
                try:
                    event_date = datetime.fromisoformat(event_date_str.replace("Z", ""))
                    if now <= event_date <= future:
                        events.append({
                            "company": app.get("company"),
                            "position": app.get("position"),
                            "event": event.get("event"),
                            "date": event_date_str,
                            "application_id": app.get("id"),
                        })
                except (ValueError, TypeError):
                    continue

        return sorted(events, key=lambda x: x.get("date", ""))

    @mcp.tool
    def add_application_contact(
        application_id: Annotated[str, "Application ID"],
        name: Annotated[str, "Contact name"],
        role: Annotated[str | None, "Contact role/title"] = None,
        email: Annotated[str | None, "Contact email"] = None,
        phone: Annotated[str | None, "Contact phone"] = None,
        linkedin: Annotated[str | None, "LinkedIn profile"] = None,
        notes: Annotated[str | None, "Notes about contact"] = None,
    ) -> dict:
        """Add a contact person to an application.

        Args:
            application_id: ID of the application
            name: Contact name
            role: Contact role/title
            email: Contact email
            phone: Contact phone
            linkedin: LinkedIn profile URL
            notes: Notes about the contact

        Returns:
            Updated application
        """
        applications = load_data("applications")
        apps = applications.get("applications", [])

        for app in apps:
            if app.get("id") == application_id:
                contact = {
                    "id": str(uuid.uuid4())[:8],
                    "name": name,
                    "role": role,
                    "email": email,
                    "phone": phone,
                    "linkedin": linkedin,
                    "notes": notes,
                    "created_at": datetime.now().isoformat(),
                }

                if "contacts" not in app:
                    app["contacts"] = []

                app["contacts"].append(contact)
                save_data("applications", applications)
                return app

        return {"error": f"Application {application_id} not found"}