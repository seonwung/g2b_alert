import unittest
from types import SimpleNamespace
from unittest.mock import patch

from g2b_alert.api.smtp_client import SmtpClient


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.login_args = None
        self.sent_messages = []
        self.ehlo_count = 0
        self.tls_started = False
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def ehlo(self):
        self.ehlo_count += 1

    def starttls(self, context):
        self.tls_started = context is not None

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, message):
        self.sent_messages.append(message)


class SmtpClientTest(unittest.TestCase):
    def setUp(self):
        FakeSMTP.instances.clear()
        self.config = SimpleNamespace(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="sender@example.com",
            smtp_sender_name="나라장터 알림",
        )

    @patch("g2b_alert.api.smtp_client.smtplib.SMTP", FakeSMTP)
    def test_connection_checks_tls_and_login_without_sending(self):
        self.assertTrue(SmtpClient().test_connection(self.config, "app-password"))

        smtp = FakeSMTP.instances[0]
        self.assertEqual(("sender@example.com", "app-password"), smtp.login_args)
        self.assertTrue(smtp.tls_started)
        self.assertEqual(2, smtp.ehlo_count)
        self.assertEqual([], smtp.sent_messages)

    @patch("g2b_alert.api.smtp_client.smtplib.SMTP", FakeSMTP)
    def test_test_email_has_required_subject_and_diagnostics(self):
        self.assertTrue(
            SmtpClient().send_test(
                self.config,
                "app-password",
                "recipient@example.com",
            )
        )

        message = FakeSMTP.instances[0].sent_messages[0]
        self.assertEqual("[키워드알람 테스트] 이메일 발송 확인", message["Subject"])
        self.assertIn("recipient@example.com", message["To"])
        text_body = message.get_body(preferencelist=("plain",)).get_content()
        self.assertIn("발송시각", text_body)
        self.assertIn("sender@example.com", text_body)
        self.assertIn("스팸함", text_body)


if __name__ == "__main__":
    unittest.main()
