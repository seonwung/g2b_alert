import threading

from ..api.smtp_client import SmtpClient
from ..model.credentials import CredentialStoreError, get_smtp_password


MAX_EMAIL_RETRIES = 3
RETRY_DELAYS_SECONDS = (60, 300, 900)


class EmailDeliveryWorker:
    """Coordinate SMTP delivery outside the domain model."""

    def __init__(self, config, email_repository, on_log=None, logger=None, smtp_client=None):
        self.config = config
        self.email_repository = email_repository
        self.on_log = on_log
        self.logger = logger
        self.smtp_client = smtp_client or SmtpClient()
        self.running = False
        self.stop_event = threading.Event()
        self.worker = None

    def start(self):
        if self.worker is not None and self.worker.is_alive():
            return False
        self.email_repository.reset_interrupted_email_deliveries()
        self.running = True
        self.stop_event.clear()
        self.worker = threading.Thread(target=self._loop, daemon=True, name="email-delivery-worker")
        self.worker.start()
        return True

    def stop(self):
        self.running = False
        self.stop_event.set()

    def wait(self, timeout=None):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=timeout)

    def update_config(self, config):
        self.config = config

    def _loop(self):
        while self.running:
            if not self._credentials_ready():
                self.stop_event.wait(5)
                continue
            delivery = self.email_repository.claim_next_email_delivery()
            if not delivery:
                self.stop_event.wait(2)
                continue
            self.send_delivery(delivery)

    def _credentials_ready(self):
        username = (getattr(self.config, "smtp_username", "") or "").strip()
        if not username:
            return False
        try:
            return bool(get_smtp_password(username))
        except CredentialStoreError:
            return False

    def send_delivery(self, delivery):
        try:
            password = get_smtp_password(self.config.smtp_username)
            if not password:
                raise RuntimeError("Windows 자격 증명 관리자에 SMTP 앱 비밀번호가 없습니다.")
            self.smtp_client.send(self.config, delivery, password)
        except Exception as error:
            retry_index = min(int(delivery["retry_count"]), len(RETRY_DELAYS_SECONDS) - 1)
            self.email_repository.mark_email_delivery_failed(
                delivery["id"],
                error,
                max_retries=MAX_EMAIL_RETRIES,
                retry_delay_seconds=RETRY_DELAYS_SECONDS[retry_index],
            )
            if self.logger:
                self.logger.exception("Email delivery failed for %s", delivery["recipient_email"])
            if self.on_log:
                attempt = int(delivery["retry_count"]) + 1
                self.on_log(
                    f"이메일 발송 실패: {delivery['recipient_email']} / "
                    f"시도 {attempt}/{MAX_EMAIL_RETRIES} / {error}"
                )
            return False

        self.email_repository.mark_email_delivery_sent(delivery["id"])
        if self.on_log:
            self.on_log(f"이메일 발송 성공: {delivery['recipient_email']} / {delivery['subject']}")
        return True
