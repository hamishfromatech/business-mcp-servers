"""Tests for Change Management Tracker MCP Server."""

import os
import pytest
from pathlib import Path
import sys

SERVER_PATH = Path(__file__).parent / "server.py"
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def clean_dataDir():
    """Clean up data directory before and after each test."""
    data_dir = Path(__file__).parent / "data"
    data_file = data_dir / "change_management.json"
    (data_dir / "backups").mkdir(exist_ok=True)
    if data_file.exists():
        data_file.unlink()
    yield
    for f in data_dir.iterdir():
        if f.suffix == ".json":
            f.unlink()


class TestBackupRestore:
    def test_backup(self, clean_dataDir):
        """Test backup creates a timestamped copy."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import backup_data, create_change_request

        cr = create_change_request(
            reference="CHANGE-2025-001",
            title="Test Change",
            description="Test description",
            priority="high",
        )
        assert cr is not None
        result = backup_data()
        assert "backup" in result
        assert result["bytes"] > 0

    def test_list_backups(self, clean_dataDir):
        """Test list backups returns correct results."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import list_backups

        backups = list_backups()
        assert isinstance(backups, list)

    def test_restore_backup(self, clean_dataDir):
        """Test restore backup handles unknown backup."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import restore_backup

        with pytest.raises(ValueError, match="Unknown backup"):
            restore_backup("nonexistent-backup")


class TestChangeRequest:
    def test_create_change_request(self, clean_dataDir):
        """Test creating a change request."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import create_change_request

        cr = create_change_request(
            reference="CHANGE-2025-001",
            title="Test Change Request",
            description="This is a test change",
            change_category="standard",
            impact="medium",
            priority="high",
            approval_authority="individual",
            required_approvers=["alice", "bob"],
        )
        assert cr is not None
        assert cr.reference == "CHANGE-2025-001"
        assert cr.status == "draft"

    def test_get_change_request(self, clean_dataDir):
        """Test getting a change request by ID."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import create_change_request, get_change_request

        cr = create_change_request(
            reference="CHANGE-2025-001",
            title="Test Change Request",
            description="Test description",
        )
        retrieved = get_change_request(cr.id)
        assert retrieved is not None
        assert retrieved.title == "Test Change Request"
        assert get_change_request(9999) is None

    def test_list_change_requests(self, clean_dataDir):
        """Test listing change requests with filters."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import create_change_request, list_change_requests

        create_change_request(reference="CHANGE-2025-001", title="CRM", description="Test")
        create_change_request(reference="CHANGE-2025-002", title="SSR", description="Test")
        create_change_request(reference="CHANGE-2025-003", title="PRM", description="Test")

        results = list_change_requests(category="standard", limit=2)
        assert len(results) == 2

    def test_delete_change_request(self, clean_dataDir):
        """Test deleting a change request."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import create_change_request, delete_change_request

        cr = create_change_request(
            reference="CHANGE-2025-001",
            title="ToDelete",
            description="Test",
        )
        assert delete_change_request(cr.id, soft=True) is True
        cr2 = get_change_request(cr.id)
        assert cr2 is not None
        assert cr2.status == "closed"


class TestApproval:
    def test_approval_workflow(self, clean_dataDir):
        """Test the approval workflow."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import (
            create_change_request, submit_change_request,
            approve_change_request, reject_change_request,
        )

        cr = create_change_request(
            reference="CHANGE-2025-001",
            title="Approval Test",
            description="Test approval",
        )
        assert cr.status == "draft"

        submitted = submit_change_request(cr.id, approver_id="alice")
        assert submitted.get("submitted_at") is not None

        approved = approve_change_request(
            cr.id, approver_id="alice", approval_status="approved"
        )
        assert approved.status == "approved"
        assert len(approved.approved_by) == 1

        reject_change_request(cr.id, approver_id="charlie", decision_notes="Too risky")
        assert len(approved.rejected_by) == 1


class TestDeployment:
    def test_create_deployment(self, clean_dataDir):
        """Test creating a deployment."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import create_change_request, create_deployment

        cr = create_change_request(
            reference="CHANGE-2025-001",
            title="Deploy Test",
            description="Test deployment",
        )
        dep = create_deployment(
            change_id=cr.id,
            deployment_number="DEP-2025-001",
            deployment_type="production",
            environment="production",
        )
        assert dep is not None
        assert dep.state == "planned"

    def test_rollback_deployment(self, clean_dataDir):
        """Test rolling back a deployment."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import create_change_request, create_deployment, rollback_deployment

        cr = create_change_request(
            reference="CHANGE-2025-001",
            title="Rollback Test",
            description="Test rollback",
        )
        dep = create_deployment(
            change_id=cr.id,
            deployment_number="DEP-2025-001",
            environment="production",
        )

        rolled_back = rollback_deployment(dep.id, rollback_reason="Failed tests")
        assert rolled_back.state == "rolled_back"


class TestNotifiedParties:
    def test_notified_party_workflow(self, clean_dataDir):
        """Test notified party workflow."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import add_notified_party, mark_notified

        party = add_notified_party(
            party_identifier="alice@company.com",
            party_type="email",
            party_name="Alice Smith",
        )
        assert party.party_type == "email"
        assert not party.notified

        mark_notified(party.id, method="email")
        assert party.notified is True
        assert party.notification_count == 1


class TestChangeSummary:
    def test_change_summary(self, clean_dataDir):
        """Test change summary analytics."""
        os.environ["MCP_DATA_DIR"] = str(Path("data"))
        from server import get_change_summary, create_change_request

        summary = get_change_summary()
        assert summary["total_requests"] == 0

        create_change_request(
            reference="CHANGE-2025-001",
            title="Summary Test",
            description="Test",
            priority="high",
        )

        summary = get_change_summary()
        assert summary["total_requests"] == 1
        assert "by_status" in summary
        assert "by_category" in summary
        assert "by_priority" in summary