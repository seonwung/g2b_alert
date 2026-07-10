import threading
import time
from datetime import datetime

import requests

from .database import G2BDatabase, build_result_key
from .g2b_client import parse_items


RESULT_BASE_URL = "https://apis.data.go.kr/1230000/ScsbidInfoService"

RESULT_ENDPOINTS = {
    "service": "/getOpengResultListInfoServc",
    "goods": "/getOpengResultListInfoThng",
    "works": "/getOpengResultListInfoCnstwk",
    "etc": "/getOpengResultListInfoEtc",
}


def first_value(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def describe_lookup_error(error):
    if isinstance(error, requests.exceptions.Timeout):
        return "API 응답 시간이 초과되었습니다."
    if isinstance(error, requests.exceptions.ConnectionError):
        return "네트워크 연결에 실패했습니다."
    if isinstance(error, requests.exceptions.HTTPError):
        response = error.response
        status_code = response.status_code if response is not None else ""
        if status_code == 500:
            return "나라장터 API 500 오류입니다. 아직 낙찰/개찰 결과가 등록되지 않았거나 해당 공고 유형의 결과 조회를 API가 제공하지 않을 수 있습니다."
        if status_code == 404:
            return "낙찰정보 API 경로 또는 공고 정보를 찾지 못했습니다."
        if status_code in (401, 403):
            return "API 키 권한 또는 인증 문제로 조회하지 못했습니다."
        if status_code:
            return f"낙찰정보 API HTTP {status_code} 오류입니다."
        return "낙찰정보 API HTTP 오류입니다."
    if isinstance(error, ValueError):
        return "API 응답을 JSON으로 해석하지 못했습니다."
    return str(error) or "알 수 없는 오류가 발생했습니다."


class ResultApiService:
    def __init__(self, api_key, timeout_seconds=30, num_of_rows=100):
        self.api_key = "".join((api_key or "").split())
        self.timeout_seconds = timeout_seconds
        self.num_of_rows = num_of_rows

    def fetch_results(self, saved_bid):
        category = saved_bid["category"] or "service"
        endpoint = RESULT_ENDPOINTS.get(category, RESULT_ENDPOINTS["service"])
        url = RESULT_BASE_URL + endpoint
        params = {
            "serviceKey": self.api_key,
            "bidNtceNo": saved_bid["bid_pbanc_no"],
            "bidNtceOrd": saved_bid["bid_pbanc_ord"] or "",
            "pageNo": "1",
            "numOfRows": str(self.num_of_rows),
            "type": "json",
        }
        response = requests.get(url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        return [self._normalize(item) for item in parse_items(response.json())]

    def _normalize(self, item):
        result = {
            "result_type": first_value(item, "rsltTyNm", "opengRsltDivNm", "bidClsfcNoNm", "bidNtceNm"),
            "opening_datetime": first_value(item, "opengDt", "rlOpengDt", "opengDate"),
            "successful_bidder_name": first_value(
                item,
                "sucsfbidCorpNm",
                "fnlSucsfCorpNm",
                "bidwinnrNm",
                "prcbdrNm",
                "entrpsNm",
            ),
            "business_number": first_value(
                item,
                "sucsfbidBizrno",
                "fnlSucsfBizrno",
                "bizrno",
                "prcbdrBizrno",
            ),
            "successful_bid_amount": first_value(
                item,
                "sucsfbidAmt",
                "fnlSucsfAmt",
                "bidprcAmt",
                "bidAmt",
            ),
            "successful_bid_rate": first_value(item, "sucsfbidRate", "bidRate", "sucsfbidLwltRate"),
            "ranking": first_value(item, "bidRank", "rank", "prcbdrRank"),
            "result_status": first_value(item, "bidwinnrSlctnAplBssNm", "opengRsltNm", "rsltSttusNm", "bidResultNm"),
            "raw": item,
        }
        result["result_key"] = build_result_key(result)
        return result


class ResultMonitorService:
    def __init__(self, config, database=None, notifier=None, logger=None, email_alert_service=None):
        self.config = config
        self.database = database or G2BDatabase()
        self.notifier = notifier
        self.logger = logger
        self.email_alert_service = email_alert_service

    def check_saved_bids(self, on_log=None):
        if not self.config.api_key:
            raise ValueError("API 키가 없어 낙찰정보를 조회할 수 없습니다.")

        api = ResultApiService(
            self.config.api_key,
            timeout_seconds=int(self.config.request_timeout_seconds),
            num_of_rows=int(self.config.num_of_rows),
        )
        checked = 0
        failed = 0
        no_result = 0
        new_results = 0
        notifications = []
        reports = []

        for saved_bid in self.database.list_monitoring_bids():
            checked += 1
            try:
                results = api.fetch_results(saved_bid)
            except Exception as error:
                self.database.update_result_check_time(saved_bid["id"])
                failed += 1
                reason = describe_lookup_error(error)
                reports.append(
                    {
                        "bid_no": saved_bid["bid_pbanc_no"],
                        "bid_ord": saved_bid["bid_pbanc_ord"],
                        "bid_name": saved_bid["bid_name"],
                        "status": "failed",
                        "reason": reason,
                    }
                )
                if self.logger:
                    self.logger.exception("Result fetch failed for %s", saved_bid["bid_pbanc_no"])
                if on_log:
                    on_log(f"낙찰정보 조회 실패: {saved_bid['bid_pbanc_no']} - {reason}")
                continue

            has_result = bool(results)
            self.database.update_result_check_time(saved_bid["id"], result_found=has_result)
            if not has_result:
                no_result += 1
                reason = "아직 낙찰/개찰 결과가 등록되지 않았습니다."
                reports.append(
                    {
                        "bid_no": saved_bid["bid_pbanc_no"],
                        "bid_ord": saved_bid["bid_pbanc_ord"],
                        "bid_name": saved_bid["bid_name"],
                        "status": "no_result",
                        "reason": reason,
                    }
                )
                if on_log:
                    on_log(f"낙찰정보 결과 없음: {saved_bid['bid_pbanc_no']} - {reason}")
                continue

            saved_count = 0
            for result in results:
                is_new = self.database.save_result(saved_bid, result)
                if not is_new:
                    continue
                saved_count += 1
                new_results += 1
                if self.email_alert_service:
                    self.email_alert_service.queue_bid_result(saved_bid, result)
                notification = self._build_notification(saved_bid, result)
                if not self._should_notify(result):
                    continue
                if self.database.record_notification(
                    saved_bid["id"],
                    "bid_result",
                    result["result_key"],
                    notification["message"],
                ):
                    notifications.append(notification)
            reports.append(
                {
                    "bid_no": saved_bid["bid_pbanc_no"],
                    "bid_ord": saved_bid["bid_pbanc_ord"],
                    "bid_name": saved_bid["bid_name"],
                    "status": "found",
                    "reason": f"결과 {len(results)}건 확인, 새 결과 {saved_count}건 저장",
                }
            )

        return {
            "checked": checked,
            "failed": failed,
            "no_result": no_result,
            "new_results": new_results,
            "notifications": notifications,
            "reports": reports,
            "checked_at": datetime.now(),
        }

    def _should_notify(self, result):
        if not bool(getattr(self.config, "notify_all_opening_results", True)):
            return False
        company_name = (getattr(self.config, "company_name", "") or "").strip()
        business_number = (getattr(self.config, "business_number", "") or "").replace("-", "").strip()
        if business_number:
            found_number = (result.get("business_number") or "").replace("-", "").strip()
            if found_number and found_number == business_number:
                return True
        if company_name and company_name in (result.get("successful_bidder_name") or ""):
            return True
        return bool(getattr(self.config, "notify_all_opening_results", True))

    def _build_notification(self, saved_bid, result):
        title = "[낙찰정보 등록]"
        company = result.get("successful_bidder_name") or "낙찰/개찰정보"
        amount = result.get("successful_bid_amount")
        status = result.get("result_status")
        message_lines = [
            f"{saved_bid['bid_name'] or saved_bid['bid_pbanc_no']} 결과가 등록되었습니다.",
            f"업체: {company}",
        ]
        if amount:
            message_lines.append(f"금액: {amount}")
        if status:
            message_lines.append(f"상태: {status}")
        message_lines.append(f"공고번호: {saved_bid['bid_pbanc_no']} / 차수: {saved_bid['bid_pbanc_ord'] or '000'}")
        return {
            "title": title,
            "message": "\n".join(message_lines),
            "saved_bid": saved_bid,
            "result": result,
        }


class SavedResultScheduler:
    def __init__(
        self,
        config,
        database,
        on_log,
        on_notification,
        on_check_complete,
        notifier,
        logger,
        email_alert_service=None,
    ):
        self.config = config
        self.database = database
        self.on_log = on_log
        self.on_notification = on_notification
        self.on_check_complete = on_check_complete
        self.notifier = notifier
        self.logger = logger
        self.email_alert_service = email_alert_service
        self.running = False
        self.worker = None
        self.check_lock = threading.Lock()

    def start(self):
        if self.worker is not None and self.worker.is_alive():
            return False
        self.running = True
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()
        return True

    def stop(self):
        self.running = False

    def update_config(self, config):
        self.config = config

    def _loop(self):
        while self.running:
            try:
                self.check_once()
            except Exception as error:
                if self.logger:
                    self.logger.exception("Saved result monitor failed.")
                self.on_log(f"낙찰정보 자동 감시 오류: {error}")

            interval_seconds = max(1, int(getattr(self.config, "result_interval", self.config.interval))) * 60
            for _ in range(interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

    def check_once(self):
        if not self.check_lock.acquire(blocking=False):
            self.on_log("이전 낙찰정보 조회가 아직 끝나지 않아 이번 자동 조회는 건너뜁니다.")
            return

        try:
            monitor = ResultMonitorService(
                self.config,
                database=self.database,
                notifier=self.notifier,
                logger=self.logger,
                email_alert_service=self.email_alert_service,
            )
            summary = monitor.check_saved_bids(on_log=None)
            for notification in summary["notifications"]:
                if self.config.windows_notifications_enabled:
                    self.notifier.send(notification["title"], notification["message"])
                self.on_notification(notification)

            self._log_important_reports(summary)
            self.on_check_complete(summary)
        finally:
            self.check_lock.release()

    def _log_important_reports(self, summary):
        checked = summary["checked"]
        failed = summary.get("failed", 0)
        new_results = summary["new_results"]
        if checked == 0:
            self.on_log("낙찰정보 자동 감시: 조회대상 공고가 없습니다.")
            return
        if failed or new_results:
            self.on_log(
                f"낙찰정보 자동 감시 완료: 대상 {checked}건 / "
                f"실패 {failed}건 / 새 결과 {new_results}건"
            )
        for report in summary.get("reports", []):
            status = report.get("status")
            reason = report.get("reason") or ""
            if status == "failed" or (status == "found" and "새 결과 0건" not in reason):
                bid_no = report.get("bid_no") or "-"
                bid_ord = report.get("bid_ord") or "000"
                self.on_log(f"낙찰정보 자동 감시: {bid_no} / 차수 {bid_ord} - {reason}")
