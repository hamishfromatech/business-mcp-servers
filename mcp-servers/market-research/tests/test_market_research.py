"""
pytest suite for Market Research MCP Server.
Run with: pytest tests/ -v
"""

import os
import json
import sys
import tempfile
from pathlib import Path

import pytest
from fastmcp import FastMCP

pytest_plugins = ["pytest_env"]


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def clean_data_dir(test_data_dir):
    """Setup and cleanup data directory per test session."""
    data_dir = test_data_dir / "market_research"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_file = data_dir / "market_research.json"
    if data_file.exists():
        data_file.unlink()
    yield data_file
    # Already cleaned up by tempfile, this is a no-op


@pytest.fixture
def mcp_server(clean_data_dir):
    """Create a FastMCP server instance with our custom setup."""
    # Set environment before importing
    os.environ["MCP_DATA_DIR"] = str(clean_data_dir)
    # Reimport to reload data file paths
    import importlib
    import market_research.server as server
    importlib.reload(server)
    return server.mcp


# -----------------------------------------------------------------------------
# Server Import Tests
# -----------------------------------------------------------------------------

class TestServerImport:
    """Basic server import and initialization tests."""

    def test_server_module_imports(self):
        """Test that all required modules import successfully."""
        import market_research.server as server
        from fastmcp import FastMCP
        assert isinstance(server.mcp, FastMCP)

    def test_server_name(self):
        """Test server name is set correctly."""
        import market_research.server as server
        assert server.mcp.name == "Market Research"

    def test_server_instructions(self):
        """Test server instructions are set."""
        import market_research.server as server
        assert "market research" in server.mcp.instructions.lower()


# -----------------------------------------------------------------------------
# Survey Tests
# -----------------------------------------------------------------------------

class TestSurvey:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_create_survey(self, clean_data_dir):
        """Test creating a new survey."""
        from market_research.server import (
            create_survey,
            _load_data,
        )
        os.environ["MCP_DATA_DIR"] = str(clean_data_dir)

        # Need to reload to use the test data dir
        import importlib
        import market_research.server as server
        importlib.reload(server)
        create_survey(
            title="Test Survey",
            description="A test survey",
            language="en",
            is_active=True,
        )
        data = _load_data()
        survey_ids = list(data.get("surveys", {}).keys())
        assert len(survey_ids) == 1
        assert data["surveys"][survey_ids[0]]["title"] == "Test Survey"
        assert data["surveys"][survey_ids[0]]["is_active"] is True

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_create_survey_with_settings(self, clean_data_dir):
        """Test creating a survey with all settings."""
        from market_research.server import create_survey, _load_data
        import importlib
        import market_research.server as server
        importlib.reload(server)

        create_survey(
            title="NPS Survey",
            description="Rate your experience",
            language="en",
            is_active=True,
            auto_decline_nps_below=6,
            opt_out_allowed=True,
            allow_multiple_responses=False,
            allow_anonymized=False,
        )
        data = _load_data()
        survey_id = list(data["surveys"].keys())[0]
        s = data["surveys"][survey_id]
        assert s["auto_decline_nps_below"] == 6
        assert s["opt_out_allowed"] is True
        assert s["allow_multiple_responses"] is False

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_get_survey(self, clean_data_dir):
        """Test retrieving a survey by ID."""
        from market_research.server import create_survey, get_survey, _load_data
        import importlib
        import market_research.server as server
        importlib.reload(server)

        create_survey(title="Test", description="Hello")
        data = _load_data()
        survey_id = list(data["surveys"].keys())[0]

        result = get_survey(survey_id)
        assert result is not None
        assert result["title"] == "Test"

        non_existent = get_survey(9999)
        assert non_existent is None

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_list_surveys(self, clean_data_dir):
        """Test listing surveys."""
        from market_research.server import create_survey, _load_data
        import importlib
        import market_research.server as server
        importlib.reload(server)

        create_survey("Survey A", "", is_active=True)
        create_survey("Survey B", "", is_active=True)
        create_survey("Survey C", "", is_active=False)

        data = _load_data()
        surveys = server.list_surveys()
        titles = [s["title"] for s in surveys]
        assert "Survey A" in titles
        assert "Survey B" in titles
        assert "Survey C" in titles  # list includes inactive

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_list_surveys_filter(self, clean_data_dir):
        """Test filtering surveys by status and language."""
        from market_research.server import create_survey, _load_data
        import importlib
        import market_research.server as server
        importlib.reload(server)

        create_survey("En Survey", "", language="en", is_active=True)
        create_survey("Es Survey", "", language="es", is_active=True)
        create_survey("En Inactive", "", language="en", is_active=False)

        data = _load_data()
        # Filter by language
        en_surveys = server.list_surveys(language="en")
        titles = [s["title"] for s in en_surveys]
        assert "En Survey" in titles
        assert "En Inactive" in titles

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_update_survey(self, clean_data_dir):
        """Test updating survey fields."""
        from market_research.server import (
            create_survey, update_survey, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Test", description="Old desc", is_active=False)
        survey_id = survey["id"]

        result = update_survey(
            survey_id,
            title="Updated Title",
            description="New description",
        )
        assert result["title"] == "Updated Title"
        assert result["description"] == "New description"

        # Try to update active survey - should fail
        active = create_survey(title="Active", description="", is_active=True)
        with pytest.raises(ValueError):
            update_survey(active["id"], title="Cannot Modify")

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_delete_survey(self, clean_data_dir):
        """Test deleting a survey."""
        from market_research.server import create_survey, _load_data
        import importlib
        import market_research.server as server
        importlib.reload(server)

        create_survey(title="To Delete", description="Me")
        data = _load_data()
        survey_id = list(data["surveys"].keys())[0]

        result = server.delete_survey(survey_id)
        assert result is True
        updated_data = _load_data()
        assert survey_id not in updated_data["surveys"]

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_create_survey_with_no_questions(self, clean_data_dir):
        """Test creating a survey without questions."""
        from market_research.server import create_survey, _load_data
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(
            title="Empty Survey",
            description="No questions yet",
            is_active=False,
        )
        assert len(survey["questions"]) == 0

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_survey_answer_count(self, clean_data_dir):
        """Test answer_count is reflected after submitting responses."""
        from market_research.server import (
            create_survey, submit_response, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Count Survey", is_active=True)
        survey_id = survey["id"]

        # Create answer, submit, then get
        submit_response(
            survey_id=survey_id,
            respondent_id="user1",
            answers={"test": "value"},
        )

        result = server.get_survey(survey_id)
        assert result["answer_count"] == 1

        # Submit another
        submit_response(
            survey_id=survey_id,
            respondent_id="user2",
            answers={"test": "value2"},
        )
        result = server.get_survey(survey_id)
        assert result["answer_count"] == 2


# -----------------------------------------------------------------------------
# Question Tests
# -----------------------------------------------------------------------------

class TestQuestion:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_add_question_to_survey(self, clean_data_dir):
        """Test adding a question to a survey."""
        from market_research.server import (
            create_survey, add_question_to_survey, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Q Survey", is_active=False)
        survey_id = survey["id"]

        result = add_question_to_survey(
            survey_id=survey_id,
            question_text="What is your name?",
            question_type="text",
            is_required=True,
            position=1,
        )
        assert result["question_text"] == "What is your name?"
        assert result["is_required"] is True
        assert result["position"] == 1

        survey = server.get_survey(survey_id)
        assert len(survey["questions"]) == 1

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_create_question(self, clean_data_dir):
        """Test creating a question with all fields."""
        from market_research.server import (
            create_survey, create_question, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Options Survey", is_active=False)
        survey_id = survey["id"]

        question = create_question(
            survey_id=survey_id,
            question_text="How likely are you to recommend us?",
            question_type="nps",
            is_required=True,
            options=[
                server.QuestionOption(value="0", display_text="Not at all likely"),
                server.QuestionOption(value="10", display_text="Very likely"),
                server.QuestionOption(value="5", weight=2.0),
            ],
            position=0,
        )

        assert question["question_text"] == "How likely are you to recommend us?"
        assert question["question_type"] == "nps"
        assert len(question["options"]) == 3

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_delete_question_from_survey(self, clean_data_dir):
        """Test removing a question from a survey."""
        from market_research.server import (
            create_survey, add_question_to_survey, remove_question_from_survey,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Remove Q", is_active=False)
        survey_id = survey["id"]

        server.add_question_to_survey(survey_id, "Q1", "text")
        server.add_question_to_survey(survey_id, "Q2", "text")
        server.add_question_to_survey(survey_id, "Q3", "text")

        result = remove_question_from_survey(survey_id, 2)
        assert result is True
        survey = server.get_survey(survey_id)
        assert len(survey["questions"]) == 2

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_delete_question_dont_exist(self, clean_data_dir):
        """Test deleting a non-existent question."""
        from market_research.server import (
            create_survey, remove_question_from_survey,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Delete Q", is_active=False)
        result = remove_question_from_survey(survey["id"], 999)
        assert result is False


# -----------------------------------------------------------------------------
# Category Tests
# -----------------------------------------------------------------------------

class TestCategory:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_create_category(self, clean_data_dir):
        """Test creating a category."""
        from market_research.server import create_category
        import importlib
        import market_research.server as server
        importlib.reload(server)

        cat = create_category(name="Product", slug="product", description="For products")
        assert cat.name == "Product"
        assert cat.slug == "product"
        assert cat.description == "For products"
        assert cat.is_active is True

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_list_categories(self, clean_data_dir):
        """Test listing categories."""
        from market_research.server import create_category, list_categories
        import importlib
        import market_research.server as server
        importlib.reload(server)

        create_category(name="Product", slug="product")
        create_category(name="Support", slug="support")

        cats = list_categories()
        names = [c["name"] for c in cats]
        assert "Product" in names
        assert "Support" in names

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_update_category(self, clean_data_dir):
        """Test updating a category."""
        from market_research.server import create_category, update_category
        import importlib
        import market_research.server as server
        importlib.reload(server)

        cat = create_category(name="Old", slug="old")
        cat_id = cat.id

        result = update_category(cat_id, name="New", slug="new-ext")
        assert result.name == "New"
        assert result.slug == "new-ext"

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_delete_category(self, clean_data_dir):
        """Test soft-deleting a category."""
        from market_research.server import create_category, delete_category
        import importlib
        import market_research.server as server
        importlib.reload(server)

        cat = create_category(name="Delete Me", slug="me")
        cat_id = cat.id

        result = delete_category(cat_id)
        assert result is True
        updated = server.get_category(cat_id)
        assert updated.get("is_active") is False


# -----------------------------------------------------------------------------
# NPS Tests
# -----------------------------------------------------------------------------

class TestNPS:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_nps_score_calculation(self, clean_data_dir):
        """Test NPS score calculation."""
        from market_research.server import (
            create_survey, submit_response, get_nps_summary,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="NPS Test", is_active=True)
        survey_id = survey["id"]

        # Submit responses: 2 detractors (3, 2), 1 passive (6), 3 promoters (9, 9, 10)
        submit_response(survey_id, "u1", answers={}, nps_raw_score=3)
        submit_response(survey_id, "u2", answers={}, nps_raw_score=2)
        submit_response(survey_id, "u3", answers={}, nps_raw_score=6)
        submit_response(survey_id, "u4", answers={}, nps_raw_score=9)
        submit_response(survey_id, "u5", answers={}, nps_raw_score=9)
        submit_response(survey_id, "u6", answers={}, nps_raw_score=10)

        summary = get_nps_summary(survey_id)
        assert summary["respondents"] == 6
        assert summary["nps_score"] == 33.3  # 66.7% - 33.3%
        assert summary["distribution_buckets"]["promoter"] == 3
        assert summary["distribution_buckets"]["passive"] == 1
        assert summary["distribution_buckets"]["detractor"] == 2

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_nps_auto_decline(self, clean_data_dir):
        """Test auto-discarding NPS scores below threshold."""
        from market_research.server import (
            create_survey, submit_response, get_nps_summary,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(
            title="NPS Auto-Discard Test",
            is_active=True,
            auto_decline_nps_below=6,
        )
        survey_id = survey["id"]

        # Submit: score 5 (should be discarded), score 9
        submit_response(survey_id, "u1", answers={}, nps_raw_score=5)
        submit_response(survey_id, "u2", answers={}, nps_raw_score=9)

        summary = get_nps_summary(survey_id)
        # Only u2 counts: NPS = 100% - 0% = 100.0
        assert summary["respondents"] == 1
        assert summary["nps_score"] == 100.0

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_nps_distribution(self, clean_data_dir):
        """Test NPS distribution buckets."""
        from market_research.server import (
            create_survey, submit_response, get_nps_summary,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="NPS Dist", is_active=True)
        survey_id = survey["id"]

        for score in [0, 1, 2, 6, 7, 8, 9, 10]:
            submit_response(survey_id, f"u{score}", answers={}, nps_raw_score=score)

        summary = get_nps_summary(survey_id)
        dist = summary["distribution_buckets"]
        assert dist["detractor"] == 3
        assert dist["passive"] == 2
        assert dist["promoter"] == 3

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_nps_surveys_list(self, clean_data_dir):
        """Test NPS summary for specific survey."""
        from market_research.server import (
            create_survey, submit_response, get_nps_summary,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey1 = create_survey(title="Survey 1", is_active=True)
        survey2 = create_survey(title="Survey 2", is_active=True)
        survey_id1 = survey1["id"]
        survey_id2 = survey2["id"]

        # Survey 1: all detractors
        for score in [1, 2, 3]:
            submit_response(survey_id1, f"u{score}", answers={}, nps_raw_score=score)
        # Survey 2: all promoters
        for score in [9, 10, 10]:
            submit_response(survey_id2, f"u{score}", answers={}, nps_raw_score=score)

        s1 = get_nps_summary(survey_id1)
        s2 = get_nps_summary(survey_id2)
        overall = get_nps_summary()

        assert s1["nps_score"] == -73.3
        assert s2["nps_score"] == 66.7
        assert overall["nps_score"] == 0.0  # 50% - 50%


# -----------------------------------------------------------------------------
# Response Tests
# -----------------------------------------------------------------------------

class TestResponse:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_submit_response(self, clean_data_dir):
        """Test submitting a survey response."""
        from market_research.server import (
            create_survey, submit_response, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Answer Survey", is_active=True)
        survey_id = survey["id"]

        result = submit_response(
            survey_id=survey_id,
            respondent_id="test-user-001",
            respondent_email="test@example.com",
            category_id=1,
            answers={"q1": "good", "q2": 5},
            nps_raw_score=9,
            follow_up=False,
        )

        assert result.id > 0
        assert result.respondent_id == "test-user-001"
        assert result.respondent_email == "test@example.com"
        assert result.category_id == 1
        assert result.answers == {"q1": "good", "q2": 5}
        assert result.nps_raw_score == 9
        assert result.status == "submitted"
        assert result.submitted_date == _today()

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_submit_duplicate_rejected(self, clean_data_dir):
        """Test that duplicate responses are rejected."""
        from market_research.server import (
            create_survey, submit_response, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(
            title="No Duplicates",
            is_active=True,
            allow_multiple_responses=False,
        )
        survey_id = survey["id"]

        submit_response(
            survey_id=survey_id,
            respondent_id="same-person",
            respondent_email="person@a.com",
            answers={},
        )

        with pytest.raises(ValueError) as exc:
            submit_response(
                survey_id=survey_id,
                respondent_id="same-person",
                respondent_email="person@a.com",
                answers={},
            )
        assert "already submitted" in str(exc.value).lower()

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_duplicate_allowed(self, clean_data_dir):
        """Test that duplicates are allowed when enabled."""
        from market_research.server import (
            create_survey, submit_response, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(
            title="Duplicates OK",
            is_active=True,
            allow_multiple_responses=True,
        )
        survey_id = survey["id"]

        result1 = submit_response(
            survey_id=survey_id,
            respondent_id="same-person",
            respondent_email="person@a.com",
            answers={"email": "p1"},
        )
        result2 = submit_response(
            survey_id=survey_id,
            respondent_id="same-person",
            respondent_email="person@a.com",
            answers={"email": "p2"},
        )
        assert result2.id > result1.id


# -----------------------------------------------------------------------------
# Duplicate Check
# -----------------------------------------------------------------------------

class TestDuplicateCheck:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_check_duplicate_found(self, clean_data_dir):
        """Test duplicate detection returns True (no duplicate)."""
        from market_research.server import (
            create_survey, check_duplicate, submit_response,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(
            title="Dup Check",
            is_active=True,
            allow_multiple_responses=False,
        )
        survey_id = survey["id"]

        # Submit first response
        submit_response(
            survey_id=survey_id,
            respondent_id="john",
            respondent_email="john@example.com",
            answers={},
        )

        # Check - should return True (no duplicate)
        assert check_duplicate(survey_id, "john", "john@example.com") is True

        # Submit second - duplicate
        with pytest.raises(ValueError):
            submit_response(
                survey_id=survey_id,
                respondent_id="john",
                respondent_email="john@example.com",
                answers={},
            )

        # After submitting duplicate, check returns False
        assert check_duplicate(survey_id, "john", "john@example.com") is False

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_no_duplicate(self, clean_data_dir):
        """Test no duplicate exists."""
        from market_research.server import create_survey, check_duplicate
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Fresh", is_active=True)
        survey_id = survey["id"]

        assert check_duplicate(survey_id, "someone") is True


# -----------------------------------------------------------------------------
# Response List & Update
# -----------------------------------------------------------------------------

class TestResponseList:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_list_responses(self, clean_data_dir):
        """Test listing responses with filters."""
        from market_research.server import (
            create_survey, submit_response, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="List Responses", is_active=True)
        survey_id = survey["id"]

        submit_response(survey_id, "u1", answers={}, nps_raw_score=9)
        submit_response(survey_id, "u2", answers={}, nps_raw_score=3)
        submit_response(survey_id, "u3", answers={}, nps_raw_score=8)

        all_responses = server.list_responses(survey_id=survey_id)
        assert len(all_responses) == 3

        # Filter by category
        cats = {1: "cat1", 2: "cat2"}
        r1 = submit_response(survey_id, "c1", answers={}, category_id=1)
        r2 = submit_response(survey_id, "c2", answers={}, category_id=2)

        cat1 = server.list_responses(survey_id=survey_id, category_id=1)
        assert len(cat1) == 1
        assert cat1[0]["respondent_id"] == "c1"

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_response_update(self, clean_data_dir):
        """Test updating a response."""
        from market_research.server import (
            create_survey, submit_response, update_response,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Update Response", is_active=True)
        survey_id = survey["id"]

        r = submit_response(
            survey_id=survey_id,
            respondent_id="to-update",
            answers={},
            nps_raw_score=5,
        )
        response_id = r.id

        updated = update_response(response_id, nps_raw_score=9)
        assert updated.nps_raw_score == 9

        non_existent = update_response(9999, nps_raw_score=9)
        assert non_existent is None

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_delete_response(self, clean_data_dir):
        """Test deleting a response."""
        from market_research.server import (
            create_survey, submit_response, delete_response,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(title="Delete Response", is_active=True)
        survey_id = survey["id"]

        submit_response(survey_id, "to-delete", answers={})
        r = submit_response(survey_id, "to-delete-2", answers={})

        delete_response(r.id)
        remaining = server.list_responses(survey_id=survey_id)
        assert len(remaining) == 1
        assert remaining[0].id == r.id

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_delete_non_existent(self, clean_data_dir):
        """Test deleting a non-existent response."""
        from market_research.server import delete_response
        import importlib
        import market_research.server as server
        importlib.reload(server)

        result = delete_response(9999)
        assert result is False


# -----------------------------------------------------------------------------
# Analytics Tests
# -----------------------------------------------------------------------------

class TestAnalytics:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_survey_overview(self, clean_data_dir):
        """Test survey overview analytics."""
        from market_research.server import (
            create_survey, submit_response, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        survey = create_survey(
            title="Analytics Survey",
            is_active=True,
            language="en",
        )
        survey_id = survey["id"]

        # Add questions and answers
        server.add_question_to_survey(
            survey_id, "Satisfaction (1-5)", "rating", position=0,
        )
        server.add_question_to_survey(
            survey_id, "Likelihood to Recommend (0-10)", "nps", position=1,
        )

        server.submit_response(
            survey_id, "user1", answers={"0": "4", "1": "9"},
            nps_raw_score=9, category_id=1,
        )
        server.submit_response(
            survey_id, "user2", answers={"0": "5", "1": "10"},
            nps_raw_score=10, category_id=2,
        )

        overview = server.get_survey_overview(survey_id)
        assert overview["survey_id"] == survey_id
        assert overview["title"] == "Analytics Survey"
        assert overview["total_responses"] == 2
        assert overview["completion_rate"] == 100.0
        assert overview["nps_score"] == 50.0
        assert overview["category_breakdown"] == {1: 1, 2: 1}

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_analytics_overview(self, clean_data_dir):
        """Test overall analytics overview."""
        from market_research.server import (
            create_survey, submit_response, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        s1 = create_survey(title="Survey A", is_active=True)
        s2 = create_survey(title="Survey B", is_active=True)

        survey_id1 = s1["id"]
        survey_id2 = s2["id"]

        for i in range(5):
            submit_response(survey_id1, f"a{i}", answers={})
        for i in range(2):
            submit_response(survey_id2, f"b{i}", answers={})

        overview = server.get_analytics_overview()
        assert overview["total_surveys"] == 2
        assert overview["active_surveys"] == 2
        assert overview["total_responses"] == 7
        assert overview["submitted_responses"] == 7

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_analytics_overview_inactive(self, clean_data_dir):
        """Test analytics overview excludes inactive surveys."""
        from market_research.server import (
            create_survey, submit_response, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        active = create_survey(title="Active", is_active=True)
        inactive = create_survey(title="Inactive", is_active=False)

        server.submit_response(active["id"], "u1", answers={})

        overview = server.get_analytics_overview()
        assert overview["total_surveys"] == 2
        assert overview["active_surveys"] == 1
        assert overview["submitted_responses"] == 1

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_feedback_by_category(self, clean_data_dir):
        """Test feedback volume by category."""
        from market_research.server import (
            create_survey, create_category, submit_response,
            get_feedback_by_category,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        # Create and populate
        server.create_category("Product", slug="product")
        server.create_category("Support", slug="support")
        server.create_category("Pricing", slug="pricing")

        survey = create_survey(title="Cat Survey", is_active=True)
        survey_id = survey["id"]

        submit_response(survey_id, "p1", answers={}, category_id=1)  # Product
        submit_response(survey_id, "p2", answers={}, category_id=1)  # Product
        submit_response(survey_id, "s1", answers={}, category_id=2)  # Support
        submit_response(survey_id, "s2", answers={}, category_id=2)  # Support
        submit_response(survey_id, "s3", answers={}, category_id=2)  # Support
        submit_response(survey_id, "pr1", answers={}, category_id=3)  # Pricing

        cats = server.get_feedback_by_category()
        by_cat = {c["category_id"]: c["recent"] for c in cats}

        assert by_cat[1] == 2
        assert by_cat[2] == 3
        assert by_cat[3] == 1


# -----------------------------------------------------------------------------
# Resource Tests
# -----------------------------------------------------------------------------

class TestResources:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_survey_resources(self, clean_data_dir):
        """Test survey resources are created."""
        from market_research.server import create_survey, _load_data
        import importlib
        import market_research.server as server
        importlib.reload(server)

        s = create_survey(title="Resource Test", is_active=True)
        survey_id = s["id"]

        # Test active surveys resource
        active_text = server.get_active_surveys_resource()
        assert f"**{s['title']}**" in active_text or f"{s['title']}" in active_text

        # Test all surveys resource
        all_text = server.get_all_surveys_resource()
        assert s.get("id") in all_text

        # Test NPS resource
        nps_text = server.get_nps_resource()
        assert "NPS Summary" in nps_text


# -----------------------------------------------------------------------------
# Backup / Restore Tests
# -----------------------------------------------------------------------------

class TestBackup:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_backup_data(self, clean_data_dir):
        """Test backing up data."""
        from market_research.server import (
            create_survey, backup_data, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        create_survey(title="Backup Test", is_active=True)
        backup = server.backup_data()
        assert "backup" in backup
        assert "bytes" in backup
        assert backup["bytes"] > 0

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_list_backups(self, clean_data_dir):
        """Test listing backups."""
        from market_research.server import create_survey, _load_data
        import importlib
        import market_research.server as server
        importlib.reload(server)

        create_survey(title="List Backups", is_active=True)
        backups = server.list_backups()
        assert len(backups) >= 1  # At least the current one

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_restore_backup(self, clean_data_dir):
        """Test restoring from backup."""
        from market_research.server import (
            create_survey, backup_data, restore_backup, _load_data,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        create_survey(title="To Be Restored", is_active=False)
        create_survey(title="To Be Deleted", is_active=True)  # This will be deleted

        # Delete the survey we need
        server.delete_survey(list(server.list_surveys())[0]["id"])

        # Create fresh data
        new_survey = create_survey(title="Fresh Data", is_active=True)

        # Backup and restore
        backup = server.backup_data()
        restore_result = server.restore_backup(backup["backup"])

        # Should have the old data restored
        data = _load_data()
        restored = [s for s in data["surveys"].values() if s.get("is_active")]
        assert len(restored) >= 1


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

class TestIntegration:

    @pytest.mark.parametrize("clean_data_dir", [None])
    def test_full_survey_workflow(self, clean_data_dir):
        """Test a complete survey-to-results workflow."""
        from market_research.server import (
            create_survey, create_question, submit_response,
            get_survey_overview, get_nps_summary,
        )
        import importlib
        import market_research.server as server
        importlib.reload(server)

        # Step 1: Create survey
        survey = create_survey(
            title="Customer Satisfaction Survey",
            description="Please take a moment to tell us about your experience",
            language="en",
            is_active=True,
            allow_multiple_responses=False,
        )
        survey_id = survey["id"]

        # Step 2: Add questions
        server.create_question(
            survey_id,
            "How likely are you to recommend us? (0-10)",
            "nps",
            is_required=True,
        )
        server.create_question(
            survey_id,
            "Rate your overall satisfaction (1-5)",
            "rating",
            is_required=False,
            options=[
                server.QuestionOption(value="1", display_text="Very Dissatisfied"),
                server.QuestionOption(value="5", display_text="Very Satisfied"),
                server.QuestionOption(value="3", weight=2.0),
            ],
            position=1,
        )
        server.create_question(
            survey_id,
            "Any additional comments?",
            "text_area",
            is_required=False,
            position=2,
        )

        # Step 3: Collect responses
        server.submit_response(
            survey_id, "client-001",
            respondent_email="happy@client.com",
            category_id=1,
            answers={"0": "9", "1": "5", "2": "Excellent service!"},
            nps_raw_score=9,
        )
        server.submit_response(
            survey_id, "client-002",
            respondent_email="neutral@client.com",
            category_id=2,
            answers={"0": "7", "1": "3"},
            nps_raw_score=7,
        )
        server.submit_response(
            survey_id, "client-003",
            respondent_email="unhappy@client.com",
            category_id=3,
            answers={"0": "4", "1": "2"},
            nps_raw_score=4,
        )

        # Step 4: Analyze results
        overview = server.get_survey_overview(survey_id)
        assert overview["total_responses"] == 3

        nps = get_nps_summary(survey_id)
        assert nps["nps_score"] == -16.7  # 33.3% - 50%
        assert nps["nss_summary"]["detractors"] == 1  # one score of 4
        assert nps["nss_summary"]["passives"] == 1  # one score of 7
        assert nps["nss_summary"]["promoters"] == 1  # one score of 9

        # Step 5: Check category distribution
        cats = server.get_feedback_by_category()
        by_cat = {c["category_id"]: c["recent"] for c in cats}
        assert by_cat[1] == 1
        assert by_cat[2] == 1
        assert by_cat[3] == 1

        print("Full workflow test passed!")


# Helper for tests
def _today():
    from datetime import date
    return date.today().isoformat()