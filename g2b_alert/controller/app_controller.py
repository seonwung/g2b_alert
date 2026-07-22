import threading
import webbrowser
import os

from ..api.attachment_downloader import AttachmentDownloader
from ..model.config import ensure_keyword_rules
from ..model.email_model import EmailAlertService
from ..model.logging_setup import LOG_FILE
from ..presentation.contracts import AppViewProtocol, MainViewState, ViewFactoryProtocol
from .email_delivery_worker import EmailDeliveryWorker
from .bid_monitor_controller import BidMonitorControllerMixin
from .saved_bids_controller import SavedBidsControllerMixin
from .saved_result_controller import SavedResultControllerMixin
from .email_controller import EmailControllerMixin
from .recent_alert_controller import RecentAlertControllerMixin


class AppController(
    BidMonitorControllerMixin,
    SavedBidsControllerMixin,
    SavedResultControllerMixin,
    EmailControllerMixin,
    RecentAlertControllerMixin,
):
    def __init__(
        self,
        root,
        logger,
        config,
        database,
        view_factory: ViewFactoryProtocol,
    ):
        self.logger = logger
        self.config = ensure_keyword_rules(config)
        self.scheduler = None
        self.manual_check_running = False
        self.result_check_running = False
        self.saved_result_scheduler = None
        self.result_cycle_lock = threading.Lock()
        self.bid_repository = database.bids
        self.result_repository = database.results
        self.email_repository = database.email
        self.attachment_downloader = AttachmentDownloader(
            root_dir=self.config.attachment_download_dir,
            timeout_seconds=int(self.config.request_timeout_seconds)
        )
        self.email_repository.sync_keyword_setting(
            self._keyword_setting_text(self.config), self.config.keyword_email_enabled
        )
        self.initialize_recent_alerts()

        initial_state = MainViewState(
            api_key=self.config.api_key,
            interval=str(self.config.interval),
            result_interval=str(self.config.result_interval),
            keyword_rules=tuple(dict(rule) for rule in self.config.keyword_rules),
            windows_notifications_enabled=bool(self.config.windows_notifications_enabled),
            notify_all_opening_results=bool(self.config.notify_all_opening_results),
            keyword_email_enabled=bool(self.config.keyword_email_enabled),
            attachment_download_dir=str(self.config.attachment_download_dir or ""),
        )
        self.view: AppViewProtocol = view_factory(root, self, initial_state)
        self.email_alert_service = EmailAlertService(self.config, self.email_repository)
        self.email_delivery_worker = EmailDeliveryWorker(
            self.config, self.email_repository, self.log, self.logger
        )
        self.view.set_close_handler(self.close)
        self.view.update_running_ui(False)
        self.refresh_saved_bids()
        self.email_delivery_worker.start()
        self.view.schedule(500, self.start_saved_result_monitor_if_needed)
        self.view.schedule(700, self.resume_keyword_monitoring_if_needed)
        self.log("프로그램 준비 완료")
        self.logger.info("Program started.")

    def log(self, message):
        self.view.log(message)
        if message:
            self.logger.info(message)

    def set_status(self, message):
        self.view.set_status(message)

    def open_link(self, link):
        try:
            webbrowser.open(link)
        except Exception as error:
            self.log(f"링크 열기 실패: {error}")

    def open_log_file(self):
        try:
            os.startfile(LOG_FILE)
        except Exception as error:
            self.log(f"로그 파일 열기 실패: {error}")
            self.view.show_error("로그 파일 열기 실패", str(error))

    def close(self):
        self.logger.info("Application close requested.")
        self.view.stop_dispatcher()
        result_scheduler = self.saved_result_scheduler
        if self.scheduler:
            self.scheduler.stop()
        self.stop_saved_result_monitor()
        self.email_delivery_worker.stop()
        for worker in (self.scheduler, result_scheduler, self.email_delivery_worker):
            if worker:
                worker.wait(timeout=0.5)
        self.view.destroy()
