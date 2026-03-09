"""
Networking and contact management tools.
"""

from typing import Annotated
from datetime import datetime
import uuid
from fastmcp import FastMCP

from ..storage import load_data, save_data


def register_network_tools(mcp: FastMCP) -> None:
    """Register networking management tools."""

    @mcp.tool
    def add_contact(
        name: Annotated[str, "Contact name"],
        company: Annotated[str | None, "Company name"] = None,
        title: Annotated[str | None, "Job title"] = None,
        email: Annotated[str | None, "Email address"] = None,
        phone: Annotated[str | None, "Phone number"] = None,
        linkedin: Annotated[str | None, "LinkedIn profile URL"] = None,
        twitter: Annotated[str | None, "Twitter handle"] = None,
        how_met: Annotated[str | None, "How you met this contact"] = None,
        tags: Annotated[list[str] | None, "Tags for categorizing"] = None,
        notes: Annotated[str | None, "Notes about the contact"] = None,
    ) -> dict:
        """Add a networking contact.

        Args:
            name: Contact name
            company: Company name
            title: Job title
            email: Email address
            phone: Phone number
            linkedin: LinkedIn profile URL
            twitter: Twitter handle
            how_met: How you met this contact
            tags: Tags for categorizing
            notes: Notes about the contact

        Returns:
            Created contact entry
        """
        network = load_data("network")
        contacts = network.get("contacts", [])

        contact = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "company": company,
            "title": title,
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "twitter": twitter,
            "how_met": how_met,
            "tags": tags or [],
            "notes": notes,
            "interactions": [],
            "reminders": [],
            "created_at": datetime.now().isoformat(),
            "last_contact": None,
        }

        contacts.append(contact)
        network["contacts"] = contacts
        save_data("network", network)

        return contact

    @mcp.tool
    def update_contact(
        contact_id: Annotated[str, "Contact ID"],
        name: Annotated[str | None, "Contact name"] = None,
        company: Annotated[str | None, "Company name"] = None,
        title: Annotated[str | None, "Job title"] = None,
        email: Annotated[str | None, "Email address"] = None,
        phone: Annotated[str | None, "Phone number"] = None,
        linkedin: Annotated[str | None, "LinkedIn profile URL"] = None,
        notes: Annotated[str | None, "Notes"] = None,
    ) -> dict:
        """Update a contact's information.

        Args:
            contact_id: ID of the contact
            name: Contact name
            company: Company name
            title: Job title
            email: Email address
            phone: Phone number
            linkedin: LinkedIn profile
            notes: Notes

        Returns:
            Updated contact
        """
        network = load_data("network")
        contacts = network.get("contacts", [])

        for contact in contacts:
            if contact.get("id") == contact_id:
                if name is not None:
                    contact["name"] = name
                if company is not None:
                    contact["company"] = company
                if title is not None:
                    contact["title"] = title
                if email is not None:
                    contact["email"] = email
                if phone is not None:
                    contact["phone"] = phone
                if linkedin is not None:
                    contact["linkedin"] = linkedin
                if notes is not None:
                    contact["notes"] = notes

                contact["updated_at"] = datetime.now().isoformat()
                save_data("network", network)
                return contact

        return {"error": f"Contact {contact_id} not found"}

    @mcp.tool
    def get_contacts(
        company: Annotated[str | None, "Filter by company"] = None,
        tag: Annotated[str | None, "Filter by tag"] = None,
        search: Annotated[str | None, "Search in name, company, title"] = None,
        limit: Annotated[int, "Maximum results"] = 50,
    ) -> list:
        """Get contacts with optional filtering.

        Args:
            company: Filter by company
            tag: Filter by tag
            search: Search term
            limit: Maximum results

        Returns:
            List of matching contacts
        """
        network = load_data("network")
        contacts = network.get("contacts", [])

        if company:
            contacts = [c for c in contacts if company.lower() in (c.get("company") or "").lower()]
        if tag:
            contacts = [c for c in contacts if tag.lower() in [t.lower() for t in c.get("tags", [])]]
        if search:
            search_lower = search.lower()
            contacts = [
                c
                for c in contacts
                if search_lower in (c.get("name") or "").lower()
                or search_lower in (c.get("company") or "").lower()
                or search_lower in (c.get("title") or "").lower()
            ]

        # Sort by last contact (most recent first)
        contacts = sorted(
            contacts,
            key=lambda x: x.get("last_contact") or "",
            reverse=True,
        )

        return contacts[:limit]

    @mcp.tool
    def log_interaction(
        contact_id: Annotated[str, "Contact ID"],
        interaction_type: Annotated[
            str, "Type: 'email', 'call', 'meeting', 'event', 'message', 'other'"
        ],
        date: Annotated[str | None, "Date of interaction (YYYY-MM-DD)"] = None,
        summary: Annotated[str | None, "Summary of interaction"] = None,
        follow_up: Annotated[str | None, "Follow-up needed"] = None,
        follow_up_date: Annotated[str | None, "Follow-up date (YYYY-MM-DD)"] = None,
    ) -> dict:
        """Log an interaction with a contact.

        Args:
            contact_id: Contact ID
            interaction_type: Type of interaction
            date: Date of interaction
            summary: Summary of interaction
            follow_up: Follow-up needed
            follow_up_date: Follow-up date

        Returns:
            Updated contact with logged interaction
        """
        network = load_data("network")
        contacts = network.get("contacts", [])

        for contact in contacts:
            if contact.get("id") == contact_id:
                interaction = {
                    "id": str(uuid.uuid4())[:8],
                    "type": interaction_type,
                    "date": date or datetime.now().strftime("%Y-%m-%d"),
                    "summary": summary,
                    "follow_up": follow_up,
                    "follow_up_date": follow_up_date,
                    "created_at": datetime.now().isoformat(),
                }

                contact["interactions"].append(interaction)
                contact["last_contact"] = interaction["date"]
                save_data("network", network)

                # Also add to global interactions
                interactions = network.get("interactions", [])
                interactions.append(
                    {
                        **interaction,
                        "contact_id": contact_id,
                        "contact_name": contact.get("name"),
                        "contact_company": contact.get("company"),
                    }
                )
                network["interactions"] = interactions
                save_data("network", network)

                return contact

        return {"error": f"Contact {contact_id} not found"}

    @mcp.tool
    def get_interaction_history(
        contact_id: Annotated[str | None, "Contact ID (optional, returns all if not provided)"] = None,
        limit: Annotated[int, "Maximum results"] = 20,
    ) -> list:
        """Get interaction history.

        Args:
            contact_id: Optional contact ID to filter
            limit: Maximum results

        Returns:
            List of interactions
        """
        network = load_data("network")

        if contact_id:
            contacts = network.get("contacts", [])
            for contact in contacts:
                if contact.get("id") == contact_id:
                    return contact.get("interactions", [])[:limit]
            return []
        else:
            interactions = network.get("interactions", [])
            return sorted(interactions, key=lambda x: x.get("date", ""), reverse=True)[:limit]

    @mcp.tool
    def add_company_note(
        company_name: Annotated[str, "Company name"],
        note: Annotated[str, "Note content"],
        note_type: Annotated[
            str, "Type: 'culture', 'interview_tips', 'salary', 'benefits', 'general'"
        ] = "general",
    ) -> dict:
        """Add notes about a company for networking/interviewing.

        Args:
            company_name: Company name
            note: Note content
            note_type: Type of note

        Returns:
            Updated company entry
        """
        network = load_data("network")
        companies = network.get("companies", [])

        for company in companies:
            if company.get("name", "").lower() == company_name.lower():
                if "notes" not in company:
                    company["notes"] = []
                company["notes"].append(
                    {
                        "id": str(uuid.uuid4())[:8],
                        "note": note,
                        "type": note_type,
                        "created_at": datetime.now().isoformat(),
                    }
                )
                save_data("network", network)
                return company

        # Company doesn't exist, create it
        company = {
            "id": str(uuid.uuid4())[:8],
            "name": company_name,
            "notes": [
                {
                    "id": str(uuid.uuid4())[:8],
                    "note": note,
                    "type": note_type,
                    "created_at": datetime.now().isoformat(),
                }
            ],
            "contacts": [],
            "created_at": datetime.now().isoformat(),
        }
        companies.append(company)
        network["companies"] = companies
        save_data("network", network)

        return company

    @mcp.tool
    def get_company_info(company_name: Annotated[str, "Company name"]) -> dict:
        """Get all information about a company.

        Args:
            company_name: Company name

        Returns:
            Company info including notes and contacts
        """
        network = load_data("network")
        companies = network.get("companies", [])
        contacts = network.get("contacts", [])

        company_info = None
        for company in companies:
            if company.get("name", "").lower() == company_name.lower():
                company_info = company
                break

        if not company_info:
            company_info = {"name": company_name, "notes": [], "contacts": []}

        # Add contacts from this company
        company_info["contacts"] = [
            c for c in contacts if c.get("company", "").lower() == company_name.lower()
        ]

        return company_info

    @mcp.tool
    def get_network_stats() -> dict:
        """Get networking statistics.

        Returns:
            Statistics about your network
        """
        network = load_data("network")
        contacts = network.get("contacts", [])
        interactions = network.get("interactions", [])

        # Companies
        companies = {}
        for contact in contacts:
            company = contact.get("company")
            if company:
                companies[company] = companies.get(company, 0) + 1

        # Tags
        tags = {}
        for contact in contacts:
            for tag in contact.get("tags", []):
                tags[tag] = tags.get(tag, 0) + 1

        # Interaction types
        interaction_types = {}
        for interaction in interactions:
            itype = interaction.get("type", "other")
            interaction_types[itype] = interaction_types.get(itype, 0) + 1

        # Contacts needing follow-up
        from datetime import timedelta
        follow_ups = []
        for contact in contacts:
            for interaction in contact.get("interactions", []):
                if interaction.get("follow_up") and interaction.get("follow_up_date"):
                    follow_ups.append({
                        "contact_id": contact.get("id"),
                        "contact_name": contact.get("name"),
                        "follow_up": interaction.get("follow_up"),
                        "date": interaction.get("follow_up_date"),
                    })

        return {
            "total_contacts": len(contacts),
            "total_interactions": len(interactions),
            "companies": companies,
            "tags": tags,
            "interaction_types": interaction_types,
            "pending_follow_ups": sorted(follow_ups, key=lambda x: x.get("date", "")),
        }

    @mcp.tool
    def delete_contact(contact_id: Annotated[str, "Contact ID to delete"]) -> dict:
        """Delete a contact.

        Args:
            contact_id: ID of contact to delete

        Returns:
            Confirmation
        """
        network = load_data("network")
        contacts = network.get("contacts", [])

        for i, contact in enumerate(contacts):
            if contact.get("id") == contact_id:
                del contacts[i]
                network["contacts"] = contacts
                save_data("network", network)
                return {"deleted": True, "contact_id": contact_id}

        return {"deleted": False, "error": f"Contact {contact_id} not found"}

    @mcp.tool
    def add_tag_to_contact(
        contact_id: Annotated[str, "Contact ID"],
        tag: Annotated[str, "Tag to add"],
    ) -> dict:
        """Add a tag to a contact.

        Args:
            contact_id: Contact ID
            tag: Tag to add

        Returns:
            Updated contact
        """
        network = load_data("network")
        contacts = network.get("contacts", [])

        for contact in contacts:
            if contact.get("id") == contact_id:
                if tag.lower() not in [t.lower() for t in contact.get("tags", [])]:
                    contact["tags"].append(tag)
                    save_data("network", network)
                return contact

        return {"error": f"Contact {contact_id} not found"}