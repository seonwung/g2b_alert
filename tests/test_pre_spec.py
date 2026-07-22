import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from g2b_alert.api.contract_process_api import ContractProcessApi
from g2b_alert.api.pre_spec_api import (
    PreSpecificationApi,
    complete_opinion_attachment_url,
    extract_pre_spec_reference,
    filename_from_content_disposition,
    looks_like_pre_spec_reference,
)
from g2b_alert.model.bid_model import BidMonitorService
from g2b_alert.model.config import AppConfig
from g2b_alert.model.database import G2BDatabase
from g2b_alert.model.entities import Bid, PreSpecification
from g2b_alert.model.keyword_matcher import parse_keyword_condition_rules, parse_keyword_rules
from g2b_alert.model.result_model import ResultMonitorService


class PreSpecificationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = G2BDatabase(Path(self.temp_dir.name) / "prespec.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("g2b_alert.api.pre_spec_api.request_json")
    def test_official_prespec_endpoint_and_normalization(self, request_json):
        request_json.return_value = {
            "response": {
                "body": {
                    "totalCount": 1,
                    "items": [
                        {
                            "bfSpecRgstNo": "356759",
                            "bfSpecNm": "수원 BIS 구축",
                            "ordInsttNm": "수원시",
                            "dminsttNm": "수원시",
                            "asignBdgtAmt": "100000000",
                            "opnEndDt": "202607201800",
                        }
                    ],
                }
            }
        }
        api = PreSpecificationApi("key")
        rows = api.fetch_pre_specifications(
            "service",
            datetime(2026, 7, 16, 0, 0),
            datetime(2026, 7, 16, 23, 59),
        )

        url, params, *_ = request_json.call_args.args
        self.assertTrue(url.endswith("/getPublicPrcureThngInfoServcPPSSrch"))
        self.assertEqual("1", params["inqryDiv"])
        self.assertEqual("202607160000", params["inqryBgnDt"])
        self.assertEqual("356759", rows[0].pre_spec_no)
        self.assertEqual("수원 BIS 구축", rows[0].title)

    @patch("g2b_alert.api.pre_spec_api.request_json")
    def test_normalizes_current_prespec_response_fields(self, request_json):
        request_json.return_value = {
            "response": {
                "body": {
                    "totalCount": 1,
                    "items": [
                        {
                            "bfSpecRgstNo": "R26BD00251411",
                            "prdctClsfcNoNm": "비긴급 상담 시스템 구축 사업 감리",
                            "orderInsttNm": "국민권익위원회",
                            "rlDminsttNm": "정부합동민원센터",
                            "asignBdgtAmt": "85000000",
                            "rgstDt": "2026-07-13 14:11:48",
                            "opninRgstClseDt": "2026-07-18 23:59:00",
                            "specDocFileUrl1": "https://www.g2b.go.kr/specification-file",
                        }
                    ],
                }
            }
        }

        row = PreSpecificationApi("key").fetch_pre_specifications(
            "service",
            datetime(2026, 7, 13, 0, 0),
            datetime(2026, 7, 13, 23, 59),
        )[0]

        self.assertEqual("비긴급 상담 시스템 구축 사업 감리", row.title)
        self.assertEqual("국민권익위원회", row.agency)
        self.assertEqual("정부합동민원센터", row.demand_agency)
        self.assertEqual("2026-07-18 23:59:00", row.opinion_end_at)
        self.assertEqual("https://www.g2b.go.kr/specification-file", row.link)

    def test_extracts_prespec_number_from_file_url(self):
        url = (
            "https://www.g2b.go.kr/pn/pnz/pnza/UntyAtchFile/downloadFile.do"
            "?bfSpecRegNo=R26BD00251411&fileType=BFDTL&fileSeq=1"
        )

        self.assertEqual("R26BD00251411", extract_pre_spec_reference(url))
        self.assertTrue(looks_like_pre_spec_reference(url))
        self.assertFalse(looks_like_pre_spec_reference("R26BK01621405-000"))

    def test_decodes_korean_filename_from_download_header(self):
        header = "attachment; filename*=UTF-8''%EA%B7%9C%EA%B2%A9%EC%84%9C.pdf"

        self.assertEqual("규격서.pdf", filename_from_content_disposition(header))

    def test_repairs_incomplete_opinion_attachment_url(self):
        source = (
            "https://www.g2b.go.kr/pn/pnz/pnza/UntyAtchFile/downloadFile.do"
            "?bfSpecRegNo=R26BD00249496&fileType=BFOPNN&fileSeq=1"
        )

        repaired = complete_opinion_attachment_url(source, "3")

        self.assertIn("fileType=BFOPNN", repaired)
        self.assertIn("opnnSqno=3", repaired)
        self.assertEqual(repaired, complete_opinion_attachment_url(repaired, "3"))

    @patch.object(PreSpecificationApi, "_resolve_download_filename")
    @patch("g2b_alert.api.pre_spec_api.request_json")
    def test_detail_fetches_opinions_and_resolves_attachment_names(
        self, request_json, resolve_filename
    ):
        request_json.side_effect = [
            {
                "response": {
                    "body": {
                        "totalCount": 1,
                        "items": [
                            {
                                "bfSpecRgstNo": "R26BD00244936",
                                "prdctClsfcNoNm": "탄소중립 설비투자",
                                "specDocFileUrl1": "https://example.com/main",
                            }
                        ],
                    }
                }
            },
            {
                "response": {
                    "body": {
                        "totalCount": 1,
                        "items": [
                            {
                                "bfSpecRgstNo": "R26BD00244936",
                                "opninNo": "1",
                                "rplyNo": "0",
                                "opninTitl": "규격 검토 의견",
                                "opninCntnts": "요구 규격을 확인해 주세요.",
                                "specDocOpninFileUrl1": (
                                    "https://www.g2b.go.kr/downloadFile.do"
                                    "?bfSpecRegNo=R26BD00244936&fileType=BFOPNN&fileSeq=1"
                                ),
                            }
                        ],
                    }
                }
            },
        ]
        resolve_filename.side_effect = ["규격서.pdf", "의견서.hwp"]

        detail = PreSpecificationApi("key").fetch_pre_specification_detail(
            "R26BD00244936", "service"
        )

        self.assertEqual("규격서.pdf", detail["raw"]["specDocFileNm1"])
        self.assertEqual("규격 검토 의견", detail["opinions"][0]["title"])
        self.assertEqual(
            "의견서.hwp",
            detail["opinions"][0]["raw"]["specDocOpninFileNm1"],
        )
        self.assertIn(
            "opnnSqno=1",
            detail["opinions"][0]["raw"]["specDocOpninFileUrl1"],
        )
        opinion_url, opinion_params, *_ = request_json.call_args_list[1].args
        self.assertTrue(opinion_url.endswith("/getPublicPrcureThngOpinionInfoServc"))
        self.assertEqual("2", opinion_params["inqryDiv"])

    @patch("g2b_alert.api.pre_spec_api.request_json")
    def test_fetches_prespec_directly_by_registration_number(self, request_json):
        request_json.side_effect = [
            {"response": {"body": {"totalCount": 0, "items": []}}},
            {
                "response": {
                    "body": {
                        "totalCount": 1,
                        "items": [
                            {
                                "bfSpecRgstNo": "R26BD00251411",
                                "prdctClsfcNoNm": "탄소중립 설비투자",
                            }
                        ],
                    }
                }
            },
        ]

        row = PreSpecificationApi("key").fetch_pre_specification_by_no(
            "R26BD00251411"
        )

        self.assertEqual("R26BD00251411", row.pre_spec_no)
        self.assertEqual("goods", row.category)
        self.assertEqual(2, request_json.call_count)
        for call in request_json.call_args_list:
            _url, params, *_ = call.args
            self.assertEqual("2", params["inqryDiv"])
            self.assertEqual("R26BD00251411", params["bfSpecRgstNo"])

    @patch("g2b_alert.api.contract_process_api.request_json")
    def test_contract_process_finds_bid_from_prespec_number(self, request_json):
        request_json.return_value = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bfSpecRgstNo": "356759",
                            "bidNtceNo": "R26BK01621405",
                            "bidNtceOrd": "001",
                            "bidNtceNm": "수원 BIS 구축",
                        }
                    ]
                }
            }
        }

        bid = ContractProcessApi("key").find_bid_for_pre_specification(
            "356759",
            "service",
        )

        _url, params, *_ = request_json.call_args.args
        self.assertEqual("356759", params["bfSpecRgstNo"])
        self.assertEqual("R26BK01621405", bid.bid_no)
        self.assertEqual("001", bid.bid_ord)

    def test_keyword_monitor_includes_prespec_results(self):
        class BidApi:
            last_total_count = 0

            @staticmethod
            def fetch_bids(_category, _begin, _end):
                return []

        class PreSpecApi:
            last_total_count = 1

            @staticmethod
            def fetch_pre_specifications(_category, _begin, _end):
                return [
                    PreSpecification(
                        category="service",
                        title="수원 BIS 구축",
                        pre_spec_no="356759",
                        agency="수원시",
                        demand_agency="수원시",
                        link="",
                    )
                ]

        config = AppConfig(
            selected_categories=["service"],
            prespec_search_enabled=True,
            bootstrap_minutes=30,
            overlap_minutes=5,
        )
        summary = BidMonitorService(
            BidApi(),
            self.database.bids,
            pre_spec_api=PreSpecApi(),
        ).check_once(
            config,
            parse_keyword_rules("수원", "BIS"),
            checked_at=datetime(2026, 7, 16, 12, 0),
        )

        self.assertEqual(1, summary["new_alert_count"])
        self.assertEqual("356759", summary["alerts"][0]["bid"].pre_spec_no)

    def test_prespec_only_rule_does_not_call_bid_api(self):
        class BidApi:
            @staticmethod
            def fetch_bids(_category, _begin, _end):
                raise AssertionError("사전규격 전용 규칙이 입찰공고 API를 호출했습니다.")

        class PreSpecApi:
            last_total_count = 1

            @staticmethod
            def fetch_pre_specifications(_category, _begin, _end):
                return [
                    PreSpecification(
                        category="service",
                        title="수원 BIS 구축",
                        pre_spec_no="356759",
                        agency="수원시",
                        demand_agency="수원시",
                        link="",
                    )
                ]

        rules = parse_keyword_condition_rules(
            [
                {
                    "keyword": "BIS",
                    "operator": "or",
                    "categories": ["service"],
                    "targets": ["prespec"],
                    "enabled": True,
                }
            ]
        )
        summary = BidMonitorService(
            BidApi(),
            self.database.bids,
            pre_spec_api=PreSpecApi(),
        ).check_once(
            AppConfig(selected_categories=["service"], prespec_search_enabled=True),
            rules,
            checked_at=datetime(2026, 7, 20, 12, 0),
            skip_seen=False,
        )

        self.assertTrue(summary["all_success"])
        self.assertEqual(1, len(summary["alerts"]))
        self.assertEqual(["사전규격·용역"], [row["label"] for row in summary["category_reports"]])

    def test_bid_failure_does_not_skip_prespec_query(self):
        class BidApi:
            @staticmethod
            def fetch_bids(_category, _begin, _end):
                raise RuntimeError("입찰 API 실패")

        class PreSpecApi:
            last_total_count = 1

            @staticmethod
            def fetch_pre_specifications(_category, _begin, _end):
                return [
                    PreSpecification(
                        category="service",
                        title="수원 BIS 구축",
                        pre_spec_no="356759",
                        agency="수원시",
                        demand_agency="수원시",
                        link="",
                    )
                ]

        rules = parse_keyword_condition_rules(
            [
                {
                    "keyword": "BIS",
                    "operator": "or",
                    "categories": ["service"],
                    "targets": ["bid_lifecycle", "prespec"],
                    "enabled": True,
                }
            ]
        )
        summary = BidMonitorService(
            BidApi(),
            self.database.bids,
            pre_spec_api=PreSpecApi(),
        ).check_once(
            AppConfig(selected_categories=["service"], prespec_search_enabled=True),
            rules,
            checked_at=datetime(2026, 7, 20, 12, 0),
            skip_seen=False,
        )

        self.assertFalse(summary["all_success"])
        self.assertEqual(1, len(summary["alerts"]))
        self.assertEqual(["failed", "success"], [row["status"] for row in summary["category_reports"]])

    def test_single_keyword_search_does_not_move_regular_cycle(self):
        class BidApi:
            last_total_count = 1

            @staticmethod
            def fetch_bids(_category, _begin, _end):
                return [
                    Bid(
                        category="service",
                        title="수원 BIS 구축",
                        bid_no="R-1",
                        bid_ord="000",
                        agency="수원시",
                        demand_agency="수원시",
                        link="",
                    )
                ]

        original_cycle = "2026-07-20T10:00:00"
        self.database.bids.set_last_check_time(original_cycle)
        config = AppConfig(selected_categories=["service"], bootstrap_minutes=30)
        summary = BidMonitorService(BidApi(), self.database.bids).check_once(
            config,
            parse_keyword_rules("", "BIS"),
            checked_at=datetime(2026, 7, 20, 10, 3),
            use_last_check=False,
            record_cycle=False,
            skip_seen=False,
        )

        self.assertEqual(1, len(summary["alerts"]))
        self.assertEqual(original_cycle, self.database.bids.get_last_check_time())

    def test_saved_prespec_transitions_to_bid_in_same_tracking_row(self):
        pre_spec = PreSpecification(
            category="service",
            title="수원 BIS 사전규격",
            pre_spec_no="356759",
            agency="수원시",
            demand_agency="수원시",
            link="",
        )
        saved_id, _ = self.database.bids.save_pre_specification(pre_spec)

        class ContractApi:
            @staticmethod
            def find_bid_for_pre_specification(_pre_spec_no, _category):
                return Bid(
                    category="service",
                    title="수원 BIS 입찰공고",
                    bid_no="R26BK01621405",
                    bid_ord="000",
                    agency="수원시",
                    demand_agency="수원시",
                    link="",
                )

        class ResultApi:
            @staticmethod
            def fetch_results(_saved_bid):
                return []

        summary = ResultMonitorService(
            AppConfig(api_key="key"),
            self.database.bids,
            self.database.results,
            ResultApi(),
            contract_process_api=ContractApi(),
        ).check_saved_bids()

        self.assertEqual(1, len(summary["transition_events"]))
        transitioned = self.database.bids.find_saved_bid("R26BK01621405", "000")
        self.assertEqual(saved_id, transitioned.id)
        self.assertEqual("356759", transitioned.pre_spec_no)
        self.assertEqual("입찰공고", transitioned.stage_label())

    def test_saved_prespec_waiting_for_bid_records_lookup_attempt(self):
        pre_spec = PreSpecification(
            category="service",
            title="수원 BIS 사전규격",
            pre_spec_no="356759",
            agency="수원시",
            demand_agency="수원시",
            link="",
        )
        saved_id, _ = self.database.bids.save_pre_specification(pre_spec)

        class ContractApi:
            @staticmethod
            def find_bid_for_pre_specification(_pre_spec_no, _category):
                return None

        class ResultApi:
            @staticmethod
            def fetch_results(_saved_bid):
                raise AssertionError("사전규격 대기 중에는 개찰결과를 조회하면 안 됩니다.")

        summary = ResultMonitorService(
            AppConfig(api_key="key"),
            self.database.bids,
            self.database.results,
            ResultApi(),
            contract_process_api=ContractApi(),
        ).check_saved_bids()

        saved = self.database.bids.find_saved_pre_specification("356759")
        self.assertTrue(saved.last_result_check_at)
        self.assertEqual(saved_id, saved.id)
        self.assertEqual("waiting", summary["tracking_reports"][0]["status"])


if __name__ == "__main__":
    unittest.main()
