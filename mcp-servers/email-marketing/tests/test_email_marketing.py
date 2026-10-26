"""
Pytest tests for Email Marketing Campaign Manager MCP Server.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path

import pytest

# Force tests to use a temporary data directory
TEST_DATA_DIR = Path(os.environ.get("MCP_DATA_DIR", tempfile.mkdtemp()))


@pytest.fixture(scope="function")
def clean_data():
    """Remove the test data directory before each test."""
    # Save current data dir
    orig = os.environ.get("MCP_DATA_DIR")
    if TEST_DATA_DIR.exists():
        TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if TEST_DATA_DIR.exists() and TEST_DATA_DIR.is_dir():
        for f in TEST_DATA_DIR.iterdir():
            if f.suffix == ".json":
                f.unlink()
    # Use our temp dir
    os.environ["MCP_DATA_DIR"] = str(TEST_DATA_DIR)
    yield
    # Restore
    if orig is None:
        os.environ.pop("MCP_DATA_DIR", None)
    elif orig:
        os.environ["MCP_DATA_DIR"] = orig


@pytest.fixture(scope="function")
def sample_campaign_id():
    yield 999


@pytest.fixture(scope="function")
def sample_list_id():
    yield 888


class TestRecipientLists:

    def test_create_list(self, clean_data):
        result = create_list(name="Test List", category="newsletter")
        assert result["id"] >= 1
        assert result["name"] == "Test List"
        assert result["category"] == "newsletter"
        assert result["member_count"] == 0
        assert result["created_at"].startswith("20")

    def test_list_lists_all(self, clean_data):
        create_list(name="List A", category="customer")
        create_list(name="List B", category="newsletter")
        all_list = list_lists()
        assert len(all_list) == 2

    def test_list_lists_filter(self, clean_data):
        create_list(name="List A", category="customer")
        create_list(name="List B", category="newsletter")
        filtered = list_lists(category="newsletter")
        assert len(filtered) == 1
        assert filtered[0]["name"] == "List B"

    def test_add_member(self, clean_data):
        list_id = create_list(name="Test", category="customer")["id"]
        member = add_member(list_id, "alice@example.com")
        assert member["list_id"] == list_id
        assert member["address"] == "alice@example.com"
        assert member["added_at"].startswith("20")

    def test_add_multiple_members(self, clean_data):
        list_id = create_list(name="Test", category="customer")["id"]
        add_member(list_id, "alice@example.com")
        add_member(list_id, "bob@example.com")
        add_member(list_id, "charlie@example.com")
        members = get_list_members(list_id)
        assert len(members) == 3

    def test_remove_member(self, clean_data):
        list_id = create_list(name="Test", category="customer")["id"]
        add_member(list_id, "alice@example.com")
        assert get_list_members(list_id)[0]["address"] == "alice@example.com"
        removed = remove_member(list_id, "alice@example.com")
        assert removed is True
        members = get_list_members(list_id)
        assert len(members) == 0

    def test_remove_nonexistent_member(self, clean_data):
        list_id = create_list(name="Test", category="customer")["id"]
        assert remove_member(list_id, "nonexistent@example.com") is False

    def test_delete_list(self, clean_data):
        list_id = create_list(name="Test", category="customer")["id"]
        add_member(list_id, "alice@example.com")
        deleted = delete_list(list_id)
        assert deleted is True
        lists = list_lists(limit=100)
        assert all(l["id"] != list_id for l in lists)
        # Check member is gone
        all_members = [m for m in members.values() if m.get("list_id") != list_id]
        assert len(all_members) == 0

    def test_delete_nonexistent_list(self, clean_data):
        list_id = create_list(name="Test", category="customer")["id"]
        assert delete_list(list_id) is False


class TestCampaigns:

    def test_create_campaign(self, clean_data):
        result = create_campaign(
            campaign_name="Summer Sale",
            category="promotional",
            from_name="Team Sales",
            from_email="sales@example.com",
        )
        assert result["id"] >= 1
        assert result["campaign_name"] == "Summer Sale"
        assert result["category"] == "promotional"
        assert result["status"] == "draft"
        assert result["created_at"].startswith("20")

    def test_list_campaigns(self, clean_data):
        create_campaign(campaign_name="Camp A", category="promotional")
        create_campaign(campaign_name="Camp B", category="newsletter")
        all_camps = list_campaigns(limit=100)
        assert len(all_camps) == 2

    def test_list_campaigns_filter(self, clean_data):
        create_campaign(campaign_name="Camp A", category="promotional")
        create_campaign(campaign_name="Camp B", category="newsletter")
        promo = list_campaigns(category="promotional")
        assert len(promo) == 1

    def test_update_campaign(self, clean_data):
        camp = create_campaign(campaign_name="Camp A", category="promotional")
        result = update_campaign(camp["id"], campaign_name="Camp B")
        assert result["campaign_name"] == "Camp B"
        assert result["updated_at"].startswith("20")

    def test_delete_campaign(self, clean_data):
        camp = create_campaign(campaign_name="Del Me")
        deleted = delete_campaign(camp["id"])
        assert deleted is True
        campaigns = list_campaigns(limit=100)
        assert all(c["id"] != camp["id"] for c in campaigns)

    def test_delete_campaign_removes_templates(self, clean_data):
        camp = create_campaign(campaign_name="With Template")
        template = create_template(campaign_id=camp["id"], from_name="Team", from_email="t@t.com",
                                   subject_line="Hey", body_html="<p>Hi</p>", body_text="Hi",
                                   is_variant_a=False)
        templates = list_templates(limit=100)
        assert len(templates) == 1
        # Delete campaign
        delete_campaign(camp["id"])
        remaining = list_campaigns(limit=100)
        assert len(remaining) == 0
        # No templates left
        assert len(templates) == 0


class TestTemplates:

    def test_create_template(self, clean_data):
        camp = create_campaign(campaign_name="Test Camp")
        result = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Summer Sale!",
            body_html="<h1>Sale</h1>",
            body_text="Get a sale!",
        )
        assert result["campaign_id"] == camp["id"]
        assert result["status"] == "draft"
        assert result["subject_line"] == "Summer Sale!"
        assert result["opens"] == 0
        assert result["clicks"] == 0

    def test_approve_template(self, clean_data):
        camp = create_campaign(campaign_name="Test")
        template = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )
        approved = approve_template(template["id"])
        assert approved["status"] == "approved"

    def test_cannot_approve_non_draft(self, clean_data):
        camp = create_campaign(campaign_name="Test")
        template = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )
        # Manually set status to approved via update
        update_template(template["id"], status="approved")
        with pytest.raises(ValueError):
            approve_template(template["id"])

    def test_list_templates(self, clean_data):
        camp = create_campaign(campaign_name="Test")
        create_template(campaign_id=camp["id"], from_name="Team", from_email="t@example.com",
                        subject_line="V1", body_html="<p>V1</p>", body_text="V1", is_variant_a=False)
        create_template(campaign_id=camp["id"], from_name="Team", from_email="t@example.com",
                        subject_line="V2", body_html="<p>V2</p>", body_text="V2", is_variant_a=False)
        templates = list_templates(campaign_id=camp["id"])
        assert len(templates) == 2
        assert templates[0]["subject_line"] == "V2"

    def test_copy_template(self, clean_data):
        camp_source = create_campaign(campaign_name="Source Camp")
        template_src = create_template(
            campaign_id=camp_source["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Original Subject",
            body_html="<p>Original</p>",
            body_text="Original",
            is_variant_a=False,
        )
        camp_dest = create_campaign(campaign_name="Dest Camp")
        copied = copy_template(template_src["id"], camp_dest["id"], is_variant_a=False)
        assert copied["campaign_id"] == camp_dest["id"]
        assert copied["subject_line"] == "Original Subject"
        assert len(list_templates(campaign_id=camp_dest["id"])) == 1

    def test_compare_ab_test(self, clean_data):
        camp = create_campaign(campaign_name="A/B Test")
        template_a = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Version A",
            body_html="<p>A</p>",
            body_text="A",
            is_variant_a=True,
        )
        template_b = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Version B",
            body_html="<p>B</p>",
            body_text="B",
            is_variant_b=True,
        )
        result = compare_ab_test(camp["id"])
        assert result["campaign_name"] == "A/B Test"
        assert "variant_a" in result["results"]
        assert "variant_b" in result["results"]

    def test_cannot_create_both_variants(self, clean_data):
        camp = create_campaign(campaign_name="Test")
        with pytest.raises(ValueError):
            create_template(
                campaign_id=camp["id"],
                from_name="Team",
                from_email="t@example.com",
                subject_line="Test",
                body_html="<p>Test</p>",
                body_text="Test",
                is_variant_a=True,
                is_variant_b=True,
            )


class TestSendCampaign:

    def test_send_campaign(self, clean_data):
        newsletter = create_list(name="Subscribers", category="newsletter")
        camp = create_campaign(
            campaign_name="Test Send",
            category="promotional",
            from_name="Team",
            from_email="t@example.com",
            recipient_lists=[newsletter["id"]],
        )
        template = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Test Subject",
            body_html="<p>Body</p>",
            body_text="Body",
        )
        approve_template(template["id"])
        result = send_campaign(camp["id"])
        assert result["status"] == "sent"
        assert result["campaign_id"] == camp["id"]

    def test_send_cannot_send_unapproved(self, clean_data):
        newsletter = create_list(name="Subscribers")
        camp = create_campaign(
            category="promotional",
            from_name="Team",
            from_email="t@example.com",
            recipient_lists=[newsletter["id"]],
        )
        template = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )
        # Don't approve
        with pytest.raises(ValueError):
            send_campaign(camp["id"])

    def test_send_cannot_send_unscheduled(self, clean_data):
        newsletter = create_list(name="Subscribers")
        camp = create_campaign(
            category="promotional",
            from_name="Team",
            from_email="t@example.com",
            recipient_lists=[newsletter["id"]],
        )
        template = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )
        approve_template(template["id"])
        with pytest.raises(ValueError):
            send_campaign(camp["id"])

    def test_send_analytics_recorded(self, clean_data):
        newsletter = create_list(name="Subscribers")
        camp = create_campaign(
            category="promotional",
            from_name="Team",
            from_email="t@example.com",
            recipient_lists=[newsletter["id"]],
        )
        template = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Test",
            body_html="<p>Test</p>",
            body_text="Test",
        )
        approve_template(template["id"])
        send_campaign(camp["id"])
        # Template should have analytics recorded
        t = next(t for t in templates.values() if t["id"] == template["id"])
        assert t["opens"] > 0

    def test_a_b_split(self, clean_data):
        newsletter = create_list(name="Subscribers")
        camp = create_campaign(
            category="promotional",
            from_name="Team",
            from_email="t@example.com",
            recipient_lists=[newsletter["id"]],
        )
        template_a = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Subject A",
            body_html="<p>A</p>",
            body_text="A",
            is_variant_a=True,
        )
        template_b = create_template(
            campaign_id=camp["id"],
            from_name="Team",
            from_email="t@example.com",
            subject_line="Subject B",
            body_html="<p>B</p>",
            body_text="B",
            is_variant_b=True,
        )
        approve_template(template_a["id"])
        approve_template(template_b["id"])
        result = send_campaign(camp["id"])
        assert "split" in result
        assert "variant_a" in result["split"]
        assert "variant_b" in result["split"]


class TestDataPersistence:

    def test_data_fil_created(self, clean_data):
        create_list(name="Test")
        data_file = TEST_DATA_DIR / "email-marketing.json"
        assert data_file.exists()

    def test_data_round_trip(self, clean_data):
        create_list(name="Test List", category="newsletter")
        add_member("Test List", "test@example.com")
        camp = create_campaign(campaign_name="Test Camp")
        template = create_template(campaign_id=camp["id"], from_name="Team", from_email="t@t.com",
                                   subject_line="Test", body_html="<p>X</p>", body_text="X")
        approve_template(template["id"])

        # Check data file is valid JSON
        data_file = TEST_DATA_DIR / "email-marketing.json"
        assert data_file.exists()
        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["recipient_lists"]) == 1
        assert len(data["campaigns"]) == 1
        assert len(data["templates"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])