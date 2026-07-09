import threading
import time
from datetime import datetime, timedelta

from .config_manager import SEEN_FILE, STATE_FILE, load_json, save_json
from .g2b_client import CATEGORY_LABELS, G2BClient
from .keyword_matcher import match_keywords


class BidScheduler:
    def __init__(self, config, keywords, on_log, on_status, on_alert, on_check_complete, notifier, logger):
        self.config = config
        self.keywords = keywords
        self.on_log = on_log
        self.on_status = on_status
        self.on_alert = on_alert
        self.on_check_complete = on_check_complete
        self.notifier = notifier
        self.logger = logger
        self.running = False
        self.worker = None
        self.check_lock = threading.Lock()
        self.check_cycle_count = 0

    def start(self):
        if self.worker is not None and self.worker.is_alive():
            return False

        self.running = True
        self.check_cycle_count = 0
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()
        return True

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                self.check_once()
            except Exception as error:
                self.logger.exception("Unhandled error while checking bids.")
                self.on_log(f"오류 발생: {error}")
                self.on_status("오류 발생")

            for _ in range(int(self.config.interval) * 60):
                if not self.running:
                    break
                time.sleep(1)

    def check_once(self):
        if not self.check_lock.acquire(blocking=False):
            self.on_log("이전 조회가 아직 끝나지 않아 이번 조회는 건너뜁니다.")
            return

        try:
            self.check_cycle_count += 1
            self.on_log("")
            self.on_log("-" * 70)
            self.on_log(f"조회 {self.check_cycle_count}회차 시작")
            self.on_status("공고 조회 중")

            seen = set(load_json(SEEN_FILE, []))
            state = load_json(STATE_FILE, {})
            current_check_time = datetime.now()
            begin_time = self._get_begin_time(state, current_check_time)

            self.on_log(
                "공고 조회: "
                f"{begin_time.strftime('%Y-%m-%d %H:%M')}부터 "
                f"{current_check_time.strftime('%Y-%m-%d %H:%M')}까지"
            )

            client = G2BClient(
                self.config.api_key,
                timeout_seconds=int(self.config.request_timeout_seconds),
                num_of_rows=int(self.config.num_of_rows),
            )

            all_success = True
            new_alert_count = 0

            for category in self.config.selected_categories:
                category_label = CATEGORY_LABELS.get(category, category)
                try:
                    bids = client.fetch_bids(category, begin_time, current_check_time)
                except Exception as error:
                    all_success = False
                    self.logger.exception("%s fetch failed.", category_label)
                    self.on_log(f"{category_label} 조회 실패: {error}")
                    continue

                for bid in bids:
                    if not bid.bid_no:
                        self.on_log(f"{category_label} 공고번호 없음: {bid.title}")
                        continue
                    if bid.unique_id in seen:
                        continue

                    matched_keywords = match_keywords(bid, self.keywords)
                    if not matched_keywords:
                        continue

                    self._send_alert(bid, matched_keywords)
                    seen.add(bid.unique_id)
                    new_alert_count += 1

            save_json(SEEN_FILE, sorted(seen))

            if all_success:
                save_json(STATE_FILE, {"last_check_time": current_check_time.isoformat()})
                self.on_log(
                    "마지막 확인 시각 저장: "
                    f"{current_check_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                self.on_log("일부 조회 실패로 마지막 확인 시각은 갱신하지 않았습니다.")

            self.on_log(f"확인 완료: 새 알림 {new_alert_count}건")
            self.on_status(f"최근 확인 완료 / 새 알림 {new_alert_count}건")
            self.on_check_complete(current_check_time, new_alert_count, all_success)
        finally:
            self.check_lock.release()

    def _get_begin_time(self, state, current_check_time):
        last_check_time = None
        last_check_str = state.get("last_check_time")

        if last_check_str:
            try:
                last_check_time = datetime.fromisoformat(last_check_str)
            except Exception:
                self.logger.warning("Could not read last_check_time from state file.")
                self.on_log("마지막 확인 시각을 읽지 못해 최근 기준으로 조회합니다.")

        if last_check_time:
            return last_check_time - timedelta(minutes=int(self.config.overlap_minutes))
        return current_check_time - timedelta(minutes=int(self.config.bootstrap_minutes))

    def _send_alert(self, bid, matched_keywords):
        matched_keyword_text = ", ".join(matched_keywords)
        message = (
            f"[{bid.category_label}] {bid.title}\n"
            f"기관: {bid.agency}\n"
            f"수요기관: {bid.demand_agency}\n"
            f"공고번호: {bid.bid_no}\n"
            f"차수: {bid.bid_ord or '000'}\n"
            f"매칭 키워드: {matched_keyword_text}"
        )
        if self.config.windows_notifications_enabled:
            self.notifier.send("나라장터 새 공고", message)
        else:
            self.on_log("윈도우 알림 OFF: 화면 배지로만 표시합니다.")
        self.on_alert(bid, matched_keywords)
        self.on_log(f"알림: [{bid.category_label}] {bid.title}")
        self.on_log(f"공고번호: {bid.bid_no} / 차수: {bid.bid_ord or '000'}")
        self.on_log(f"매칭 키워드: {matched_keyword_text}")
        if bid.link:
            self.on_log(f"링크: {bid.link}")
