import threading

from ..api.bid_api import G2BClient, split_bid_reference
from ..api.pre_spec_api import (
    PreSpecificationApi,
    extract_pre_spec_reference,
    looks_like_pre_spec_reference,
)
from ..api.windows_notifier import WindowsNotifier
from ..model.notice_detail_model import build_notice_detail
from ..model.notice_version_model import compare_latest_versions


class SavedBidsControllerMixin:
    """Handle saved-bid lookup, persistence, selection, and display actions."""

    def lookup_notice_by_no(self):
        if self.result_check_running:
            self.view.show_info("확인", "다른 조회가 실행 중입니다.")
            return
        config = self.read_config_from_screen()
        if not config.api_key:
            self.view.show_warning("확인", "API 키를 입력해 주세요.")
            return
        reference = self.view.get_lookup_reference()
        if not reference:
            self.view.show_warning("확인", "공고번호 또는 나라장터 URL을 입력해 주세요.")
            return
        lookup_type = self.view.get_lookup_type()
        if lookup_type == "auto":
            lookup_type = "prespec" if looks_like_pre_spec_reference(reference) else "bid"

        if lookup_type == "prespec":
            normalized_reference = extract_pre_spec_reference(reference)
        else:
            bid_no, bid_ord = split_bid_reference(reference)
            normalized_reference = f"{bid_no}-{bid_ord}" if bid_ord else bid_no
        if not normalized_reference:
            self.view.show_warning("확인", "공고번호 또는 나라장터 URL 형식을 확인해 주세요.")
            return
        self.view.set_lookup_reference(normalized_reference)

        self.view.begin_lookup_notice()

        def run_lookup():
            try:
                if lookup_type == "prespec":
                    client = PreSpecificationApi(
                        config.api_key,
                        timeout_seconds=int(config.request_timeout_seconds),
                        num_of_rows=int(config.num_of_rows),
                    )
                    notice = client.fetch_pre_specification_by_no(normalized_reference)
                    duplicate = self.bid_repository.find_saved_pre_specification(
                        notice.pre_spec_no if notice else normalized_reference
                    )
                else:
                    client = G2BClient(
                        config.api_key,
                        timeout_seconds=int(config.request_timeout_seconds),
                        num_of_rows=int(config.num_of_rows),
                    )
                    notice = client.fetch_bid_by_no(normalized_reference)
                    duplicate = self.bid_repository.find_saved_bid(
                        notice.bid_no if notice else bid_no,
                        notice.bid_ord if notice else bid_ord,
                    )
                self.view.post(
                    lambda: self.view.finish_lookup_notice(notice, None, duplicate)
                )
            except Exception as error:
                self.logger.exception("Notice lookup failed.")
                self.view.post(
                    lambda error=error: self.view.finish_lookup_notice(None, error, None)
                )

        threading.Thread(target=run_lookup, daemon=True, name="saved-notice-lookup").start()

    def save_lookup_notice(self):
        notice = self.view.get_lookup_notice()
        if not notice:
            self.view.show_info("확인", "먼저 공고번호로 조회해 주세요.")
            return
        if hasattr(notice, "pre_spec_no"):
            self._save_pre_specification(notice)
            return
        duplicate = self.bid_repository.find_saved_bid(notice.bid_no, notice.bid_ord)
        if duplicate and not self.view.ask_yes_no(
            "중복 공고 확인",
            "동일한 공고번호와 차수가 이미 저장되어 있습니다.\n\n"
            "기존 원본은 유지하면서 최신 조회 정보로 갱신할까요?",
        ):
            return
        self._save_bid(notice)

    def _save_bid(self, bid):
        if not bid.bid_no:
            self.view.show_warning("확인", "공고번호가 없는 공고는 저장할 수 없습니다.")
            return
        try:
            saved_id, created = self.bid_repository.save_bid(bid)
        except Exception as error:
            self.logger.exception("Save bid failed.")
            self.view.show_error("저장 실패", f"공고 저장에 실패했습니다.\n\n{error}")
            return

        self.refresh_saved_bids(select_id=saved_id)
        self._download_saved_notice_attachments_async(bid, overwrite=not created)
        if created:
            self.log(f"저장 완료: {bid.bid_no} / {bid.title}")
            self.view.show_info("저장 완료", "공고를 저장했습니다.")
        else:
            self.log(f"이미 저장된 공고 갱신: {bid.bid_no}")
            self.view.show_info("저장 완료", "이미 저장된 공고의 정보를 갱신했습니다.")
        self.start_saved_result_monitor_if_needed()

    def _save_pre_specification(self, pre_spec):
        if not pre_spec.pre_spec_no:
            self.view.show_warning("확인", "사전규격등록번호가 없는 건은 저장할 수 없습니다.")
            return
        duplicate = self.bid_repository.find_saved_pre_specification(pre_spec.pre_spec_no)
        if duplicate and not self.view.ask_yes_no(
            "중복 사전규격 확인",
            "동일한 사전규격등록번호가 이미 저장되어 있습니다.\n\n"
            "최신 조회 정보로 갱신할까요?",
        ):
            return
        try:
            saved_id, created = self.bid_repository.save_pre_specification(pre_spec)
        except Exception as error:
            self.logger.exception("Save pre-specification failed.")
            self.view.show_error("저장 실패", f"사전규격 저장에 실패했습니다.\n\n{error}")
            return
        self.refresh_saved_bids(select_id=saved_id)
        self._download_saved_notice_attachments_async(pre_spec, overwrite=not created)
        if created:
            self.log(f"사전규격 추적 시작: {pre_spec.pre_spec_no} / {pre_spec.title}")
            self.view.show_info("추적 시작", "사전규격을 저장하고 입찰공고 전환 추적을 시작합니다.")
        else:
            self.log(f"저장 사전규격 갱신: {pre_spec.pre_spec_no}")
            self.view.show_info("저장 완료", "저장된 사전규격 정보를 갱신했습니다.")
        self.start_saved_result_monitor_if_needed()

    def _download_saved_notice_attachments_async(self, notice, overwrite=False):
        download = getattr(self, "_download_notice_attachments", None)
        if not callable(download):
            return

        def run_download():
            try:
                report = download(notice, overwrite=overwrite)
                downloaded = len(report.get("downloaded", []))
                existing = len(report.get("existing", []))
                removed = len(report.get("removed", []))
                failed = len(report.get("failed", []))
                if downloaded:
                    message = f"{notice.title}\n첨부파일 {downloaded}개 저장 완료"
                elif existing:
                    message = f"{notice.title}\n첨부파일 {existing}개가 이미 저장되어 있습니다."
                elif failed:
                    message = f"{notice.title}\n첨부파일 {failed}개 다운로드 실패"
                else:
                    message = f"{notice.title}\n다운로드할 첨부파일이 없습니다."
                if removed:
                    message += f"\n이전 첨부파일 {removed}개 삭제"
                    self.log(
                        f"이전 첨부파일 삭제: {notice.title} / {removed}개"
                    )
                if self.config.windows_notifications_enabled:
                    WindowsNotifier(logger=self.logger).send(
                        "저장공고 첨부파일", message
                    )
            except Exception:
                self.logger.exception("Unhandled saved-notice attachment download error.")

        threading.Thread(
            target=run_download,
            daemon=True,
            name="saved-notice-attachment-download",
        ).start()

    def refresh_saved_bids(self, select_id=None, select_ids=None):
        self.view.post(
            lambda: self._refresh_saved_bids_on_ui(select_id, select_ids)
        )

    def _refresh_saved_bids_on_ui(self, select_id=None, select_ids=None):
        try:
            search_text = self.view.get_saved_search_text()
            rows = self.bid_repository.list_saved_bids(search_text)
            rows = self._filter_saved_bids(rows, self.view.get_saved_filters())
            rows = self._sort_saved_bids(rows, self.view.get_saved_sort())
        except Exception as error:
            self.logger.exception("Could not load saved bids.")
            self.log(f"저장 공고 목록 조회 실패: {error}")
            return

        self.view.render_saved_bids(rows)
        if select_ids:
            self.view.select_saved_bids(select_ids)
        elif select_id is not None:
            self.view.select_saved_bid(select_id)
        monitoring_count = sum(1 for row in rows if row.monitoring_enabled)
        self._update_saved_monitor_status(monitoring_count, len(rows))

    def permanently_delete_saved_bid(self):
        row = self.view.get_selected_saved_bid()
        if not row:
            self.view.show_info("확인", "완전히 삭제할 공고를 선택해 주세요.")
            return
        if not self.view.ask_yes_no(
            "완전 삭제 확인",
            "선택한 공고와 관련 결과·수신자 연결·알림 이력을 완전히 삭제할까요?\n\n"
            "이 작업은 되돌릴 수 없습니다.",
        ):
            return
        try:
            self.bid_repository.delete_saved_bid(row.id)
        except Exception as error:
            self.logger.exception("Delete saved bid failed.")
            self.view.show_error("삭제 실패", f"완전 삭제에 실패했습니다.\n\n{error}")
            return
        self.refresh_saved_bids()
        self.log(f"저장 공고 완전 삭제: {row.bid_no}")
        self.start_saved_result_monitor_if_needed()

    def toggle_saved_bid_monitoring(self):
        rows = self.view.get_selected_saved_bids()
        if not rows:
            self.view.show_info("확인", "조회대상 여부를 변경할 공고를 선택해 주세요.")
            return
        enabled = not all(row.monitoring_enabled for row in rows)
        self._set_saved_bid_monitoring(rows, enabled, show_confirmation=True)

    def set_saved_bid_monitoring(self, row, enabled):
        if not row:
            return
        selected_rows = self.view.get_selected_saved_bids()
        selected_ids = [item.id for item in selected_rows]
        target_rows = (
            selected_rows
            if len(selected_rows) > 1
            and any(item.id == row.id for item in selected_rows)
            else [row]
        )
        self._set_saved_bid_monitoring(
            target_rows,
            bool(enabled),
            selected_ids=selected_ids,
            show_confirmation=False,
        )

    def _set_saved_bid_monitoring(
        self,
        rows,
        enabled,
        *,
        selected_ids=None,
        show_confirmation=False,
    ):
        rows = list(rows or [])
        if not rows:
            return
        row_ids = [row.id for row in rows]
        try:
            self.bid_repository.set_monitoring_enabled_many(row_ids, enabled)
        except Exception as error:
            self.logger.exception("Monitoring toggle failed.")
            self.view.show_error("변경 실패", f"모니터링 설정 변경에 실패했습니다.\n\n{error}")
            return

        selected_ids = list(selected_ids or row_ids)
        if not selected_ids:
            selected_ids = row_ids
        self.refresh_saved_bids(select_ids=selected_ids)
        references = ", ".join(row.bid_no for row in rows[:3])
        if len(rows) > 3:
            references += f" 외 {len(rows) - 3}건"
        self.log(
            f"저장 공고 낙찰정보 조회대상 {'ON' if enabled else 'OFF'} "
            f"{len(rows)}건: {references}"
        )
        self.start_saved_result_monitor_if_needed(show_warning=True)
        if show_confirmation:
            self.view.show_info(
                "조회대상 변경",
                f"선택한 공고 {len(rows)}건을 낙찰정보 자동 감시 대상에서 "
                f"{'포함' if enabled else '제외'}했습니다.\n\n"
                f"조회대상 ON인 공고는 {self._get_result_interval()}분마다 "
                "낙찰정보 API로 확인합니다.",
            )

    def open_saved_bid_link(self):
        row = self.view.get_selected_saved_bid()
        if not row:
            self.view.show_info("확인", "링크를 열 공고를 선택해 주세요.")
            return
        if not row.link:
            self.view.show_info("확인", "선택한 공고에 링크가 없습니다.")
            return
        self.open_link(row.link)

    def show_saved_bid_detail(self):
        rows = self.view.get_selected_saved_bids()
        if not rows:
            row = self.view.get_selected_saved_bid()
            rows = [row] if row else []
        if not rows:
            self.view.show_info("확인", "상세보기할 공고를 선택해 주세요.")
            return
        config = None
        missing_api_key_warned = False
        for row in rows:
            if row.status == "pre_spec" and row.pre_spec_no:
                if config is None:
                    config = self.read_config_from_screen()
                if not config.api_key:
                    if not missing_api_key_warned:
                        self.view.show_warning(
                            "확인",
                            "사전규격 상세정보를 조회하려면 API 키가 필요합니다.",
                        )
                        missing_api_key_warned = True
                    continue
                self._show_pre_spec_detail_async(row, config)
                continue
            try:
                detail = self._build_saved_bid_detail(row)
            except Exception as error:
                self.logger.exception("Could not build saved bid detail.")
                self.view.show_error("상세정보 조회 실패", str(error))
                continue
            self.view.show_saved_bid_detail(detail)

    def _show_pre_spec_detail_async(self, row, config):
        if row.status == "pre_spec" and row.pre_spec_no:
            self.set_status("사전규격 상세 조회 중")

            def run_pre_spec_detail():
                try:
                    api = PreSpecificationApi(
                        config.api_key,
                        timeout_seconds=int(config.request_timeout_seconds),
                        num_of_rows=int(config.num_of_rows),
                    )
                    pre_spec_detail = api.fetch_pre_specification_detail(
                        row.pre_spec_no,
                        category_hint=row.category,
                    )
                    if not pre_spec_detail:
                        raise ValueError("사전규격 상세정보를 찾지 못했습니다.")
                    detail = self._build_saved_bid_detail(
                        row,
                        pre_spec_detail=pre_spec_detail,
                    )
                    self.view.post(lambda: self.view.show_saved_bid_detail(detail))
                except Exception as error:
                    self.logger.exception("Could not load pre-specification detail.")
                    self.view.post(
                        lambda error=error: self.view.show_error(
                            "상세정보 조회 실패", str(error)
                        )
                    )
                finally:
                    self.view.post(lambda: self.set_status("대기 중"))

            threading.Thread(
                target=run_pre_spec_detail,
                daemon=True,
                name="pre-specification-detail",
            ).start()

    def _build_saved_bid_detail(self, row, pre_spec_detail=None):
        versions = self.bid_repository.list_notice_versions(row.id)
        results = self.result_repository.list_results(row.id)
        comparison = compare_latest_versions(versions)
        recipient_count = len(self.email_repository.get_saved_bid_recipient_ids(row.id))
        return build_notice_detail(
            row,
            versions,
            results,
            comparison,
            recipient_count=recipient_count,
            pre_spec_detail=pre_spec_detail,
        )

    def show_notice_version_history(self):
        row = self.view.get_selected_saved_bid()
        if not row:
            self.view.show_info("확인", "변경이력을 확인할 공고를 선택해 주세요.")
            return
        try:
            versions = self.bid_repository.list_notice_versions(row.id)
            comparisons = [
                compare_latest_versions(versions[: index + 1])
                for index in range(len(versions))
            ]
        except Exception as error:
            self.logger.exception("Could not load notice versions.")
            self.view.show_error("변경이력 조회 실패", str(error))
            return
        self.view.show_notice_version_history(row, versions, comparisons)

    @staticmethod
    def _filter_saved_bids(rows, filters):
        category = filters.get("category", "")
        stage = filters.get("stage", "")
        tracking = filters.get("tracking", "")
        filtered = []
        for row in rows:
            if category and row.category != category:
                continue
            if stage and row.stage_label() != stage:
                continue
            if tracking == "active" and not row.monitoring_enabled:
                continue
            if tracking == "paused" and row.monitoring_enabled:
                continue
            filtered.append(row)
        return filtered

    @staticmethod
    def _sort_saved_bids(rows, sort_state):
        column, descending = sort_state

        def text(value):
            return str(value or "").casefold()

        key_functions = {
            "stage": lambda row: text(row.stage_label()),
            "no": lambda row: (text(row.bid_no), text(row.bid_ord)),
            "title": lambda row: text(row.title),
            "category": lambda row: text(row.category),
            "demand": lambda row: text(row.demand_agency),
            "bid_end": lambda row: text(row.bid_end_datetime),
            "opening": lambda row: text(row.opening_datetime),
            "last_check": lambda row: text(row.last_result_check_at),
            "monitoring": lambda row: row.monitoring_enabled,
            "result": lambda row: text(row.progress_status()),
        }
        key_function = key_functions.get(column, key_functions["last_check"])
        return sorted(rows, key=key_function, reverse=bool(descending))
