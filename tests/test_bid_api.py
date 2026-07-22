"""Tests for the bid API adapter."""

import unittest
from unittest.mock import patch

from g2b_alert.api.bid_api import (
    G2BClient,
    extract_bid_reference,
    parse_total_count,
    split_bid_reference,
)


class SplitBidReferenceTests(unittest.TestCase):
    def test_splits_three_digit_order_from_full_reference(self):
        self.assertEqual(
            split_bid_reference("R25BK01234567-000"),
            ("R25BK01234567", "000"),
        )

    def test_keeps_bid_number_when_order_is_omitted(self):
        self.assertEqual(
            split_bid_reference("R25BK01234567"),
            ("R25BK01234567", ""),
        )

    def test_ignores_whitespace_from_pasted_reference(self):
        self.assertEqual(
            split_bid_reference("  R25BK01234567 - 001  "),
            ("R25BK01234567", "001"),
        )

    def test_reads_total_count_for_truncation_warning(self):
        data = {"response": {"body": {"totalCount": "134"}}}
        self.assertEqual(134, parse_total_count(data))

    def test_extracts_reference_from_g2b_query_url(self):
        url = (
            "https://www.g2b.go.kr/link?"
            "bidNtceNo=R26BK01621405&bidNtceOrd=001"
        )
        self.assertEqual("R26BK01621405-001", extract_bid_reference(url))

    def test_extracts_reference_from_pasted_url_text(self):
        self.assertEqual(
            "R26BK01621405-000",
            extract_bid_reference(
                "https://www.g2b.go.kr/pt/menu/selectSubFrame.do?notice=R26BK01621405-000"
            ),
        )

    @patch("g2b_alert.api.bid_api.request_json")
    def test_lookup_without_order_selects_highest_order_and_uses_category_hint(self, request_json):
        request_json.return_value = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bidNtceNo": "R26BK01621405",
                            "bidNtceOrd": "000",
                            "bidNtceNm": "최초 공고",
                        },
                        {
                            "bidNtceNo": "R26BK01621405",
                            "bidNtceOrd": "002",
                            "bidNtceNm": "최신 공고",
                        },
                        {
                            "bidNtceNo": "R26BK01621405",
                            "bidNtceOrd": "001",
                            "bidNtceNm": "중간 공고",
                        },
                    ]
                }
            }
        }

        bid = G2BClient("key").fetch_bid_by_no(
            "R26BK01621405",
            category_hint="service",
        )

        self.assertEqual("002", bid.bid_ord)
        self.assertEqual("최신 공고", bid.title)
        self.assertEqual(1, request_json.call_count)


if __name__ == "__main__":
    unittest.main()
