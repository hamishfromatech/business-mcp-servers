"""
Career goals and milestones tracking tools.
"""

from typing import Annotated
from datetime import datetime
import uuid
from fastmcp import FastMCP

from ..storage import load_data, save_data


def register_goals_tools(mcp: FastMCP) -> None:
    """Register goals management tools."""

    @mcp.tool
    def get_goals() -> dict:
        """Get all career goals and milestones.

        Returns short-term goals, long-term goals, milestones, and achievements.
        """
        return load_data("goals")

    @mcp.tool
    def add_short_term_goal(
        goal: Annotated[str, "Goal description"],
        category: Annotated[
            str, "Category: 'skill', 'position', 'project', 'network', 'other'"
        ] = "other",
        target_date: Annotated[str | None, "Target date (YYYY-MM-DD)"] = None,
        milestones: Annotated[list[str] | None, "Key milestones"] = None,
        priority: Annotated[str, "Priority: 'high', 'medium', 'low'"] = "medium",
    ) -> dict:
        """Add a short-term career goal (0-12 months).

        Args:
            goal: Goal description
            category: Goal category
            target_date: Target completion date
            milestones: Key milestones to achieve
            priority: Goal priority

        Returns:
            Created goal
        """
        goals = load_data("goals")
        short_term = goals.get("short_term", [])

        entry = {
            "id": str(uuid.uuid4())[:8],
            "goal": goal,
            "category": category,
            "target_date": target_date,
            "milestones": [{"text": m, "completed": False} for m in (milestones or [])],
            "priority": priority,
            "status": "active",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
        }

        short_term.append(entry)
        goals["short_term"] = short_term
        save_data("goals", goals)

        return entry

    @mcp.tool
    def add_long_term_goal(
        goal: Annotated[str, "Goal description"],
        timeframe: Annotated[str, "Timeframe: '1-2_years', '3-5_years', '5+_years'"] = "3-5_years",
        category: Annotated[
            str, "Category: 'career', 'education', 'financial', 'personal', 'other'"
        ] = "career",
        description: Annotated[str | None, "Detailed description"] = None,
        short_term_links: Annotated[list[str] | None, "Linked short-term goal IDs"] = None,
    ) -> dict:
        """Add a long-term career goal (1+ years).

        Args:
            goal: Goal description
            timeframe: Target timeframe
            category: Goal category
            description: Detailed description
            short_term_links: IDs of related short-term goals

        Returns:
            Created goal
        """
        goals = load_data("goals")
        long_term = goals.get("long_term", [])

        entry = {
            "id": str(uuid.uuid4())[:8],
            "goal": goal,
            "timeframe": timeframe,
            "category": category,
            "description": description,
            "short_term_links": short_term_links or [],
            "status": "active",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
        }

        long_term.append(entry)
        goals["long_term"] = long_term
        save_data("goals", goals)

        return entry

    @mcp.tool
    def update_goal_progress(
        goal_id: Annotated[str, "Goal ID"],
        progress: Annotated[int, "Progress percentage (0-100)"],
        status: Annotated[
            str | None, "Status: 'active', 'completed', 'paused', 'cancelled'"
        ] = None,
    ) -> dict:
        """Update progress on a goal.

        Args:
            goal_id: Goal ID
            progress: Progress percentage
            status: Optional new status

        Returns:
            Updated goal
        """
        goals = load_data("goals")

        # Check short-term goals
        for goal in goals.get("short_term", []):
            if goal.get("id") == goal_id:
                goal["progress"] = min(100, max(0, progress))
                if status:
                    goal["status"] = status
                if progress >= 100:
                    goal["status"] = "completed"
                    # Add to achievements
                    achievements = goals.get("achievements", [])
                    achievements.append({
                        "id": str(uuid.uuid4())[:8],
                        "goal": goal.get("goal"),
                        "category": goal.get("category"),
                        "completed_at": datetime.now().isoformat(),
                        "original_goal_id": goal_id,
                    })
                    goals["achievements"] = achievements
                save_data("goals", goals)
                return goal

        # Check long-term goals
        for goal in goals.get("long_term", []):
            if goal.get("id") == goal_id:
                goal["progress"] = min(100, max(0, progress))
                if status:
                    goal["status"] = status
                if progress >= 100:
                    goal["status"] = "completed"
                    achievements = goals.get("achievements", [])
                    achievements.append({
                        "id": str(uuid.uuid4())[:8],
                        "goal": goal.get("goal"),
                        "category": goal.get("category"),
                        "completed_at": datetime.now().isoformat(),
                        "original_goal_id": goal_id,
                    })
                    goals["achievements"] = achievements
                save_data("goals", goals)
                return goal

        return {"error": f"Goal {goal_id} not found"}

    @mcp.tool
    def complete_milestone(
        goal_id: Annotated[str, "Goal ID"],
        milestone_index: Annotated[int, "Index of milestone to complete"],
    ) -> dict:
        """Mark a milestone as completed.

        Args:
            goal_id: Goal ID
            milestone_index: Index of milestone (0-based)

        Returns:
            Updated goal
        """
        goals = load_data("goals")

        for goal in goals.get("short_term", []):
            if goal.get("id") == goal_id:
                milestones = goal.get("milestones", [])
                if 0 <= milestone_index < len(milestones):
                    milestones[milestone_index]["completed"] = True
                    # Update progress
                    completed = sum(1 for m in milestones if m.get("completed"))
                    goal["progress"] = round(completed / len(milestones) * 100)
                    save_data("goals", goals)
                    return goal

        return {"error": f"Goal or milestone not found"}

    @mcp.tool
    def get_active_goals(
        category: Annotated[str | None, "Filter by category"] = None,
    ) -> list:
        """Get all active goals.

        Args:
            category: Optional category filter

        Returns:
            List of active goals
        """
        goals = load_data("goals")
        active = []

        for goal in goals.get("short_term", []):
            if goal.get("status") == "active":
                if category is None or goal.get("category") == category:
                    active.append({**goal, "type": "short_term"})

        for goal in goals.get("long_term", []):
            if goal.get("status") == "active":
                if category is None or goal.get("category") == category:
                    active.append({**goal, "type": "long_term"})

        # Sort by priority and target date
        priority_order = {"high": 0, "medium": 1, "low": 2}
        active.sort(
            key=lambda x: (
                priority_order.get(x.get("priority", "medium"), 1),
                x.get("target_date", "9999"),
            )
        )

        return active

    @mcp.tool
    def get_achievements(
        limit: Annotated[int, "Maximum results"] = 20,
    ) -> list:
        """Get completed goals/achievements.

        Args:
            limit: Maximum results

        Returns:
            List of achievements
        """
        goals = load_data("goals")
        achievements = goals.get("achievements", [])

        # Sort by completion date (newest first)
        achievements = sorted(
            achievements,
            key=lambda x: x.get("completed_at", ""),
            reverse=True,
        )

        return achievements[:limit]

    @mcp.tool
    def delete_goal(goal_id: Annotated[str, "Goal ID to delete"]) -> dict:
        """Delete a goal.

        Args:
            goal_id: Goal ID

        Returns:
            Confirmation
        """
        goals = load_data("goals")

        # Check short-term
        short_term = goals.get("short_term", [])
        for i, goal in enumerate(short_term):
            if goal.get("id") == goal_id:
                del short_term[i]
                goals["short_term"] = short_term
                save_data("goals", goals)
                return {"deleted": True, "goal_id": goal_id}

        # Check long-term
        long_term = goals.get("long_term", [])
        for i, goal in enumerate(long_term):
            if goal.get("id") == goal_id:
                del long_term[i]
                goals["long_term"] = long_term
                save_data("goals", goals)
                return {"deleted": True, "goal_id": goal_id}

        return {"deleted": False, "error": f"Goal {goal_id} not found"}

    @mcp.tool
    def get_goal_summary() -> dict:
        """Get a summary of all goals.

        Returns:
            Summary with counts and progress
        """
        goals = load_data("goals")

        short_term = goals.get("short_term", [])
        long_term = goals.get("long_term", [])
        achievements = goals.get("achievements", [])

        active_short = [g for g in short_term if g.get("status") == "active"]
        active_long = [g for g in long_term if g.get("status") == "active"]

        # Calculate average progress
        short_progress = (
            sum(g.get("progress", 0) for g in active_short) / len(active_short)
            if active_short
            else 0
        )
        long_progress = (
            sum(g.get("progress", 0) for g in active_long) / len(active_long)
            if active_long
            else 0
        )

        # Get goals due soon
        from datetime import timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        soon = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        due_soon = [
            g
            for g in active_short
            if g.get("target_date") and today <= g.get("target_date", "9999") <= soon
        ]

        return {
            "short_term": {
                "total": len(short_term),
                "active": len(active_short),
                "completed": len([g for g in short_term if g.get("status") == "completed"]),
                "average_progress": round(short_progress, 1),
            },
            "long_term": {
                "total": len(long_term),
                "active": len(active_long),
                "completed": len([g for g in long_term if g.get("status") == "completed"]),
                "average_progress": round(long_progress, 1),
            },
            "achievements_count": len(achievements),
            "due_this_month": due_soon,
            "categories": {
                "skill": len([g for g in active_short if g.get("category") == "skill"]),
                "position": len([g for g in active_short if g.get("category") == "position"]),
                "project": len([g for g in active_short if g.get("category") == "project"]),
                "network": len([g for g in active_short if g.get("category") == "network"]),
            },
        }

    @mcp.tool
    def link_goals(
        short_term_id: Annotated[str, "Short-term goal ID"],
        long_term_id: Annotated[str, "Long-term goal ID to link to"],
    ) -> dict:
        """Link a short-term goal to a long-term goal.

        Args:
            short_term_id: Short-term goal ID
            long_term_id: Long-term goal ID

        Returns:
            Updated long-term goal
        """
        goals = load_data("goals")

        long_term = goals.get("long_term", [])
        for goal in long_term:
            if goal.get("id") == long_term_id:
                if short_term_id not in goal.get("short_term_links", []):
                    goal.setdefault("short_term_links", []).append(short_term_id)
                    save_data("goals", goals)
                return goal

        return {"error": f"Long-term goal {long_term_id} not found"}