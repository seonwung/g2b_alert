import tempfile
import unittest
from pathlib import Path

from g2b_alert.database import G2BDatabase
from g2b_alert.g2b_client import BidItem


class EmailDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = G2BDatabase(Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_recipient_mappings_and_duplicate_event(self):
        self.database.sync_keyword_setting("FIDS", True)
        recipient_id = self.database.save_recipient("테스트", "test@example.com")
        self.database.set_keyword_recipients([recipient_id])

        keyword_recipients = self.database.get_keyword_email_recipients()
        self.assertEqual(1, len(keyword_recipients))

        bid = BidItem(
            category="service",
            title="테스트 공고",
            bid_no="R1",
            bid_ord="000",
            agency="기관",
            demand_agency="수요기관",
            link="https://example.com",
        )
        saved_bid_id, _ = self.database.save_bid(bid)
        self.database.set_saved_bid_recipients(saved_bid_id, [recipient_id])
        self.assertEqual({recipient_id}, self.database.get_saved_bid_recipient_ids(saved_bid_id))

        created, delivery_count = self.database.create_email_event(
            "keyword_bid:R1-000",
            "keyword_bid",
            "R1-000",
            "제목",
            "본문",
            keyword_recipients,
        )
        self.assertTrue(created)
        self.assertEqual(1, delivery_count)

        duplicate_created, duplicate_count = self.database.create_email_event(
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
        self.database.sync_keyword_setting("FIDS", True)
        recipient_id = self.database.save_recipient("테스트", "test@example.com")
        self.database.set_keyword_recipients([recipient_id])
        self.database.create_email_event(
            "keyword_bid:R2-000",
            "keyword_bid",
            "R2-000",
            "제목",
            "본문",
            self.database.get_keyword_email_recipients(),
        )

        for attempt in range(3):
            delivery = self.database.claim_next_email_delivery()
            self.assertIsNotNone(delivery)
            self.database.mark_email_delivery_failed(
                delivery["id"],
                f"테스트 오류 {attempt + 1}",
                max_retries=3,
                retry_delay_seconds=0,
            )
        summary = self.database.get_email_delivery_summary()
        self.assertEqual(0, summary["pending"])
        self.assertEqual(1, summary["failed"])
        history = self.database.list_recent_email_deliveries(1)
        self.assertEqual(3, history[0]["retry_count"])


if __name__ == "__main__":
    unittest.main()
