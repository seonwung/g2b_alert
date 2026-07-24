"""PySide6 implementation of the toolkit-neutral AppViewProtocol."""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QEvent, QItemSelectionModel, Qt, QTimer
from PySide6.QtGui import QBrush, QCloseEvent, QColor
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QStackedWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..presentation.contracts import MainViewState, ViewActionsProtocol
from ..model.notice_detail_model import format_amount
from .dialogs import EmailSettingsDialog, NoticeDetailDialog, VersionHistoryDialog
from .qt_common import button
from .screens import (
    KeywordMonitorPage, LogPage, RecipientSelectionDialog, SavedBidsPage,
    SettingsPage,
)
from .resources import load_pretendard, local_icon, qss_url
from .design_tokens import STAGE_COLORS
from .styles import PRIMARY, PRIMARY_DARK, build_stylesheet
from .ui_dispatcher import UiDispatcher


class MainView(QMainWindow):
    def __init__(self, root, actions: ViewActionsProtocol, initial_state: MainViewState):
        super().__init__()
        self.app = root if isinstance(root, QApplication) else QApplication.instance()
        self.actions = actions
        self.initial_state = initial_state
        self.closing = False
        self.close_handler = None
        self.log_records = []
        self.log_filter = "all"
        self.recent_alert_ids = []
        self.saved_bid_rows = {}
        self.keyword_popup = None
        self.dialogs = []
        self.ui_dispatcher = UiDispatcher(self.app or root)
        load_pretendard()
        if self.app:
            self.app.setWindowIcon(local_icon("notice.png"))
            self.app.setStyleSheet(build_stylesheet(
                qss_url("icons", "check-S-off.svg"),
                qss_url("icons", "check-S-on.svg"),
                qss_url("icons", "togle-S.svg"),
            ))
        self.setWindowIcon(local_icon("notice.png"))
        self.setWindowTitle("g2bAlert")
        self.resize(1024, 786)
        self.setMinimumSize(960, 720)
        self._build_ui()
        self.show()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("appRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(80)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(40, 0, 40, 0)
        left = QWidget()
        left_layout = QHBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("나라장터 키워드 알림")
        title.setProperty("role", "appTitle")
        left_layout.addWidget(title)
        left_layout.addStretch()
        header_layout.addWidget(left, 1)
        self.nav_group = QWidget()
        nav_layout = QHBoxLayout(self.nav_group)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)
        self.nav_buttons = []
        nav = (("키워드 감지", 0), ("저장 공고", 1), ("통합 로그", 2), ("기본 설정", 3))
        for label, index in nav:
            item = QPushButton(label)
            item.setProperty("nav", True)
            item.setFixedHeight(36)
            item.setCursor(Qt.CursorShape.PointingHandCursor)
            item.clicked.connect(lambda _checked=False, value=index: self.show_page(value))
            nav_layout.addWidget(item)
            self.nav_buttons.append(item)
        header_layout.addWidget(self.nav_group, 0, Qt.AlignmentFlag.AlignCenter)
        right = QWidget()
        header_layout.addWidget(right, 1)
        root.addWidget(header)
        self.stack = QStackedWidget()
        self.keyword_page = KeywordMonitorPage(self.actions, self.initial_state, self._open_keyword_recipients)
        self.saved_page = SavedBidsPage(self.actions, self.initial_state)
        self._saved_double_click_selection_ids = []
        self.saved_page.table.viewport().installEventFilter(self)
        self.saved_page.table.cellDoubleClicked.connect(
            self._saved_bid_double_clicked
        )
        self.log_page = LogPage(self.actions)
        self.settings_page = SettingsPage(self.actions, self.initial_state)
        for page in (self.keyword_page, self.saved_page, self.log_page, self.settings_page):
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.show_page(0)

    def show_page(self, index):
        self.stack.setCurrentIndex(index)
        for button_widget_index, nav in enumerate(self.nav_buttons):
            nav.setProperty("navSelected", button_widget_index == index)
            nav.style().unpolish(nav)
            nav.style().polish(nav)

    # CommonViewProtocol
    def post(self, callback):
        if not self.closing:
            self.ui_dispatcher.post(callback)

    def schedule(self, delay_ms, callback):
        QTimer.singleShot(delay_ms, callback)

    def set_close_handler(self, callback):
        self.close_handler = callback

    def stop_dispatcher(self):
        self.closing = True
        self.ui_dispatcher.stop()

    def destroy(self):
        self.closing = True
        self.close()
        if self.app:
            self.app.quit()

    def closeEvent(self, event: QCloseEvent):
        if not self.closing and self.close_handler:
            event.ignore()
            self.close_handler()
            return
        event.accept()

    def log(self, message):
        self.post(lambda: self._append_log(message))

    def _append_log(self, message):
        category = self._classify_log(message)
        self.log_page.append(message, category)
        self.log_records = self.log_page.records

    def set_status(self, message):
        self.post(lambda: self.keyword_page.status.setText(message))

    def show_info(self, title, message, parent=None):
        QMessageBox.information(parent or self, title, message)

    def show_warning(self, title, message, parent=None):
        QMessageBox.warning(parent or self, title, message)

    def show_error(self, title, message, parent=None):
        QMessageBox.critical(parent or self, title, message)

    def ask_yes_no(self, title, message, parent=None):
        return QMessageBox.question(parent or self, title, message) == QMessageBox.StandardButton.Yes

    def update_running_ui(self, is_running):
        self.keyword_page.start.setVisible(not is_running)
        self.keyword_page.stop.setVisible(is_running)
        self.keyword_page.status.setText("감시중" if is_running else "대기중")
        self.keyword_page.status.setStyleSheet(f"color:{PRIMARY if is_running else '#2F9E72'};font-size:12pt;font-weight:700")

    # BidMonitorViewProtocol
    def get_monitor_form(self):
        return {
            "api_key": self.settings_page.api.api_key.text().strip(),
            "keyword_rules": [dict(rule) for rule in self.keyword_page.rules],
            "interval": self.settings_page.query.interval.text().strip(),
            "result_interval": self.saved_page.result_interval.text().strip(),
            "windows_notifications_enabled": self.settings_page.query.windows_notifications.isChecked(),
            "notify_all_opening_results": self.saved_page.notify_all.isChecked(),
            "keyword_email_enabled": self.settings_page.query.keyword_email.isChecked(),
            "attachment_download_dir": self.settings_page.query.attachment_dir.text().strip(),
        }

    def set_all_keyword_monitoring(self, enabled):
        for rule in self.keyword_page.rules:
            if rule.get("keyword"):
                rule["enabled"] = bool(enabled)
        self.keyword_page._render_rules()

    def set_keyword_monitoring(self, rule_id, enabled):
        for rule in self.keyword_page.rules:
            if rule.get("id") == rule_id:
                rule["enabled"] = bool(enabled)
        if rule_id in self.keyword_page.row_widgets:
            self.keyword_page.row_widgets[rule_id].set_enabled_state(enabled)

    def set_attachment_download_directory(self, directory):
        self.settings_page.query.attachment_dir.setText(directory)

    def set_check_summary(self, checked_at, new_alert_count, all_success, interval):
        def apply():
            self.keyword_page.last_check.setText(f"마지막 확인  {checked_at:%Y-%m-%d %H:%M:%S} · 신규 {new_alert_count}건")
            next_check = checked_at + timedelta(minutes=int(interval))
            self.keyword_page.next_check.setText(f"다음 확인 예정  {next_check:%H:%M:%S}" if all_success else "일부 조회 실패 · 다음 주기에 재시도")
        self.post(apply)

    def set_monitor_summary(self, summary):
        self.post(lambda: self.keyword_page.monitor_summary.setText(summary))

    def set_next_check_pending(self):
        self.keyword_page.next_check.setText("다음 확인 예정  계산 중")

    def clear_next_check(self):
        self.keyword_page.next_check.setText("다음 확인 예정  -")

    def start_manual_check(self):
        self.keyword_page.manual_running = True
        self.keyword_page.check_now.setEnabled(False)
        self.keyword_page.check_now.setText("조회 중")

    def finish_manual_check(self):
        self.keyword_page.manual_running = False
        self.keyword_page.check_now.setEnabled(True)
        self.keyword_page.check_now.setText("즉시 조회")

    # SavedBidsViewProtocol
    def get_lookup_reference(self): return self.saved_page.lookup_reference.text().strip()
    def get_lookup_type(self):
        return {"자동 감지": "auto", "입찰공고": "bid", "사전규격": "prespec"}.get(self.saved_page.lookup_type.currentText(), "auto")
    def set_lookup_reference(self, value): self.saved_page.lookup_reference.setText(value)
    def get_lookup_notice(self): return self.saved_page.lookup_notice

    def begin_lookup_notice(self):
        self.saved_page.lookup_button.setEnabled(False)
        self.saved_page.lookup_button.setText("조회 중")
        self.saved_page.lookup_summary.setText("공고를 조회하고 있습니다.")
        self.saved_page.lookup_notice = None
        self.saved_page.save_lookup.setEnabled(False)

    def finish_lookup_notice(self, notice, error, duplicate=None):
        self.saved_page.lookup_button.setEnabled(True)
        self.saved_page.lookup_button.setText("조회")
        self.saved_page.lookup_notice = notice
        if error:
            self.saved_page.lookup_summary.setText(f"조회 실패: {error}")
            self.show_error("조회 실패", str(error))
        elif notice:
            title = getattr(notice, "title", "") or getattr(notice, "bid_no", "")
            self.saved_page.lookup_summary.setText(("[저장됨] " if duplicate else "") + title)
            self.saved_page.save_lookup.setEnabled(True)

    def get_saved_search_text(self): return self.saved_page.search.text().strip()
    def get_saved_filters(self):
        stage = self.saved_page.stage_filter.currentText()
        category = {
            "용역": "service", "물품": "goods", "공사": "works", "기타": "etc"
        }.get(self.saved_page.category_filter.currentText(), "")
        tracking = {
            "추적 중": "active", "일시정지": "paused"
        }.get(self.saved_page.tracking_filter.currentText(), "")
        return {
            "stage": "" if stage == "전체 단계" else stage,
            "category": category,
            "tracking": tracking,
        }
    def get_saved_sort(self): return self.saved_page.sort_column, self.saved_page.sort_descending

    @staticmethod
    def _short_datetime(value):
        value = str(value or "")
        if len(value) >= 16 and value[4:5] == "-": return value[:16].replace("T", " ")
        if len(value) >= 12 and value[:12].isdigit(): return f"{value[:4]}-{value[4:6]}-{value[6:8]} {value[8:10]}:{value[10:12]}"
        return value[:16] or "-"

    def render_saved_bids(self, rows):
        self.saved_page.table.setRowCount(len(rows))
        self.saved_bid_rows.clear()
        for index, row in enumerate(rows):
            self.saved_bid_rows[index] = row
            reference = row.pre_spec_no if row.pre_spec_no and row.status == "pre_spec" else f"{row.bid_no}-{row.bid_ord or '000'}"
            values = (
                row.stage_label(),
                "ON" if row.monitoring_enabled else "OFF",
                reference,
                row.title,
                getattr(row, "category_label", row.category),
                row.demand_agency,
                format_amount(row.budget_amount),
                row.progress_status(),
            )
            stage_color = STAGE_COLORS.get(str(values[0]))
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or "-"))
                if column in {2, 3, 5, 6, 7}:
                    item.setToolTip(str(value or "-"))
                if stage_color:
                    item.setBackground(QBrush(QColor(stage_color)))
                if column == 0:
                    if values[0] == "사전규격":
                        item.setForeground(QBrush(QColor("#08745A")))
                        stage_font = item.font()
                        stage_font.setBold(True)
                        item.setFont(stage_font)
                    else:
                        item.setForeground(QBrush(QColor("#2F343B")))
                self.saved_page.table.setItem(index, column, item)

    def select_saved_bid(self, saved_id):
        self.select_saved_bids([saved_id])

    def select_saved_bids(self, saved_ids):
        wanted = set(saved_ids or [])
        table = self.saved_page.table
        table.clearSelection()
        selection_model = table.selectionModel()
        first_index = None
        for row_index, row in self.saved_bid_rows.items():
            if row.id in wanted:
                index = table.model().index(row_index, 0)
                selection_model.select(
                    index,
                    QItemSelectionModel.SelectionFlag.Select
                    | QItemSelectionModel.SelectionFlag.Rows,
                )
                if first_index is None:
                    first_index = index
        if first_index is not None:
            selection_model.setCurrentIndex(
                first_index,
                QItemSelectionModel.SelectionFlag.NoUpdate,
            )

    def get_selected_saved_bid(self):
        row = self.saved_page.table.currentRow()
        return self.saved_bid_rows.get(row)

    def get_selected_saved_bids(self):
        selected_rows = sorted(
            {index.row() for index in self.saved_page.table.selectionModel().selectedRows()}
        )
        return [
            self.saved_bid_rows[row_index]
            for row_index in selected_rows
            if row_index in self.saved_bid_rows
        ]

    def _saved_bid_double_clicked(self, row_index, column):
        modifiers = QApplication.keyboardModifiers()
        if modifiers & (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.ShiftModifier
        ):
            return
        row = self.saved_bid_rows.get(row_index)
        if row:
            if (
                len(self._saved_double_click_selection_ids) > 1
                and row.id in self._saved_double_click_selection_ids
            ):
                self.select_saved_bids(
                    self._saved_double_click_selection_ids
                )
            self._saved_double_click_selection_ids = []
            if column == 1:
                self.actions.set_saved_bid_monitoring(
                    row,
                    not row.monitoring_enabled,
                )
            else:
                self.actions.show_saved_bid_detail()

    def eventFilter(self, watched, event):
        table = getattr(getattr(self, "saved_page", None), "table", None)
        if (
            table is not None
            and watched is table.viewport()
            and event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            index = table.indexAt(event.position().toPoint())
            modifiers = event.modifiers()
            if (
                index.isValid()
                and not modifiers
                & (
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.ShiftModifier
                )
            ):
                clicked = self.saved_bid_rows.get(index.row())
                selected = self.get_selected_saved_bids()
                if (
                    clicked is not None
                    and len(selected) > 1
                    and any(row.id == clicked.id for row in selected)
                ):
                    self._saved_double_click_selection_ids = [
                        row.id for row in selected
                    ]
                else:
                    self._saved_double_click_selection_ids = []
        return super().eventFilter(watched, event)

    def get_result_interval_text(self): return self.saved_page.result_interval.text().strip()
    def set_saved_monitor_status(self, text): self.saved_page.monitor_status.setText(text)
    def set_saved_result_status(self, text): self.saved_page.result_status.setText(text)

    def render_saved_result_auto_check(self, summary):
        checked_at = summary["checked_at"].strftime("%Y-%m-%d %H:%M:%S")
        self.set_saved_result_status(f"최근 자동 조회 {checked_at} · 대상 {summary['checked']}건 · 신규 결과 {summary['new_results']}건 · 실패 {summary.get('failed', 0)}건")

    def render_saved_result_check(self, summary, error):
        if error:
            self.set_saved_result_status("낙찰정보 조회 실패")
            self.show_error("조회 실패", str(error))
            return
        self.render_saved_result_auto_check(summary)
        self.show_info("조회 완료", self.saved_page.result_status.text())

    def show_saved_bid_detail(self, detail):
        dialog = NoticeDetailDialog(detail, self.actions.open_link, self)
        self._cascade_dialog(dialog)
        self._track_dialog(dialog)
        dialog.show()
        return dialog

    def show_notice_version_history(self, row, versions, comparisons):
        dialog = VersionHistoryDialog(row, versions, comparisons, self)
        self._cascade_dialog(dialog)
        self._track_dialog(dialog)
        dialog.show()

    def _cascade_dialog(self, dialog):
        offset = (len(self.dialogs) % 8) * 28
        dialog.move(
            self.frameGeometry().x() + 70 + offset,
            self.frameGeometry().y() + 70 + offset,
        )

    # RecentAlertViewProtocol
    def add_recent_alert(self, item_id, bid, keywords):
        table = self.keyword_page.alert_table
        table.insertRow(0)
        values = (
            bid.title,
            self._format_keyword_summary(keywords),
            "열기" if bid.link else "-",
        )
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if column == 0:
                item.setData(Qt.ItemDataRole.UserRole, item_id)
            table.setItem(0, column, item)
        self.recent_alert_ids.insert(0, item_id)

    def remove_recent_alert_rows(self, item_ids):
        wanted = set(item_ids)
        table = self.keyword_page.alert_table
        for row in reversed(range(table.rowCount())):
            item = table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) in wanted:
                self.recent_alert_ids.remove(item.data(Qt.ItemDataRole.UserRole))
                table.removeRow(row)

    def clear_recent_alert_rows(self):
        self.keyword_page.alert_table.setRowCount(0)
        self.recent_alert_ids.clear()

    def get_selected_alert_id(self):
        row = self.keyword_page.alert_table.currentRow()
        item = self.keyword_page.alert_table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def select_first_alert(self):
        if self.keyword_page.alert_table.rowCount():
            self.keyword_page.alert_table.selectRow(0)
            return self.get_selected_alert_id()
        return None

    def set_unread_alert_count(self, count):
        self.keyword_page.unread.setText(f"미확인 {count}")
        self.keyword_page.unread.setVisible(bool(count))

    def show_keyword_popup(self, bid, keywords):
        QMessageBox.information(self, "매칭 키워드", f"{bid.title}\n\n" + "\n".join(f"• {word}" for word in keywords))

    def close_keyword_popup(self):
        if self.keyword_popup:
            self.keyword_popup.close()
            self.keyword_popup = None

    # EmailViewProtocol
    def open_email_settings_window(self, **kwargs):
        dialog = EmailSettingsDialog(parent=self, **kwargs)
        dialog.setWindowFlags(Qt.WindowType.Widget)
        if hasattr(dialog, "close_button"):
            dialog.close_button.setVisible(False)
        self.settings_page.show_email_management(dialog)
        return dialog

    def open_saved_bid_recipient_window(self, **kwargs):
        saved_bid = kwargs["saved_bid"]
        label = f"[저장 공고] {saved_bid.title or saved_bid.bid_no}"
        dialog = RecipientSelectionDialog(label, kwargs["recipients"], kwargs["mapped_ids"], kwargs["on_save"], self)
        self._track_dialog(dialog)
        dialog.show()
        return dialog

    def open_keyword_rule_recipient_window(self, **kwargs):
        rule = kwargs["rule"]
        label = f"조건명: {rule.get('name') or rule.get('keyword')}"
        dialog = RecipientSelectionDialog(label, kwargs["recipients"], kwargs["mapped_ids"], kwargs["on_save"], self)
        self._track_dialog(dialog)
        dialog.show()
        return dialog

    def _open_keyword_recipients(self, rule_id):
        action = getattr(self.actions, "open_keyword_rule_recipients", None)
        if action:
            action(rule_id)

    def _track_dialog(self, dialog):
        self.dialogs.append(dialog)
        dialog.finished.connect(lambda _result, value=dialog: self.dialogs.remove(value) if value in self.dialogs else None)

    @staticmethod
    def _format_keyword_summary(keywords):
        if not keywords: return "-"
        first = str(keywords[0])
        return first if len(keywords) == 1 else f"{first} 외 {len(keywords)-1}개"

    @staticmethod
    def truncate_text(text, max_length):
        text = str(text or "")
        return text if len(text) <= max_length else text[:max_length - 3] + "..."

    @staticmethod
    def _classify_log(message):
        text = str(message or "").casefold()
        if any(token in text for token in ("이메일", "메일", "smtp")): return "email"
        if any(token in text for token in ("실패", "오류", "error", "exception")): return "error"
        if any(token in text for token in ("api", "조회")): return "api"
        if "알림" in text: return "notification"
        return "info"
