import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from g2b_alert.config_manager import AppConfig
from g2b_alert.database import G2BDatabase
from g2b_alert.email_service import EmailAlertService
from g2b_alert.g2b_client import BidItem


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
        self.config = AppConfig(
            keyword_email_enabled=True,
            smtp_username="sender@example.com",
        )
        self.database.sync_keyword_setting("FIDS", True)
        recipient_id = self.database.save_recipient("수신자", "recipient@example.com")
        self.database.set_keyword_recipients([recipient_id])
        self.service = EmailAlertService(self.config, self.database)
        FakeSMTP.sent_messages.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_keyword_event_is_queued_once_and_sent(self):
        bid = BidItem(
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

        delivery = self.database.claim_next_email_delivery()
        with patch("g2b_alert.email_service.get_smtp_password", return_value="app-password"), patch(
            "g2b_alert.email_service.smtplib.SMTP", FakeSMTP
        ):
            self.service._send_delivery(delivery)

        summary = self.database.get_email_delivery_summary()
        self.assertEqual(1, summary["sent"])
        self.assertEqual(1, len(FakeSMTP.sent_messages))
        self.assertIn("recipient@example.com", FakeSMTP.sent_messages[0]["To"])


if __name__ == "__main__":
    unittest.main()
