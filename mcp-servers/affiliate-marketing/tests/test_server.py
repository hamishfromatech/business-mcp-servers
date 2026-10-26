"""Tests for Affiliate Marketing Tracker MCP server."""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from server import (
    AffiliateNetwork, Affiliate, TrackingLink, Commission, Payout,
    AffiliateStatus, CommissionType, PayoutStatus,
    _load_data, _save_data, _write_payload, _flush_pending,
    DATA_FILE, DATA_DIR, _save,
    create_affiliate_network, create_affiliate, create_tracking_link,
    record_click, record_conversion, create_commission, create_payout,
    get_affiliate_performance, get_click_rate, get_commission_summary,
    backup_data, list_backups, restore_backup, flush_data,
    list_affiliate_networks, list_affiliates, list_tracking_links,
    list_commissions, list_payouts, get_affiliate_network, get_tracking_link,
    update_affiliate_network, update_affiliate, update_tracking_link,
    update_commission, get_commission, delete_affiliate, delete_tracking_link,
    delete_commission, delete_payout, get_conversion_log, get_click_log,
)


class TestDataPersistence:
    """Test data persistence layer."""

    def test_load_empty_data(self):
        data = _load_data()
        assert "affiliate_networks" in data
        assert "affiliates" in data
        assert "tracking_links" in data
        assert "commissions" in data
        assert "payouts" in data

    def test_save_and_load_cycle(self):
        test_data = {
            "affiliate_networks": {"1": {"id": 1, "name": "Test", "slug": "test", "currency": "USD", "available": True, "created_at": "", "updated_at": ""}},
            "affiliates": {}, "tracking_links": {}, "commissions": {},
            "payouts": {}, "click_log": [], "conversion_log": [],
            "next_network_id": 1, "next_affiliate_id": 1, "next_link_id": 1,
            "next_commission_id": 1, "next_payout_id": 1,
            "next_click_id": 1, "next_conversion_id": 1,
        }

        test_dir = Path(tempfile.mkdtemp())
        test_file = test_dir / "test.json"
        payload = json.dumps(test_data, indent=2, default=str)

        fd, tmp_path = tempfile.mkstemp(dir=str(test_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp_path, test_file)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        loaded = _load_data()
        assert loaded["affiliate_networks"]["1"]["name"] == "Test"
        shutil.rmtree(test_dir)


class TestAffiliateNetwork:
    """Test affiliate network CRUD."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_create_affiliate_network(self):
        network = create_affiliate_network(
            name="Amazon Associates",
            slug="amazon-associates",
            currency="USD",
            available=True,
            nexus_url="https://affiliate.amazon.com/",
        )
        assert network.id == 1
        assert network.name == "Amazon Associates"
        assert network.currency == "USD"

    def test_list_affiliate_networks(self):
        create_affiliate_network(name="Amazon", slug="amazon", currency="USD")
        create_affiliate_network(name="ShareASale", slug="shareasale", currency="USD")
        all_networks = list_affiliate_networks()
        assert len(all_networks) == 2

    def test_update_affiliate_network(self):
        network = create_affiliate_network(name="Test", slug="test")
        result = update_affiliate_network(network.id, available=False, currency="EUR")
        assert result.available is False
        assert result.currency == "EUR"

    def test_get_affiliate_network(self):
        create_affiliate_network(name="Test", slug="test")
        network = get_affiliate_network(1)
        assert network.name == "Test"

    def test_invalid_network_id(self):
        network = get_affiliate_network(999)
        assert network is None


class TestAffiliate:
    """Test affiliate CRUD."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_create_affiliate(self):
        affiliate = create_affiliate(
            name="John Doe",
            email="john@example.com",
            status="active",
            join_method="user",
            location="New York",
        )
        assert affiliate.id == 1
        assert affiliate.name == "John Doe"
        assert affiliate.email == "john@example.com"

    def test_list_affiliates(self):
        create_affiliate(name="John", email="john@example.com", status="active")
        create_affiliate(name="Jane", email="jane@example.com", status="active")
        results = list_affiliates(status="active")
        assert len(results) == 2

    def test_search_affiliates(self):
        create_affiliate(name="John Doe", location="NY")
        create_affiliate(name="Jane Smith", location="CA")
        results = list_affiliates(search="john")
        assert len(results) == 1
        assert results[0].name == "John Doe"

    def test_update_affiliate(self):
        affiliate = create_affiliate(name="John", email="john@example.com")
        result = update_affiliate(affiliate.id, status="pending", email="new@example.com")
        assert result.status == "pending"
        assert result.email == "new@example.com"

    def test_delete_affiliate(self):
        create_affiliate(name="John", email="john@example.com")
        assert delete_affiliate(1) is True
        assert get_affiliate(1) is None

    def test_delete_invalid(self):
        assert delete_affiliate(999) is False


class TestTrackingLink:
    """Test tracking link CRUD."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_create_tracking_link(self):
        create_affiliate(name="John", email="john@example.com")
        network = create_affiliate_network(name="Amazon", slug="amazon")
        link = create_tracking_link(
            affiliate_id=1, name="Acme Laptop Deal", slug="acme-laptop-2025",
            network_id=1, product_category="electronics", product="acme-laptop",
            commission_rate_pct=5.0, payout_override_pct=2.5,
        )
        assert link.id == 1
        assert link.affiliate_id == 1
        assert link.network_id == 1
        assert link.commission_rate_pct == 5.0

    def test_list_tracking_links(self):
        create_affiliate(name="John", email="john@example.com")
        create_tracking_link(affiliate_id=1, name="Link 1", slug="link1")
        create_tracking_link(affiliate_id=1, name="Link 2", slug="link2")
        links = list_tracking_links(affiliate_id=1)
        assert len(links) == 2

    def test_get_tracking_link(self):
        create_affiliate(name="John", email="john@example.com")
        link = create_tracking_link(affiliate_id=1, name="Test", slug="test")
        result = get_tracking_link(1)
        assert result.name == "Test"

    def test_update_tracking_link(self):
        create_affiliate(name="John", email="john@example.com")
        link = create_tracking_link(affiliate_id=1, name="Test", slug="test")
        result = update_tracking_link(link.id, name="Updated", slug="updated")
        assert result.name == "Updated"


class TestClickTracking:
    """Test click and impression tracking."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_record_click(self):
        create_affiliate(name="John", email="john@example.com")
        link = create_tracking_link(affiliate_id=1, name="Test", slug="test")
        click = record_click(link_id=1, source="google", medium="cpc")
        assert click["id"] == 1
        assert click["link_id"] == 1
        assert click["link_clicks"] == 1
        assert click["impressions"] == 1

    def test_record_impression(self):
        create_affiliate(name="John", email="john@example.com")
        link = create_tracking_link(affiliate_id=1, name="Test", slug="test")
        impression = record_impression(link_id=1, source="facebook")
        assert impression["id"] == 1
        assert impression["type"] == "impression"

    def test_link_stats_from_clicks(self):
        create_affiliate(name="John", email="john@example.com")
        link = create_tracking_link(affiliate_id=1, name="Test", slug="test")
        for _ in range(5):
            record_click(link_id=1, source="google")
        l = get_tracking_link(1)
        assert l.clicks == 5
        assert l.link_clicks == 5


class TestConversionTracking:
    """Test conversion tracking."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_record_conversion(self):
        create_affiliate(name="John", email="john@example.com")
        link = create_tracking_link(affiliate_id=1, name="Test", slug="test")
        conv = record_conversion(
            link_id=1, conversion_type="purchase", revenue=999.00,
            currency="USD", quantity=1, price=999.00, product="acme-laptop",
        )
        assert conv["id"] == 1
        assert conv["conversion_type"] == "purchase"
        assert conv["revenue"] == 999.00

    def test_conversion_log(self):
        create_affiliate(name="John", email="john@example.com")
        link = create_tracking_link(affiliate_id=1, name="Test", slug="test")
        record_conversion(link_id=1, conversion_type="purchase", revenue=100.00)
        record_conversion(link_id=1, conversion_type="purchase", revenue=200.00)
        log = get_conversion_log(link_id=1)
        assert len(log) == 2


class TestCommissions:
    """Test commission management."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_create_commission(self):
        create_affiliate(name="John", email="john@example.com")
        commission = create_commission(
            affiliate_id=1, link_id=1, type=CommissionType.STANDARD.value,
            rate_pct=5.0, currency="USD", padded_with="commission",
            period_days=30, lower_commission_pct=2.5, earned_commission=125.50,
        )
        assert commission.id == 1
        assert commission.rate_pct == 5.0
        assert commission.earned_commission == 125.50

    def test_list_commissions(self):
        create_affiliate(name="John", email="john@example.com")
        create_commission(affiliate_id=1, rate_pct=5.0)
        create_commission(affiliate_id=1, rate_pct=7.0)
        commissions = list_commissions(status="active")
        assert len(commissions) == 2

    def test_update_commission(self):
        create_affiliate(name="John", email="john@example.com")
        commission = create_commission(affiliate_id=1, rate_pct=5.0)
        result = update_commission(commission.id, rate_pct=7.0, status="expired")
        assert result.status == "expired"


class TestPayouts:
    """Test payout management."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_create_payout(self):
        create_affiliate(name="John", email="john@example.com")
        payout = create_payout(
            affiliate_id=1, amount=125.50, currency="USD",
            payout_status="pending", payout_method="paypal",
            fees=2.51, invoice_number="INV-001",
        )
        assert payout.id == 1
        assert payout.amount == 125.50
        assert payout.payout_status == "pending"

    def test_process_payout(self):
        create_affiliate(name="John", email="john@example.com")
        payout = create_payout(affiliate_id=1, amount=125.50, payout_status="pending")
        result = process_payout(payout.id, payout_status="paid", payment_date="2025-01-15")
        assert result.payout_status == "paid"
        assert result.payment_date == "2025-01-15"

    def test_list_payouts(self):
        create_affiliate(name="John", email="john@example.com")
        create_payout(affiliate_id=1, amount=100.00, payout_status="paid")
        create_payout(affiliate_id=1, amount=200.00, payout_status="pending")
        payouts = list_payouts(affiliate_id=1)
        assert len(payouts) == 2


class TestPerformanceAnalytics:
    """Test analytics tools."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_get_affiliate_performance(self):
        create_affiliate(name="John Doe", email="john@example.com")
        network = create_affiliate_network("Amazon", "amazon")
        link = create_tracking_link(affiliate_id=1, name="Test Deal", slug="test",
            network_id=1, commission_rate_pct=5.0)
        for _ in range(10):
            record_click(link_id=link.id, source="google")
        for _ in range(2):
            record_conversion(link_id=link.id, conversion_type="purchase",
                revenue=99.99, currency="USD")
        perf = get_affiliate_performance(1)
        assert perf["name"] == "John Doe"
        assert perf["total_clicks"] == 10
        assert perf["total_conversions"] == 2
        assert perf["total_revenue"] == 199.98

    def test_get_click_rate(self):
        create_affiliate(name="John", email="john@example.com")
        link = create_tracking_link(affiliate_id=1, name="Test", slug="test")
        for _ in range(100):
            record_click(link_id=1, source="google")
        rates = get_click_rate(1)
        assert rates["impressions"] == 100
        assert rates["clicks"] == 100
        assert rates["ctr"] == 100.0

    def test_get_commission_summary(self):
        create_affiliate(name="John", email="john@example.com")
        create_commission(affiliate_id=1, rate_pct=5.0, earned_commission=300.00)
        create_payout(affiliate_id=1, amount=250.00, payout_status="paid")
        summary = get_commission_summary()
        assert summary["total_commissions_earned"] == 300.00
        assert summary["total_payouts"] == 250.00
        assert summary["net_earnings"] == 50.00


class TestResourceEndpoints:
    """Test resource endpoints."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_affiliates_resource(self):
        create_affiliate(name="John", email="john@example.com")
        resource = None
        try:
            from server import mcp
            resource = mcp.get_resource("affiliates://all")
        except ImportError:
            pass
        if resource:
            assert "John" in resource

    def test_flush_data(self):
        flush_data()
        result = flush_data()
        assert result["flushed"] is True


class TestBackupRestore:
    """Test backup and restore functionality."""

    def setup_method(self):
        DATA_FILE.write_text("{}")

    def teardown_method(self):
        DATA_FILE.write_text("{}")

    def test_backup_data(self):
        create_affiliate(name="John", email="john@example.com")
        backup = backup_data()
        assert "backup" in backup
        assert "bytes" in backup
        assert Path(backup["backup"]).exists()

    def test_list_backups(self):
        DATA_DIR.mkdir(exist_ok=True)
        backups_dir = DATA_DIR / "backups"
        backups_dir.mkdir(exist_ok=True)
        (backups_dir / "test.json").write_text("{}")
        backups = list_backups()
        assert len(backups) == 1

    def test_restore_backup(self):
        backup_file = DATA_DIR / "backups" / "test-backup.json"
        backup_file.write_text(json.dumps({
            "affiliates": {"1": {"id": 1, "name": "Test", "email": "test@test.com", "created_at": "", "updated_at": ""}},
            "next_affiliate_id": 1,
        }))
        result = restore_backup("test-backup.json")
        assert result["restored"] == "test-backup.json"

    def test_restore_nonexistent_backup(self):
        with pytest.raises(ValueError):
            restore_backup("nonexistent.json")
