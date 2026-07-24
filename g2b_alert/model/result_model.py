from datetime import datetime

from .notice_version_model import compare_latest_versions


def describe_lookup_error(error):
    status_code = getattr(error, "status_code", None)
    kind = getattr(error, "kind", "")
    if status_code == 500:
        return "나라장터 API 500 오류입니다. 아직 낙찰/개찰 결과가 등록되지 않았거나 해당 공고 유형의 결과 조회를 API가 제공하지 않을 수 있습니다."
    if status_code == 404:
        return "낙찰정보 API 경로 또는 공고 정보를 찾지 못했습니다."
    if status_code in (401, 403):
        return "API 키 권한 또는 인증 문제로 조회하지 못했습니다."
    if kind == "timeout":
        return "API 응답 시간이 초과되었습니다."
    if kind == "connection":
        return "네트워크 연결에 실패했습니다."
    if kind == "invalid_json":
        return "API 응답을 JSON으로 해석하지 못했습니다."
    if status_code:
        return f"낙찰정보 API HTTP {status_code} 오류입니다."
    return str(error) or "알 수 없는 오류가 발생했습니다."


class ResultMonitorService:
    """Run one saved-bid result cycle without scheduling or UI work."""

    def __init__(
        self,
        config,
        bid_repository,
        result_repository,
        result_api,
        error_counts=None,
        bid_api=None,
        contract_process_api=None,
    ):
        self.config = config
        self.bid_repository = bid_repository
        self.result_repository = result_repository
        self.result_api = result_api
        self.bid_api = bid_api
        self.contract_process_api = contract_process_api
        self.error_counts = error_counts if error_counts is not None else {}

    def check_saved_bids(self):
        if not self.config.api_key:
            raise ValueError("API 키가 없어 낙찰정보를 조회할 수 없습니다.")

        checked = failed = no_result = new_results = 0
        notifications = []
        new_result_events = []
        change_events = []
        transition_events = []
        tracking_reports = []
        reports = []

        for saved_bid in self.bid_repository.list_monitoring_bids():
            checked += 1
            transitioned = False
            if (
                saved_bid.status == "pre_spec"
                and saved_bid.pre_spec_no
                and self.contract_process_api
            ):
                saved_bid, transition_event, tracking_report = (
                    self._check_pre_specification_transition(saved_bid)
                )
                tracking_reports.append(tracking_report)
                if transition_event:
                    transition_events.append(transition_event)
                    transitioned = True
                if saved_bid.status == "pre_spec":
                    # A pre-specification transition lookup is a real tracking
                    # attempt even when no related bid has been published yet.
                    # Persist it so the saved-notice table does not misleadingly
                    # leave "최근 조회시도" empty.
                    self.bid_repository.update_result_check_time(saved_bid.id)
                    continue
            if self.bid_api and not transitioned:
                saved_bid, change_event, tracking_report = self._check_notice_change(saved_bid)
                tracking_reports.append(tracking_report)
                if saved_bid is None:
                    # The user deleted the notice while this cycle was waiting
                    # for the API response. Do not process or recreate it.
                    continue
                if change_event:
                    change_events.append(change_event)
            try:
                results = self.result_api.fetch_results(saved_bid)
            except Exception as error:
                self.bid_repository.update_result_check_time(saved_bid.id)
                failed += 1
                reports.append(self._failure_report(saved_bid, error))
                continue

            previous_error = self.error_counts.pop(saved_bid.id, None)
            has_result = bool(results)
            self.bid_repository.update_result_check_time(saved_bid.id, result_found=has_result)
            if not has_result:
                no_result += 1
                reports.append(
                    {
                        "bid_no": saved_bid.bid_no,
                        "bid_ord": saved_bid.bid_ord,
                        "bid_name": saved_bid.title,
                        "status": "no_result",
                        "reason": "아직 낙찰/개찰 결과가 등록되지 않았습니다.",
                        "recovered_after": previous_error[1] if previous_error else 0,
                    }
                )
                continue

            saved_count = 0
            for result in results:
                if not self.result_repository.save_result(saved_bid, result):
                    continue
                saved_count += 1
                new_results += 1
                new_result_events.append({"saved_bid": saved_bid, "result": result})
                notification = self._build_notification(saved_bid, result)
                if self._should_notify(result) and self.result_repository.record_notification(
                    saved_bid.id, "bid_result", result.result_key, notification["message"]
                ):
                    notifications.append(notification)

            reports.append(
                {
                    "bid_no": saved_bid.bid_no,
                    "bid_ord": saved_bid.bid_ord,
                    "bid_name": saved_bid.title,
                    "status": "found",
                    "reason": f"결과 {len(results)}건 확인, 새 결과 {saved_count}건 저장",
                    "recovered_after": previous_error[1] if previous_error else 0,
                }
            )

        return {
            "checked": checked,
            "failed": failed,
            "tracking_failed": sum(
                1 for report in tracking_reports if report.get("status") == "failed"
            ),
            "no_result": no_result,
            "new_results": new_results,
            "notifications": notifications,
            "new_result_events": new_result_events,
            "change_events": change_events,
            "transition_events": transition_events,
            "tracking_reports": tracking_reports,
            "reports": reports,
            "checked_at": datetime.now(),
        }

    def _check_pre_specification_transition(self, saved_bid):
        try:
            bid = self.contract_process_api.find_bid_for_pre_specification(
                saved_bid.pre_spec_no,
                saved_bid.category,
            )
        except Exception as error:
            return (
                saved_bid,
                None,
                {
                    "bid_no": saved_bid.pre_spec_no,
                    "status": "failed",
                    "reason": str(error) or "계약과정통합공개 API 조회에 실패했습니다.",
                },
            )
        if not bid:
            return (
                saved_bid,
                None,
                {
                    "bid_no": saved_bid.pre_spec_no,
                    "status": "waiting",
                    "reason": "관련 입찰공고가 아직 확인되지 않았습니다.",
                },
            )

        if self.bid_api:
            try:
                detailed_bid = self.bid_api.fetch_bid_by_no(
                    f"{bid.bid_no}-{bid.bid_ord}" if bid.bid_ord else bid.bid_no,
                    category_hint=bid.category,
                )
                if detailed_bid:
                    bid = detailed_bid
            except Exception:
                # The transition itself remains valid even if the detail API is
                # temporarily unavailable. A later tracking cycle can refresh it.
                pass

        transitioned = self.bid_repository.transition_pre_specification(saved_bid.id, bid)
        if not transitioned:
            return (
                saved_bid,
                None,
                {
                    "bid_no": saved_bid.pre_spec_no,
                    "status": "failed",
                    "reason": "입찰공고 전환 정보를 저장하지 못했습니다.",
                },
            )
        message = (
            f"{transitioned.title or transitioned.bid_no}\n"
            f"사전규격 {saved_bid.pre_spec_no} → "
            f"입찰공고 {transitioned.bid_no}-{transitioned.bid_ord or '000'}"
        )
        notification_key = f"{saved_bid.pre_spec_no}:{transitioned.unique_id}"
        should_notify = self.result_repository.record_notification(
            transitioned.id,
            "pre_spec_transition",
            notification_key,
            message,
        )
        event = {
            "saved_bid": transitioned,
            "pre_spec_no": saved_bid.pre_spec_no,
            "message": message,
            "should_notify": should_notify,
        }
        return (
            transitioned,
            event,
            {
                "bid_no": transitioned.bid_no,
                "status": "transitioned",
                "reason": (
                    f"사전규격 {saved_bid.pre_spec_no} → "
                    f"입찰공고 {transitioned.bid_no}-{transitioned.bid_ord or '000'}"
                ),
            },
        )

    def _check_notice_change(self, saved_bid):
        previous_order = saved_bid.bid_ord or ""
        try:
            latest = self.bid_api.fetch_bid_by_no(
                saved_bid.bid_no,
                category_hint=saved_bid.category,
            )
        except Exception as error:
            return (
                saved_bid,
                None,
                {
                    "bid_no": saved_bid.bid_no,
                    "status": "failed",
                    "reason": describe_lookup_error(error),
                },
            )
        if not latest:
            return (
                saved_bid,
                None,
                {
                    "bid_no": saved_bid.bid_no,
                    "status": "not_found",
                    "reason": "최신 입찰공고 정보를 찾지 못했습니다.",
                },
            )

        updated_id, _created = self.bid_repository.save_bid(
            latest,
            existing_saved_id=saved_bid.id,
        )
        if updated_id is None:
            return (
                None,
                None,
                {
                    "bid_no": saved_bid.bid_no,
                    "status": "deleted",
                    "reason": "조회 중 삭제되어 갱신을 건너뛰었습니다.",
                },
            )
        current = self.bid_repository.find_saved_bid(saved_bid.bid_no) or saved_bid
        current_order = current.bid_ord or ""
        if current_order == previous_order:
            return (
                current,
                None,
                {
                    "bid_no": current.bid_no,
                    "status": "unchanged",
                    "reason": f"현재 차수 {current_order or '000'}",
                },
            )

        versions = self.bid_repository.list_notice_versions(current.id)
        comparison = compare_latest_versions(versions)
        notification_key = f"{previous_order or '000'}->{current_order or '000'}"
        message = self._build_change_message(current, previous_order, comparison)
        should_notify = self.result_repository.record_notification(
            current.id,
            "bid_change",
            notification_key,
            message,
        )
        event = {
            "saved_bid": current,
            "previous_order": previous_order or "000",
            "current_order": current_order or "000",
            "comparison": comparison,
            "message": message,
            "should_notify": should_notify,
        }
        return (
            current,
            event,
            {
                "bid_no": current.bid_no,
                "status": "changed",
                "reason": f"차수 {previous_order or '000'} → {current_order or '000'}",
            },
        )

    @staticmethod
    def _build_change_message(saved_bid, previous_order, comparison):
        current_order = saved_bid.bid_ord or "000"
        lines = [
            saved_bid.title or saved_bid.bid_no,
            f"차수: {previous_order or '000'} → {current_order}",
        ]
        for change in (comparison.get("changes") or [])[:3]:
            lines.append(f"{change['label']}: {change['before']} → {change['after']}")
        if len(comparison.get("changes") or []) > 3:
            lines.append(f"외 {len(comparison['changes']) - 3}개 항목 변경")
        return "\n".join(lines)

    def _failure_report(self, saved_bid, error):
        reason = describe_lookup_error(error)
        signature = getattr(error, "signature", error.__class__.__name__)
        previous = self.error_counts.get(saved_bid.id)
        failure_count = previous[1] + 1 if previous and previous[0] == signature else 1
        self.error_counts[saved_bid.id] = (signature, failure_count)
        return {
            "bid_no": saved_bid.bid_no,
            "bid_ord": saved_bid.bid_ord,
            "bid_name": saved_bid.title,
            "status": "failed",
            "reason": reason,
            "failure_count": failure_count,
            "should_log_detail": failure_count == 1 or failure_count % 10 == 0,
        }

    def _should_notify(self, result):
        return bool(getattr(self.config, "notify_all_opening_results", True))

    @staticmethod
    def _build_notification(saved_bid, result):
        company = result.successful_bidder_name or "낙찰/개찰정보"
        lines = [f"{saved_bid.title or saved_bid.bid_no} 결과가 등록되었습니다.", f"업체: {company}"]
        if result.successful_bid_amount:
            lines.append(f"금액: {result.successful_bid_amount}")
        if result.result_status:
            lines.append(f"상태: {result.result_status}")
        lines.append(f"공고번호: {saved_bid.bid_no} / 차수: {saved_bid.bid_ord or '000'}")
        return {
            "title": "[낙찰정보 등록]",
            "message": "\n".join(lines),
            "saved_bid": saved_bid,
            "result": result,
        }
