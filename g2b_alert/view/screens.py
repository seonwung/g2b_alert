"""Screen-level QWidget implementations matching the g2bAlert Figma file."""

from __future__ import annotations

import uuid
from datetime import datetime

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog,
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from .qt_common import (
    AsteriskPasswordLineEdit,
    Card,
    DraggableDialog,
    FigmaComboBox,
    HelpIcon,
    Page,
    button,
    clear_layout,
    labeled_row,
    muted,
    show_app_message,
    setup_table,
)
from .resources import local_icon
from .design_tokens import Colors
from .styles import DANGER, PRIMARY, PRIMARY_DARK, SUB_TEXT


CATEGORY_LABELS = {"service": "용역", "goods": "물품", "works": "공사", "etc": "기타"}
OPERATOR_OPTIONS = {
    "키워드 중 하나라도 포함되면 감지(OR)": "or",
    "키워드가 모두 포함되면 감지(AND)": "and",
    "등록 키워드가 포함된 공고 제외": "exclude",
}
TARGET_OPTIONS = {
    "입찰공고": ("bid_lifecycle",),
    "사전규격": ("prespec",),
    "사전규격 + 입찰공고": ("prespec", "bid_lifecycle"),
}


class ConditionDialog(DraggableDialog):
    def __init__(self, rule=None, parent=None):
        super().__init__(parent)
        self.rule = dict(rule or {})
        self.setWindowTitle("조건 수정" if rule else "조건 추가")
        self.setObjectName("conditionDialog")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(540, 470)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        card = Card()
        card.setObjectName("conditionDialogCard")
        card.layout.setContentsMargins(22, 18, 22, 20)
        card.layout.setSpacing(12)
        outer.addWidget(card)

        header = QHBoxLayout()
        header.setSpacing(5)
        caption = QLabel("조건 수정" if rule else "새로운 조건 추가")
        caption.setProperty("conditionCaption", True)
        header.addWidget(caption)
        if not rule:
            header.addWidget(
                HelpIcon(
                    "조건명을 입력하고 감시할 키워드를 하나씩 등록합니다. 검색 대상, 공고 종류와 검색 방식을 지정한 뒤 저장하면 감시 조건 카드로 추가됩니다.",
                    icon_size=12,
                )
            )
        header.addStretch()
        close_button = button(
            "",
            self.reject,
            height=24,
            icon="close-tab-S.svg",
        )
        close_button.setProperty("conditionClose", True)
        close_button.setToolTip("닫기")
        header.addWidget(close_button)
        card.layout.addLayout(header)

        self.name = QLineEdit(self.rule.get("name") or self.rule.get("keyword", ""))
        self.name.setPlaceholderText("조건명 입력")
        self.name.setToolTip("Enter를 누르면 조건을 저장합니다.")
        card.layout.addWidget(self._field_group("조건명", self.name))

        keyword_group = QWidget()
        keyword_group_layout = QVBoxLayout(keyword_group)
        keyword_group_layout.setContentsMargins(0, 0, 0, 0)
        keyword_group_layout.setSpacing(4)
        keyword_label = QLabel("키워드 등록")
        keyword_label.setProperty("conditionFieldLabel", True)
        keyword_group_layout.addWidget(keyword_label)
        keyword_row = QHBoxLayout()
        keyword_row.setSpacing(6)
        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText("검색 키워드 입력")
        self.keyword.setToolTip(
            "Enter로 키워드를 등록합니다. 등록 후 빈 입력칸에서 Enter를 한 번 더 누르면 조건이 저장됩니다."
        )
        self.name.installEventFilter(self)
        self.keyword.installEventFilter(self)
        keyword_row.addWidget(self.keyword, 1)
        register_keyword = button(
            "등록",
            self.add_keyword,
            primary=True,
            height=30,
        )
        register_keyword.setProperty("conditionCompact", True)
        register_keyword.setFixedWidth(50)
        keyword_row.addWidget(register_keyword)
        keyword_group_layout.addLayout(keyword_row)
        card.layout.addWidget(keyword_group)

        self.keywords = []
        for value in str(self.rule.get("keyword", "") or "").replace("\n", ",").split(","):
            value = value.strip()
            if value and value.casefold() not in {item.casefold() for item in self.keywords}:
                self.keywords.append(value)
        self.keyword_cards = QWidget()
        self.keyword_cards.setMinimumHeight(27)
        self.keyword_cards_layout = QVBoxLayout(self.keyword_cards)
        self.keyword_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.keyword_cards_layout.setSpacing(8)
        keyword_scroll = QScrollArea()
        keyword_scroll.setWidgetResizable(True)
        keyword_scroll.setFrameShape(QFrame.Shape.NoFrame)
        keyword_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        keyword_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        keyword_scroll.setFixedHeight(31)
        keyword_scroll.setWidget(self.keyword_cards)
        self.keyword_scroll = keyword_scroll
        self.keyword_base_height = 31
        self.dialog_base_height = 470
        self.keyword_available_width = 476
        card.layout.addWidget(self.keyword_scroll)
        self._render_keyword_cards()

        self.operator = FigmaComboBox()
        self.operator.addItems(OPERATOR_OPTIONS)
        wanted_operator = self.rule.get("operator", "or")
        self.operator.setCurrentText(
            next(
                (label for label, value in OPERATOR_OPTIONS.items() if value == wanted_operator),
                next(iter(OPERATOR_OPTIONS)),
            )
        )
        self.target = FigmaComboBox()
        self.target.addItems(TARGET_OPTIONS)
        targets = set(self.rule.get("targets") or ["bid_lifecycle"])
        self.target.setCurrentText(next((k for k, v in TARGET_OPTIONS.items() if set(v) == targets), "입찰공고"))

        target_and_categories = QHBoxLayout()
        target_and_categories.setSpacing(58)
        target_group = self._field_group("검색 대상", self.target)
        target_group.setFixedWidth(112)
        target_and_categories.addWidget(target_group)

        category_box = QWidget()
        category_layout = QHBoxLayout(category_box)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(12)
        self.categories = {}
        selected = set(self.rule.get("categories") or CATEGORY_LABELS)
        for key, label in CATEGORY_LABELS.items():
            check = QCheckBox(label)
            check.setChecked(key in selected)
            self.categories[key] = check
            category_layout.addWidget(check)
        category_layout.addStretch()
        category_group = self._field_group("공고 종류", category_box)
        target_and_categories.addWidget(category_group, 1)
        card.layout.addLayout(target_and_categories)

        card.layout.addWidget(self._field_group("검색 방식", self.operator))
        card.layout.addStretch()
        footer = QHBoxLayout()
        footer.addStretch()
        save_button = button(
            "저장",
            self._validate,
            primary=True,
            height=30,
        )
        save_button.setProperty("conditionCompact", True)
        save_button.setFixedWidth(52)
        footer.addWidget(save_button)
        card.layout.addLayout(footer)

    def eventFilter(self, watched, event):
        if (
            watched in (self.name, self.keyword)
            and event.type() == QEvent.Type.KeyPress
            and event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}
        ):
            if watched is self.keyword and self.keyword.text().strip():
                self.add_keyword()
            else:
                self._validate()
            return True
        return super().eventFilter(watched, event)

    @staticmethod
    def _field_group(label_text, field):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(label_text)
        label.setProperty("conditionFieldLabel", True)
        layout.addWidget(label)
        layout.addWidget(field)
        return container

    def add_keyword(self):
        raw = self.keyword.text().strip()
        if not raw:
            return
        candidates = [raw]
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
        self.keyword_cards_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        row_count = 0
        row_layout = None
        occupied_width = 0
        horizontal_spacing = 8
        for value in self.keywords:
            chip = QFrame(self.keyword_cards)
            chip.setProperty("conditionKeywordChip", True)
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(10, 2, 4, 2)
            chip_layout.setSpacing(2)
            chip_label = QLabel(value, chip)
            chip_layout.addWidget(chip_label)
            remove = button(
                "",
                lambda item=value: self.remove_keyword(item),
                height=22,
                icon="close-tab-S.svg",
            )
            remove.setProperty("conditionChipRemove", True)
            remove.setToolTip(f"{value} 삭제")
            chip_layout.addWidget(remove)
            chip.ensurePolished()
            chip_label.ensurePolished()
            remove.ensurePolished()
            chip_width = min(
                self.keyword_available_width,
                max(48, chip_label.sizeHint().width() + 36),
            )
            chip.setFixedWidth(chip_width)
            required_width = (
                chip_width
                if occupied_width == 0
                else occupied_width + horizontal_spacing + chip_width
            )
            if occupied_width and required_width > self.keyword_available_width:
                row_layout.addStretch()
                row_layout = None
                occupied_width = 0
                required_width = chip_width
            if row_layout is None:
                row_layout = QHBoxLayout()
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(horizontal_spacing)
                self.keyword_cards_layout.addLayout(row_layout)
                row_count += 1
            row_layout.addWidget(chip)
            occupied_width = required_width
        if row_layout is not None:
            row_layout.addStretch()

        row_count = max(1, row_count)
        keyword_height = self.keyword_base_height + (row_count - 1) * 34
        self.keyword_scroll.setFixedHeight(keyword_height)
        self.setFixedHeight(
            self.dialog_base_height
            + keyword_height
            - self.keyword_base_height
        )

    def _validate(self):
        self.add_keyword()
        if not self.keywords:
            show_app_message(
                self,
                "확인",
                "감시할 키워드를 하나 이상 등록해 주세요.",
                kind="warning",
            )
            return
        if not self.name.text().strip():
            self.name.setText(self.keywords[0])
        if not any(check.isChecked() for check in self.categories.values()):
            show_app_message(
                self,
                "확인",
                "업무 구분을 하나 이상 선택해 주세요.",
                kind="warning",
            )
            return
        self.accept()

    def value(self):
        keyword = ", ".join(self.keywords)
        return {
            "id": str(self.rule.get("id") or uuid.uuid4().hex),
            "name": self.name.text().strip() or (self.keywords[0] if self.keywords else ""),
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
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QFrame {background:#FFFFFF;border:1px solid #D8E5FF;border-radius:10px;}"
            "QLabel {border:none;}"
        )
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
        self._edit_click_targets = (number, title, summary)
        for click_target in self._edit_click_targets:
            click_target.setCursor(Qt.CursorShape.PointingHandCursor)
            click_target.installEventFilter(self)
        text.addWidget(title)
        text.addWidget(summary)
        layout.addLayout(text, 1)
        recipients = button(
            "수신 설정",
            lambda: self.recipientsRequested.emit(self.rule["id"]),
            height=30,
        )
        recipients.setProperty("outlinePrimary", True)
        recipients.setProperty("figmaCompact", True)
        recipients.setFixedWidth(84)
        layout.addWidget(recipients)
        enabled = bool(self.rule.get("enabled"))
        self.toggle = button(
            "감시 중지" if enabled else "감시 시작",
            self._toggle,
            height=30,
        )
        self.toggle.setProperty("monitorState", "stop" if enabled else "start")
        self.toggle.setFixedWidth(78)
        layout.addWidget(self.toggle)
        edit = button("수정", lambda: self.editRequested.emit(self.rule["id"]), height=30)
        edit.setVisible(False)
        layout.addWidget(edit)
        delete = button("", lambda: self.deleteRequested.emit(self.rule["id"]), delete=True, height=30, icon="trash.svg")
        delete.setProperty("rowDelete", True)
        delete.setFixedWidth(38)
        delete.setToolTip("조건 삭제")
        layout.addWidget(delete)

    def eventFilter(self, watched, event):
        if (
            watched in self._edit_click_targets
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.editRequested.emit(self.rule["id"])
            return True
        return super().eventFilter(watched, event)

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.editRequested.emit(self.rule["id"])
            event.accept()
            return
        super().mouseReleaseEvent(event)

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
        self.toggle.setProperty(
            "monitorState",
            "busy" if busy else ("stop" if enabled else "start"),
        )
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
        self.status_bar.layout.setContentsMargins(18, 11, 18, 11)
        status_row = QHBoxLayout()
        self.status = QLabel("대기중")
        self.status.setProperty("role", "title")
        self.status.setStyleSheet("color:#2F9E72")
        self.last_check = muted("마지막 확인  -")
        self.next_check = muted("다음 확인 예정: -")
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
        self.check_now = button("즉시 확인", actions.check_now)
        self.check_now.setProperty("outlinePrimary", True)
        self.check_now.setProperty("figmaCompact", True)
        self.start = button("일괄 감시 시작", actions.start, primary=True)
        self.start.setProperty("figmaCompact", True)
        self.stop = button("일괄 감시 중지", actions.stop, danger=True)
        self.stop.setProperty("figmaCompact", True)
        self.stop.setVisible(False)
        status_row.addWidget(self.check_now)
        status_row.addWidget(self.start)
        status_row.addWidget(self.stop)
        self.status_bar.layout.addLayout(status_row)
        self.monitor_summary.hide()
        self.layout.addWidget(self.status_bar)

        conditions = Card()
        conditions.setFixedHeight(306)
        top = QHBoxLayout()
        label = QLabel("감시 조건")
        label.setProperty("role", "section")
        top.addWidget(label)
        top.addStretch()
        add_condition = button("조건 추가", self.add_rule, icon="add.svg")
        add_condition.setProperty("textAction", True)
        add_condition.setProperty("figmaCompact", True)
        top.addWidget(add_condition)
        conditions.layout.addLayout(top)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.rows_widget = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(10)
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
        reset_alerts = button("초기화", actions.clear_recent_alerts)
        reset_alerts.setProperty("outlinePrimary", True)
        reset_alerts.setProperty("figmaCompact", True)
        save_alert = button(
            "선택한 공고 저장",
            actions.save_selected_alert_bid,
            primary=True,
        )
        save_alert.setProperty("figmaCompact", True)
        alert_header.addWidget(reset_alerts)
        alert_header.addWidget(save_alert)
        alerts.layout.addLayout(alert_header)
        self.alert_table = QTableWidget()
        setup_table(
            self.alert_table,
            ["공고명", "감시 조건명", "공고 바로가기"],
            [390, 240, 130],
        )
        self.alert_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
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
        dialog, result = self._open_condition_dialog()
        if result == QDialog.DialogCode.Accepted:
            self.rules.append(dialog.value())
            self._render_rules()
            self.actions.keyword_rules_changed()

    def edit_rule(self, rule_id):
        rule = next((r for r in self.rules if r["id"] == rule_id), None)
        if not rule:
            return
        dialog, result = self._open_condition_dialog(rule)
        if result == QDialog.DialogCode.Accepted:
            self.rules[self.rules.index(rule)] = dialog.value()
            self._render_rules()
            self.actions.keyword_rules_changed()

    def _open_condition_dialog(self, rule=None):
        modal_parent = self.window()
        overlay = QWidget(modal_parent)
        overlay.setObjectName("modalOverlay")
        overlay.setGeometry(modal_parent.rect())
        overlay.show()
        overlay.raise_()
        dialog = ConditionDialog(rule, modal_parent)
        try:
            result = dialog.exec()
        finally:
            overlay.deleteLater()
        return dialog, result

    def delete_rule(self, rule_id):
        if not show_app_message(
            self,
            "조건 삭제",
            "해당 조건을 삭제하시겠습니까?",
            kind="warning",
            question=True,
        ):
            return
        self.rules = [rule for rule in self.rules if rule["id"] != rule_id]
        self._render_rules()
        self.actions.keyword_rules_changed()
        show_app_message(self, "안내", "조건을 삭제했습니다.")

    def _toggle_rule(self, rule_id, enabled):
        rule = next((r for r in self.rules if r["id"] == rule_id), None)
        if not rule:
            return
        self.row_widgets[rule_id].set_enabled_state(enabled, busy=True)
        self.actions.set_keyword_rule_monitoring(
            dict(rule),
            enabled,
            lambda: self._finish_rule_toggle(rule_id),
        )

    def _finish_rule_toggle(self, rule_id):
        rule = next((r for r in self.rules if r["id"] == rule_id), None)
        row = self.row_widgets.get(rule_id)
        if rule is not None and row is not None:
            row.set_enabled_state(bool(rule.get("enabled", False)))

    def _alert_click(self, row, column):
        self.alert_table.selectRow(row)
        if column == 1:
            item = self.alert_table.item(row, 0)
            if item:
                self.actions.show_alert_keywords(item.data(Qt.ItemDataRole.UserRole))

    def _alert_double_click(self, row, column):
        self.alert_table.selectRow(row)
        if column == 1:
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
        lookup.layout.setContentsMargins(18, 18, 18, 18)
        lookup.layout.setSpacing(10)
        lookup.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.lookup_type = FigmaComboBox()
        self.lookup_type.addItems(["자동 감지", "입찰공고", "사전규격"])
        self.lookup_reference = QLineEdit()
        self.lookup_reference.setPlaceholderText("공고번호 또는 나라장터 URL")
        self.lookup_reference.returnPressed.connect(actions.lookup_notice_by_no)
        controls.addWidget(self.lookup_type)
        controls.addWidget(self.lookup_reference, 1)
        self.lookup_button = button("조회", actions.lookup_notice_by_no, primary=True)
        controls.addWidget(self.lookup_button)
        lookup.layout.addLayout(controls)
        top.addWidget(lookup, 5)
        result = Card("조회 결과")
        result.setFixedHeight(148)
        result.layout.setContentsMargins(18, 18, 18, 18)
        result.layout.setSpacing(10)
        self.lookup_summary = muted("공고를 조회하면 결과가 표시됩니다.")
        result.layout.addWidget(self.lookup_summary)
        result.layout.addStretch(1)
        result_footer = QHBoxLayout()
        result_footer.addStretch(1)
        self.save_lookup = button("저장", actions.save_lookup_notice, primary=True)
        self.save_lookup.setEnabled(False)
        result_footer.addWidget(self.save_lookup)
        result.layout.addLayout(result_footer)
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
        self.saved_recipient_settings = button(
            "수신 설정",
            actions.open_saved_bid_recipients,
        )
        toolbar.addWidget(self.saved_recipient_settings)
        self.toggle_saved_tracking = button(
            "추적 시작/중지",
            actions.toggle_saved_bid_monitoring,
        )
        toolbar.addWidget(self.toggle_saved_tracking)
        self.delete_saved_bid = button(
            "삭제",
            actions.permanently_delete_saved_bid,
            delete=True,
            icon="trash.svg",
        )
        toolbar.addWidget(self.delete_saved_bid)
        card.layout.addLayout(toolbar)

        # Figma에 아직 위치가 없는 작업은 숨긴 보조 행에 유지한다.
        actions_row = QHBoxLayout()
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
        actions_row.addStretch()
        card.layout.addLayout(actions_row)
        settings = QHBoxLayout()
        self.result_interval = QLineEdit(initial_state.result_interval)
        self.result_interval.setFixedWidth(55)
        settings.addWidget(QLabel("감시 주기"))
        settings.addWidget(self.result_interval)
        settings.addWidget(QLabel("분"))
        settings.addWidget(button("적용", actions.apply_saved_result_interval))
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
        self.table.setObjectName("savedBidsTable")
        setup_table(
            self.table,
            ["단계", "추적", "공고번호", "공고명", "업무", "수요기관", "사업금액", "결과"],
            [68, 44, 112, 300, 56, 140, 110, 128],
        )
        saved_header = self.table.horizontalHeader()
        saved_header.setStretchLastSection(False)
        for column in range(self.table.columnCount()):
            saved_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        saved_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        card.layout.addWidget(self.table, 1)
        self.layout.addWidget(card, 1)

    def set_pending_features_visible(self, visible: bool) -> None:
        for widget in self.pending_feature_widgets:
            widget.setVisible(visible)


class LogPage(Page):
    def __init__(self, actions, parent=None):
        super().__init__(parent)
        page_margins = self.layout.contentsMargins()
        self.layout.setContentsMargins(
            page_margins.left(),
            8,
            page_margins.right(),
            page_margins.bottom(),
        )
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
        toolbar.addWidget(button("초기화", self.clear))
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
        card = Card()
        card.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        title = QLabel("공공데이터포털 API 키")
        title.setProperty("role", "section")
        title_row.addWidget(title)
        title_row.addWidget(
            HelpIcon(
                "공공데이터포털에서 발급받은 일반 인증키를 입력합니다. 입찰공고, 낙찰정보, 사전규격과 계약과정 API 조회에 공통으로 사용됩니다."
            )
        )
        title_row.addStretch()
        card.layout.addLayout(title_row)

        self.api_key = AsteriskPasswordLineEdit(initial_state.api_key)
        self.api_key.setProperty("apiKeyInput", True)
        self.api_key.setPlaceholderText("공공데이터포털 일반 인증키 입력")
        visibility_action = self.api_key.addAction(
            local_icon("eye-closed.svg"),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self.api_key.set_trailing_action_inset(14)
        visibility_action.setToolTip("API 키 표시")
        self.api_key_visible = False

        def toggle_api_key():
            self.api_key_visible = not self.api_key_visible
            self.api_key.setEchoMode(
                QLineEdit.EchoMode.Normal
                if self.api_key_visible
                else QLineEdit.EchoMode.Password
            )
            visibility_action.setIcon(
                local_icon("eye.svg" if self.api_key_visible else "eye-closed.svg")
            )
            visibility_action.setToolTip(
                "API 키 숨기기" if self.api_key_visible else "API 키 표시"
            )

        visibility_action.triggered.connect(toggle_api_key)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.api_key, 1)
        save = button("저장", actions.keyword_rules_changed, primary=True)
        save.setFixedWidth(64)
        row.addWidget(save)
        card.layout.addLayout(row)

        description = muted(
            "공공데이터포털은 한 계정에서 하나의 일반 인증키를 공통으로 사용합니다.\n"
            "전체 기능 사용을 위해 아래 네 개의 API를 모두 활용신청한 계정의 인증키를 입력하세요."
        )
        card.layout.addWidget(description)

        links = [
            ("입찰공고정보서비스 API 활용 신청", "https://www.data.go.kr/data/15129394/openapi.do"),
            ("낙찰정보서비스 API 활용 신청", "https://www.data.go.kr/data/15129397/openapi.do"),
            ("사전규격정보서비스 API 활용 신청", "https://www.data.go.kr/data/15129437/openapi.do"),
            ("계약과정통합공개서비스 API 활용 신청", "https://www.data.go.kr/data/15129459/openapi.do"),
        ]
        links_widget = QWidget()
        links_widget.setMaximumWidth(480)
        grid = QGridLayout(links_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for index, (label, url) in enumerate(links):
            link_button = button(
                label,
                lambda value=url: actions.open_link(value),
                height=40,
            )
            link_button.setProperty("apiLink", True)
            link_button.setMinimumWidth(230)
            grid.addWidget(link_button, index // 2, index % 2)
        card.layout.addWidget(links_widget, 0, Qt.AlignmentFlag.AlignLeft)
        card.layout.addStretch()
        self.layout.addWidget(card, 1)


class QuerySettingsPage(Page):
    def __init__(self, actions, initial_state, parent=None):
        super().__init__(parent)
        top = QHBoxLayout()
        top.setSpacing(12)

        interval = Card()
        interval.setFixedHeight(216)
        interval.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        interval_title = QLabel("감시 주기 설정")
        interval_title.setProperty("cardCaption", True)
        interval.layout.addWidget(interval_title)
        self.interval = QLineEdit(initial_state.interval)
        self.interval.setFixedWidth(55)
        interval_row = QHBoxLayout()
        interval_row.setSpacing(10)
        interval_row.addWidget(self.interval)
        interval_row.addWidget(QLabel("분마다 새 입찰공고 확인"))
        interval_row.addStretch()
        interval.layout.addLayout(interval_row)
        interval.layout.addWidget(muted("* 5분 권장 / 최소 1분"))
        top.addWidget(interval, 35)

        notifications = Card()
        notifications.setFixedHeight(216)
        notifications.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        notification_header = QHBoxLayout()
        notification_title = QLabel("알림 설정")
        notification_title.setProperty("cardCaption", True)
        notification_header.addWidget(notification_title)
        notification_header.addStretch()
        self.windows_test = button(
            "윈도우 알림 테스트",
            actions.test_alert,
            height=30,
        )
        self.windows_test.setProperty("textAction", True)
        self.windows_test.setProperty("figmaCompact", True)
        notification_header.addWidget(self.windows_test)
        notifications.layout.addLayout(notification_header)

        notification_options = QHBoxLayout()
        notification_options.setSpacing(42)
        self.windows_notifications = QCheckBox("Windows 알림 사용")
        self.windows_notifications.setChecked(initial_state.windows_notifications_enabled)
        self.windows_notifications.stateChanged.connect(lambda _state: actions.toggle_windows_notifications())
        notification_options.addWidget(self.windows_notifications)
        self.keyword_email = QCheckBox("신규 공고 이메일 알림 사용")
        self.keyword_email.setChecked(initial_state.keyword_email_enabled)
        self.keyword_email.stateChanged.connect(lambda _state: actions.toggle_keyword_email_notifications())
        notification_options.addWidget(self.keyword_email)
        notification_options.addStretch()
        notifications.layout.addLayout(notification_options)
        notifications.layout.addWidget(
            muted("* 알림 채널은 모든 감시 키워드에 공통으로 적용됩니다.")
        )
        top.addWidget(notifications, 65)
        self.layout.addLayout(top)

        attachment = Card()
        attachment.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        attachment_header = QHBoxLayout()
        attachment_header.setSpacing(6)
        attachment_title = QLabel("첨부파일 자동 저장 경로")
        attachment_title.setProperty("cardCaption", True)
        attachment_header.addWidget(attachment_title)
        attachment_header.addWidget(
            HelpIcon(
                "조회한 공고의 첨부파일을 저장할 기본 폴더입니다. 공고별 하위 폴더는 선택한 경로 아래에 자동으로 생성됩니다."
            )
        )
        attachment_header.addStretch()
        reset_attachment = button(
            "초기화",
            actions.reset_attachment_download_directory,
            height=30,
        )
        reset_attachment.setProperty("outlinePrimary", True)
        reset_attachment.setProperty("figmaCompact", True)
        attachment_header.addWidget(reset_attachment)
        attachment.layout.addLayout(attachment_header)

        self.attachment_dir = QLineEdit(initial_state.attachment_download_dir)
        attachment_row = QHBoxLayout()
        attachment_row.setSpacing(8)
        attachment_row.addWidget(self.attachment_dir, 1)
        attachment_row.addWidget(
            button("폴더 선택", self._choose_directory, primary=True)
        )
        attachment_row.addWidget(
            button(
                "적용",
                lambda: actions.save_attachment_download_directory(
                    self.attachment_dir.text()
                ),
                primary=True,
            )
        )
        attachment.layout.addLayout(attachment_row)
        attachment.layout.addStretch()
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
        self.tabs.setObjectName("settingsTabs")
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


class RecipientSelectionDialog(DraggableDialog):
    """Shared recipient selector for keyword conditions and saved bids."""

    def __init__(self, target_label, recipients, mapped_ids, on_save, parent=None):
        super().__init__(parent)
        self.on_save = on_save
        self.setWindowTitle("수신 설정")
        self.setObjectName("recipientSelectionDialog")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(620, 500)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        card = Card()
        card.setObjectName("recipientSelectionCard")
        card.layout.setContentsMargins(22, 18, 22, 20)
        card.layout.setSpacing(12)
        outer.addWidget(card)

        header = QHBoxLayout()
        header.setSpacing(5)
        title = QLabel("수신 설정")
        title.setProperty("recipientCaption", True)
        header.addWidget(title)
        header.addWidget(
            HelpIcon(
                "이 감시 조건 또는 저장 공고의 이메일 알림을 받을 수신자를 선택합니다. 새로운 수신자는 기본 설정의 이메일 화면에서 등록할 수 있습니다.",
                icon_size=12,
            )
        )
        header.addStretch()
        close_button = button(
            "",
            self.reject,
            height=24,
            icon="close-tab-S.svg",
        )
        close_button.setProperty("recipientClose", True)
        close_button.setToolTip("닫기")
        header.addWidget(close_button)
        card.layout.addLayout(header)

        label = QLabel(target_label)
        label.setWordWrap(True)
        label.setProperty("recipientTarget", True)
        card.layout.addWidget(label)

        self.select_all = QCheckBox("전체 선택")
        self.select_all.stateChanged.connect(self._toggle_all)
        card.layout.addWidget(self.select_all)

        self.recipient_checks = []
        recipient_area = QWidget()
        recipient_columns = QHBoxLayout(recipient_area)
        recipient_columns.setContentsMargins(12, 0, 0, 0)
        recipient_columns.setSpacing(18)
        mapped = set(mapped_ids)

        column_count = 2 if len(recipients) > 8 else 1
        rows_per_column = max(
            1,
            (len(recipients) + column_count - 1) // column_count,
        )
        for column_index in range(column_count):
            if column_index:
                divider = QFrame()
                divider.setProperty("recipientDivider", True)
                divider.setFrameShape(QFrame.Shape.VLine)
                recipient_columns.addWidget(divider)
            column_widget = QWidget()
            column_layout = QVBoxLayout(column_widget)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.setSpacing(8)
            start = column_index * rows_per_column
            end = min(start + rows_per_column, len(recipients))
            for recipient in recipients[start:end]:
                organization = recipient["organization"] or "-"
                check = QCheckBox(
                    f"{organization} {recipient['name']} · {recipient['email']}"
                )
                check.setProperty("recipientId", recipient["id"])
                selected = (
                    recipient["id"] in mapped
                    or (not mapped and bool(recipient["is_default"]))
                )
                check.setChecked(selected)
                self.recipient_checks.append(check)
                column_layout.addWidget(check)
            column_layout.addStretch()
            recipient_columns.addWidget(column_widget, 1)
        recipient_columns.addStretch()
        recipient_scroll = QScrollArea()
        recipient_scroll.setWidgetResizable(True)
        recipient_scroll.setFrameShape(QFrame.Shape.NoFrame)
        recipient_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        recipient_scroll.setWidget(recipient_area)
        card.layout.addWidget(recipient_scroll, 1)

        if self.recipient_checks:
            self.select_all.blockSignals(True)
            self.select_all.setChecked(
                all(check.isChecked() for check in self.recipient_checks)
            )
            self.select_all.blockSignals(False)

        footer = QHBoxLayout()
        hint = muted(
            "새로운 이메일주소 등록은 기본 설정 > 이메일 관리 > 수신자 설정에서 등록 가능합니다."
        )
        hint.setProperty("recipientHint", True)
        footer.addWidget(hint, 1)
        save_button = button(
            "저장",
            self.save,
            primary=True,
            height=34,
        )
        save_button.setProperty("recipientSave", True)
        save_button.setFixedWidth(60)
        footer.addWidget(save_button)
        card.layout.addLayout(footer)

    def _toggle_all(self, state):
        checked = bool(state)
        for recipient_check in self.recipient_checks:
            recipient_check.setChecked(checked)

    def save(self):
        ids = [
            check.property("recipientId")
            for check in self.recipient_checks
            if check.isChecked()
        ]
        if self.on_save(ids):
            self.accept()
