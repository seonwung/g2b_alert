"""Tests for email persistence repositories."""

import tempfile
import unittest
from pathlib import Path

from g2b_alert.model.database import G2BDatabase
from g2b_alert.model.entities import Bid, SavedBid


class RepositoryIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = G2BDatabase(Path(self.temp_dir.name) / "test.db")
        self.bid_repository = self.database.bids
        self.email_repository = self.database.email

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_recipient_mappings_and_duplicate_event(self):
        self.email_repository.sync_keyword_setting("FIDS", True)
        recipient_id = self.email_repository.save_recipient("테스트", "test@example.com")
        self.email_repository.set_keyword_recipients([recipient_id])

        keyword_recipients = self.email_repository.get_keyword_email_recipients()
        self.assertEqual(1, len(keyword_recipients))

        bid = Bid(
            category="service",
            title="테스트 공고",
            bid_no="R1",
            bid_ord="000",
            agency="기관",
            demand_agency="수요기관",
            link="https://example.com",
        )
        saved_bid_id, _ = self.bid_repository.save_bid(bid)
        saved_bid = self.bid_repository.list_saved_bids()[0]
        self.assertIsInstance(saved_bid, SavedBid)
        self.assertEqual("R1", saved_bid.bid_no)
        self.email_repository.set_saved_bid_recipients(saved_bid_id, [recipient_id])
        self.assertEqual({recipient_id}, self.email_repository.get_saved_bid_recipient_ids(saved_bid_id))

        created, delivery_count = self.email_repository.create_email_event(
            "keyword_bid:R1-000",
            "keyword_bid",
            "R1-000",
            "제목",
            "본문",
            keyword_recipients,
        )
        self.assertTrue(created)
        self.assertEqual(1, delivery_count)

        duplicate_created, duplicate_count = self.email_repository.create_email_event(
            "keyword_bid:R1-000",
            "keyword_bid",
            "R1-000",
            "제목",
            "본문",
            keyword_recipients,
        )
        self.assertFalse(duplicate_created)
        self.assertEqual(0, duplicate_count)

    def test_delivery_retry_state(self):
        self.email_repository.sync_keyword_setting("FIDS", True)
        recipient_id = self.email_repository.save_recipient("테스트", "test@example.com")
        self.email_repository.set_keyword_recipients([recipient_id])
        self.email_repository.create_email_event(
            "keyword_bid:R2-000",
            "keyword_bid",
            "R2-000",
            "제목",
            "본문",
            self.email_repository.get_keyword_email_recipients(),
        )

        for attempt in range(3):
            delivery = self.email_repository.claim_next_email_delivery()
            self.assertIsNotNone(delivery)
            self.email_repository.mark_email_delivery_failed(
                delivery["id"],
                f"테스트 오류 {attempt + 1}",
                max_retries=3,
                retry_delay_seconds=0,
            )
        summary = self.email_repository.get_email_delivery_summary()
        self.assertEqual(0, summary["pending"])
        self.assertEqual(1, summary["failed"])
        history = self.email_repository.list_recent_email_deliveries(1)
        self.assertEqual(3, history[0]["retry_count"])

    def test_resets_bid_monitor_state(self):
        self.bid_repository.mark_bid_seen("BID-1-000")
        self.bid_repository.mark_bid_seen("BID-2-000")
        self.bid_repository.set_last_check_time("2026-07-13T15:00:00")
        self.assertTrue(self.bid_repository.is_bid_seen("BID-1-000"))
        self.assertEqual("2026-07-13T15:00:00", self.bid_repository.get_last_check_time())

        deleted = self.bid_repository.reset_bid_monitor_state()
        self.assertEqual(3, deleted)
        self.assertFalse(self.bid_repository.is_bid_seen("BID-1-000"))
        self.assertFalse(self.bid_repository.is_bid_seen("BID-2-000"))
        self.assertEqual("", self.bid_repository.get_last_check_time())

    def test_persists_result_monitor_success_across_repository_instances(self):
        checked_at = "2026-07-13T18:00:00"
        self.bid_repository.set_result_monitor_last_success_time(checked_at)

        reopened = G2BDatabase(self.database.db_path)

        self.assertEqual(checked_at, reopened.bids.get_result_monitor_last_success_time())

    def test_finds_duplicate_and_pauses_tracking_without_deleting_history(self):
        saved_id, _ = self.bid_repository.save_bid(
            Bid(
                category="service",
                title="추적 일시정지 테스트 공고",
                bid_no="R26BK01621405",
                bid_ord="001",
                agency="기관",
                demand_agency="수요기관",
                link="",
            )
        )

        found = self.bid_repository.find_saved_bid("R26BK01621405", "001")
        self.assertEqual(saved_id, found.id)

        self.bid_repository.set_monitoring_enabled(saved_id, False)
        paused = self.bid_repository.find_saved_bid("R26BK01621405", "001")
        self.assertEqual("saved", paused.status)
        self.assertFalse(paused.monitoring_enabled)

        self.bid_repository.set_monitoring_enabled(saved_id, True)
        restored = self.bid_repository.find_saved_bid("R26BK01621405", "001")
        self.assertEqual("saved", restored.status)
        self.assertTrue(restored.monitoring_enabled)

    def test_recipient_address_book_fields_are_persisted(self):
        recipient_id = self.email_repository.save_recipient(
            "홍길동",
            "hong@example.com",
            organization="교통정보팀",
            memo="변경공고 담당",
            is_default=True,
        )

        recipient = next(
            row for row in self.email_repository.list_recipients() if row["id"] == recipient_id
        )
        self.assertEqual("교통정보팀", recipient["organization"])
        self.assertEqual("변경공고 담당", recipient["memo"])
        self.assertEqual(1, recipient["is_default"])

        self.email_repository.save_recipient(
            "홍길동",
            "hong@example.com",
            recipient_id,
            organization="스마트도시팀",
            memo="낙찰결과 담당",
            is_default=False,
        )
        updated = next(
            row for row in self.email_repository.list_recipients() if row["id"] == recipient_id
        )
        self.assertEqual("스마트도시팀", updated["organization"])
        self.assertEqual("낙찰결과 담당", updated["memo"])
        self.assertEqual(0, updated["is_default"])


if __name__ == "__main__":
    unittest.main()
