import unittest
from types import SimpleNamespace

from g2b_alert.model.notice_detail_model import build_notice_detail, extract_attachments


class NoticeDetailTest(unittest.TestCase):
    def test_extracts_paired_attachment_names_and_urls(self):
        attachments = extract_attachments(
            {
                "ntceSpecFileNm1": "제안요청서.pdf",
                "ntceSpecDocUrl1": "https://example.com/rfp.pdf",
                "ntceSpecFileNm2": "과업지시서.hwp",
                "ntceSpecDocUrl2": "https://example.com/task.hwp",
            }
        )
        self.assertEqual(
            [
                {"name": "제안요청서.pdf", "url": "https://example.com/rfp.pdf"},
                {"name": "과업지시서.hwp", "url": "https://example.com/task.hwp"},
            ],
            attachments,
        )

    def test_ignores_repeated_standard_notice_url(self):
        first_url = "https://example.com/downloadFile.do?fileSeq=1"
        attachments = extract_attachments(
            {
                "stdNtceDocUrl": first_url,
                "ntceSpecDocUrl1": first_url,
                "ntceSpecFileNm1": "제안요청서.pdf",
                "ntceSpecDocUrl2": "https://example.com/downloadFile.do?fileSeq=2",
                "ntceSpecFileNm2": "과업지시서.hwp",
            }
        )

        self.assertEqual(
            [
                {"name": "제안요청서.pdf", "url": first_url},
                {
                    "name": "과업지시서.hwp",
                    "url": "https://example.com/downloadFile.do?fileSeq=2",
                },
            ],
            attachments,
        )

    def test_builds_all_detail_sections_with_dash_for_missing_values(self):
        saved_bid = SimpleNamespace(
            title="BIS 구축",
            bid_no="R26BK01621405",
            bid_ord="001",
            category_label="용역",
            agency="수원시",
            demand_agency="수원시",
            contract_method="협상",
            bid_method="전자입찰",
            budget_amount="1000000",
            monitoring_enabled=True,
            saved_at="2026-07-16T10:00:00",
            updated_at="2026-07-16T11:00:00",
            bid_start_datetime="202607161000",
            bid_end_datetime="202607221000",
            opening_datetime="202607241100",
            link="https://example.com",
            raw={},
            stage_label=lambda: "입찰공고",
        )
        detail = build_notice_detail(
            saved_bid,
            [],
            [],
            {"previous": None, "current": None, "changes": []},
            recipient_count=2,
        )

        self.assertEqual("R26BK01621405-001", detail["reference"])
        self.assertEqual("입찰공고", detail["stage"])
        self.assertIn(("이메일 수신자", "2명"), detail["basic_rows"])
        self.assertEqual([], detail["results"])
        self.assertEqual([], detail["attachments"])


if __name__ == "__main__":
    unittest.main()
