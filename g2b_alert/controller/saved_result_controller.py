import threading
from datetime import datetime

from ..api.bid_api import G2BClient
from ..api.contract_process_api import ContractProcessApi
from ..api.result_api import ResultApiService
from ..api.windows_notifier import WindowsNotifier
from ..model.config import save_config
from ..model.result_model import ResultMonitorService
from .result_monitor_worker import ResultMonitorWorker


MIN_INTERVAL_MINUTES = 1


class SavedResultControllerMixin:
    """Control result-monitor settings, cycles, alerts, and worker lifecycle."""

    def _update_saved_monitor_status(self, monitoring_count=None, total_count=None):
        if monitoring_count is None or total_count is None:
            monitoring_count, total_count = self._get_saved_monitor_counts()
        interval = self._get_result_interval(default="-")
        running = bool(self.saved_result_scheduler and self.saved_result_scheduler.running)
        running_text = "작동 중" if running else "중지"
        self.view.set_saved_monitor_status(
            f"저장공고 자동 추적: {running_text} / 주기: {interval}분 / "
            f"조회대상 {monitoring_count}건 / 저장 공고 {total_count}건"
        )

    def _get_saved_monitor_counts(self):
        try:
            rows = self.bid_repository.list_saved_bids("")
        except Exception as error:
            self.logger.exception("Could not count saved bids.")
            self.log(f"저장 공고 개수 조회 실패: {error}")
            return 0, 0
        return sum(1 for row in rows if row.monitoring_enabled), len(rows)

    def _get_result_interval(self, default=1):
        try:
            interval = int(self.view.get_result_interval_text())
        except (TypeError, ValueError):
            try:
                interval = int(getattr(self.config, "result_interval", self.config.interval))
            except (TypeError, ValueError):
                return default
        return max(MIN_INTERVAL_MINUTES, interval)

    def apply_saved_result_interval(self):
        config = self._read_result_monitor_config(show_warning=True)
        if not config:
            return
        if self.saved_result_scheduler and self.saved_result_scheduler.running:
            self.saved_result_scheduler.update_config(config)
        else:
            self.start_saved_result_monitor_if_needed(show_warning=True)
        self._update_saved_monitor_status()
        self.log(f"저장공고 추적 주기 변경: {config.result_interval}분")
        self.view.show_info(
            "주기 적용",
            f"저장공고 변경·낙찰정보 추적 주기를 {config.result_interval}분으로 적용했습니다.",
        )

    def save_result_notification_setting(self):
        try:
            config = self.read_config_from_screen()
            self._apply_result_config(config)
            self.log(f"모든 낙찰정보 알림: {'ON' if config.notify_all_opening_results else 'OFF'}")
        except Exception as error:
            self.logger.exception("Could not save result notification setting.")
            self.view.show_error("저장 실패", str(error))

    def start_saved_result_monitor_if_needed(self, show_warning=False):
        monitoring_count, total_count = self._get_saved_monitor_counts()
        if monitoring_count == 0:
            self.stop_saved_result_monitor()
            self.view.post(lambda: self._update_saved_monitor_status(monitoring_count, total_count))
            return False

        config = self._read_result_monitor_config(show_warning=show_warning)
        if not config:
            self.view.post(lambda: self._update_saved_monitor_status(monitoring_count, total_count))
            return False

        if self.saved_result_scheduler and self.saved_result_scheduler.running:
            self.saved_result_scheduler.update_config(config)
            self.saved_result_scheduler.request_check()
            self.view.post(lambda: self._update_saved_monitor_status(monitoring_count, total_count))
            return True

        last_success_at = self.bid_repository.get_result_monitor_last_success_time()
        if last_success_at:
            try:
                gap = datetime.now() - datetime.fromisoformat(last_success_at)
                gap_minutes = max(0, int(gap.total_seconds() // 60))
                hours, minutes = divmod(gap_minutes, 60)
                self.log(
                    f"낙찰정보 감시 공백 복구 시작: 마지막 성공 조회 후 "
                    f"{hours}시간 {minutes}분 / 조회대상 {monitoring_count}건 즉시 확인"
                )
            except (TypeError, ValueError):
                self.log("낙찰정보 감시 시작: 조회대상 공고를 즉시 확인합니다.")
        else:
            self.log("낙찰정보 첫 감시 시작: 조회대상 공고를 즉시 확인합니다.")

        self.saved_result_scheduler = ResultMonitorWorker(
            config,
            lambda error_counts: self._make_result_service(self.config, error_counts),
            self._handle_saved_result_auto_check_complete,
            self._handle_saved_result_auto_check_error,
            check_lock=self.result_cycle_lock,
        )
        self.saved_result_scheduler.start()
        self.view.post(lambda: self._update_saved_monitor_status(monitoring_count, total_count))
        self.log(
            f"저장 공고 낙찰정보 자동 감시 시작: {config.result_interval}분마다 / "
            f"조회대상 {monitoring_count}건"
        )
        return True

    def stop_saved_result_monitor(self):
        if self.saved_result_scheduler:
            self.saved_result_scheduler.stop()
            self.saved_result_scheduler = None

    def _read_result_monitor_config(self, show_warning=False):
        config = self.read_config_from_screen()
        if not config.api_key:
            if show_warning:
                self.view.show_warning("확인", "낙찰정보 자동 감시를 시작하려면 API 키를 입력해 주세요.")
            return None
        try:
            interval = int(self.view.get_result_interval_text())
        except ValueError:
            if show_warning:
                self.view.show_warning("확인", "낙찰정보 자동 감시 주기는 숫자로 입력해 주세요.")
            return None
        if interval < MIN_INTERVAL_MINUTES:
            if show_warning:
                self.view.show_warning(
                    "확인", f"낙찰정보 자동 감시 주기는 최소 {MIN_INTERVAL_MINUTES}분 이상이어야 합니다."
                )
            return None
        config.result_interval = str(interval)
        self._apply_result_config(config)
        return config

    def _apply_result_config(self, config):
        self.config = config
        save_config(config)
        self.email_alert_service.update_config(config)
        self.email_delivery_worker.update_config(config)
        if self.saved_result_scheduler and self.saved_result_scheduler.running:
            self.saved_result_scheduler.update_config(config)

    def _make_result_service(self, config, error_counts=None):
        api = ResultApiService(
            config.api_key,
            timeout_seconds=int(config.request_timeout_seconds),
            num_of_rows=int(config.num_of_rows),
        )
        bid_api = G2BClient(
            config.api_key,
            timeout_seconds=int(config.request_timeout_seconds),
            num_of_rows=int(config.num_of_rows),
        )
        contract_process_api = ContractProcessApi(
            config.api_key,
            timeout_seconds=int(config.request_timeout_seconds),
            num_of_rows=int(config.num_of_rows),
        )
        return ResultMonitorService(
            config,
            self.bid_repository,
            self.result_repository,
            api,
            error_counts=error_counts,
            bid_api=bid_api,
            contract_process_api=contract_process_api,
        )

    def _handle_saved_result_auto_check_complete(self, summary):
        checked_at = summary.get("checked_at") or datetime.now()
        checked_at_text = checked_at.isoformat(timespec="seconds")
        self.bid_repository.set_result_monitor_last_cycle_time(checked_at_text)
        if summary.get("failed", 0) == 0 and summary.get("tracking_failed", 0) == 0:
            self.bid_repository.set_result_monitor_last_success_time(checked_at_text)
        self._process_result_summary(summary)
        self.view.post(lambda: self.view.render_saved_result_auto_check(summary))

    def _handle_saved_result_auto_check_error(self, error):
        self.logger.exception("Automatic saved-result check failed.")
        self.log(f"저장 공고 낙찰정보 자동 조회 오류: {error}")
        self.view.post(lambda: self.view.set_saved_result_status(f"자동 조회 오류: {error}"))

    def _process_result_summary(self, summary):
        for event in summary.get("transition_events", []):
            download_transition_files = getattr(
                self, "_download_saved_notice_attachments_async", None
            )
            if callable(download_transition_files):
                download_transition_files(event["saved_bid"])
            created, count = self.email_alert_service.queue_pre_spec_transition(
                event["saved_bid"],
                event["pre_spec_no"],
            )
            if created and count:
                self.log(
                    f"이메일 발송 대기: 사전규격 입찰공고 전환 "
                    f"{event['saved_bid'].bid_no} / 수신자 {count}명"
                )
            if event.get("should_notify"):
                if self.config.windows_notifications_enabled:
                    WindowsNotifier(logger=self.logger).send(
                        "[사전규격 → 입찰공고]",
                        event["message"],
                    )
                self.mark_unread_alert(
                    event["saved_bid"],
                    ["입찰공고 전환", event["pre_spec_no"]],
                )
            self.log(
                f"사전규격 입찰공고 전환: {event['pre_spec_no']} → "
                f"{event['saved_bid'].bid_no}-{event['saved_bid'].bid_ord or '000'}"
            )

        for event in summary.get("change_events", []):
            download_changed_files = getattr(
                self, "_download_saved_notice_attachments_async", None
            )
            if callable(download_changed_files):
                download_changed_files(event["saved_bid"], overwrite=True)
            created, count = self.email_alert_service.queue_bid_change(
                event["saved_bid"],
                event["previous_order"],
                event["current_order"],
                event["comparison"],
            )
            if created and count:
                self.log(
                    f"이메일 발송 대기: 변경공고 {event['saved_bid'].bid_no} / "
                    f"수신자 {count}명"
                )
            if event.get("should_notify"):
                if self.config.windows_notifications_enabled:
                    WindowsNotifier(logger=self.logger).send(
                        "[변경공고]",
                        event["message"],
                    )
                self.mark_unread_alert(
                    event["saved_bid"],
                    ["변경공고", f"{event['previous_order']}→{event['current_order']}"],
                )
            self.log(
                f"변경공고 감지: {event['saved_bid'].bid_no} / "
                f"차수 {event['previous_order']} → {event['current_order']}"
            )

        for event in summary.get("new_result_events", []):
            created, count = self.email_alert_service.queue_bid_result(event["saved_bid"], event["result"])
            if created and count:
                self.log(f"이메일 발송 대기: 낙찰정보 {event['saved_bid'].bid_no} / 수신자 {count}명")

        for notification in summary.get("notifications", []):
            if self.config.windows_notifications_enabled:
                WindowsNotifier(logger=self.logger).send(notification["title"], notification["message"])
            self.mark_result_alert(notification)

        for report in summary.get("reports", []):
            if report["status"] == "failed":
                if report.get("should_log_detail", True):
                    count = report.get("failure_count", 1)
                    self.log(
                        f"낙찰정보 조회 실패({count}회): {report['bid_no']} / "
                        f"차수 {report.get('bid_ord') or '000'} - {report['reason']}"
                    )
            elif report.get("recovered_after"):
                self.log(
                    f"낙찰정보 조회 복구: {report['bid_no']} / "
                    f"이전 연속 실패 {report['recovered_after']}회"
                )

        for report in summary.get("tracking_reports", []):
            if report.get("status") == "failed":
                self.log(f"변경공고 조회 실패: {report['bid_no']} - {report['reason']}")

        self.refresh_saved_bids()

    def check_saved_results_now(self):
        if self.result_check_running:
            self.view.show_info("확인", "낙찰정보 조회가 이미 실행 중입니다.")
            return
        config = self._read_result_monitor_config(show_warning=True)
        if not config:
            return

        self.result_check_running = True
        self.set_status("낙찰정보 조회 중")
        self.view.set_saved_result_status("낙찰정보를 조회하는 중입니다.")
        self.log("저장 공고 낙찰정보 즉시 조회 시작")

        def run_check():
            acquired = self.result_cycle_lock.acquire(blocking=False)
            if not acquired:
                self.result_check_running = False
                self.view.post(
                    lambda: self.view.render_saved_result_check(
                        None, "자동 조회가 진행 중입니다. 잠시 후 다시 시도해 주세요."
                    )
                )
                return
            try:
                summary = self._make_result_service(config).check_saved_bids()
                self._process_result_summary(summary)
                self.view.post(lambda: self.view.render_saved_result_check(summary, None))
            except Exception as error:
                self.logger.exception("Saved result check failed.")
                self.view.post(lambda error=error: self.view.render_saved_result_check(None, error))
            finally:
                self.result_cycle_lock.release()
                self.result_check_running = False
                self.set_status("대기 중")

        threading.Thread(target=run_check, daemon=True, name="manual-result-check").start()
