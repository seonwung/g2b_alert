"""Screen-level QWidget implementations matching the g2bAlert Figma file."""

from __future__ import annotations

import uuid
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from .qt_common import Card, FigmaComboBox, Page, button, clear_layout, labeled_row, muted, setup_table
from .resources import local_icon
from .design_tokens import Colors
from .styles import DANGER, PRIMARY, PRIMARY_DARK, SUB_TEXT


CATEGORY_LABELS = {"service": "용역", "goods": "물품", "works": "공사", "etc": "기타"}
OPERATOR_OPTIONS = {"OR": "or", "AND": "and", "제외": "exclude"}
TARGET_OPTIONS = {
    "입찰공고": ("bid_lifecycle",),
    "사전규격": ("prespec",),
    "사전규격 + 입찰공고": ("prespec", "bid_lifecycle"),
}


class ConditionDialog(QDialog):
    def __init__(self, rule=None, parent=None):
        super().__init__(parent)
        self.rule = dict(rule or {})
        self.setWindowTitle("조건 수정" if rule else "조건 추가")
        self.resize(606, 590)
        self.setMinimumSize(606, 560)
        root = QVBoxLayout(self)
        root.setContentsMargins(23, 18, 23, 20)
        root.setSpacing(14)
        title = QLabel(self.windowTitle())
        title.setProperty("role", "title")
        root.addWidget(title)
        self.name = QLineEdit(self.rule.get("name") or self.rule.get("keyword", ""))
        self.name.setPlaceholderText("키워드 조건명 입력")
        root.addWidget(QLabel("키워드 조건명"))
        root.addWidget(self.name)

        keyword_label = QLabel("키워드")
        root.addWidget(keyword_label)
        keyword_row = QHBoxLayout()
        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText("키워드를 하나씩 입력해 주세요")
        self.keyword.returnPressed.connect(self.add_keyword)
        keyword_row.addWidget(self.keyword, 1)
        keyword_row.addWidget(button("등록", self.add_keyword, primary=True))
        root.addLayout(keyword_row)
        self.keywords = []
        for value in str(self.rule.get("keyword", "") or "").replace("\n", ",").split(","):
            value = value.strip()
            if value and value.casefold() not in {item.casefold() for item in self.keywords}:
                self.keywords.append(value)
        self.keyword_cards = QWidget()
        self.keyword_cards.setMinimumHeight(46)
        self.keyword_cards_layout = QGridLayout(self.keyword_cards)
        self.keyword_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.keyword_cards_layout.setHorizontalSpacing(8)
        self.keyword_cards_layout.setVerticalSpacing(8)
        keyword_scroll = QScrollArea()
        keyword_scroll.setWidgetResizable(True)
        keyword_scroll.setFrameShape(QFrame.Shape.NoFrame)
        keyword_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        keyword_scroll.setFixedHeight(86)
        keyword_scroll.setWidget(self.keyword_cards)
        root.addWidget(keyword_scroll)
        self._render_keyword_cards()

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        self.operator = FigmaComboBox()
        self.operator.addItems(OPERATOR_OPTIONS)
        wanted_operator = self.rule.get("operator", "or")
        self.operator.setCurrentText(next((k for k, v in OPERATOR_OPTIONS.items() if v == wanted_operator), "OR"))
        self.target = FigmaComboBox()
        self.target.addItems(TARGET_OPTIONS)
        targets = set(self.rule.get("targets") or ["bid_lifecycle"])
        self.target.setCurrentText(next((k for k, v in TARGET_OPTIONS.items() if set(v) == targets), "입찰공고"))
        form.addRow("검색 방식", self.operator)
        form.addRow("검색 대상", self.target)
        category_box = QWidget()
        category_layout = QHBoxLayout(category_box)
        category_layout.setContentsMargins(0, 0, 0, 0)
        self.categories = {}
        selected = set(self.rule.get("categories") or CATEGORY_LABELS)
        for key, label in CATEGORY_LABELS.items():
            check = QCheckBox(label)
            check.setChecked(key in selected)
            self.categories[key] = check
            category_layout.addWidget(check)
        category_layout.addStretch()
        form.addRow("업무 구분", category_box)
        root.addLayout(form)
        root.addWidget(muted("공고명, 공고기관, 수요기관에서 키워드를 검색합니다."))
        root.addStretch()
        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        actions.button(QDialogButtonBox.StandardButton.Save).setText("저장")
        actions.button(QDialogButtonBox.StandardButton.Save).setProperty("primary", True)
        actions.button(QDialogButtonBox.StandardButton.Save).setIcon(local_icon("check-L-on.svg"))
        actions.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        actions.accepted.connect(self._validate)
        actions.rejected.connect(self.reject)
        root.addWidget(actions)

    def add_keyword(self):
        raw = self.keyword.text().strip()
        if not raw:
            return
        candidates = [value.strip() for value in raw.replace("\n", ",").split(",") if value.strip()]
        existing = {value.casefold() for value in self.keywords}
        for value in candidates:
            if value.casefold() not in existing:
                self.keywords.append(value)
                existing.add(value.casefold())
        self.keyword.clear()
        self._render_keyword_cards()

    def remove_keyword(self, value):
        self.keywords = [item for item in self.keywords if item != value]
        self._render_keyword_cards()

    def _render_keyword_cards(self):
        clear_layout(self.keyword_cards_layout)
        for index, value in enumerate(self.keywords):
            chip = QFrame()
            chip.setStyleSheet(
                "QFrame {background:#DAE7FF;border:0;border-radius:17px;}"
                "QLabel {color:#154CB2;font-size:11pt;font-weight:600;border:0;}"
                "QPushButton {background:transparent;border:0;min-width:22px;min-height:22px;padding:0;}"
            )
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(12, 4, 6, 4)
            chip_layout.setSpacing(4)
            chip_layout.addWidget(QLabel(value))
            remove = button("", lambda _checked=False, item=value: self.remove_keyword(item), height=24, icon="delete.svg")
            remove.setToolTip(f"{value} 삭제")
            chip_layout.addWidget(remove)
            self.keyword_cards_layout.addWidget(chip, index // 3, index % 3)
        self.keyword_cards_layout.setColumnStretch(3, 1)

    def _validate(self):
        self.add_keyword()
        if not self.name.text().strip():
            QMessageBox.warning(self, "확인", "키워드 조건명을 입력해 주세요.")
            return
        if not self.keywords:
            QMessageBox.warning(self, "확인", "감시할 키워드를 하나 이상 등록해 주세요.")
            return
        if not any(check.isChecked() for check in self.categories.values()):
            QMessageBox.warning(self, "확인", "업무 구분을 하나 이상 선택해 주세요.")
            return
        self.accept()

    def value(self):
        keyword = ", ".join(self.keywords)
        return {
            "id": str(self.rule.get("id") or uuid.uuid4().hex),
            "name": self.name.text().strip(),
            "keyword": keyword,
            "operator": OPERATOR_OPTIONS[self.operator.currentText()],
            "categories": [key for key, check in self.categories.items() if check.isChecked()],
            "targets": list(TARGET_OPTIONS[self.target.currentText()]),
            "enabled": bool(self.rule.get("enabled", False)),
        }


class KeywordRuleRow(QFrame):
    toggleRequested = Signal(str, bool)
    editRequested = Signal(str)
    deleteRequested = Signal(str)
    recipientsRequested = Signal(str)

    def __init__(self, index, rule, parent=None):
        super().__init__(parent)
        self.rule = dict(rule)
        self.setStyleSheet("QFrame {background:#FFFFFF;border:1px solid #D8E5FF;border-radius:10px;} QLabel,QPushButton{border:none;}")
        self.setFixedHeight(58)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 7, 10, 7)
        layout.setSpacing(10)
        number = QLabel(str(index).zfill(2))
        number.setStyleSheet("font-size:15pt;font-weight:700;color:#5487E4")
        number.setFixedWidth(34)
        layout.addWidget(number)
        text = QVBoxLayout()
        text.setSpacing(1)
        title = QLabel(self.rule.get("name") or self.rule.get("keyword") or "새 조건")
        title.setStyleSheet("font-size:11pt;font-weight:700")
        summary = QLabel(self._summary())
        summary.setStyleSheet("font-size:9pt;color:#767676")
        text.addWidget(title)
        text.addWidget(summary)
        layout.addLayout(text, 1)
        recipients = button("수신 설정", lambda: self.recipientsRequested.emit(self.rule["id"]), height=30, icon="notice.svg")
        recipients.setFixedWidth(92)
        layout.addWidget(recipients)
        enabled = bool(self.rule.get("enabled"))
        self.toggle = button(
            "감시 중지" if enabled else "감시 시작",
            self._toggle,
            primary=not enabled,
            danger=enabled,
            height=30,
        )
        self.toggle.setFixedWidth(88)
        layout.addWidget(self.toggle)
        edit = button("수정", lambda: self.editRequested.emit(self.rule["id"]), height=30)
        edit.setVisible(False)
        layout.addWidget(edit)
        delete = button("", lambda: self.deleteRequested.emit(self.rule["id"]), delete=True, height=30, icon="trash.svg")
        delete.setToolTip("조건 삭제")
        layout.addWidget(delete)

    def _summary(self):
        operator = {"or": "OR", "and": "AND", "exclude": "제외"}.get(self.rule.get("operator"), "OR")
        categories = ", ".join(CATEGORY_LABELS.get(v, v) for v in self.rule.get("categories", []))
        target = next((k for k, v in TARGET_OPTIONS.items() if set(v) == set(self.rule.get("targets", []))), "입찰공고")
        return f"{operator} · {self.rule.get('keyword','')} · {categories or '전체'} · {target}"

    def _toggle(self):
        self.toggleRequested.emit(self.rule["id"], not bool(self.rule.get("enabled")))

    def set_enabled_state(self, enabled, busy=False):
        self.rule["enabled"] = bool(enabled)
        self.toggle.setText("적용 중" if busy else ("감시 중지" if enabled else "감시 시작"))
        self.toggle.setEnabled(not busy)
        self.toggle.setProperty("primary", bool(not enabled and not busy))
        self.toggle.setProperty("danger", bool(enabled and not busy))
        self.toggle.style().unpolish(self.toggle)
        self.toggle.style().polish(self.toggle)


class KeywordMonitorPage(Page):
    def __init__(self, actions, initial_state, recipient_callback, parent=None):
        super().__init__(parent)
        self.actions = actions
        self.recipient_callback = recipient_callback
        self.rules = [dict(rule) for rule in initial_state.keyword_rules]
        self.manual_running = False
        self.status_bar = Card()
        self.status_bar.setFixedHeight(64)
        status_row = QHBoxLayout()
        self.status = QLabel("대기중")
        self.status.setProperty("role", "title")
        self.status.setStyleSheet("color:#2F9E72")
        self.last_check = muted("마지막 확인  -")
        self.next_check = muted("다음 확인 예정  -")
        self.monitor_summary = muted("감시 조건: 대기중")
        status_text = QHBoxLayout()
        status_text.setSpacing(16)
        status_text.addWidget(self.status)
        status_text.addWidget(self.last_check)
        status_text.addWidget(self.next_check)
        status_row.addLayout(status_text, 1)
        self.unread = button("미확인 0", actions.acknowledge_alerts, icon="notice.svg")
        self.unread.hide()
        status_row.addWidget(self.unread)
        self.check_now = button("즉시 조회", actions.check_now)
        self.start = button("감시 시작", actions.start, primary=True)
        self.stop = button("감시 중지", actions.stop, danger=True)
        status_row.addWidget(self.check_now)
        status_row.addWidget(self.start)
        status_row.addWidget(self.stop)
        self.status_bar.layout.addLayout(status_row)
        self.monitor_summary.hide()
        self.layout.addWidget(self.status_bar)

        conditions = Card()
        conditions.setFixedHeight(274)
        top = QHBoxLayout()
        label = QLabel("감시 조건")
        label.setProperty("role", "section")
        top.addWidget(label)
        top.addStretch()
        top.addWidget(button("조건 추가", self.add_rule, primary=True, icon="add.svg"))
        conditions.layout.addLayout(top)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget {background:white;}")
        self.rows_widget = QWidget()
        self.rows_widget.setStyleSheet("background:white")
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(8)
        self.rows_layout.addStretch()
        scroll.setWidget(self.rows_widget)
        conditions.layout.addWidget(scroll)
        self.layout.addWidget(conditions)

        alerts = Card()
        alert_header = QHBoxLayout()
        title = QLabel("최근 알림")
        title.setProperty("role", "section")
        alert_header.addWidget(title)
        alert_header.addStretch()
        alert_header.addWidget(button("목록 지우기", actions.clear_recent_alerts, icon="trash.svg"))
        alert_header.addWidget(button("선택한 공고 저장", actions.save_selected_alert_bid, primary=True, icon="check-L-on.svg"))
        alerts.layout.addLayout(alert_header)
        self.alert_table = QTableWidget()
        setup_table(self.alert_table, ["시간", "공고 구분", "공고명", "감시 조건명", "공고 바로가기"], [68, 90, 390, 190, 100])
        self.alert_table.cellDoubleClicked.connect(self._alert_double_click)
        self.alert_table.cellClicked.connect(self._alert_click)
        alerts.layout.addWidget(self.alert_table)
        self.layout.addWidget(alerts, 1)
        self._render_rules()

    def _render_rules(self):
        clear_layout(self.rows_layout)
        self.row_widgets = {}
        for index, rule in enumerate(self.rules, 1):
            row = KeywordRuleRow(index, rule)
            row.toggleRequested.connect(self._toggle_rule)
            row.editRequested.connect(self.edit_rule)
            row.deleteRequested.connect(self.delete_rule)
            row.recipientsRequested.connect(self.recipient_callback)
            self.rows_layout.addWidget(row)
            self.row_widgets[rule["id"]] = row
        self.rows_layout.addStretch()

    def add_rule(self):
        dialog = ConditionDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rules.append(dialog.value())
            self._render_rules()
            self.actions.keyword_rules_changed()

    def edit_rule(self, rule_id):
        rule = next((r for r in self.rules if r["id"] == rule_id), None)
        if not rule:
            return
        dialog = ConditionDialog(rule, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rules[self.rules.index(rule)] = dialog.value()
            self._render_rules()
            self.actions.keyword_rules_changed()

    def delete_rule(self, rule_id):
        if QMessageBox.question(self, "조건 삭제", "해당 조건을 삭제하시겠습니까?") != QMessageBox.StandardButton.Yes:
            return
        self.rules = [rule for rule in self.rules if rule["id"] != rule_id]
        self._render_rules()
        self.actions.keyword_rules_changed()
        QMessageBox.information(self, "안내", "조건을 삭제했습니다.")

    def _toggle_rule(self, rule_id, enabled):
        rule = next((r for r in self.rules if r["id"] == rule_id), None)
        if not rule:
            return
        rule["enabled"] = enabled
        self.row_widgets[rule_id].set_enabled_state(enabled, busy=True)
        self.actions.set_keyword_rule_monitoring(dict(rule), enabled, lambda: self.row_widgets.get(rule_id) and self.row_widgets[rule_id].set_enabled_state(enabled))

    def _alert_click(self, row, column):
        self.alert_table.selectRow(row)
        if column == 3:
            item = self.alert_table.item(row, 0)
            if item:
                self.actions.show_alert_keywords(item.data(Qt.ItemDataRole.UserRole))

    def _alert_double_click(self, row, column):
        self.alert_table.selectRow(row)
        if column == 3:
            self._alert_click(row, column)
        else:
            self.actions.open_selected_alert_link()


class SavedBidsPage(Page):
    def __init__(self, actions, initial_state, parent=None):
        super().__init__(parent)
        self.actions = actions
        self.lookup_notice = None
        self.saved_rows = {}
        self.sort_column = "last_check"
        self.sort_descending = True
        top = QHBoxLayout()
        lookup = Card("공고 직접 조회")
        lookup.setFixedHeight(148)
        controls = QHBoxLayout()
        self.lookup_type = FigmaComboBox()
        self.lookup_type.addItems(["자동 감지", "입찰공고", "사전규격"])
        self.lookup_reference = QLineEdit()
        self.lookup_reference.setPlaceholderText("공고번호 또는 나라장터 URL")
        controls.addWidget(self.lookup_type)
        controls.addWidget(self.lookup_reference, 1)
        self.lookup_button = button("조회", actions.lookup_notice_by_no, primary=True)
        controls.addWidget(self.lookup_button)
        lookup.layout.addLayout(controls)
        top.addWidget(lookup, 5)
        result = Card("조회 결과")
        result.setFixedHeight(148)
        result_row = QHBoxLayout()
        self.lookup_summary = muted("공고를 조회하면 결과가 표시됩니다.")
        result_row.addWidget(self.lookup_summary, 1)
        self.save_lookup = button("저장", actions.save_lookup_notice, primary=True, icon="check-L-on.svg")
        self.save_lookup.setEnabled(False)
        self.save_lookup.setVisible(False)
        result_row.addWidget(self.save_lookup)
        result.layout.addLayout(result_row)
        top.addWidget(result, 4)
        self.layout.addLayout(top)

        card = Card()
        toolbar = QHBoxLayout()
        title = QLabel("저장 공고")
        title.setProperty("role", "section")
        toolbar.addWidget(title)
        self.search = QLineEdit()
        self.search.setPlaceholderText("공고번호, 공고명, 수요기관 검색")
        self.search.setMaximumWidth(260)
        self.search.returnPressed.connect(actions.refresh_saved_bids)
        self.search.setVisible(False)
        toolbar.addWidget(self.search)
        self.stage_filter = FigmaComboBox()
        self.stage_filter.addItems(["전체 단계", "사전규격", "입찰공고", "개찰결과", "낙찰결과", "유찰·취소", "계약완료"])
        self.stage_filter.currentIndexChanged.connect(lambda _index: actions.refresh_saved_bids())
        toolbar.addWidget(self.stage_filter)
        self.category_filter = FigmaComboBox()
        self.category_filter.addItems(["전체 업무", "용역", "물품", "공사", "기타"])
        self.category_filter.currentIndexChanged.connect(lambda _index: actions.refresh_saved_bids())
        toolbar.addWidget(self.category_filter)
        self.tracking_filter = FigmaComboBox()
        self.tracking_filter.addItems(["전체 추적", "추적 중", "일시정지"])
        self.tracking_filter.currentIndexChanged.connect(lambda _index: actions.refresh_saved_bids())
        toolbar.addWidget(self.tracking_filter)
        toolbar.addStretch()
        card.layout.addLayout(toolbar)
        actions_row = QHBoxLayout()
        self.saved_recipient_settings = button(
            "수신 설정", actions.open_saved_bid_recipients, icon="notice.svg"
        )
        actions_row.addWidget(self.saved_recipient_settings)
        self.pending_feature_widgets = [
            button("새로고침", actions.refresh_saved_bids),
            button("상세", actions.show_saved_bid_detail),
            button("변경 이력", actions.show_notice_version_history),
            button("링크 열기", actions.open_saved_bid_link),
            button("결과 확인", actions.check_saved_results_now),
        ]
        for pending_widget in self.pending_feature_widgets:
            pending_widget.setVisible(False)
            actions_row.addWidget(pending_widget)
        actions_row.addWidget(button("삭제", actions.permanently_delete_saved_bid, delete=True, icon="trash.svg"))
        actions_row.addStretch()
        card.layout.addLayout(actions_row)
        settings = QHBoxLayout()
        self.result_interval = QLineEdit(initial_state.result_interval)
        self.result_interval.setFixedWidth(55)
        settings.addWidget(QLabel("감시 주기"))
        settings.addWidget(self.result_interval)
        settings.addWidget(QLabel("분"))
        settings.addWidget(button("적용", actions.apply_saved_result_interval))
        settings.addWidget(button("추적 시작/중지", actions.toggle_saved_bid_monitoring))
        self.notify_all = QCheckBox("모든 개찰 결과 알림")
        self.notify_all.setChecked(initial_state.notify_all_opening_results)
        self.notify_all.stateChanged.connect(lambda _state: actions.save_result_notification_setting())
        settings.addWidget(self.notify_all)
        settings.addStretch()
        self.monitor_status = muted("")
        self.monitor_status.setVisible(False)
        settings.addWidget(self.monitor_status)
        card.layout.addLayout(settings)
        self.result_status = muted("")
        self.result_status.setVisible(False)
        card.layout.addWidget(self.result_status)
        self.table = QTableWidget()
        setup_table(self.table, ["단계", "추적", "공고번호", "공고명", "업무", "수요기관", "입찰마감", "개찰일시", "결과"], [82, 48, 115, 285, 58, 125, 110, 110, 90])
        self.table.cellDoubleClicked.connect(lambda *_: actions.show_saved_bid_detail())
        card.layout.addWidget(self.table, 1)
        self.layout.addWidget(card, 1)

    def set_pending_features_visible(self, visible: bool) -> None:
        for widget in self.pending_feature_widgets:
            widget.setVisible(visible)


class LogPage(Page):
    def __init__(self, actions, parent=None):
        super().__init__(parent)
        toolbar = QHBoxLayout()
        self.auto_scroll = QCheckBox("자동 스크롤")
        self.auto_scroll.setChecked(True)
        toolbar.addWidget(self.auto_scroll)
        toolbar.addStretch()
        self.filter_combo = FigmaComboBox()
        self.filter_combo.addItem("전체 로그", "all")
        self.filter_combo.addItem("오류", "error")
        self.filter_combo.addItem("이메일", "email")
        self.filter_combo.setMinimumWidth(132)
        self.filter_combo.currentIndexChanged.connect(
            lambda _index: self.set_filter(self.filter_combo.currentData())
        )
        toolbar.addWidget(self.filter_combo)
        toolbar.addWidget(button("초기화", self.clear, icon="trash.svg"))
        self.log_file = button("로그 파일 열기", actions.open_log_file)
        self.log_file.setVisible(False)
        toolbar.addWidget(self.log_file)
        self.layout.addLayout(toolbar)
        card = Card()
        card.setProperty("logCard", True)
        self.browser = QTextBrowser()
        self.browser.setProperty("logView", True)
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(lambda url: actions.open_link(url.toString()))
        card.layout.addWidget(self.browser)
        self.layout.addWidget(card, 1)
        self.records = []
        self.filter_name = "all"

    def append(self, message, category):
        line = "" if message == "" else f"[{datetime.now():%H:%M:%S}] {message}"
        self.records.append((line, category))
        self.records = self.records[-5000:]
        if self.filter_name == "all" or self.filter_name == category:
            self.browser.append(self._colored_line(line, category))
            if self.auto_scroll.isChecked():
                self.browser.verticalScrollBar().setValue(self.browser.verticalScrollBar().maximum())

    def set_filter(self, name):
        self.filter_name = name
        self.browser.clear()
        for line, category in self.records:
            if name == "all" or name == category:
                self.browser.append(self._colored_line(line, category))

    @staticmethod
    def _colored_line(line, category):
        from html import escape
        color = {
            "error": Colors.LOG_ERROR,
            "email": Colors.LOG_EMAIL,
            "warning": Colors.LOG_WARNING,
        }.get(category, Colors.LOG_TEXT)
        safe = escape(line)
        if safe.startswith("[") and "]" in safe:
            timestamp, body = safe.split("]", 1)
            return (
                f'<span style="color:{Colors.LOG_TIME};">{timestamp}]</span>'
                f'<span style="color:{color};">{body}</span>'
            )
        return f'<span style="color:{color};">{safe}</span>'

    def clear(self):
        self.records.clear()
        self.browser.clear()


class ApiSettingsPage(Page):
    def __init__(self, actions, initial_state, parent=None):
        super().__init__(parent)
        card = Card("공공데이터포털 API 설정")
        self.api_key = QLineEdit(initial_state.api_key)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        show = button("보기", icon="eye.svg")
        show.setCheckable(True)
        def toggle_api_key(checked):
            self.api_key.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
            show.setIcon(local_icon("eye-closed.svg" if checked else "eye.svg"))
        show.toggled.connect(toggle_api_key)
        row = QHBoxLayout()
        row.addWidget(self.api_key, 1)
        row.addWidget(show)
        card.layout.addLayout(row)
        card.layout.addWidget(muted("공공데이터포털은 한 계정에서 하나의 일반 인증키를 공통으로 사용합니다."))
        links = [
            ("입찰공고정보서비스", "https://www.data.go.kr/data/15129394/openapi.do"),
            ("낙찰정보서비스", "https://www.data.go.kr/data/15129397/openapi.do"),
            ("사전규격정보서비스", "https://www.data.go.kr/data/15129401/openapi.do"),
            ("계약과정통합공개서비스", "https://www.data.go.kr/data/15129403/openapi.do"),
        ]
        grid = QGridLayout()
        for index, (label, url) in enumerate(links):
            grid.addWidget(button(label, lambda _=False, value=url: actions.open_link(value), icon="help.svg"), index // 2, index % 2)
        card.layout.addLayout(grid)
        save = button("저장", actions.keyword_rules_changed, primary=True, icon="check-L-on.svg")
        card.layout.addWidget(save, 0, Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(card, 1)


class QuerySettingsPage(Page):
    def __init__(self, actions, initial_state, parent=None):
        super().__init__(parent)
        top = QHBoxLayout()
        interval = Card("공고 조회 주기")
        self.interval = QLineEdit(initial_state.interval)
        interval.layout.addWidget(labeled_row("키워드 감시", self.interval, "분마다 조회 · 최소 1분"))
        interval.layout.addWidget(muted("권장 조회 주기는 5분입니다."))
        top.addWidget(interval, 1)
        notifications = Card("알림 설정")
        self.windows_notifications = QCheckBox("Windows 알림 사용")
        self.windows_notifications.setChecked(initial_state.windows_notifications_enabled)
        self.windows_notifications.stateChanged.connect(lambda _state: actions.toggle_windows_notifications())
        notifications.layout.addWidget(self.windows_notifications)
        self.windows_test = button("Windows 알림 테스트", actions.test_alert, icon="notice.svg")
        self.windows_test.setVisible(False)
        notifications.layout.addWidget(self.windows_test)
        self.keyword_email = QCheckBox("신규 공고 이메일 알림 사용")
        self.keyword_email.setChecked(initial_state.keyword_email_enabled)
        self.keyword_email.stateChanged.connect(lambda _state: actions.toggle_keyword_email_notifications())
        notifications.layout.addWidget(self.keyword_email)
        top.addWidget(notifications, 2)
        self.layout.addLayout(top)
        attachment = Card("첨부파일 자동 저장")
        self.attachment_dir = QLineEdit(initial_state.attachment_download_dir)
        row = QHBoxLayout()
        row.addWidget(self.attachment_dir, 1)
        row.addWidget(button("폴더 선택", self._choose_directory))
        row.addWidget(button("적용", lambda: actions.save_attachment_download_directory(self.attachment_dir.text()), primary=True))
        row.addWidget(button("초기화", actions.reset_attachment_download_directory))
        attachment.layout.addLayout(row)
        attachment.layout.addWidget(muted("업무명별 하위 폴더가 선택한 경로 안에 자동으로 생성됩니다."))
        self.layout.addWidget(attachment, 1)

    def _choose_directory(self):
        path = QFileDialog.getExistingDirectory(self, "첨부파일 저장 폴더", self.attachment_dir.text())
        if path:
            self.attachment_dir.setText(path)


class SettingsPage(QWidget):
    def __init__(self, actions, initial_state, parent=None):
        super().__init__(parent)
        self.actions = actions
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.api = ApiSettingsPage(actions, initial_state)
        self.email_placeholder = Page()
        self.email_panel = None
        self.email_loading = muted("이메일 설정을 불러오는 중입니다.")
        self.email_placeholder.layout.addWidget(
            self.email_loading, 1, Qt.AlignmentFlag.AlignCenter
        )
        self.query = QuerySettingsPage(actions, initial_state)
        self.tabs.addTab(self.api, "API")
        self.tabs.addTab(self.email_placeholder, "이메일")
        self.tabs.addTab(self.query, "공고 조회 및 저장")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

    def _on_tab_changed(self, _index):
        if self.tabs.currentWidget() is self.email_placeholder and self.email_panel is None:
            self.email_loading.setText("이메일 설정을 불러오는 중입니다.")
            self.actions.open_email_settings()

    def show_email_management(self, panel):
        """Show email management inside Settings without creating a top-level window."""
        if self.email_panel is not None:
            self.email_placeholder.layout.removeWidget(self.email_panel)
            self.email_panel.deleteLater()
        for index in reversed(range(self.email_placeholder.layout.count())):
            item = self.email_placeholder.layout.itemAt(index)
            widget = item.widget()
            if widget is not None:
                widget.setVisible(False)
        self.email_panel = panel
        panel.setParent(self.email_placeholder)
        self.email_placeholder.layout.addWidget(panel, 1)
        panel.setVisible(True)
        self.tabs.setCurrentWidget(self.email_placeholder)


class RecipientSelectionDialog(QDialog):
    """Shared recipient selector for keyword conditions and saved bids."""

    def __init__(self, target_label, recipients, mapped_ids, on_save, parent=None):
        super().__init__(parent)
        self.on_save = on_save
        self.setWindowTitle("수신 설정")
        self.setFixedSize(606, 556)
        root = QVBoxLayout(self)
        root.setContentsMargins(23, 18, 23, 20)
        header = QHBoxLayout()
        title = QLabel("수신 설정")
        title.setProperty("role", "title")
        header.addWidget(title)
        root.addLayout(header)
        label = QLabel(target_label)
        label.setWordWrap(True)
        label.setStyleSheet("font-weight:600")
        root.addWidget(label)
        self.select_all = QCheckBox("전체 선택")
        self.select_all.stateChanged.connect(self._toggle_all)
        root.addWidget(self.select_all)
        self.list = QListWidget()
        mapped = set(mapped_ids)
        for recipient in recipients:
            item = QListWidgetItem(f"{recipient['organization'] or '-'} · {recipient['name']} · {recipient['email']}")
            item.setData(Qt.ItemDataRole.UserRole, recipient["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            selected = recipient["id"] in mapped or (not mapped and bool(recipient["is_default"]))
            item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
            self.list.addItem(item)
        root.addWidget(self.list, 1)
        root.addWidget(muted("새 이메일 등록은 기본 설정 > 이메일 관리 > 수신자 설정에서 할 수 있습니다."))
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(button("취소", self.reject))
        footer.addWidget(button("저장", self.save, primary=True, icon="check-L-on.svg"))
        root.addLayout(footer)

    def _toggle_all(self, state):
        value = Qt.CheckState.Checked if state else Qt.CheckState.Unchecked
        for index in range(self.list.count()):
            self.list.item(index).setCheckState(value)

    def save(self):
        ids = [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.CheckState.Checked]
        if self.on_save(ids):
            QMessageBox.information(self, "저장 완료", f"수신자 {len(ids)}명을 연결했습니다.")
            self.accept()
