class RecentAlertControllerMixin:
    def initialize_recent_alerts(self):
        self.unread_alert_count = 0
        self.recent_alerts = {}
        self.recent_alert_seq = 0

    def mark_unread_alert(self, bid=None, matched_keywords=None, unread=True):
        self.view.post(lambda: self._record_alert(bid, matched_keywords or [], unread))

    def mark_result_alert(self, notification):
        self.view.post(lambda: self._record_result_alert(notification))

    def _record_alert(self, bid, matched_keywords, unread=True):
        if bid is not None:
            self.recent_alert_seq += 1
            item_id = f"alert_{self.recent_alert_seq}"
            self.recent_alerts[item_id] = {"bid": bid, "keywords": list(matched_keywords), "link": bid.link}
            self.view.add_recent_alert(item_id, bid, matched_keywords)
            old_ids = list(self.recent_alerts)[:-100]
            for old_id in old_ids:
                self.recent_alerts.pop(old_id, None)
            self.view.remove_recent_alert_rows(old_ids)
        if unread:
            self.unread_alert_count += 1
            self.view.set_unread_alert_count(self.unread_alert_count)

    def _record_result_alert(self, notification):
        self.unread_alert_count += 1
        self.view.set_unread_alert_count(self.unread_alert_count)
        self.refresh_saved_bids()
        saved_bid = notification.get("saved_bid")
        result = notification.get("result")
        title = saved_bid.title if saved_bid else "저장 공고"
        self.log(f"낙찰정보 알림: {title} / {result.successful_bidder_name or '결과 등록'}")

    def acknowledge_alerts(self):
        self.unread_alert_count = 0
        self.view.set_unread_alert_count(0)
        self.view.select_first_alert()

    def get_selected_alert_record(self):
        item_id = self.view.get_selected_alert_id()
        return self.recent_alerts.get(item_id) if item_id else None

    def save_selected_alert_bid(self):
        record = self.get_selected_alert_record()
        if not record:
            self.view.show_info("확인", "저장할 공고를 선택해 주세요.")
            return
        item = record["bid"]
        if hasattr(item, "pre_spec_no"):
            self._save_pre_specification(item)
        else:
            self._save_bid(item)

    def open_selected_alert_link(self):
        record = self.get_selected_alert_record()
        if not record or not record.get("link"):
            self.view.show_info("확인", "링크가 있는 공고를 선택해 주세요.")
            return
        self.open_link(record["link"])

    def show_alert_keywords(self, item_id):
        record = self.recent_alerts.get(item_id)
        if not record:
            return
        self.view.show_keyword_popup(record["bid"], record["keywords"])

    def clear_recent_alerts(self):
        self.view.close_keyword_popup()
        self.recent_alerts.clear()
        self.unread_alert_count = 0
        self.view.clear_recent_alert_rows()
        self.view.set_unread_alert_count(0)
