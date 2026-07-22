import unittest

from g2b_alert.view.log_view import LogViewMixin


class LogViewTest(unittest.TestCase):
    def test_classifies_error_and_email_before_generic_api_text(self):
        self.assertEqual("email", LogViewMixin._classify_log("SMTP 테스트 메일 발송 성공"))
        self.assertEqual("error", LogViewMixin._classify_log("API 조회 실패"))
        self.assertEqual("api", LogViewMixin._classify_log("입찰공고 API 조회 시작"))
        self.assertEqual("notification", LogViewMixin._classify_log("윈도우 알림 전송"))
        self.assertEqual("info", LogViewMixin._classify_log("프로그램 준비 완료"))


if __name__ == "__main__":
    unittest.main()
