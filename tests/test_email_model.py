"""Tests for email alert business rules."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from g2b_alert.model.config import AppConfig
from g2b_alert.model.database import G2BDatabase
from g2b_alert.model.email_model import EmailAlertService
from g2b_alert.model.entities import Bid, BidResult
from g2b_alert.controller.email_delivery_worker import EmailDeliveryWorker


class FakeSMTP:
    sent_messages = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def ehlo(self):
        return None

    def starttls(self, context):
        return None

    def login(self, username, password):
        self.username = username
        self.password = password

    def send_message(self, message):
        self.sent_messages.append(message)


class EmailAlertServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = G2BDatabase(Path(self.temp_dir.name) / "test.db")
        self.email_repository = self.database.email
        self.config = AppConfig(
            keyword_email_enabled=True,
            smtp_username="sender@example.com",
        )
        self.email_repository.sync_keyword_setting("FIDS", True)
        recipient_id = self.email_repository.save_recipient("수신자", "recipient@example.com")
        self.email_repository.set_keyword_recipients([recipient_id])
        self.service = EmailAlertService(self.config, self.email_repository)
        FakeSMTP.sent_messages.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_keyword_event_is_queued_once_and_sent(self):
        bid = Bid(
            category="service",
            title="FIDS 테스트 공고",
            bid_no="R3",
            bid_ord="000",
            agency="기관",
            demand_agency="수요기관",
            link="https://example.com",
        )
        created, count = self.service.queue_keyword_bid(bid, ["FIDS"])
        duplicate_created, duplicate_count = self.service.queue_keyword_bid(bid, ["FIDS"])
        self.assertTrue(created)
        self.assertEqual(1, count)
        self.assertFalse(duplicate_created)
        self.assertEqual(0, duplicate_count)

        delivery = self.email_repository.claim_next_email_delivery()
        worker = EmailDeliveryWorker(self.config, self.email_repository)
        with patch(
            "g2b_alert.controller.email_delivery_worker.get_smtp_password",
            return_value="app-password",
        ), patch(
            "g2b_alert.api.smtp_client.smtplib.SMTP", FakeSMTP
        ):
            worker.send_delivery(delivery)

        summary = self.email_repository.get_email_delivery_summary()
        self.assertEqual(1, summary["sent"])
        self.assertEqual(1, len(FakeSMTP.sent_messages))
        self.assertIn("recipient@example.com", FakeSMTP.sent_messages[0]["To"])
        message = FakeSMTP.sent_messages[0]
        self.assertTrue(message.is_multipart())
        html_body = message.get_body(preferencelist=("html",)).get_content()
        self.assertIn("<table", html_body)
        self.assertIn("신규 입찰공고가 등록되었습니다", html_body)
        self.assertEqual(1, html_body.count(bid.title))
        self.assertIn("나라장터 공고 바로가기", html_body)
        self.assertIn("FIDS", html_body)

    def test_bid_result_email_uses_result_table(self):
        bid = Bid(
            category="service",
            title="개찰결과 테스트 공고",
            bid_no="R26BK01608695",
            bid_ord="001",
            agency="공고기관",
            demand_agency="수요기관",
            link="https://example.com/result",
        )
        saved_bid_id, _ = self.database.bids.save_bid(bid)
        recipient_id = self.email_repository.list_recipients()[0]["id"]
        self.email_repository.set_saved_bid_recipients(saved_bid_id, [recipient_id])
        saved_bid = self.database.bids.list_saved_bids()[0]
        result = BidResult(
            opening_datetime="2026-07-16 10:33:41",
            successful_bidder_name="개찰 1순위 업체",
            business_number="1234567890",
            ranking="1",
            result_status="개찰완료",
        )

        created, count = self.service.queue_bid_result(saved_bid, result)

        self.assertTrue(created)
        self.assertEqual(1, count)
        delivery = self.email_repository.claim_next_email_delivery()
        self.assertIn("<table", delivery["body_html"])
        self.assertIn("개찰·낙찰정보가 확인되었습니다", delivery["body_html"])
        self.assertIn("개찰 1순위 업체", delivery["body_html"])
        self.assertIn("개찰완료", delivery["body_html"])

    def test_bid_change_email_contains_order_and_changed_fields(self):
        saved_id, _ = self.database.bids.save_bid(
            Bid(
                category="service",
                title="변경공고 테스트",
                bid_no="R26BK01621405",
                bid_ord="001",
                agency="기관",
                demand_agency="수원시",
                link="https://example.com/change",
            )
        )
        recipient_id = self.email_repository.list_recipients()[0]["id"]
        self.email_repository.set_saved_bid_recipients(saved_id, [recipient_id])
        saved_bid = self.database.bids.find_saved_bid("R26BK01621405", "001")

        created, count = self.service.queue_bid_change(
            saved_bid,
            "000",
            "001",
            {
                "changes": [
                    {
                        "label": "입찰 마감일시",
                        "before": "2026-07-20 10:00",
                        "after": "2026-07-22 10:00",
                    }
                ]
            },
        )

        self.assertTrue(created)
        self.assertEqual(1, count)
        delivery = self.email_repository.claim_next_email_delivery()
        self.assertIn("[변경공고]", delivery["subject"])
        self.assertIn("000 → 001", delivery["body_html"])
        self.assertIn("입찰 마감일시", delivery["body_html"])


if __name__ == "__main__":
    unittest.main()
