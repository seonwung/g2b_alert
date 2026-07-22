import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr


class SmtpClient:
    """External SMTP adapter responsible only for message delivery."""

    def send(self, config, delivery, password):
        message = self._make_message(
            config,
            delivery["recipient_name"],
            delivery["recipient_email"],
            delivery["subject"],
            delivery["body"],
            delivery["body_html"],
        )
        self._send_message(config, password, message)

    def test_connection(self, config, password):
        with self._authenticated_smtp(config, password):
            return True

    def send_test(self, config, password, recipient_email):
        sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        username = (getattr(config, "smtp_username", "") or "").strip()
        subject = "[키워드알람 테스트] 이메일 발송 확인"
        body = (
            "나라장터 키워드 알림 프로그램의 테스트 메일입니다.\n\n"
            f"발송시각: {sent_at}\n"
            f"발신 계정: {username}\n\n"
            "메일이 보이지 않으면 받은편지함, 스팸함, 발신주소 차단 여부를 확인해 주세요."
        )
        body_html = (
            '<div style="font-family:Arial,\'Malgun Gothic\',sans-serif;line-height:1.7;'
            'color:#1f2937;"><h2 style="color:#2563eb;">나라장터 알림 테스트</h2>'
            "<p>SMTP 설정과 실제 메일 수신을 확인하기 위한 테스트 메일입니다.</p>"
            f"<p><strong>발송시각</strong>: {sent_at}<br>"
            f"<strong>발신 계정</strong>: {username}</p>"
            "<p>메일이 보이지 않으면 받은편지함, 스팸함, 발신주소 차단 여부, "
            "앱 비밀번호와 수신자 주소를 확인해 주세요.</p></div>"
        )
        message = self._make_message(
            config,
            "테스트 수신자",
            recipient_email,
            subject,
            body,
            body_html,
        )
        self._send_message(config, password, message)
        return True

    def _make_message(self, config, recipient_name, recipient_email, subject, body, body_html=""):
        message = EmailMessage()
        sender_name = (getattr(config, "smtp_sender_name", "") or "나라장터 알림").strip()
        message["From"] = formataddr((sender_name, config.smtp_username))
        message["To"] = formataddr((recipient_name, recipient_email))
        message["Subject"] = subject
        message.set_content(body)
        if body_html:
            message.add_alternative(body_html, subtype="html")
        return message

    def _send_message(self, config, password, message):
        with self._authenticated_smtp(config, password) as smtp:
            smtp.send_message(message)

    def _authenticated_smtp(self, config, password):
        host = (getattr(config, "smtp_host", "") or "smtp.gmail.com").strip()
        port = int(getattr(config, "smtp_port", 587))
        return _AuthenticatedSmtpSession(
            host,
            port,
            (getattr(config, "smtp_username", "") or "").strip(),
            password,
        )


class _AuthenticatedSmtpSession:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.smtp_context = None
        self.smtp = None

    def __enter__(self):
        self.smtp_context = smtplib.SMTP(self.host, self.port, timeout=30)
        self.smtp = self.smtp_context.__enter__()
        self.smtp.ehlo()
        self.smtp.starttls(context=ssl.create_default_context())
        self.smtp.ehlo()
        self.smtp.login(self.username, self.password)
        return self.smtp

    def __exit__(self, exc_type, exc_value, traceback):
        if self.smtp_context is None:
            return False
        return self.smtp_context.__exit__(exc_type, exc_value, traceback)
