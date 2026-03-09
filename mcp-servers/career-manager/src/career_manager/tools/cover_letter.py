"""
Cover letter generation and management tools.
"""

from typing import Annotated
from datetime import datetime
import uuid
from fastmcp import FastMCP

from ..storage import load_data, save_data


def register_cover_letter_tools(mcp: FastMCP) -> None:
    """Register cover letter tools."""

    @mcp.tool
    def create_cover_letter(
        company: Annotated[str, "Company name"],
        position: Annotated[str, "Position title"],
        job_description: Annotated[str | None, "Job description text"] = None,
        hiring_manager: Annotated[str | None, "Hiring manager name"] = None,
        key_points: Annotated[list[str] | None, "Key points to highlight"] = None,
        template: Annotated[str, "Template style: 'professional', 'creative', 'technical'"] = "professional",
    ) -> dict:
        """Create a cover letter template with placeholders.

        This generates a structured cover letter template that can be customized.
        The AI assistant can help fill in the content based on your profile and resume.

        Args:
            company: Company name
            position: Position title
            job_description: Job description text
            hiring_manager: Hiring manager name
            key_points: Key points to highlight
            template: Template style

        Returns:
            Cover letter structure with sections
        """
        profile = load_data("profile")
        resume = load_data("resume")
        cover_letters = load_data("cover_letters") if "cover_letters" in load_data("applications") else {"letters": []}

        personal = profile.get("personal_info", {})
        experience = resume.get("sections", {}).get("experience", [])
        skills = resume.get("sections", {}).get("skills", [])

        # Build cover letter structure
        letter = {
            "id": str(uuid.uuid4())[:8],
            "company": company,
            "position": position,
            "job_description": job_description,
            "hiring_manager": hiring_manager,
            "key_points": key_points or [],
            "template": template,
            "sections": {
                "header": {
                    "name": personal.get("name", "[Your Name]"),
                    "email": personal.get("email", "[Your Email]"),
                    "phone": personal.get("phone", "[Your Phone]"),
                    "location": personal.get("location", "[Your Location]"),
                    "linkedin": profile.get("social_links", {}).get("linkedin", ""),
                },
                "greeting": f"Dear {hiring_manager or 'Hiring Manager'},",
                "opening": "",
                "body": {
                    "paragraph_1": "",  # Why you're interested
                    "paragraph_2": "",  # Relevant experience
                    "paragraph_3": "",  # Why this company
                },
                "closing": "",
                "signature": f"Sincerely,\n{personal.get('name', '[Your Name]')}",
            },
            "suggestions": {
                "relevant_experience": [
                    {"role": e.get("title"), "company": e.get("company"), "achievements": e.get("achievements", [])[:2]}
                    for e in experience[:3]
                ],
                "relevant_skills": [s.get("name") for s in skills[:10]],
                "company_research_prompts": [
                    f"Research {company}'s mission and values",
                    f"Find recent news about {company}",
                    f"Identify {company}'s main products/services",
                    f"Research the team and culture at {company}",
                ],
            },
            "created_at": datetime.now().isoformat(),
            "status": "draft",
        }

        # Save to applications data
        applications = load_data("applications")
        if "cover_letters" not in applications:
            applications["cover_letters"] = {"letters": []}
        applications["cover_letters"]["letters"].append(letter)
        save_data("applications", applications)

        return letter

    @mcp.tool
    def update_cover_letter_section(
        letter_id: Annotated[str, "Cover letter ID"],
        section: Annotated[str, "Section: 'opening', 'body.paragraph_1', 'body.paragraph_2', 'body.paragraph_3', 'closing'"],
        content: Annotated[str, "Section content"],
    ) -> dict:
        """Update a section of a cover letter.

        Args:
            letter_id: Cover letter ID
            section: Section to update (use dot notation for nested)
            content: New content

        Returns:
            Updated cover letter
        """
        applications = load_data("applications")
        letters = applications.get("cover_letters", {}).get("letters", [])

        for letter in letters:
            if letter.get("id") == letter_id:
                # Handle nested sections
                parts = section.split(".")
                current = letter["sections"]
                for part in parts[:-1]:
                    current = current[part]
                current[parts[-1]] = content
                letter["updated_at"] = datetime.now().isoformat()
                save_data("applications", applications)
                return letter

        return {"error": f"Cover letter {letter_id} not found"}

    @mcp.tool
    def get_cover_letter(letter_id: Annotated[str, "Cover letter ID"]) -> dict:
        """Get a specific cover letter.

        Args:
            letter_id: Cover letter ID

        Returns:
            Cover letter details
        """
        applications = load_data("applications")
        letters = applications.get("cover_letters", {}).get("letters", [])

        for letter in letters:
            if letter.get("id") == letter_id:
                return letter

        return {"error": f"Cover letter {letter_id} not found"}

    @mcp.tool
    def list_cover_letters(
        company: Annotated[str | None, "Filter by company"] = None,
        status: Annotated[str | None, "Filter by status"] = None,
    ) -> list:
        """List cover letters with optional filtering.

        Args:
            company: Filter by company name
            status: Filter by status

        Returns:
            List of cover letters
        """
        applications = load_data("applications")
        letters = applications.get("cover_letters", {}).get("letters", [])

        if company:
            letters = [l for l in letters if company.lower() in l.get("company", "").lower()]
        if status:
            letters = [l for l in letters if l.get("status") == status]

        return sorted(letters, key=lambda x: x.get("created_at", ""), reverse=True)

    @mcp.tool
    def generate_cover_letter_text(letter_id: Annotated[str, "Cover letter ID"]) -> str:
        """Generate the full text of a cover letter.

        Args:
            letter_id: Cover letter ID

        Returns:
            Full cover letter text
        """
        applications = load_data("applications")
        letters = applications.get("cover_letters", {}).get("letters", [])

        for letter in letters:
            if letter.get("id") == letter_id:
                sections = letter.get("sections", {})
                lines = []

                # Header
                header = sections.get("header", {})
                lines.append(header.get("name", ""))
                if header.get("location"):
                    lines.append(header.get("location", ""))
                contact_parts = []
                if header.get("email"):
                    contact_parts.append(header.get("email"))
                if header.get("phone"):
                    contact_parts.append(header.get("phone"))
                if contact_parts:
                    lines.append(" | ".join(contact_parts))
                if header.get("linkedin"):
                    lines.append(header.get("linkedin"))
                lines.append("")

                # Date
                lines.append(datetime.now().strftime("%B %d, %Y"))
                lines.append("")

                # Company address placeholder
                lines.append(letter.get("company", ""))
                lines.append("")
                lines.append("")

                # Greeting
                lines.append(sections.get("greeting", "Dear Hiring Manager,"))
                lines.append("")

                # Opening
                if sections.get("opening"):
                    lines.append(sections.get("opening"))
                    lines.append("")

                # Body
                body = sections.get("body", {})
                for para in ["paragraph_1", "paragraph_2", "paragraph_3"]:
                    if body.get(para):
                        lines.append(body.get(para))
                        lines.append("")

                # Closing
                if sections.get("closing"):
                    lines.append(sections.get("closing"))
                    lines.append("")

                # Signature
                lines.append(sections.get("signature", "Sincerely,"))
                lines.append("")

                return "\n".join(lines)

        return f"Cover letter {letter_id} not found"

    @mcp.tool
    def finalize_cover_letter(
        letter_id: Annotated[str, "Cover letter ID"],
    ) -> dict:
        """Mark a cover letter as finalized.

        Args:
            letter_id: Cover letter ID

        Returns:
            Updated cover letter
        """
        applications = load_data("applications")
        letters = applications.get("cover_letters", {}).get("letters", [])

        for letter in letters:
            if letter.get("id") == letter_id:
                letter["status"] = "finalized"
                letter["finalized_at"] = datetime.now().isoformat()
                save_data("applications", applications)
                return letter

        return {"error": f"Cover letter {letter_id} not found"}

    @mcp.tool
    def delete_cover_letter(letter_id: Annotated[str, "Cover letter ID"]) -> dict:
        """Delete a cover letter.

        Args:
            letter_id: Cover letter ID

        Returns:
            Confirmation
        """
        applications = load_data("applications")
        letters = applications.get("cover_letters", {}).get("letters", [])

        for i, letter in enumerate(letters):
            if letter.get("id") == letter_id:
                del letters[i]
                applications["cover_letters"]["letters"] = letters
                save_data("applications", applications)
                return {"deleted": True, "letter_id": letter_id}

        return {"deleted": False, "error": f"Cover letter {letter_id} not found"}

    @mcp.tool
    def get_cover_letter_tips() -> dict:
        """Get tips for writing effective cover letters.

        Returns:
            Tips and best practices
        """
        return {
            "structure": [
                "Opening paragraph: Hook the reader and state the position",
                "Body paragraph 1: Highlight relevant experience",
                "Body paragraph 2: Show why you're a great fit",
                "Body paragraph 3: Demonstrate knowledge of the company",
                "Closing: Call to action and thank the reader",
            ],
            "best_practices": [
                "Customize each letter for the specific role",
                "Use keywords from the job description",
                "Show, don't just tell - use specific examples",
                "Keep it to one page",
                "Proofread carefully",
                "Address a specific person if possible",
            ],
            "avoid": [
                "Generic templates without customization",
                "Repeating your resume word for word",
                "Negative language about past employers",
                "Typos and grammatical errors",
                "Being too casual or too formal",
            ],
            "power_words": [
                "achieved", "improved", "developed", "created", "managed",
                "led", "increased", "reduced", "implemented", "delivered",
                "designed", "optimized", "streamlined", "coordinated", "initiated",
            ],
        }