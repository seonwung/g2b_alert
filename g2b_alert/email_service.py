import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr

from .credential_store import CredentialStoreError, get_smtp_password


MAX_EMAIL_RETRIES = 3
RETRY_DELAYS_SECONDS = (60, 300, 900)


class EmailAlertService:
    def __init__(self, config, database, on_log=None, logger=None):
        self.config = config
        self.database = database
        self.on_log = on_log
        self.logger = logger
        self.running = False
        self.worker = None

    def start(self):
        if self.worker is not None and self.worker.is_alive():
            return False
        self.database.reset_interrupted_email_deliveries()
        self.running = True
        self.worker = threading.Thread(target=self._loop, daemon=True, name="email-delivery-worker")
        self.worker.start()
        return True

    def stop(self):
        self.running = False

    def update_config(self, config):
        self.config = config

    def queue_keyword_bid(self, bid, matched_keywords):
        recipients = self.database.get_keyword_email_recipients()
        subject = f"[나라장터 신규 공고] {bid.title}"
        body_lines = [
            f"공고명: {bid.title}",
            f"공고번호: {bid.bid_no} / 차수: {bid.bid_ord or '000'}",
            f"공고종류: {bid.category_label}",
            f"공고기관: {bid.agency or '-'}",
            f"수요기관: {bid.demand_agency or '-'}",
            f"매칭 키워드: {', '.join(matched_keywords)}",
        ]
        if bid.bid_end_datetime:
            body_lines.append(f"입찰마감: {bid.bid_end_datetime}")
        if bid.link:
            body_lines.extend(["", f"공고 링크: {bid.link}"])
        created, delivery_count = self.database.create_email_event(
            event_key=f"keyword_bid:{bid.unique_id}",
            event_type="keyword_bid",
            source_ref=bid.unique_id,
            subject=subject,
            body="\n".join(body_lines),
            recipients=recipients,
        )
        if created and delivery_count and self.on_log:
            self.on_log(f"이메일 발송 대기: 신규 공고 {bid.bid_no} / 수신자 {delivery_count}명")
        return created, delivery_count

    def queue_bid_result(self, saved_bid, result):
        recipients = self.database.get_saved_bid_email_recipients(saved_bid["id"])
        result_key = result.get("result_key") or ""
        bid_ref = f"{saved_bid['bid_pbanc_no']}-{saved_bid['bid_pbanc_ord'] or '000'}"
        subject = f"[나라장터 낙찰정보] {saved_bid['bid_name'] or saved_bid['bid_pbanc_no']}"
        body_lines = [
            f"공고명: {saved_bid['bid_name'] or '-'}",
            f"공고번호: {saved_bid['bid_pbanc_no']} / 차수: {saved_bid['bid_pbanc_ord'] or '000'}",
            f"낙찰업체: {result.get('successful_bidder_name') or '-'}",
            f"사업자번호: {result.get('business_number') or '-'}",
            f"낙찰금액: {result.get('successful_bid_amount') or '-'}",
            f"낙찰률: {result.get('successful_bid_rate') or '-'}",
            f"상태: {result.get('result_status') or '-'}",
        ]
        if saved_bid["detail_url"]:
            body_lines.extend(["", f"공고 링크: {saved_bid['detail_url']}"])
        created, delivery_count = self.database.create_email_event(
            event_key=f"bid_result:{saved_bid['id']}:{result_key}",
            event_type="bid_result",
            source_ref=bid_ref,
            subject=subject,
            body="\n".join(body_lines),
            recipients=recipients,
        )
        if created and delivery_count and self.on_log:
            self.on_log(f"이메일 발송 대기: 낙찰정보 {bid_ref} / 수신자 {delivery_count}명")
        return created, delivery_count

    def _loop(self):
        while self.running:
            if not self._credentials_ready():
                self._wait(5)
                continue
            delivery = self.database.claim_next_email_delivery()
            if not delivery:
                self._wait(2)
                continue
            self._send_delivery(delivery)

    def _credentials_ready(self):
        if not (getattr(self.config, "smtp_username", "") or "").strip():
            return False
        try:
            return bool(get_smtp_password(self.config.smtp_username))
        except CredentialStoreError:
            return False

    def _send_delivery(self, delivery):
        try:
            password = get_smtp_password(self.config.smtp_username)
            if not password:
                raise RuntimeError("Windows 자격 증명 관리자에 SMTP 앱 비밀번호가 없습니다.")
            message = EmailMessage()
            sender_name = (getattr(self.config, "smtp_sender_name", "") or "나라장터 알림").strip()
            message["From"] = formataddr((sender_name, self.config.smtp_username))
            message["To"] = formataddr((delivery["recipient_name"], delivery["recipient_email"]))
            message["Subject"] = delivery["subject"]
            message.set_content(delivery["body"])

            host = (getattr(self.config, "smtp_host", "") or "smtp.gmail.com").strip()
            port = int(getattr(self.config, "smtp_port", 587))
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(self.config.smtp_username, password)
                smtp.send_message(message)
        except Exception as error:
            retry_index = min(int(delivery["retry_count"]), len(RETRY_DELAYS_SECONDS) - 1)
            self.database.mark_email_delivery_failed(
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
            return

        self.database.mark_email_delivery_sent(delivery["id"])
        if self.on_log:
            self.on_log(f"이메일 발송 성공: {delivery['recipient_email']} / {delivery['subject']}")

    def _wait(self, seconds):
        for _ in range(seconds):
            if not self.running:
                return
            time.sleep(1)
