import re
import threading
from types import SimpleNamespace

from ..api.smtp_client import SmtpClient
from ..model.config import save_config
from ..model.credentials import CredentialStoreError, get_smtp_password, save_smtp_password
from ..presentation.contracts import EmailSettingsState


class EmailControllerMixin:
    def toggle_keyword_email_notifications(self):
        config = self.read_config_from_screen()
        enabled = config.keyword_email_enabled
        self.config = config
        self.email_repository.sync_keyword_setting(self._keyword_setting_text(config), enabled)
        save_config(config)
        self.email_alert_service.update_config(config)
        self.email_delivery_worker.update_config(config)
        self.log(f"신규 공고 이메일 알림: {'ON' if enabled else 'OFF'}")
        if enabled and (not config.smtp_username or not self.email_repository.get_keyword_email_recipients()):
            self.view.show_info(
                "이메일 설정 필요",
                "이메일 알림을 사용하려면 SMTP 앱 비밀번호와 키워드 알림 수신자를 설정해 주세요.",
            )
            self.open_email_settings()

    def open_email_settings(self):
        config = self.read_config_from_screen()
        self.config = config
        self.email_repository.sync_keyword_setting(
            self._keyword_setting_text(config), config.keyword_email_enabled
        )
        self.view.open_email_settings_window(
            settings=EmailSettingsState(
                smtp_host=config.smtp_host,
                smtp_port=int(config.smtp_port),
                smtp_username=config.smtp_username,
                smtp_sender_name=config.smtp_sender_name,
            ),
            recipients=self.email_repository.list_recipients(),
            keyword_recipient_ids=self.email_repository.get_keyword_recipient_ids(),
            password_state=self._smtp_password_state(config.smtp_username),
            history_data=self.get_email_history(),
            on_save=self.save_email_settings,
            on_refresh_history=self.get_email_history,
            on_test_connection=self.test_smtp_connection,
            on_send_test=self.send_smtp_test,
        )

    def _smtp_password_state(self, username):
        username = (username or "").strip()
        if not username:
            return "Windows 자격 증명: SMTP 계정 미설정"
        try:
            saved = bool(get_smtp_password(username))
        except CredentialStoreError as error:
            return f"Windows 자격 증명: 확인 불가 ({error})"
        return "Windows 자격 증명: 앱 비밀번호 저장됨" if saved else "Windows 자격 증명: 앱 비밀번호 없음"

    def save_email_settings(self, payload):
        try:
            port = int(payload["smtp_port"])
            if not payload["smtp_host"] or "@" not in payload["smtp_username"]:
                raise ValueError("SMTP 서버와 Gmail 주소를 확인해 주세요.")
            if payload["smtp_username"] != payload["old_username"] and not payload["password"]:
                raise ValueError("SMTP 계정을 변경할 때는 해당 계정의 앱 비밀번호도 입력해 주세요.")

            recipients = []
            for recipient in payload["recipients"]:
                normalized_recipient = dict(recipient)
                normalized_recipient["name"] = str(recipient.get("name") or "").strip()
                normalized_recipient["email"] = str(recipient.get("email") or "").strip().lower()
                if not normalized_recipient["name"] and not normalized_recipient["email"]:
                    continue
                if not normalized_recipient["name"] or not re.fullmatch(
                    r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized_recipient["email"]
                ):
                    raise ValueError("모든 수신자의 이름과 올바른 이메일 주소를 입력해 주세요.")
                recipients.append(normalized_recipient)

            if payload["password"]:
                save_smtp_password(payload["smtp_username"], payload["password"])
            for recipient_id in payload["deleted_recipient_ids"]:
                self.email_repository.deactivate_recipient(recipient_id)
            keyword_ids = []
            for recipient in recipients:
                recipient_id = self.email_repository.save_recipient(
                    recipient["name"],
                    recipient["email"],
                    recipient["id"],
                    organization=recipient.get("organization", ""),
                    memo=recipient.get("memo", ""),
                    is_default=recipient.get("is_default", False),
                )
                if recipient["keyword_enabled"]:
                    keyword_ids.append(recipient_id)
            self.email_repository.set_keyword_recipients(keyword_ids)

            self.config.smtp_host = payload["smtp_host"]
            self.config.smtp_port = port
            self.config.smtp_username = payload["smtp_username"]
            self.config.smtp_sender_name = payload["smtp_sender_name"]
            save_config(self.config)
            self.email_repository.sync_keyword_setting(
                self._keyword_setting_text(self.config), self.config.keyword_email_enabled
            )
            self.email_alert_service.update_config(self.config)
            self.email_delivery_worker.update_config(self.config)
            self.log("SMTP 및 이메일 수신자 설정 저장 완료")
            return {
                "ok": True,
                "recipient_count": len(keyword_ids),
                "password_state": self._smtp_password_state(self.config.smtp_username),
            }
        except Exception as error:
            self.logger.exception("Could not save email settings.")
            return {"ok": False, "error": str(error)}

    def get_email_history(self):
        return {
            "summary": self.email_repository.get_email_delivery_summary(),
            "rows": self.email_repository.list_recent_email_deliveries(50),
        }

    def test_smtp_connection(self, payload, on_complete):
        self._run_smtp_test(payload, on_complete, send_mail=False)

    def send_smtp_test(self, payload, on_complete):
        self._run_smtp_test(payload, on_complete, send_mail=True)

    def _run_smtp_test(self, payload, on_complete, send_mail):
        def run():
            try:
                config, password, recipient = self._smtp_test_inputs(payload, send_mail)
                client = SmtpClient()
                if send_mail:
                    client.send_test(config, password, recipient)
                    message = (
                        f"테스트 메일을 {recipient} 주소로 발송했습니다.\n\n"
                        "받은편지함과 스팸함을 확인해 주세요."
                    )
                    self.log(f"SMTP 테스트 메일 발송 성공: {recipient}")
                else:
                    client.test_connection(config, password)
                    message = "SMTP 서버 연결, TLS, 로그인에 성공했습니다."
                    self.log(f"SMTP 연결 테스트 성공: {config.smtp_username}")
                result = {"ok": True, "message": message}
            except Exception as error:
                action = "테스트 메일 발송" if send_mail else "SMTP 연결 테스트"
                self.logger.exception("%s failed.", action)
                self.log(f"{action} 실패: {error}")
                result = {
                    "ok": False,
                    "message": (
                        f"{action}에 실패했습니다.\n\n{error}\n\n"
                        "SMTP 서버, 포트, 계정, 앱 비밀번호를 확인해 주세요."
                    ),
                }
            self.view.post(lambda: on_complete(result))

        threading.Thread(target=run, daemon=True, name="smtp-settings-test").start()

    def _smtp_test_inputs(self, payload, require_recipient):
        host = (payload.get("smtp_host") or "").strip()
        username = (payload.get("smtp_username") or "").strip()
        sender_name = (payload.get("smtp_sender_name") or "나라장터 알림").strip()
        recipient = (payload.get("test_recipient") or "").strip().lower()
        if not host or not username or "@" not in username:
            raise ValueError("SMTP 서버와 발신 계정 주소를 확인해 주세요.")
        try:
            port = int(payload.get("smtp_port"))
        except (TypeError, ValueError) as error:
            raise ValueError("SMTP 포트는 숫자로 입력해 주세요.") from error
        if port < 1 or port > 65535:
            raise ValueError("SMTP 포트 범위는 1~65535입니다.")
        if require_recipient and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient):
            raise ValueError("테스트 메일을 받을 이메일 주소를 확인해 주세요.")

        password = "".join((payload.get("password") or "").split())
        if not password:
            password = get_smtp_password(username) or ""
        if not password:
            raise ValueError("앱 비밀번호를 입력하거나 Windows 자격 증명에 먼저 저장해 주세요.")
        config = SimpleNamespace(
            smtp_host=host,
            smtp_port=port,
            smtp_username=username,
            smtp_sender_name=sender_name,
        )
        return config, password, recipient

    def open_saved_bid_recipients(self):
        saved_bid = self.view.get_selected_saved_bid()
        if not saved_bid:
            self.view.show_info("확인", "이메일 수신자를 지정할 저장 공고를 선택해 주세요.")
            return
        self.view.open_saved_bid_recipient_window(
            saved_bid=saved_bid,
            recipients=self.email_repository.list_recipients(),
            mapped_ids=self.email_repository.get_saved_bid_recipient_ids(saved_bid.id),
            on_save=lambda recipient_ids: self.save_saved_bid_recipients(saved_bid, recipient_ids),
        )

    def open_keyword_rule_recipients(self, rule_id):
        config = self.read_config_from_screen()
        rule = next((row for row in config.keyword_rules if row.get("id") == rule_id), None)
        if not rule:
            self.view.show_warning("확인", "수신자를 설정할 감시 조건을 찾지 못했습니다.")
            return
        self.email_repository.sync_keyword_rules(config.keyword_rules)
        self.view.open_keyword_rule_recipient_window(
            rule=rule,
            recipients=self.email_repository.list_recipients(),
            mapped_ids=self.email_repository.get_keyword_rule_recipient_ids(rule_id),
            on_save=lambda recipient_ids: self.save_keyword_rule_recipients(rule, recipient_ids),
        )

    def save_keyword_rule_recipients(self, rule, recipient_ids):
        try:
            self.email_repository.set_keyword_rule_recipients(rule["id"], recipient_ids)
            self.log(f"감시 조건 이메일 수신자 변경: {rule.get('name') or rule.get('keyword')} / {len(recipient_ids)}명")
            return True
        except Exception as error:
            self.logger.exception("Could not save keyword-rule recipients.")
            self.view.show_error("저장 실패", str(error))
            return False

    def save_saved_bid_recipients(self, saved_bid, recipient_ids):
        try:
            self.email_repository.set_saved_bid_recipients(saved_bid.id, recipient_ids)
            self.log(f"저장 공고 이메일 수신자 변경: {saved_bid.bid_no} / {len(recipient_ids)}명")
            return True
        except Exception as error:
            self.logger.exception("Could not save saved-bid recipients.")
            self.view.show_error("저장 실패", str(error))
            return False
