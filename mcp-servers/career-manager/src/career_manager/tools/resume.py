"""
Resume management tools.
"""

from typing import Annotated
from datetime import datetime
import uuid
from fastmcp import FastMCP

from ..storage import load_data, save_data, update_data


def register_resume_tools(mcp: FastMCP) -> None:
    """Register resume management tools."""

    @mcp.tool
    def get_resume() -> dict:
        """Get the current resume data including all sections.

        Returns the complete resume with summary, experience, education,
        skills, certifications, and projects.
        """
        return load_data("resume")

    @mcp.tool
    def update_resume_summary(
        summary: Annotated[str, "Professional summary/objective for resume"]
    ) -> dict:
        """Update the professional summary section of the resume.

        Args:
            summary: Professional summary text

        Returns:
            Updated resume data
        """
        resume = load_data("resume")
        resume["sections"]["summary"] = summary
        save_data("resume", resume)
        return resume

    @mcp.tool
    def add_experience(
        company: Annotated[str, "Company name"],
        title: Annotated[str, "Job title"],
        location: Annotated[str | None, "Job location"] = None,
        start_date: Annotated[str | None, "Start date (YYYY-MM format)"] = None,
        end_date: Annotated[str | None, "End date (YYYY-MM format or 'Present')"] = None,
        description: Annotated[str | None, "Job description"] = None,
        achievements: Annotated[list[str] | None, "List of key achievements"] = None,
        technologies: Annotated[list[str] | None, "Technologies/tools used"] = None,
    ) -> dict:
        """Add a work experience entry to the resume.

        Args:
            company: Company name
            title: Job title
            location: Job location (optional)
            start_date: Start date in YYYY-MM format
            end_date: End date in YYYY-MM format or 'Present'
            description: Job description
            achievements: List of key achievements
            technologies: Technologies/tools used

        Returns:
            Updated resume with new experience
        """
        resume = load_data("resume")
        experience = resume["sections"].get("experience", [])

        entry = {
            "id": str(uuid.uuid4())[:8],
            "company": company,
            "title": title,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "description": description,
            "achievements": achievements or [],
            "technologies": technologies or [],
            "created_at": datetime.now().isoformat(),
        }

        experience.append(entry)
        resume["sections"]["experience"] = experience
        save_data("resume", resume)

        return resume

    @mcp.tool
    def update_experience(
        experience_id: Annotated[str, "ID of experience entry to update"],
        company: Annotated[str | None, "Company name"] = None,
        title: Annotated[str | None, "Job title"] = None,
        location: Annotated[str | None, "Job location"] = None,
        start_date: Annotated[str | None, "Start date (YYYY-MM format)"] = None,
        end_date: Annotated[str | None, "End date (YYYY-MM format or 'Present')"] = None,
        description: Annotated[str | None, "Job description"] = None,
        achievements: Annotated[list[str] | None, "List of key achievements"] = None,
        technologies: Annotated[list[str] | None, "Technologies/tools used"] = None,
    ) -> dict:
        """Update an existing work experience entry.

        Args:
            experience_id: ID of the experience to update
            company: Company name (optional)
            title: Job title (optional)
            location: Job location (optional)
            start_date: Start date (optional)
            end_date: End date (optional)
            description: Job description (optional)
            achievements: List of achievements (optional)
            technologies: Technologies used (optional)

        Returns:
            Updated resume data
        """
        resume = load_data("resume")
        experience = resume["sections"].get("experience", [])

        for entry in experience:
            if entry.get("id") == experience_id:
                if company is not None:
                    entry["company"] = company
                if title is not None:
                    entry["title"] = title
                if location is not None:
                    entry["location"] = location
                if start_date is not None:
                    entry["start_date"] = start_date
                if end_date is not None:
                    entry["end_date"] = end_date
                if description is not None:
                    entry["description"] = description
                if achievements is not None:
                    entry["achievements"] = achievements
                if technologies is not None:
                    entry["technologies"] = technologies
                entry["updated_at"] = datetime.now().isoformat()
                break

        save_data("resume", resume)
        return resume

    @mcp.tool
    def delete_experience(
        experience_id: Annotated[str, "ID of experience entry to delete"]
    ) -> dict:
        """Delete a work experience entry from the resume.

        Args:
            experience_id: ID of the experience to delete

        Returns:
            Updated resume data
        """
        resume = load_data("resume")
        experience = resume["sections"].get("experience", [])
        resume["sections"]["experience"] = [
            e for e in experience if e.get("id") != experience_id
        ]
        save_data("resume", resume)
        return resume

    @mcp.tool
    def add_education(
        institution: Annotated[str, "School/university name"],
        degree: Annotated[str, "Degree obtained"],
        field: Annotated[str | None, "Field of study"] = None,
        location: Annotated[str | None, "Institution location"] = None,
        start_date: Annotated[str | None, "Start date (YYYY-MM format)"] = None,
        end_date: Annotated[str | None, "End date (YYYY-MM format)"] = None,
        gpa: Annotated[str | None, "GPA"] = None,
        achievements: Annotated[list[str] | None, "Notable achievements"] = None,
    ) -> dict:
        """Add an education entry to the resume.

        Args:
            institution: School/university name
            degree: Degree obtained (e.g., "Bachelor of Science")
            field: Field of study
            location: Institution location
            start_date: Start date
            end_date: End date
            gpa: GPA
            achievements: Notable achievements

        Returns:
            Updated resume data
        """
        resume = load_data("resume")
        education = resume["sections"].get("education", [])

        entry = {
            "id": str(uuid.uuid4())[:8],
            "institution": institution,
            "degree": degree,
            "field": field,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "gpa": gpa,
            "achievements": achievements or [],
            "created_at": datetime.now().isoformat(),
        }

        education.append(entry)
        resume["sections"]["education"] = education
        save_data("resume", resume)
        return resume

    @mcp.tool
    def add_skill(
        skill: Annotated[str, "Skill name"],
        category: Annotated[str, "Category: 'technical', 'soft', or 'language'"],
        level: Annotated[str | None, "Skill level: 'beginner', 'intermediate', 'expert'"] = None,
        years: Annotated[int | None, "Years of experience"] = None,
    ) -> dict:
        """Add a skill to the resume skills section.

        Args:
            skill: Skill name
            category: Category - 'technical', 'soft', or 'language'
            level: Skill level - 'beginner', 'intermediate', 'expert'
            years: Years of experience

        Returns:
            Updated resume data
        """
        resume = load_data("resume")
        skills = resume["sections"].get("skills", [])

        entry = {
            "name": skill,
            "category": category,
            "level": level,
            "years": years,
        }

        # Avoid duplicates
        existing_names = [s.get("name", "").lower() for s in skills]
        if skill.lower() not in existing_names:
            skills.append(entry)
            resume["sections"]["skills"] = skills
            save_data("resume", resume)

        return resume

    @mcp.tool
    def add_certification(
        name: Annotated[str, "Certification name"],
        issuer: Annotated[str, "Issuing organization"],
        date: Annotated[str | None, "Date obtained (YYYY-MM format)"] = None,
        expiry: Annotated[str | None, "Expiry date (YYYY-MM format)"] = None,
        credential_id: Annotated[str | None, "Credential ID"] = None,
        url: Annotated[str | None, "Credential URL"] = None,
    ) -> dict:
        """Add a certification to the resume.

        Args:
            name: Certification name
            issuer: Issuing organization
            date: Date obtained
            expiry: Expiry date (if applicable)
            credential_id: Credential ID
            url: Link to verify credential

        Returns:
            Updated resume data
        """
        resume = load_data("resume")
        certifications = resume["sections"].get("certifications", [])

        entry = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "issuer": issuer,
            "date": date,
            "expiry": expiry,
            "credential_id": credential_id,
            "url": url,
        }

        certifications.append(entry)
        resume["sections"]["certifications"] = certifications
        save_data("resume", resume)
        return resume

    @mcp.tool
    def add_project(
        name: Annotated[str, "Project name"],
        description: Annotated[str, "Project description"],
        technologies: Annotated[list[str] | None, "Technologies used"] = None,
        url: Annotated[str | None, "Project URL"] = None,
        github: Annotated[str | None, "GitHub URL"] = None,
        start_date: Annotated[str | None, "Start date (YYYY-MM)"] = None,
        end_date: Annotated[str | None, "End date (YYYY-MM)"] = None,
    ) -> dict:
        """Add a project to the resume.

        Args:
            name: Project name
            description: Project description
            technologies: Technologies used
            url: Project URL
            github: GitHub repository URL
            start_date: Start date
            end_date: End date

        Returns:
            Updated resume data
        """
        resume = load_data("resume")
        projects = resume["sections"].get("projects", [])

        entry = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "description": description,
            "technologies": technologies or [],
            "url": url,
            "github": github,
            "start_date": start_date,
            "end_date": end_date,
        }

        projects.append(entry)
        resume["sections"]["projects"] = projects
        save_data("resume", resume)
        return resume

    @mcp.tool
    def save_resume_version(
        version_name: Annotated[str, "Name for this version (e.g., 'frontend_v1')"],
        description: Annotated[str | None, "Description of this version"] = None,
    ) -> dict:
        """Save current resume as a named version for future reference.

        Args:
            version_name: Name for this version
            description: Optional description

        Returns:
            Resume data with new version saved
        """
        resume = load_data("resume")
        versions = resume.get("versions", [])

        version = {
            "id": str(uuid.uuid4())[:8],
            "name": version_name,
            "description": description,
            "sections": resume["sections"].copy(),
            "created_at": datetime.now().isoformat(),
        }

        versions.append(version)
        resume["versions"] = versions
        resume["current_version"] = version_name
        save_data("resume", resume)
        return resume

    @mcp.tool
    def load_resume_version(
        version_name: Annotated[str, "Name of version to load"]
    ) -> dict:
        """Load a saved resume version.

        Args:
            version_name: Name of the version to load

        Returns:
            Resume data with loaded version
        """
        resume = load_data("resume")
        versions = resume.get("versions", [])

        for version in versions:
            if version["name"] == version_name:
                resume["sections"] = version["sections"].copy()
                resume["current_version"] = version_name
                save_data("resume", resume)
                return resume

        return {"error": f"Version '{version_name}' not found"}

    @mcp.tool
    def list_resume_versions() -> list:
        """List all saved resume versions.

        Returns:
            List of version names, descriptions, and creation dates
        """
        resume = load_data("resume")
        versions = resume.get("versions", [])

        return [
            {
                "name": v["name"],
                "description": v.get("description"),
                "created_at": v["created_at"],
            }
            for v in versions
        ]

    @mcp.tool
    def generate_resume_markdown() -> str:
        """Generate a markdown version of the current resume.

        Returns:
            Markdown-formatted resume string
        """
        resume = load_data("resume")
        profile = load_data("profile")
        sections = resume.get("sections", {})
        personal = profile.get("personal_info", {})

        lines = []

        # Header
        name = personal.get("name", "Your Name")
        title = personal.get("title", "")
        lines.append(f"# {name}")
        if title:
            lines.append(f"**{title}**")
        lines.append("")

        # Contact info
        contacts = []
        if personal.get("email"):
            contacts.append(f"📧 {personal['email']}")
        if personal.get("phone"):
            contacts.append(f"📱 {personal['phone']}")
        if personal.get("location"):
            contacts.append(f"📍 {personal['location']}")

        social = profile.get("social_links", {})
        if social.get("linkedin"):
            contacts.append(f"💼 LinkedIn: {social['linkedin']}")
        if social.get("github"):
            contacts.append(f"💻 GitHub: {social['github']}")
        if social.get("portfolio"):
            contacts.append(f"🌐 Portfolio: {social['portfolio']}")

        if contacts:
            lines.append(" | ".join(contacts))
            lines.append("")

        # Summary
        if sections.get("summary"):
            lines.append("## Summary")
            lines.append(sections["summary"])
            lines.append("")

        # Experience
        if sections.get("experience"):
            lines.append("## Experience")
            for exp in sections["experience"]:
                lines.append(f"### {exp.get('title', '')} at {exp.get('company', '')}")
                dates = f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}"
                if exp.get("location"):
                    lines.append(f"*{dates} | {exp['location']}*")
                else:
                    lines.append(f"*{dates}*")
                if exp.get("description"):
                    lines.append(exp["description"])
                if exp.get("achievements"):
                    lines.append("")
                    for achievement in exp["achievements"]:
                        lines.append(f"- {achievement}")
                lines.append("")

        # Education
        if sections.get("education"):
            lines.append("## Education")
            for edu in sections["education"]:
                lines.append(f"### {edu.get('degree', '')} in {edu.get('field', '')}")
                lines.append(f"{edu.get('institution', '')}")
                if edu.get("gpa"):
                    lines.append(f"GPA: {edu['gpa']}")
                lines.append("")

        # Skills
        if sections.get("skills"):
            lines.append("## Skills")
            skills_by_cat = {}
            for skill in sections["skills"]:
                cat = skill.get("category", "technical")
                if cat not in skills_by_cat:
                    skills_by_cat[cat] = []
                skills_by_cat[cat].append(skill["name"])

            for cat, skills in skills_by_cat.items():
                lines.append(f"**{cat.title()}:** {', '.join(skills)}")
            lines.append("")

        # Certifications
        if sections.get("certifications"):
            lines.append("## Certifications")
            for cert in sections["certifications"]:
                line = f"- **{cert['name']}** - {cert.get('issuer', '')}"
                if cert.get("date"):
                    line += f" ({cert['date']})"
                lines.append(line)
            lines.append("")

        # Projects
        if sections.get("projects"):
            lines.append("## Projects")
            for proj in sections["projects"]:
                lines.append(f"### {proj['name']}")
                lines.append(proj.get("description", ""))
                if proj.get("technologies"):
                    lines.append(f"*Technologies: {', '.join(proj['technologies'])}*")
                lines.append("")

        return "\n".join(lines)

    # Document Generation Tools

    @mcp.tool
    def generate_resume_files(
        formats: Annotated[
            list[str] | None, "Formats to generate: 'md', 'docx', 'pdf' (default: all)"
        ] = None,
        filename: Annotated[str | None, "Base filename without extension (auto-generated if not provided)"] = None,
    ) -> dict:
        """Generate resume files in multiple formats (PDF, DOCX, Markdown).

        Creates actual files saved to ~/.career-manager/output/

        Args:
            formats: List of formats to generate (default: ['md', 'docx', 'pdf'])
            filename: Base filename without extension (auto-generated if not provided)

        Returns:
            Dict with paths to generated files and any errors

        Note:
            - Markdown (md) always works (no dependencies)
            - DOCX requires: pip install python-docx
            - PDF requires: pip install reportlab
        """
        from ..documents import generate_all_formats

        if formats is None:
            formats = ["md", "docx", "pdf"]

        result = generate_all_formats(formats=formats, filename_base=filename)

        return {
            "files": result["files"],
            "errors": result["errors"],
            "output_directory": result["output_directory"],
        }

    @mcp.tool
    def generate_resume_pdf(
        filename: Annotated[str | None, "Output filename (auto-generated if not provided)"] = None,
    ) -> dict:
        """Generate a PDF resume file.

        Creates a professionally formatted PDF saved to ~/.career-manager/output/

        Args:
            filename: Output filename (auto-generated if not provided)

        Returns:
            Dict with path to generated file

        Note:
            Requires reportlab: pip install reportlab
        """
        from ..documents import generate_pdf

        try:
            filepath = generate_pdf(filename=filename)
            return {"success": True, "path": str(filepath)}
        except ImportError as e:
            return {"success": False, "error": "reportlab not installed. Run: pip install reportlab"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def generate_resume_docx(
        filename: Annotated[str | None, "Output filename (auto-generated if not provided)"] = None,
    ) -> dict:
        """Generate a DOCX (Word) resume file.

        Creates a professionally formatted Word document saved to ~/.career-manager/output/

        Args:
            filename: Output filename (auto-generated if not provided)

        Returns:
            Dict with path to generated file

        Note:
            Requires python-docx: pip install python-docx
        """
        from ..documents import generate_docx

        try:
            filepath = generate_docx(filename=filename)
            return {"success": True, "path": str(filepath)}
        except ImportError as e:
            return {"success": False, "error": "python-docx not installed. Run: pip install python-docx"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @mcp.tool
    def generate_resume_md(
        filename: Annotated[str | None, "Output filename (auto-generated if not provided)"] = None,
    ) -> dict:
        """Generate a Markdown resume file.

        Creates a formatted Markdown file saved to ~/.career-manager/output/

        Args:
            filename: Output filename (auto-generated if not provided)

        Returns:
            Dict with path to generated file
        """
        from ..documents import generate_markdown

        filepath = generate_markdown(filename=filename)
        return {"success": True, "path": str(filepath)}

    @mcp.tool
    def list_resume_files() -> list:
        """List all generated resume files.

        Returns:
            List of generated files with paths, sizes, and timestamps
        """
        from ..documents import list_generated_files

        return list_generated_files()

    @mcp.tool
    def delete_resume_file(
        filename: Annotated[str, "Name of file to delete"]
    ) -> dict:
        """Delete a generated resume file.

        Args:
            filename: Name of file to delete (e.g., 'resume_20240115.pdf')

        Returns:
            Dict with success status
        """
        from ..documents import delete_generated_file

        deleted = delete_generated_file(filename)
        return {"success": deleted, "filename": filename}

    @mcp.tool
    def get_resume_output_directory() -> str:
        """Get the directory where resume files are saved.

        Returns:
            Path to the output directory (~/.career-manager/output/)
        """
        from ..documents import OUTPUT_DIR

        return str(OUTPUT_DIR)

    # Document generation tools
    @mcp.tool
    def generate_resume_documents(
        formats: Annotated[
            list[str] | None,
            "Formats to generate: 'pdf', 'docx', 'md' (default: all)"
        ] = None,
        filename: Annotated[
            str | None,
            "Base filename without extension (auto-generated if not provided)"
        ] = None,
    ) -> dict:
        """Generate resume documents in PDF, DOCX, and Markdown formats.

        Creates actual files saved to ~/.career-manager/output/

        Args:
            formats: List of formats to generate (default: all)
            filename: Base filename without extension

        Returns:
            Dict with paths to generated files and any errors

        Note:
            - Markdown (.md) always works (no dependencies)
            - DOCX requires: pip install python-docx
            - PDF requires: pip install reportlab
        """
        from ..documents import generate_all_formats

        if formats is None:
            formats = ["md", "docx", "pdf"]

        result = generate_all_formats(formats=formats, filename_base=filename)

        # Simplify response for MCP
        response = {
            "files": result.get("files", {}),
            "errors": result.get("errors", {}),
            "output_directory": result.get("output_directory", ""),
        }

        if result.get("files"):
            response["message"] = f"Generated {len(result['files'])} file(s)"
        else:
            response["message"] = "No files generated"

        return response

    @mcp.tool
    def generate_resume_pdf(
        filename: Annotated[
            str | None,
            "Filename for PDF (auto-generated if not provided)"
        ] = None,
    ) -> dict:
        """Generate a PDF resume file.

        Creates a professionally formatted PDF saved to ~/.career-manager/output/

        Args:
            filename: PDF filename (auto-generated if not provided)

        Returns:
            Path to generated PDF file and status

        Requires:
            pip install reportlab
        """
        from ..documents import generate_pdf

        try:
            filepath = generate_pdf(filename=filename)
            return {
                "success": True,
                "path": str(filepath),
                "message": f"PDF generated at: {filepath}",
            }
        except ImportError:
            return {
                "success": False,
                "error": "reportlab not installed. Run: pip install reportlab",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool
    def generate_resume_docx(
        filename: Annotated[
            str | None,
            "Filename for DOCX (auto-generated if not provided)"
        ] = None,
    ) -> dict:
        """Generate a DOCX resume file.

        Creates a professionally formatted Word document saved to ~/.career-manager/output/

        Args:
            filename: DOCX filename (auto-generated if not provided)

        Returns:
            Path to generated DOCX file and status

        Requires:
            pip install python-docx
        """
        from ..documents import generate_docx

        try:
            filepath = generate_docx(filename=filename)
            return {
                "success": True,
                "path": str(filepath),
                "message": f"DOCX generated at: {filepath}",
            }
        except ImportError:
            return {
                "success": False,
                "error": "python-docx not installed. Run: pip install python-docx",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool
    def generate_resume_md(
        filename: Annotated[
            str | None,
            "Filename for Markdown (auto-generated if not provided)"
        ] = None,
    ) -> dict:
        """Generate a Markdown resume file.

        Creates a Markdown file saved to ~/.career-manager/output/

        Args:
            filename: Markdown filename (auto-generated if not provided)

        Returns:
            Path to generated Markdown file and status
        """
        from ..documents import generate_markdown

        try:
            filepath = generate_markdown(filename=filename)
            return {
                "success": True,
                "path": str(filepath),
                "message": f"Markdown generated at: {filepath}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool
    def list_resume_files() -> list:
        """List all generated resume files.

        Returns:
            List of generated files with paths, sizes, and dates
        """
        from ..documents import list_generated_files

        return list_generated_files()

    @mcp.tool
    def delete_resume_file(
        filename: Annotated[str, "Filename to delete"]
    ) -> dict:
        """Delete a generated resume file.

        Args:
            filename: Name of file to delete

        Returns:
            Status of deletion
        """
        from ..documents import delete_generated_file

        deleted = delete_generated_file(filename)
        return {
            "deleted": deleted,
            "filename": filename,
            "message": f"File {'deleted' if deleted else 'not found'}: {filename}",
        }

    @mcp.tool
    def get_resume_output_directory() -> dict:
        """Get the directory where resume files are saved.

        Returns:
            Path to the output directory
        """
        from ..documents import OUTPUT_DIR

        return {
            "directory": str(OUTPUT_DIR),
            "message": f"Resume files are saved to: {OUTPUT_DIR}",
        }