"""
Interview practice and management tools.
"""

from typing import Annotated
from datetime import datetime
import uuid
from fastmcp import FastMCP

from ..storage import load_data, save_data


# Common interview question templates by category
QUESTION_TEMPLATES = {
    "behavioral": [
        "Tell me about a time when you had to work with a difficult team member.",
        "Describe a situation where you had to meet a tight deadline.",
        "Give an example of a time you showed leadership.",
        "Tell me about a time you failed and what you learned from it.",
        "Describe a project you're particularly proud of.",
        "Tell me about a time you had to adapt to a significant change.",
        "Give an example of how you handled a conflict at work.",
        "Describe a time when you had to learn something new quickly.",
        "Tell me about a time you went above and beyond your job responsibilities.",
        "Describe a situation where you had to make a difficult decision.",
    ],
    "technical": [
        "Walk me through your approach to debugging a complex issue.",
        "How would you design a system that needs to handle high traffic?",
        "Explain your experience with [specific technology from resume].",
        "Describe your development workflow from idea to deployment.",
        "How do you ensure code quality in your projects?",
        "Tell me about a technical challenge you overcame recently.",
        "How would you optimize a slow-performing application?",
        "Explain [concept] as if you were teaching it to a junior developer.",
        "What's your approach to testing your code?",
        "How do you stay current with new technologies?",
    ],
    "situational": [
        "What would you do if you disagreed with your manager's technical decision?",
        "How would you handle being assigned a project you're not qualified for?",
        "What would you do if a project was falling behind schedule?",
        "How would you prioritize multiple urgent tasks?",
        "What would you do if you noticed a colleague was struggling?",
        "How would you handle a situation where requirements keep changing?",
        "What would you do if you made a mistake that affected production?",
        "How would you approach learning a completely new technology?",
        "What would you do if you were asked to do something unethical?",
        "How would you handle a difficult client or stakeholder?",
    ],
    "experience": [
        "Walk me through your career journey.",
        "What interests you about this role?",
        "Why are you leaving your current position?",
        "What's your greatest professional achievement?",
        "Where do you see yourself in 5 years?",
        "What do you consider your biggest weakness?",
        "What motivates you in your work?",
        "What's your ideal work environment?",
        "How do you handle work-life balance?",
        "What questions do you have for us?",
    ],
}


def register_interview_tools(mcp: FastMCP) -> None:
    """Register interview management tools."""

    @mcp.tool
    def get_interview_questions(
        category: Annotated[
            str | None, "Question category: 'behavioral', 'technical', 'situational', 'experience'"
        ] = None,
        count: Annotated[int, "Number of questions to return"] = 5,
    ) -> list:
        """Get interview practice questions.

        Returns questions for interview preparation. If no category specified,
        returns a mix from all categories.

        Args:
            category: Question category (optional)
            count: Number of questions to return

        Returns:
            List of interview questions with category labels
        """
        interviews = load_data("interviews")

        # Get custom questions from bank
        custom_questions = interviews.get("questions_bank", [])

        if category:
            # Return from specific category
            questions = QUESTION_TEMPLATES.get(category, [])
            custom_cat = [q for q in custom_questions if q.get("category") == category]
        else:
            # Mix from all categories
            questions = []
            for cat, qs in QUESTION_TEMPLATES.items():
                for q in qs:
                    questions.append({"question": q, "category": cat})
            custom_cat = custom_questions

        # Add custom questions
        for q in custom_cat[:count]:
            questions.append({"question": q.get("question"), "category": q.get("category")})

        return questions[:count]

    @mcp.tool
    def add_custom_question(
        question: Annotated[str, "The interview question"],
        category: Annotated[str, "Category: 'behavioral', 'technical', 'situational', 'experience'"],
        notes: Annotated[str | None, "Notes or tips for answering"] = None,
    ) -> dict:
        """Add a custom interview question to the question bank.

        Args:
            question: The interview question text
            category: Question category
            notes: Optional notes or tips

        Returns:
            Updated question bank
        """
        interviews = load_data("interviews")
        questions_bank = interviews.get("questions_bank", [])

        entry = {
            "id": str(uuid.uuid4())[:8],
            "question": question,
            "category": category,
            "notes": notes,
            "created_at": datetime.now().isoformat(),
        }

        questions_bank.append(entry)
        interviews["questions_bank"] = questions_bank
        save_data("interviews", interviews)

        return {"added": entry, "total_questions": len(questions_bank)}

    @mcp.tool
    def log_interview_session(
        company: Annotated[str, "Company name"],
        position: Annotated[str, "Position title"],
        date: Annotated[str, "Interview date (YYYY-MM-DD)"],
        round_type: Annotated[
            str, "Round type: 'phone', 'technical', 'behavioral', 'onsite', 'final'"
        ],
        interviewer: Annotated[str | None, "Interviewer name(s)"] = None,
        questions_asked: Annotated[list[str] | None, "Questions asked during interview"] = None,
        notes: Annotated[str | None, "Personal notes about the interview"] = None,
        went_well: Annotated[list[str] | None, "What went well"] = None,
        needs_improvement: Annotated[list[str] | None, "Areas to improve"] = None,
        follow_up: Annotated[str | None, "Follow-up actions needed"] = None,
    ) -> dict:
        """Log an interview session for tracking and reflection.

        Args:
            company: Company name
            position: Position title
            date: Interview date
            round_type: Type of interview round
            interviewer: Interviewer name(s)
            questions_asked: Questions asked during interview
            notes: Personal notes
            went_well: What went well
            needs_improvement: Areas to improve
            follow_up: Follow-up actions

        Returns:
            Logged interview session
        """
        interviews = load_data("interviews")
        sessions = interviews.get("sessions", [])

        session = {
            "id": str(uuid.uuid4())[:8],
            "company": company,
            "position": position,
            "date": date,
            "round_type": round_type,
            "interviewer": interviewer,
            "questions_asked": questions_asked or [],
            "notes": notes,
            "went_well": went_well or [],
            "needs_improvement": needs_improvement or [],
            "follow_up": follow_up,
            "created_at": datetime.now().isoformat(),
        }

        sessions.append(session)
        interviews["sessions"] = sessions
        save_data("interviews", interviews)

        return session

    @mcp.tool
    def get_interview_history(
        company: Annotated[str | None, "Filter by company name"] = None,
        limit: Annotated[int, "Maximum number of sessions to return"] = 10,
    ) -> list:
        """Get interview session history.

        Args:
            company: Filter by company (optional)
            limit: Maximum number of sessions

        Returns:
            List of interview sessions
        """
        interviews = load_data("interviews")
        sessions = interviews.get("sessions", [])

        if company:
            sessions = [s for s in sessions if s.get("company", "").lower() == company.lower()]

        # Sort by date descending
        sessions = sorted(sessions, key=lambda x: x.get("date", ""), reverse=True)

        return sessions[:limit]

    @mcp.tool
    def analyze_interview_performance() -> dict:
        """Analyze interview performance patterns and provide insights.

        Returns:
            Performance analysis with statistics and recommendations
        """
        interviews = load_data("interviews")
        sessions = interviews.get("sessions", [])

        if not sessions:
            return {"message": "No interview sessions logged yet"}

        # Analyze patterns
        total_sessions = len(sessions)
        companies = set(s.get("company") for s in sessions)

        # Count round types
        round_types = {}
        for s in sessions:
            rt = s.get("round_type", "unknown")
            round_types[rt] = round_types.get(rt, 0) + 1

        # Aggregate feedback
        all_went_well = []
        all_improvements = []
        for s in sessions:
            all_went_well.extend(s.get("went_well", []))
            all_improvements.extend(s.get("needs_improvement", []))

        # Common questions
        all_questions = []
        for s in sessions:
            all_questions.extend(s.get("questions_asked", []))

        return {
            "total_sessions": total_sessions,
            "unique_companies": len(companies),
            "round_types": round_types,
            "strengths": all_went_well[:10],
            "areas_to_improve": all_improvements[:10],
            "frequently_asked_questions": list(set(all_questions))[:10],
            "recommendations": [
                "Practice more " + max(round_types, key=round_types.get) + " interviews",
                "Focus on improving: " + ", ".join(all_improvements[:3]) if all_improvements else "Keep practicing!",
            ],
        }

    @mcp.tool
    def add_preparation_material(
        company: Annotated[str, "Company name"],
        material_type: Annotated[
            str, "Type: 'research', 'questions_to_ask', 'company_info', 'tips'"
        ],
        content: Annotated[str, "Content/notes"],
    ) -> dict:
        """Add preparation materials for a specific company.

        Args:
            company: Company name
            material_type: Type of preparation material
            content: The content/notes

        Returns:
            Updated preparation materials
        """
        interviews = load_data("interviews")
        prep = interviews.get("preparation_materials", {})

        if company not in prep:
            prep[company] = {}

        if material_type not in prep[company]:
            prep[company][material_type] = []

        prep[company][material_type].append(
            {"content": content, "created_at": datetime.now().isoformat()}
        )

        interviews["preparation_materials"] = prep
        save_data("interviews", interviews)

        return {"company": company, "material_type": material_type, "added": True}

    @mcp.tool
    def get_preparation_materials(
        company: Annotated[str, "Company name"]
    ) -> dict:
        """Get all preparation materials for a company.

        Args:
            company: Company name

        Returns:
            All preparation materials for the company
        """
        interviews = load_data("interviews")
        prep = interviews.get("preparation_materials", {})

        return prep.get(company, {})

    @mcp.tool
    def generate_interview_prep(
        company: Annotated[str, "Company name"],
        position: Annotated[str, "Position title"],
    ) -> dict:
        """Generate a comprehensive interview preparation checklist.

        Args:
            company: Company name
            position: Position title

        Returns:
            Preparation checklist with tasks and resources
        """
        profile = load_data("profile")
        resume = load_data("resume")

        checklist = {
            "company": company,
            "position": position,
            "tasks": [
                {"task": "Research company's products/services", "done": False},
                {"task": "Review company's recent news", "done": False},
                {"task": "Understand company culture and values", "done": False},
                {"task": "Prepare elevator pitch", "done": False},
                {"task": "Review resume and prepare to discuss each role", "done": False},
                {"task": "Prepare STAR stories for behavioral questions", "done": False},
                {"task": "Prepare questions to ask interviewer", "done": False},
                {"task": "Research interviewers on LinkedIn", "done": False},
                {"task": "Prepare salary expectations", "done": False},
                {"task": "Plan outfit and logistics", "done": False},
            ],
            "questions_to_prepare": [
                f"Why do you want to work at {company}?",
                f"What do you know about {company}?",
                f"Why are you interested in the {position} role?",
                "Tell me about yourself.",
                "What are your strengths and weaknesses?",
                f"Why are you a good fit for {position}?",
                "Where do you see yourself in 5 years?",
                "What questions do you have for us?",
            ],
            "key_experiences_to_highlight": [],
        }

        # Add key experiences from resume
        for exp in resume.get("sections", {}).get("experience", [])[:3]:
            checklist["key_experiences_to_highlight"].append(
                {
                    "role": exp.get("title"),
                    "company": exp.get("company"),
                    "achievements": exp.get("achievements", [])[:2],
                }
            )

        # Add salary expectations from profile
        salary = profile.get("preferences", {}).get("salary_range", {})
        if salary.get("min") or salary.get("max"):
            checklist["salary_expectations"] = salary

        return checklist