import tempfile
"""Tests for result-monitoring business rules."""

import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from g2b_alert.api.http_client import ApiRequestError
from g2b_alert.api.result_api import ResultApiService
from g2b_alert.model.config import AppConfig
from g2b_alert.model.database import G2BDatabase
from g2b_alert.model.entities import Bid, BidResult, SavedBid
from g2b_alert.model.result_model import ResultMonitorService


class ResultErrorTrackingTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = G2BDatabase(Path(self.temp_dir.name) / "test.db")
        self.database.bids.save_bid(
            Bid(
                category="service",
                title="테스트 공고",
                bid_no="R-1",
                bid_ord="000",
                agency="기관",
                demand_agency="수요기관",
                link="",
            )
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_repeated_500_is_retried_but_detailed_log_is_compressed(self):
        counts = {}
        error = ApiRequestError("나라장터 낙찰정보 API", "http", status_code=500)
        result_api = Mock()
        result_api.fetch_results.side_effect = [error, error]
        monitor = ResultMonitorService(
            AppConfig(api_key="test-key"),
            bid_repository=self.database.bids,
            result_repository=self.database.results,
            result_api=result_api,
            error_counts=counts,
        )
        first = monitor.check_saved_bids()
        second = monitor.check_saved_bids()

        self.assertEqual(2, result_api.fetch_results.call_count)
        self.assertEqual(1, first["reports"][0]["failure_count"])
        self.assertTrue(first["reports"][0]["should_log_detail"])
        self.assertEqual(2, second["reports"][0]["failure_count"])
        self.assertFalse(second["reports"][0]["should_log_detail"])

    def test_result_api_normalizes_external_json_to_entity(self):
        result = ResultApiService("test-key")._normalize(
            {
                "sucsfbidCorpNm": "테스트 업체",
                "sucsfbidBizrno": "123-45-67890",
                "sucsfbidAmt": "1000000",
            }
        )
        self.assertIsInstance(result, BidResult)
        self.assertEqual("테스트 업체", result.successful_bidder_name)
        self.assertTrue(result.result_key)

    def test_result_api_normalizes_current_opening_result_fields(self):
        result = ResultApiService("test-key")._normalize(
            {
                "opengCorpInfo": "개찰 1순위 업체^1234567890^대표자",
                "opengDt": "2026-07-13 18:00:00",
                "inptDt": "2026-07-16 10:33:41",
                "progrsDivCdNm": "개찰완료",
            }
        )
        self.assertEqual("개찰 1순위 업체", result.successful_bidder_name)
        self.assertEqual("1234567890", result.business_number)
        self.assertEqual("2026-07-16 10:33:41", result.opening_datetime)
        self.assertEqual("개찰완료", result.result_status)

    @patch("g2b_alert.api.result_api.request_json")
    def test_result_api_uses_current_service_path_and_bid_number_query(self, request_json):
        request_json.return_value = {"response": {"body": {"items": []}}}
        saved_bid = SimpleNamespace(
            category="service",
            bid_no="R26BK01608695",
            bid_ord="001",
        )

        ResultApiService("test-key").fetch_results(saved_bid)

        url, params, *_ = request_json.call_args.args
        self.assertEqual(
            "https://apis.data.go.kr/1230000/as/ScsbidInfoService/getOpengResultListInfoServc",
            url,
        )
        self.assertEqual("4", params["inqryDiv"])
        self.assertEqual("R26BK01608695", params["bidNtceNo"])
        self.assertEqual("001", params["bidNtceOrd"])


class SavedBidProgressStatusTest(unittest.TestCase):
    def _saved_bid(self, **overrides):
        values = {
            "id": 1,
            "bid_no": "R-1",
            "bid_ord": "000",
            "category": "service",
            "title": "테스트 공고",
            "agency": "기관",
            "demand_agency": "수요기관",
            "bid_method": "",
            "contract_method": "",
            "budget_amount": "",
            "bid_start_datetime": "202607161000",
            "bid_end_datetime": "202607161200",
            "opening_datetime": "202607161300",
            "link": "",
            "raw": {},
            "saved_at": "",
            "updated_at": "",
            "monitoring_enabled": True,
            "status": "saved",
        }
        values.update(overrides)
        return SavedBid(**values)

    def test_progress_is_derived_from_bid_schedule(self):
        bid = self._saved_bid()
        self.assertEqual("입찰 개시 전", bid.progress_status(datetime(2026, 7, 16, 9, 0)))
        self.assertEqual("입찰 진행 중", bid.progress_status(datetime(2026, 7, 16, 11, 0)))
        self.assertEqual("개찰 대기", bid.progress_status(datetime(2026, 7, 16, 12, 30)))
        self.assertEqual("개찰 결과 대기", bid.progress_status(datetime(2026, 7, 16, 13, 30)))

    def test_api_result_status_has_priority(self):
        bid = self._saved_bid(current_result_status="낙찰자 선정")
        self.assertEqual("낙찰자 선정", bid.progress_status(datetime(2026, 7, 16, 11, 0)))

    def test_stage_label_is_textual_and_result_driven(self):
        self.assertEqual("입찰공고", self._saved_bid().stage_label())
        self.assertEqual(
            "개찰결과",
            self._saved_bid(current_result_status="개찰완료").stage_label(),
        )
        self.assertEqual(
            "낙찰결과",
            self._saved_bid(current_result_status="낙찰자 선정").stage_label(),
        )
        self.assertEqual(
            "유찰·취소",
            self._saved_bid(current_result_status="유찰").stage_label(),
        )

if __name__ == "__main__":
    unittest.main()
