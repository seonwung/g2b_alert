import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from g2b_alert.api import bid_api
from g2b_alert.api.bid_api import G2BClient
from g2b_alert.api.contract_process_api import ContractProcessApi
from g2b_alert.api.pre_spec_api import PreSpecificationApi
from g2b_alert.api.result_api import ResultApiService
from g2b_alert.model.config import AppConfig
from g2b_alert.model.database import G2BDatabase
from g2b_alert.model.email_model import EmailAlertService
from g2b_alert.model.entities import Bid, BidResult
from g2b_alert.model.keyword_matcher import (
    match_keyword_rule_details,
    parse_keyword_condition_rules,
)


def api_response(items, total_count):
    return {
        "response": {
            "body": {
                "totalCount": total_count,
                "items": items,
            }
        }
    }


class TemporaryDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = G2BDatabase(
            Path(self.temp_dir.name) / "g2b-alert-test.db"
        )

    def tearDown(self):
        self.temp_dir.cleanup()


class DeletedNoticeRaceTests(TemporaryDatabaseTestCase):
    def test_result_and_notification_are_skipped_after_notice_deletion(self):
        bid = Bid("service", "테스트 공고", "N1", "000", "", "", "")
        saved_id, _created = self.database.bids.save_bid(bid)
        saved_bid = self.database.bids.find_saved_bid("N1", "000")
        self.database.bids.delete_saved_bid(saved_id)

        result = BidResult(
            result_type="개찰",
            successful_bidder_name="테스트 업체",
            result_status="완료",
        )
        self.assertFalse(self.database.results.save_result(saved_bid, result))
        self.assertFalse(
            self.database.results.record_notification(
                saved_id,
                "bid_result",
                result.result_key,
                "테스트",
            )
        )

        with self.database.connect() as connection:
            result_count = connection.execute(
                "SELECT COUNT(*) AS count FROM bid_results"
            ).fetchone()["count"]
            notification_count = connection.execute(
                "SELECT COUNT(*) AS count FROM notification_history"
            ).fetchone()["count"]
        self.assertEqual(result_count, 0)
        self.assertEqual(notification_count, 0)


class KeywordCardMatchingTests(unittest.TestCase):
    @staticmethod
    def _rule(rule_id, keyword, operator="or"):
        return {
            "id": rule_id,
            "name": rule_id,
            "keyword": keyword,
            "operator": operator,
            "categories": ["service"],
            "targets": ["bid_lifecycle"],
            "enabled": True,
        }

    def test_cards_are_combined_with_or(self):
        rules = parse_keyword_condition_rules(
            [
                self._rule("smart-city", "스마트, 도시", "and"),
                self._rule("memorial-event", "순국선열, 기념식", "and"),
            ]
        )
        bid = Bid(
            "service",
            "제87회 순국선열의 날 기념식 대행용역",
            "N-CARD-1",
            "000",
            "",
            "",
            "",
        )

        match = match_keyword_rule_details(bid, rules)

        self.assertIsNotNone(match)
        self.assertEqual(match.rule_ids, ("memorial-event",))
        self.assertEqual(match.keywords, ("순국선열", "기념식"))

    def test_and_keywords_inside_one_card_must_all_match(self):
        rules = parse_keyword_condition_rules(
            [self._rule("smart-city", "스마트, 도시", "and")]
        )
        bid = Bid("service", "스마트 구축 용역", "N-CARD-2", "000", "", "", "")

        self.assertIsNone(match_keyword_rule_details(bid, rules))

    def test_exclude_card_still_blocks_all_positive_cards(self):
        rules = parse_keyword_condition_rules(
            [
                self._rule("smart", "스마트"),
                self._rule("exclude-cancelled", "취소", "exclude"),
            ]
        )
        bid = Bid(
            "service",
            "스마트 구축 용역 취소공고",
            "N-CARD-3",
            "000",
            "",
            "",
            "",
        )

        self.assertIsNone(match_keyword_rule_details(bid, rules))


class EmailRecipientDeliveryTests(TemporaryDatabaseTestCase):
    def test_existing_event_adds_only_new_recipient_with_own_snapshot(self):
        first_recipient = self.database.email.save_recipient(
            "첫 수신자",
            "first@example.com",
        )
        second_recipient = self.database.email.save_recipient(
            "둘째 수신자",
            "second@example.com",
        )
        rules = [
            {
                "id": "rule-1",
                "name": "첫 조건",
                "keyword": "alpha",
                "operator": "or",
                "categories": ["service"],
                "targets": ["bid_lifecycle"],
                "enabled": True,
            },
            {
                "id": "rule-2",
                "name": "둘째 조건",
                "keyword": "beta",
                "operator": "or",
                "categories": ["service"],
                "targets": ["bid_lifecycle"],
                "enabled": True,
            },
        ]
        self.database.email.sync_keyword_rules(rules)
        self.database.email.set_keyword_rule_recipients(
            "rule-1",
            [first_recipient],
        )
        self.database.email.set_keyword_rule_recipients(
            "rule-2",
            [second_recipient],
        )
        bid = Bid(
            "service",
            "alpha beta 공고",
            "N2",
            "000",
            "",
            "",
            "https://example.com",
        )
        service = EmailAlertService(AppConfig(), self.database.email)

        self.assertEqual(
            service.queue_keyword_bid(bid, ["alpha"], ["rule-1"]),
            (True, 1),
        )
        self.assertEqual(
            service.queue_keyword_bid(bid, ["beta"], ["rule-2"]),
            (True, 1),
        )
        self.assertEqual(
            service.queue_keyword_bid(bid, ["beta"], ["rule-2"]),
            (False, 0),
        )

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT recipient_email, body
                FROM email_deliveries
                ORDER BY id
                """
            ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertIn("매칭 키워드: alpha", rows[0]["body"])
        self.assertNotIn("매칭 키워드: beta", rows[0]["body"])
        self.assertIn("매칭 키워드: beta", rows[1]["body"])

        first_delivery = self.database.email.claim_next_email_delivery()
        self.assertIn("매칭 키워드: alpha", first_delivery["body"])
        self.database.email.mark_email_delivery_sent(first_delivery["id"])
        second_delivery = self.database.email.claim_next_email_delivery()
        self.assertIn("매칭 키워드: beta", second_delivery["body"])


class EmailDeliveryMigrationTests(unittest.TestCase):
    def test_legacy_delivery_rows_receive_message_snapshots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "legacy-email.db"
            connection = sqlite3.connect(database_path)
            connection.executescript(
                """
                CREATE TABLE email_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_key TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    source_ref TEXT,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    body_html TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE email_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    recipient_name TEXT NOT NULL,
                    recipient_email TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    next_attempt_at TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(event_id, recipient_id)
                );
                INSERT INTO email_events (
                    event_key, event_type, source_ref, subject, body,
                    body_html, created_at
                ) VALUES (
                    'legacy:1', 'keyword_bid', 'N1', '기존 제목',
                    '기존 본문', '<p>기존 본문</p>', '2026-01-01T00:00:00'
                );
                INSERT INTO email_deliveries (
                    event_id, recipient_id, recipient_name, recipient_email,
                    status, retry_count, created_at, updated_at
                ) VALUES (
                    1, 1, '기존 수신자', 'legacy@example.com',
                    'pending', 0, '2026-01-01T00:00:00',
                    '2026-01-01T00:00:00'
                );
                """
            )
            connection.commit()
            connection.close()

            database = G2BDatabase(database_path)
            delivery = database.email.claim_next_email_delivery()

        self.assertEqual(delivery["subject"], "기존 제목")
        self.assertEqual(delivery["body"], "기존 본문")
        self.assertEqual(delivery["body_html"], "<p>기존 본문</p>")


class PaginationTests(unittest.TestCase):
    def test_common_page_fetcher_reads_every_page(self):
        calls = []

        def fake_request(_url, params, _timeout, _label):
            page = int(params["pageNo"])
            calls.append(page)
            start = (page - 1) * 100
            end = min(start + 100, 250)
            items = [{"row": index} for index in range(start, end)]
            return api_response(items, 250)

        with patch.object(bid_api, "request_json", side_effect=fake_request):
            items, total_count = bid_api.fetch_all_pages(
                "https://example.com",
                {"numOfRows": "100"},
                30,
                "테스트 API",
            )

        self.assertEqual(calls, [1, 2, 3])
        self.assertEqual(total_count, 250)
        self.assertEqual(len(items), 250)

    def test_direct_bid_lookup_uses_all_pages(self):
        items = [
            {
                "bidNtceNo": f"N{index}",
                "bidNtceOrd": "000",
                "bidNtceNm": f"공고 {index}",
            }
            for index in range(205)
        ]
        with patch(
            "g2b_alert.api.bid_api.fetch_all_pages",
            return_value=(items, len(items)),
        ) as fetch:
            found = G2BClient("key").fetch_bid_by_no(
                "N204-000",
                category_hint="service",
            )
        self.assertEqual(found.bid_no, "N204")
        fetch.assert_called_once()

    def test_result_lookup_uses_all_pages(self):
        items = [
            {
                "rsltTyNm": "개찰",
                "bizrno": f"{index:010d}",
                "entrpsNm": f"업체 {index}",
            }
            for index in range(205)
        ]
        saved_bid = type(
            "SavedBidStub",
            (),
            {
                "category": "service",
                "bid_no": "N3",
                "bid_ord": "000",
            },
        )()
        with patch(
            "g2b_alert.api.result_api.fetch_all_pages",
            return_value=(items, len(items)),
        ) as fetch:
            results = ResultApiService("key").fetch_results(saved_bid)
        self.assertEqual(len(results), 205)
        fetch.assert_called_once()

    def test_contract_process_lookup_uses_all_pages(self):
        items = [
            {
                "bidNtceNo": f"N{index}",
                "bidNtceOrd": f"{index:03d}",
            }
            for index in range(205)
        ]
        with patch(
            "g2b_alert.api.contract_process_api.fetch_all_pages",
            return_value=(items, len(items)),
        ) as fetch:
            found = ContractProcessApi("key").find_bid_for_pre_specification(
                "P1",
                "service",
            )
        self.assertEqual(found.bid_no, "N204")
        fetch.assert_called_once()

    def test_prespec_opinion_lookup_uses_all_pages(self):
        items = [
            {
                "opninNo": str(index),
                "opninTitl": f"의견 {index}",
            }
            for index in range(205)
        ]
        with patch(
            "g2b_alert.api.pre_spec_api.fetch_all_pages",
            return_value=(items, len(items)),
        ) as fetch:
            opinions = PreSpecificationApi("key").fetch_opinions(
                "service",
                "P2",
            )
        self.assertEqual(len(opinions), 205)
        fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
