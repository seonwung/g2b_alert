import threading
import time
from datetime import datetime, timedelta

from .config_manager import SEEN_FILE, STATE_FILE, load_json, save_json
from .g2b_client import CATEGORY_LABELS, G2BClient
from .keyword_matcher import match_keywords


class BidScheduler:
    def __init__(self, config, keywords, on_log, on_status, notifier, logger):
        self.config = config
        self.keywords = keywords
        self.on_log = on_log
        self.on_status = on_status
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
                self.on_log(f"\uc624\ub958 \ubc1c\uc0dd: {error}")
                self.on_status("\uc624\ub958 \ubc1c\uc0dd")

            for _ in range(int(self.config.interval) * 60):
                if not self.running:
                    break
                time.sleep(1)

    def check_once(self):
        if not self.check_lock.acquire(blocking=False):
            self.on_log("\uc774\uc804 \uc870\ud68c\uac00 \uc544\uc9c1 \ub05d\ub098\uc9c0 \uc54a\uc544 \uc774\ubc88 \uc870\ud68c\ub294 \uac74\ub108\ub701\ub2c8\ub2e4.")
            return

        try:
            self.check_cycle_count += 1
            self.on_log("")
            self.on_log("-" * 70)
            self.on_log(f"\uc870\ud68c {self.check_cycle_count}\ud68c\ucc28 \uc2dc\uc791")
            self.on_status("\uacf5\uace0 \uc870\ud68c \uc911")

            seen = set(load_json(SEEN_FILE, []))
            state = load_json(STATE_FILE, {})
            current_check_time = datetime.now()
            begin_time = self._get_begin_time(state, current_check_time)

            self.on_log(
                "\uacf5\uace0 \uc870\ud68c: "
                f"{begin_time.strftime('%Y-%m-%d %H:%M')}\ubd80\ud130 "
                f"{current_check_time.strftime('%Y-%m-%d %H:%M')}\uae4c\uc9c0"
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
                    self.on_log(f"{category_label} \uc870\ud68c \uc2e4\ud328: {error}")
                    continue

                for bid in bids:
                    if not bid.bid_no:
                        self.on_log(f"{category_label} \uacf5\uace0\ubc88\ud638 \uc5c6\uc74c: {bid.title}")
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
                    "\ub9c8\uc9c0\ub9c9 \ud655\uc778 \uc2dc\uac01 \uc800\uc7a5: "
                    f"{current_check_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                self.on_log("\uc77c\ubd80 \uc870\ud68c \uc2e4\ud328\ub85c \ub9c8\uc9c0\ub9c9 \ud655\uc778 \uc2dc\uac01\uc740 \uac31\uc2e0\ud558\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.")

            self.on_log(f"\ud655\uc778 \uc644\ub8cc: \uc0c8 \uc54c\ub9bc {new_alert_count}\uac74")
            self.on_status(f"\ucd5c\uadfc \ud655\uc778 \uc644\ub8cc / \uc0c8 \uc54c\ub9bc {new_alert_count}\uac74")
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
                self.on_log("\ub9c8\uc9c0\ub9c9 \ud655\uc778 \uc2dc\uac01\uc744 \uc77d\uc9c0 \ubabb\ud574 \ucd5c\uadfc \uae30\uc900\uc73c\ub85c \uc870\ud68c\ud569\ub2c8\ub2e4.")

        if last_check_time:
            return last_check_time - timedelta(minutes=int(self.config.overlap_minutes))
        return current_check_time - timedelta(minutes=int(self.config.bootstrap_minutes))

    def _send_alert(self, bid, matched_keywords):
        matched_keyword_text = ", ".join(matched_keywords)
        message = (
            f"[{bid.category_label}] {bid.title}\n"
            f"\uae30\uad00: {bid.agency}\n"
            f"\uc218\uc694\uae30\uad00: {bid.demand_agency}\n"
            f"\uacf5\uace0\ubc88\ud638: {bid.bid_no}\n"
            f"\ucc28\uc218: {bid.bid_ord or '000'}\n"
            f"\ub9e4\uce6d \ud0a4\uc6cc\ub4dc: {matched_keyword_text}"
        )
        self.notifier.send("\ub098\ub77c\uc7a5\ud130 \uc0c8 \uacf5\uace0", message)
        self.on_log(f"\uc54c\ub9bc: [{bid.category_label}] {bid.title}")
        self.on_log(f"\uacf5\uace0\ubc88\ud638: {bid.bid_no} / \ucc28\uc218: {bid.bid_ord or '000'}")
        self.on_log(f"\ub9e4\uce6d \ud0a4\uc6cc\ub4dc: {matched_keyword_text}")
        if bid.link:
            self.on_log(f"\ub9c1\ud06c: {bid.link}")
