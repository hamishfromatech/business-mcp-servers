"""
Skills inventory and analysis tools.
"""

from typing import Annotated
from datetime import datetime
import uuid
from fastmcp import FastMCP

from ..storage import load_data, save_data


def register_skills_tools(mcp: FastMCP) -> None:
    """Register skills management tools."""

    @mcp.tool
    def get_skills_inventory() -> dict:
        """Get the complete skills inventory.

        Returns all skills categorized as technical, soft, learning, and target skills.
        """
        return load_data("skills")

    @mcp.tool
    def add_technical_skill(
        skill: Annotated[str, "Skill name"],
        level: Annotated[str, "Level: 'beginner', 'intermediate', 'advanced', 'expert'"] = "intermediate",
        years: Annotated[int | None, "Years of experience"] = None,
        last_used: Annotated[str | None, "When last used (YYYY-MM)"] = None,
        projects: Annotated[list[str] | None, "Projects using this skill"] = None,
        certifications: Annotated[list[str] | None, "Related certifications"] = None,
    ) -> dict:
        """Add a technical skill to the inventory.

        Args:
            skill: Name of the skill
            level: Proficiency level
            years: Years of experience
            last_used: When last used
            projects: Projects where this skill was used
            certifications: Related certifications

        Returns:
            Updated skills inventory
        """
        skills = load_data("skills")
        technical = skills.get("technical", [])

        # Check for duplicates
        existing = [s for s in technical if s.get("name", "").lower() == skill.lower()]
        if existing:
            return {"error": f"Skill '{skill}' already exists", "existing": existing[0]}

        entry = {
            "id": str(uuid.uuid4())[:8],
            "name": skill,
            "level": level,
            "years": years,
            "last_used": last_used,
            "projects": projects or [],
            "certifications": certifications or [],
            "created_at": datetime.now().isoformat(),
        }

        technical.append(entry)
        skills["technical"] = technical
        save_data("skills", skills)

        return skills

    @mcp.tool
    def add_soft_skill(
        skill: Annotated[str, "Skill name"],
        level: Annotated[str, "Level: 'developing', 'competent', 'proficient', 'expert'"] = "competent",
        examples: Annotated[list[str] | None, "Examples demonstrating this skill"] = None,
    ) -> dict:
        """Add a soft skill to the inventory.

        Args:
            skill: Name of the soft skill
            level: Proficiency level
            examples: Examples demonstrating this skill

        Returns:
            Updated skills inventory
        """
        skills = load_data("skills")
        soft = skills.get("soft", [])

        # Check for duplicates
        existing = [s for s in soft if s.get("name", "").lower() == skill.lower()]
        if existing:
            return {"error": f"Skill '{skill}' already exists", "existing": existing[0]}

        entry = {
            "id": str(uuid.uuid4())[:8],
            "name": skill,
            "level": level,
            "examples": examples or [],
            "created_at": datetime.now().isoformat(),
        }

        soft.append(entry)
        skills["soft"] = soft
        save_data("skills", skills)

        return skills

    @mcp.tool
    def add_learning_goal(
        skill: Annotated[str, "Skill to learn"],
        priority: Annotated[str, "Priority: 'high', 'medium', 'low'"] = "medium",
        target_date: Annotated[str | None, "Target completion date (YYYY-MM-DD)"] = None,
        resources: Annotated[list[str] | None, "Learning resources"] = None,
        notes: Annotated[str | None, "Notes about learning this skill"] = None,
    ) -> dict:
        """Add a skill learning goal.

        Args:
            skill: Skill to learn
            priority: Learning priority
            target_date: Target completion date
            resources: Learning resources
            notes: Additional notes

        Returns:
            Updated skills inventory
        """
        skills = load_data("skills")
        learning = skills.get("learning", [])

        entry = {
            "id": str(uuid.uuid4())[:8],
            "skill": skill,
            "priority": priority,
            "target_date": target_date,
            "resources": resources or [],
            "notes": notes,
            "status": "in_progress",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
        }

        learning.append(entry)
        skills["learning"] = learning
        save_data("skills", skills)

        return skills

    @mcp.tool
    def update_learning_progress(
        skill_id: Annotated[str, "Learning goal ID"],
        progress: Annotated[int, "Progress percentage (0-100)"],
        status: Annotated[str | None, "Status: 'not_started', 'in_progress', 'completed'"] = None,
    ) -> dict:
        """Update progress on a learning goal.

        Args:
            skill_id: ID of the learning goal
            progress: Progress percentage
            status: Optional new status

        Returns:
            Updated learning goal
        """
        skills = load_data("skills")
        learning = skills.get("learning", [])

        for goal in learning:
            if goal.get("id") == skill_id:
                goal["progress"] = min(100, max(0, progress))
                if status:
                    goal["status"] = status
                if progress >= 100:
                    goal["status"] = "completed"
                goal["updated_at"] = datetime.now().isoformat()
                save_data("skills", skills)
                return goal

        return {"error": f"Learning goal {skill_id} not found"}

    @mcp.tool
    def add_target_skill(
        skill: Annotated[str, "Skill name"],
        reason: Annotated[str, "Why this skill is a target"],
        jobs_requiring: Annotated[list[str] | None, "Jobs that require this skill"] = None,
        gap: Annotated[str | None, "Current gap level: 'small', 'medium', 'large'"] = None,
    ) -> dict:
        """Add a target skill for career development.

        Args:
            skill: Skill name
            reason: Why this skill is a target
            jobs_requiring: Jobs that require this skill
            gap: Current skill gap level

        Returns:
            Updated skills inventory
        """
        skills = load_data("skills")
        target = skills.get("target_skills", [])

        entry = {
            "id": str(uuid.uuid4())[:8],
            "skill": skill,
            "reason": reason,
            "jobs_requiring": jobs_requiring or [],
            "gap": gap or "medium",
            "created_at": datetime.now().isoformat(),
        }

        target.append(entry)
        skills["target_skills"] = target
        save_data("skills", skills)

        return skills

    @mcp.tool
    def remove_skill(
        skill_id: Annotated[str, "Skill ID to remove"],
        category: Annotated[str, "Category: 'technical', 'soft', 'learning', 'target_skills'"],
    ) -> dict:
        """Remove a skill from the inventory.

        Args:
            skill_id: ID of skill to remove
            category: Category the skill belongs to

        Returns:
            Updated skills inventory
        """
        skills = load_data("skills")
        category_skills = skills.get(category, [])

        skills[category] = [s for s in category_skills if s.get("id") != skill_id]
        save_data("skills", skills)

        return skills

    @mcp.tool
    def analyze_skill_gaps(
        required_skills: Annotated[list[str], "Skills required for target role"]
    ) -> dict:
        """Analyze skill gaps for a target role.

        Args:
            required_skills: List of skills required for a role

        Returns:
            Gap analysis with recommendations
        """
        skills = load_data("skills")
        technical = [s.get("name", "").lower() for s in skills.get("technical", [])]
        soft = [s.get("name", "").lower() for s in skills.get("soft", [])]
        learning = [s.get("skill", "").lower() for s in skills.get("learning", [])]
        all_current = technical + soft

        gaps = []
        matched = []
        in_progress = []

        for skill in required_skills:
            skill_lower = skill.lower()
            if skill_lower in all_current:
                matched.append(skill)
            elif skill_lower in learning:
                in_progress.append(skill)
            else:
                gaps.append(skill)

        return {
            "required_skills": required_skills,
            "matched_skills": matched,
            "skills_in_progress": in_progress,
            "gap_skills": gaps,
            "match_percentage": round(len(matched) / len(required_skills) * 100, 1) if required_skills else 0,
            "recommendations": [
                f"Focus on learning: {', '.join(gaps[:3])}" if gaps else "No critical gaps found!",
                f"Continue developing: {', '.join(in_progress[:3])}" if in_progress else "",
            ],
        }

    @mcp.tool
    def get_skills_by_level(
        category: Annotated[str | None, "Filter by category: 'technical' or 'soft'"] = None,
        level: Annotated[str | None, "Filter by level"] = None,
    ) -> list:
        """Get skills filtered by level.

        Args:
            category: Optional category filter
            level: Optional level filter

        Returns:
            List of matching skills
        """
        skills = load_data("skills")
        result = []

        if category is None or category == "technical":
            for s in skills.get("technical", []):
                if level is None or s.get("level") == level:
                    result.append({**s, "category": "technical"})

        if category is None or category == "soft":
            for s in skills.get("soft", []):
                if level is None or s.get("level") == level:
                    result.append({**s, "category": "soft"})

        return result

    @mcp.tool
    def generate_skills_section(
        max_skills: Annotated[int, "Maximum number of skills to include"] = 15,
        format: Annotated[str, "Format: 'list', 'categorized', 'markdown'"] = "markdown",
    ) -> str:
        """Generate a skills section for resume.

        Args:
            max_skills: Maximum skills to include
            format: Output format

        Returns:
            Formatted skills section
        """
        skills = load_data("skills")
        technical = sorted(
            skills.get("technical", []),
            key=lambda x: {"expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1}.get(x.get("level", ""), 0),
            reverse=True,
        )[:max_skills]
        soft = skills.get("soft", [])[:5]

        if format == "list":
            tech_names = [s.get("name") for s in technical]
            soft_names = [s.get("name") for s in soft]
            return ", ".join(tech_names + soft_names)

        elif format == "categorized":
            result = {}
            if technical:
                result["Technical Skills"] = [s.get("name") for s in technical]
            if soft:
                result["Soft Skills"] = [s.get("name") for s in soft]
            return result

        else:  # markdown
            lines = ["## Skills", ""]
            if technical:
                tech_by_level = {}
                for s in technical:
                    lvl = s.get("level", "intermediate")
                    if lvl not in tech_by_level:
                        tech_by_level[lvl] = []
                    tech_by_level[lvl].append(s.get("name"))

                lines.append("**Technical Skills:**")
                for level in ["expert", "advanced", "intermediate", "beginner"]:
                    if level in tech_by_level:
                        lines.append(f"- {level.title()}: {', '.join(tech_by_level[level])}")

            if soft:
                lines.append("")
                lines.append("**Soft Skills:** " + ", ".join(s.get("name") for s in soft))

            return "\n".join(lines)