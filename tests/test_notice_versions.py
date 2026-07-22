import tempfile
import unittest
from pathlib import Path

from g2b_alert.model.config import AppConfig
from g2b_alert.model.database import G2BDatabase
from g2b_alert.model.entities import Bid
from g2b_alert.model.notice_version_model import compare_latest_versions
from g2b_alert.model.result_model import ResultMonitorService


class NoticeVersionTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = G2BDatabase(Path(self.temp_dir.name) / "versions.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _bid(self, order, close_at, attachments):
        return Bid(
            category="service",
            title="BIS 구축사업",
            bid_no="R26BK01621405",
            bid_ord=order,
            agency="공고기관",
            demand_agency="수원시",
            link="https://example.com",
            budget_amount="1000000",
            bid_end_datetime=close_at,
            opening_datetime="202607241100",
            raw={
                "bidNtceNo": "R26BK01621405",
                "bidNtceOrd": order,
                "ntceSpecFileNm1": attachments,
            },
        )

    def test_new_order_keeps_original_and_updates_current_row(self):
        saved_id, created = self.database.bids.save_bid(
            self._bid("000", "202607201000", "규격서.pdf")
        )
        updated_id, second_created = self.database.bids.save_bid(
            self._bid("001", "202607221000", "규격서.pdf, 추가자료.pdf")
        )

        self.assertTrue(created)
        self.assertFalse(second_created)
        self.assertEqual(saved_id, updated_id)
        saved = self.database.bids.find_saved_bid("R26BK01621405")
        self.assertEqual("001", saved.bid_ord)

        versions = self.database.bids.list_notice_versions(saved_id)
        self.assertEqual(["000", "001"], [version["bid_pbanc_ord"] for version in versions])
        self.assertEqual([0, 1], [version["is_current"] for version in versions])
        comparison = compare_latest_versions(versions)
        labels = {change["label"] for change in comparison["changes"]}
        self.assertIn("입찰 마감일시", labels)
        self.assertIn("첨부파일", labels)
        attachment_change = next(
            change for change in comparison["changes"] if change["field"] == "attachments"
        )
        self.assertEqual("규격서.pdf", attachment_change["before"])
        self.assertEqual("규격서.pdf, 추가자료.pdf", attachment_change["after"])
        self.assertNotIn("http", attachment_change["after"])

    def test_rechecking_same_order_does_not_overwrite_first_raw_json(self):
        saved_id, _ = self.database.bids.save_bid(
            self._bid("000", "202607201000", "최초규격서.pdf")
        )
        self.database.bids.save_bid(
            self._bid("000", "202607211000", "나중규격서.pdf")
        )

        version = self.database.bids.list_notice_versions(saved_id)[0]
        self.assertEqual("202607201000", version["bid_close_at"])
        self.assertIn("최초규격서.pdf", version["raw_json"])
        self.assertNotIn("나중규격서.pdf", version["raw_json"])

    def test_saved_monitor_detects_new_order_and_records_notification_once(self):
        self.database.bids.save_bid(self._bid("000", "202607201000", "규격서.pdf"))

        class BidApi:
            def fetch_bid_by_no(_self, bid_no, category_hint=None):
                self.assertEqual("R26BK01621405", bid_no)
                self.assertEqual("service", category_hint)
                return self._bid("001", "202607221000", "규격서.pdf, 추가자료.pdf")

        class ResultApi:
            @staticmethod
            def fetch_results(_saved_bid):
                return []

        service = ResultMonitorService(
            AppConfig(api_key="key"),
            self.database.bids,
            self.database.results,
            ResultApi(),
            bid_api=BidApi(),
        )

        first = service.check_saved_bids()
        second = service.check_saved_bids()

        self.assertEqual(1, len(first["change_events"]))
        self.assertTrue(first["change_events"][0]["should_notify"])
        self.assertEqual("000", first["change_events"][0]["previous_order"])
        self.assertEqual("001", first["change_events"][0]["current_order"])
        self.assertEqual([], second["change_events"])


if __name__ == "__main__":
    unittest.main()
