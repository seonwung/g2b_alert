import threading
from dataclasses import replace
from pathlib import Path

from ..api.bid_api import G2BClient
from ..api.pre_spec_api import PreSpecificationApi
from ..api.windows_notifier import WindowsNotifier
from ..model.bid_model import BidMonitorService
from ..model.config import (
    DEFAULT_ATTACHMENT_DOWNLOAD_DIR,
    AppConfig,
    normalize_keyword_rules,
    save_config,
)
from ..model.entities import CATEGORY_LABELS
from ..model.keyword_matcher import parse_keyword_condition_rules, parse_keyword_rules
from .bid_monitor_worker import BidMonitorWorker


MIN_INTERVAL_MINUTES = 1
RECOMMENDED_INTERVAL_MINUTES = 5


class BidMonitorControllerMixin:
    def read_config_from_screen(self):
        form = self.view.get_monitor_form()
        keyword_rules = normalize_keyword_rules(
            form["keyword_rules"],
            default_categories=tuple(CATEGORY_LABELS),
        )
        grouped = {
            operator: ", ".join(
                rule["keyword"]
                for rule in keyword_rules
                if rule["operator"] == operator
            )
            for operator in ("and", "or", "exclude")
        }
        active_rules = [rule for rule in keyword_rules if rule["enabled"]]
        selected_categories = [
            category
            for category in CATEGORY_LABELS
            if any(category in rule["categories"] for rule in active_rules)
        ]
        return AppConfig(
            api_key="".join(form["api_key"].split()),
            keywords=grouped["or"],
            and_keywords=grouped["and"],
            or_keywords=grouped["or"],
            exclude_keywords=grouped["exclude"],
            keyword_rules=keyword_rules,
            interval=form["interval"],
            result_interval=form["result_interval"],
            selected_categories=selected_categories,
            windows_notifications_enabled=form["windows_notifications_enabled"],
            bootstrap_minutes=int(self.config.bootstrap_minutes),
            overlap_minutes=int(self.config.overlap_minutes),
            request_timeout_seconds=int(self.config.request_timeout_seconds),
            num_of_rows=int(self.config.num_of_rows),
            notify_all_opening_results=form["notify_all_opening_results"],
            keyword_email_enabled=form["keyword_email_enabled"],
            prespec_search_enabled=any(
                "prespec" in rule["targets"] for rule in active_rules
            ),
            attachment_download_dir=form["attachment_download_dir"],
            smtp_host=self.config.smtp_host,
            smtp_port=int(self.config.smtp_port),
            smtp_username=self.config.smtp_username,
            smtp_sender_name=self.config.smtp_sender_name,
        )

    def get_validated_monitor_inputs(self, warn_api_volume=True, include_all_rules=False):
        config = self.read_config_from_screen()
        if include_all_rules and config.keyword_rules:
            rows = [{**row, "enabled": True} for row in config.keyword_rules]
            categories = [
                category
                for category in CATEGORY_LABELS
                if any(category in row.get("categories", []) for row in rows)
            ]
            config = replace(
                config,
                keyword_rules=rows,
                selected_categories=categories,
                prespec_search_enabled=any(
                    "prespec" in row.get("targets", []) for row in rows
                ),
            )
        keywords = self._parse_monitor_rules(config)
        if not config.api_key:
            self.view.show_warning("확인", "API 키를 입력해 주세요.")
            return None
        if not keywords.positive_keywords:
            self.view.show_warning("확인", "키워드를 하나 이상 입력해 주세요.")
            return None
        if not config.selected_categories:
            self.view.show_warning("확인", "조회할 공고 종류를 하나 이상 선택해 주세요.")
            return None
        try:
            interval = int(config.interval)
        except ValueError:
            self.view.show_warning("확인", "키워드 감시 주기는 숫자로 입력해 주세요.")
            return None
        if interval < MIN_INTERVAL_MINUTES:
            self.view.show_warning("확인", f"키워드 감시 주기는 최소 {MIN_INTERVAL_MINUTES}분 이상이어야 합니다.")
            return None
        estimated_calls = self._estimate_daily_keyword_calls(config, interval)
        if warn_api_volume and (interval < RECOMMENDED_INTERVAL_MINUTES or estimated_calls > 1000):
            if not self.view.ask_yes_no(
                "API 호출량 확인",
                f"현재 설정은 하루 약 {estimated_calls:,}회 API를 호출할 수 있습니다.\n\n"
                f"키워드 감시 주기: {interval}분 / 조회 종류: {len(config.selected_categories)}개\n\n"
                "그래도 이 설정으로 시작할까요?",
            ):
                return None
        return config, keywords, interval, estimated_calls

    @staticmethod
    def _estimate_daily_keyword_calls(config, interval):
        request_targets = set()
        for rule in config.keyword_rules or []:
            if not rule.get("enabled", False):
                continue
            for category in rule.get("categories", []):
                for target in rule.get("targets", ["bid_lifecycle"]):
                    request_targets.add((category, target))

        if not request_targets:
            request_targets.update(
                (category, "bid_lifecycle") for category in config.selected_categories
            )
            if config.prespec_search_enabled:
                request_targets.update(
                    (category, "prespec") for category in config.selected_categories
                )
        return int(1440 / interval) * len(request_targets)

    def _make_bid_service(self, config):
        api = G2BClient(
            config.api_key,
            timeout_seconds=int(config.request_timeout_seconds),
            num_of_rows=int(config.num_of_rows),
        )
        pre_spec_api = None
        if config.prespec_search_enabled:
            pre_spec_api = PreSpecificationApi(
                config.api_key,
                timeout_seconds=int(config.request_timeout_seconds),
                num_of_rows=int(config.num_of_rows),
            )
        return BidMonitorService(api, self.bid_repository, pre_spec_api=pre_spec_api)

    def start(self, enable_all=True, warn_api_volume=True):
        if enable_all:
            self.view.set_all_keyword_monitoring(True)
        validated = self.get_validated_monitor_inputs(warn_api_volume)
        if not validated:
            if enable_all:
                self.view.set_all_keyword_monitoring(False)
            return False
        config, keywords, interval, estimated_calls = validated
        self._apply_monitor_config(config)
        self.scheduler = BidMonitorWorker(
            config,
            keywords,
            lambda: self._make_bid_service(config),
            self._handle_bid_check_complete,
            self._handle_bid_check_error,
        )
        if not self.scheduler.start():
            self.view.show_warning("확인", "이전 감시 작업이 아직 종료 중입니다.")
            if enable_all:
                self.view.set_all_keyword_monitoring(False)
            return False
        self.view.update_running_ui(True)
        self._update_monitor_summary(config, keywords)
        self.view.set_next_check_pending()
        self.set_status("감시 중")
        self.log("감시 시작")
        self.log(
            "키워드: "
            f"AND [{', '.join(keywords.and_keywords) or '-'}] / "
            f"OR [{', '.join(keywords.or_keywords) or '-'}] / "
            f"제외 [{', '.join(keywords.exclude_keywords) or '-'}]"
        )
        self.log(f"키워드 감시 주기: {interval}분 / 예상 API 호출: 하루 약 {estimated_calls:,}회")
        return True

    def resume_keyword_monitoring_if_needed(self):
        config = self.read_config_from_screen()
        if not any(rule.get("enabled", False) for rule in config.keyword_rules):
            return
        if not config.api_key:
            self.view.set_all_keyword_monitoring(False)
            self.log("키워드 자동 재개 건너뜀: API 키가 없습니다.")
            return
        if self.start(enable_all=False, warn_api_volume=False):
            self.log("이전 키워드 감시 상태를 자동으로 재개했습니다.")
        else:
            self.view.set_all_keyword_monitoring(False)

    def _apply_monitor_config(self, config):
        self.config = config
        save_config(config)
        downloader = getattr(self, "attachment_downloader", None)
        if downloader is not None:
            downloader.set_root_dir(config.attachment_download_dir)
        self.email_repository.sync_keyword_setting(
            self._keyword_setting_text(config), config.keyword_email_enabled
        )
        self.email_alert_service.update_config(config)
        self.email_delivery_worker.update_config(config)

    def save_attachment_download_directory(self, directory):
        previous = self.config.attachment_download_dir
        try:
            text = str(directory or "").strip()
            if not text:
                raise ValueError("저장 경로를 입력해 주세요.")
            path = Path(text).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            if not path.is_dir():
                raise ValueError("선택한 경로가 폴더가 아닙니다.")
            normalized = str(path.resolve())
            self.view.set_attachment_download_directory(normalized)
            self._apply_monitor_config(self.read_config_from_screen())
            self.log(f"첨부파일 저장 경로 변경: {normalized}")
        except (OSError, ValueError) as error:
            self.view.set_attachment_download_directory(previous)
            self.view.show_error("저장 경로 변경 실패", str(error))

    def reset_attachment_download_directory(self):
        self.view.set_attachment_download_directory(DEFAULT_ATTACHMENT_DOWNLOAD_DIR)
        self.save_attachment_download_directory(DEFAULT_ATTACHMENT_DOWNLOAD_DIR)

    def _handle_bid_check_complete(self, summary, update_schedule=True):
        for report in summary["category_reports"]:
            if report["status"] == "failed":
                self.logger.warning("%s fetch failed: %s", report["label"], report["error"])
                self.log(f"{report['label']} 조회 실패: {report['error']}")
            elif report["total_count"] > report["count"]:
                self.log(f"{report['label']} 조회 주의: 전체 {report['total_count']}건 중 {report['count']}건을 받았습니다.")
        for alert in summary["alerts"]:
            bid = alert["bid"]
            keywords = alert["matched_keywords"]
            if not alert.get("notify", True):
                continue
            if self.config.windows_notifications_enabled:
                WindowsNotifier(logger=self.logger).send(
                    "나라장터 새 공고", f"[{bid.category_label}] {bid.title}"
                )
            if hasattr(bid, "pre_spec_no"):
                created, count = self.email_alert_service.queue_pre_specification(bid, keywords)
            else:
                created, count = self.email_alert_service.queue_keyword_bid(bid, keywords)
            if created and count:
                reference = getattr(bid, "pre_spec_no", "") or bid.bid_no
                self.log(f"이메일 발송 대기: 신규 공고 {reference} / 수신자 {count}명")
            self.mark_unread_alert(bid, keywords, unread=not self.config.windows_notifications_enabled)
            self.log(f"알림: [{bid.category_label}] {bid.title} / 키워드: {', '.join(keywords)}")
        if not summary["all_success"]:
            self.log("일부 조회 실패로 마지막 확인 시각은 갱신하지 않았습니다.")
        if update_schedule:
            self.view.set_check_summary(
                summary["checked_at"],
                summary["new_alert_count"],
                summary["all_success"],
                int(self.config.interval),
            )

    def _download_notice_attachments(self, bid, overwrite=False):
        downloader = getattr(self, "attachment_downloader", None)
        if downloader is None:
            return {"downloaded": [], "existing": [], "failed": [], "folder": None}
        try:
            report = downloader.download_for_notice(bid, overwrite=overwrite)
        except Exception as error:
            self.logger.exception("Could not download notice attachments.")
            self.log(f"첨부파일 자동 저장 실패: {error}")
            return {"downloaded": [], "existing": [], "failed": [{"error": str(error)}], "folder": None}

        if report["downloaded"]:
            self.log(
                f"첨부파일 자동 저장: {len(report['downloaded'])}개 / {report['folder']}"
            )
        if report["existing"]:
            self.log(f"첨부파일 기존 파일 재사용: {len(report['existing'])}개")
        if report.get("removed"):
            self.log(f"이전 첨부파일 삭제: {len(report['removed'])}개")
        if report["failed"]:
            self.log(f"첨부파일 다운로드 실패: {len(report['failed'])}개")
        return report

    def _handle_bid_check_error(self, error):
        self.logger.exception("Unhandled error while checking bids.")
        self.log(f"오류 발생: {error}")
        self.set_status("오류 발생")

    def check_now(self):
        if self.manual_check_running:
            self.view.show_info("확인", "즉시 조회가 이미 실행 중입니다.")
            return
        validated = self.get_validated_monitor_inputs(False, include_all_rules=True)
        if not validated:
            return
        config, keywords, _interval, _estimated = validated
        self._apply_monitor_config(self.read_config_from_screen())
        self.manual_check_running = True
        self.view.start_manual_check()
        self.set_status("즉시 조회 중")

        def run_check():
            try:
                summary = self._make_bid_service(config).check_once(config, keywords)
                self._handle_bid_check_complete(summary)
            except Exception as error:
                self._handle_bid_check_error(error)
            finally:
                self.manual_check_running = False
                self.view.post(self.view.finish_manual_check)

        threading.Thread(target=run_check, daemon=True, name="manual-bid-check").start()

    def set_keyword_rule_monitoring(self, rule, enabled, on_finished):
        full_config = self.read_config_from_screen()
        if enabled and not full_config.api_key:
            self.view.show_warning("확인", "API 키를 입력해 주세요.")
            self.view.set_keyword_monitoring(rule["id"], False)
            on_finished()
            return
        self._apply_monitor_config(full_config)
        all_rules = self._parse_monitor_rules(full_config)
        running = bool(self.scheduler and self.scheduler.running)

        if not enabled:
            if running and all_rules.positive_keywords:
                self.scheduler.update(
                    full_config,
                    all_rules,
                    lambda: self._make_bid_service(full_config),
                )
                self._update_monitor_summary(full_config, all_rules)
            elif running:
                self.stop(disable_all=False)
            self.log(f"개별 감시 중지: {rule['keyword']}")
            on_finished()
            return

        if not running:
            if not self.start(enable_all=False):
                self.view.set_keyword_monitoring(rule["id"], False)
                self.keyword_rules_changed()
            on_finished()
            return

        self.scheduler.update(
            full_config,
            all_rules,
            lambda: self._make_bid_service(full_config),
        )
        self._update_monitor_summary(full_config, all_rules)
        self.log(f"개별 감시 시작: {rule['keyword']} / 첫 조회 실행")
        if rule.get("operator") == "exclude":
            on_finished()
            return

        search_config = replace(
            full_config,
            keyword_rules=[rule],
            selected_categories=list(rule.get("categories", [])),
            prespec_search_enabled="prespec" in rule.get("targets", []),
        )
        rules = parse_keyword_condition_rules([rule])

        def run_first_check():
            try:
                summary = self.scheduler.check_custom(
                    search_config,
                    rules,
                    lambda: self._make_bid_service(search_config),
                )
                self._handle_bid_check_complete(summary, update_schedule=False)
                self.log(
                    f"첫 조회 완료: {rule['keyword']} / 매칭 {len(summary['alerts'])}건"
                )
            except Exception as error:
                self._handle_bid_check_error(error)
            finally:
                self.view.post(on_finished)

        threading.Thread(
            target=run_first_check,
            daemon=True,
            name="new-keyword-first-check",
        ).start()

    def keyword_rules_changed(self):
        config = self.read_config_from_screen()
        self._apply_monitor_config(config)
        rules = self._parse_monitor_rules(config)
        if self.scheduler and self.scheduler.running:
            if rules.positive_keywords:
                self.scheduler.update(
                    config,
                    rules,
                    lambda: self._make_bid_service(config),
                )
                self._update_monitor_summary(config, rules)
            else:
                self.stop(disable_all=False)

    def stop(self, disable_all=True):
        if disable_all:
            self.view.set_all_keyword_monitoring(False)
            self._apply_monitor_config(self.read_config_from_screen())
        if self.scheduler:
            self.scheduler.stop()
        self.view.update_running_ui(False)
        self.set_status("대기 중")
        self.view.clear_next_check()
        self.log("감시 중지")

    def toggle_windows_notifications(self):
        config = self.read_config_from_screen()
        self._apply_monitor_config(config)
        self._update_monitor_summary(
            config,
            self._parse_monitor_rules(config),
        )
        self.log(f"윈도우 알림: {'ON' if config.windows_notifications_enabled else 'OFF'}")

    def _update_monitor_summary(self, config, keywords):
        labels = [CATEGORY_LABELS.get(category, category) for category in config.selected_categories]
        if keywords.positive_keywords and labels:
            text = (
                f"감시 조건: AND {len(keywords.and_keywords)}개 · "
                f"OR {len(keywords.or_keywords)}개 · 제외 {len(keywords.exclude_keywords)}개 / "
                f"{', '.join(labels)} / "
                f"{config.interval}분마다 / 윈도우 알림 {'ON' if config.windows_notifications_enabled else 'OFF'}"
            )
        else:
            text = "감시 조건: 대기 중"
        self.view.set_monitor_summary(text)

    @staticmethod
    def _keyword_setting_text(config):
        return (
            f"AND: {config.and_keywords}\n"
            f"OR: {config.or_keywords or config.keywords}\n"
            f"제외: {config.exclude_keywords}"
        )

    @staticmethod
    def _parse_monitor_rules(config):
        if getattr(config, "keyword_rules", None):
            return parse_keyword_condition_rules(config.keyword_rules)
        return parse_keyword_rules(
            config.and_keywords,
            config.or_keywords or config.keywords,
            config.exclude_keywords,
        )

    def test_alert(self):
        if not self.config.windows_notifications_enabled:
            self.view.show_info("알림 OFF", "윈도우 알림이 꺼져 있습니다.")
            return
        WindowsNotifier(logger=self.logger).send("나라장터 알림 테스트", "윈도우 알림이 정상 작동합니다.")
        self.log("알림 테스트 전송")

    def reset_records(self):
        if self.scheduler and self.scheduler.running:
            self.view.show_warning("확인", "감시 중에는 기록을 초기화할 수 없습니다.")
            return
        if not self.view.ask_yes_no("확인 기록 초기화", "이미 확인한 공고 기록과 마지막 조회 시각을 삭제할까요?"):
            return
        try:
            deleted = self.bid_repository.reset_bid_monitor_state()
            self.log("확인 기록 초기화 완료" if deleted else "초기화할 확인 기록이 없습니다.")
            self.view.show_info("완료", "확인 기록이 초기화되었습니다.")
        except Exception as error:
            self.logger.exception("Could not reset bid monitor state.")
            self.view.show_error("오류", str(error))
