"""PySide6 modal dialogs for details and email management."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from .qt_common import Card, button, muted, setup_table


EVENT_TYPE_LABELS = {
    "keyword_bid": "키워드 입찰공고",
    "pre_spec": "사전규격",
    "pre_spec_transition": "입찰공고 전환",
    "bid_result": "개찰·낙찰 결과",
    "bid_change": "공고 변경",
}

DELIVERY_STATUS_LABELS = {
    "pending": "대기",
    "sending": "발송 중",
    "sent": "발송 완료",
    "failed": "발송 실패",
}


class NoticeDetailDialog(QDialog):
    def __init__(self, detail, on_open_link, parent=None):
        super().__init__(parent)
        self.detail = detail
        self.setWindowTitle(f"공고 상세 - {detail.get('reference', '')}")
        self.resize(738, 639)
        self.setMinimumSize(700, 580)
        root = QVBoxLayout(self)
        root.setContentsMargins(23, 18, 23, 20)
        header = QHBoxLayout()
        title = QLabel(f"[{detail.get('stage', '-')}] {detail.get('title', '-')}")
        title.setProperty("role", "title")
        title.setWordWrap(True)
        header.addWidget(title, 1)
        if detail.get("link"):
            header.addWidget(button("나라장터에서 보기", lambda: on_open_link(detail["link"]), primary=True))
        root.addLayout(header)
        root.addWidget(muted(detail.get("reference", "")))
        tabs = QTabWidget()
        tabs.addTab(self._key_value(detail.get("basic_rows", [])), "기본정보")
        tabs.addTab(self._key_value(detail.get("schedule_rows", [])), "일정")
        tabs.addTab(self._opinions(), f"규격 의견 ({len(detail.get('opinions', []))})")
        tabs.addTab(self._results(), "개찰·낙찰")
        tabs.addTab(self._attachments(on_open_link), "첨부파일")
        tabs.addTab(self._changes(), "변경이력")
        root.addWidget(tabs, 1)

    @staticmethod
    def _display(value):
        return str(value or "").strip() or "-"

    def _key_value(self, rows):
        table = QTableWidget()
        setup_table(table, ["항목", "내용"], [185, 450])
        table.setRowCount(len(rows))
        for row, (label, value) in enumerate(rows):
            table.setItem(row, 0, QTableWidgetItem(str(label)))
            table.setItem(row, 1, QTableWidgetItem(self._display(value)))
        return table

    def _opinions(self):
        browser = QTextBrowser()
        opinions = self.detail.get("opinions", [])
        if not opinions:
            browser.setPlainText("등록된 규격 의견이 없습니다.")
        else:
            browser.setPlainText("\n\n".join(
                f"[{index}] {self._display(row.get('title'))}\n"
                f"{self._display(row.get('organization'))} · {self._display(row.get('author'))}\n"
                f"{self._display(row.get('content'))}"
                for index, row in enumerate(opinions, 1)
            ))
        return browser

    def _results(self):
        table = QTableWidget()
        columns = ["status", "company", "business_number", "amount", "rate", "ranking", "opening_at"]
        setup_table(table, ["상태", "업체명", "사업자번호", "금액", "낙찰률", "순위", "개찰일시"], [75, 145, 110, 100, 65, 45, 120])
        rows = self.detail.get("results", [])
        table.setRowCount(max(1, len(rows)))
        if not rows:
            table.setItem(0, 0, QTableWidgetItem("결과 없음"))
        for row_index, row in enumerate(rows):
            for column_index, key in enumerate(columns):
                table.setItem(row_index, column_index, QTableWidgetItem(self._display(row.get(key))))
        return table

    def _attachments(self, on_open_link):
        table = QTableWidget()
        setup_table(table, ["구분", "파일명", "URL"], [95, 260, 300])
        rows = self.detail.get("attachments", [])
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate((row.get("kind", "첨부파일"), row.get("name"), row.get("url") or "-")):
                table.setItem(row_index, column_index, QTableWidgetItem(self._display(value)))
        table.cellDoubleClicked.connect(lambda row, _column: rows[row].get("url") and on_open_link(rows[row]["url"]))
        return table

    def _changes(self):
        browser = QTextBrowser()
        versions = self.detail.get("versions", [])
        comparison = self.detail.get("comparison", {})
        lines = ["[차수별 원본]"]
        for version in reversed(versions):
            marker = "현재" if version.get("is_current") else "이전"
            lines.append(f"차수 {version.get('bid_pbanc_ord') or '000'} [{marker}] {self._display(version.get('detected_at'))}")
        lines.append("\n[최근 차수 비교]")
        changes = comparison.get("changes") or []
        lines.extend(f"• {item['label']}\n  이전: {item['before']}\n  현재: {item['after']}" for item in changes)
        if not changes:
            lines.append("표시할 변경 사항이 없습니다.")
        browser.setPlainText("\n".join(lines))
        return browser


class EmailSettingsDialog(QDialog):
    def __init__(self, settings, recipients, keyword_recipient_ids, password_state,
                 history_data, on_save, on_refresh_history, on_test_connection,
                 on_send_test, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.on_save = on_save
        self.on_refresh_history = on_refresh_history
        self.on_test_connection = on_test_connection
        self.on_send_test = on_send_test
        self.rows = []
        self.deleted_recipient_ids = set()
        self.setWindowTitle("이메일 관리")
        self.resize(944, 700)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        top = QHBoxLayout()
        sender = Card("발신자 설정")
        form = QFormLayout()
        self.host = QLineEdit(settings.smtp_host)
        self.port = QLineEdit(str(settings.smtp_port))
        self.username = QLineEdit(settings.smtp_username)
        self.sender_name = QLineEdit(settings.smtp_sender_name)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        for label, field in (("SMTP 서버", self.host), ("포트", self.port), ("발신 이메일", self.username), ("발신자 이름", self.sender_name), ("비밀번호", self.password)):
            form.addRow(label, field)
        sender.layout.addLayout(form)
        sender.layout.addWidget(muted(password_state))
        test_row = QHBoxLayout()
        self.test_recipient = QLineEdit(settings.smtp_username)
        self.test_recipient.setPlaceholderText("테스트 수신 이메일")
        test_row.addWidget(self.test_recipient, 1)
        self.connection_button = button("SMTP 연결 테스트", self.start_connection_test)
        self.send_button = button("테스트 메일", self.start_test_email, primary=True)
        test_row.addWidget(self.connection_button)
        test_row.addWidget(self.send_button)
        sender.layout.addLayout(test_row)
        top.addWidget(sender, 2)
        recipients_card = Card("수신자 설정")
        add_row = QHBoxLayout()
        add_row.addWidget(muted("공통 주소록에 등록한 수신자는 감시 조건과 저장 공고에서 선택할 수 있습니다."), 1)
        add_row.addWidget(button("수신자 추가", self.add_recipient, icon="add.svg"))
        recipients_card.layout.addLayout(add_row)
        self.recipient_table = QTableWidget()
        setup_table(self.recipient_table, ["소속", "이름", "이메일", "삭제"], [120, 110, 210, 52])
        recipients_card.layout.addWidget(self.recipient_table)
        top.addWidget(recipients_card, 3)
        root.addLayout(top, 3)
        history = Card("이메일 발송 이력")
        history_header = QHBoxLayout()
        self.history_summary = muted("")
        history_header.addWidget(self.history_summary, 1)
        history_header.addWidget(button("새로고침", self.refresh_history))
        history.layout.addLayout(history_header)
        self.history_table = QTableWidget()
        setup_table(self.history_table, ["시간", "수신자", "이벤트", "상태", "재시도", "오류"], [120, 165, 95, 65, 55, 250])
        history.layout.addWidget(self.history_table)
        root.addWidget(history, 2)
        footer = QHBoxLayout()
        footer.addStretch()
        self.close_button = button("닫기", self.reject, icon="close-tab-S.svg")
        self.save_button = button("저장", self.save, primary=True, icon="check-L-on.svg")
        footer.addWidget(self.close_button)
        footer.addWidget(self.save_button)
        root.addLayout(footer)
        for recipient in recipients:
            self.add_recipient(dict(recipient), recipient["id"] in set(keyword_recipient_ids))
        self.render_history(history_data)

    def add_recipient(self, recipient=None, keyword_enabled=False):
        recipient = recipient or {}
        row = self.recipient_table.rowCount()
        self.recipient_table.insertRow(row)
        widgets = {
            "id": recipient.get("id"),
            "name": QLineEdit(recipient.get("name", "")),
            "email": QLineEdit(recipient.get("email", "")),
            "organization": QLineEdit(recipient.get("organization", "")),
            "memo": recipient.get("memo", ""),
            "keyword_enabled": bool(keyword_enabled),
            "is_default": bool(recipient.get("is_default")),
        }
        for column, key in enumerate(("organization", "name", "email")):
            self.recipient_table.setCellWidget(row, column, widgets[key])
        remove = button("", lambda: self.remove_recipient(widgets), delete=True, height=30, icon="delete.svg")
        self.recipient_table.setCellWidget(row, 3, remove)
        self.rows.append(widgets)

    def remove_recipient(self, widgets):
        if widgets.get("id"):
            self.deleted_recipient_ids.add(widgets["id"])
        row = next((i for i in range(self.recipient_table.rowCount()) if self.recipient_table.cellWidget(i, 1) is widgets["name"]), -1)
        if row >= 0:
            self.recipient_table.removeRow(row)
        if widgets in self.rows:
            self.rows.remove(widgets)

    def _payload(self):
        return {
            "smtp_host": self.host.text().strip(), "smtp_port": self.port.text().strip(),
            "smtp_username": self.username.text().strip(), "old_username": self.settings.smtp_username,
            "smtp_sender_name": self.sender_name.text().strip(), "password": self.password.text().strip(),
            "deleted_recipient_ids": set(self.deleted_recipient_ids),
            "recipients": [{
                "id": row["id"], "name": row["name"].text().strip(), "email": row["email"].text().strip(),
                "organization": row["organization"].text().strip(), "memo": row["memo"],
                "keyword_enabled": row["keyword_enabled"], "is_default": row["is_default"],
            } for row in self.rows],
        }

    def _test_payload(self):
        result = self._payload()
        result["test_recipient"] = self.test_recipient.text().strip()
        return result

    def _start_test(self, callback):
        self.connection_button.setEnabled(False)
        self.send_button.setEnabled(False)
        callback(self._test_payload(), self.finish_test)

    def start_connection_test(self): self._start_test(self.on_test_connection)
    def start_test_email(self): self._start_test(self.on_send_test)

    def finish_test(self, result):
        self.connection_button.setEnabled(True)
        self.send_button.setEnabled(True)
        (QMessageBox.information if result.get("ok") else QMessageBox.critical)(self, "SMTP 테스트", result.get("message", ""))

    def save(self):
        result = self.on_save(self._payload())
        if not result.get("ok"):
            QMessageBox.critical(self, "저장 실패", result.get("error", "설정을 저장하지 못했습니다."))
            return
        self.password.clear()
        self.deleted_recipient_ids.clear()
        QMessageBox.information(self, "저장 완료", "SMTP와 수신자 설정을 저장했습니다.")
        self.refresh_history()

    def refresh_history(self): self.render_history(self.on_refresh_history())

    def render_history(self, data):
        summary = data["summary"]
        self.history_summary.setText(f"대기 {summary['pending'] + summary['sending']}건 · 성공 {summary['sent']}건 · 실패 {summary['failed']}건")
        rows = data["rows"]
        self.history_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = (
                (row["updated_at"] or "")[:16].replace("T", " "),
                row["recipient_email"],
                EVENT_TYPE_LABELS.get(row["event_type"], row["event_type"]),
                DELIVERY_STATUS_LABELS.get(row["status"], row["status"]),
                row["retry_count"],
                (row["last_error"] or "")[:100],
            )
            for j, value in enumerate(values):
                self.history_table.setItem(i, j, QTableWidgetItem(str(value)))


class VersionHistoryDialog(QDialog):
    def __init__(self, row, versions, comparison, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"변경공고 이력 - {row.bid_no}")
        self.resize(780, 580)
        layout = QVBoxLayout(self)
        title = QLabel(row.title or row.bid_no)
        title.setProperty("role", "title")
        layout.addWidget(title)
        browser = QTextBrowser()
        lines = [f"보관 차수 {len(versions)}개"]
        for version in reversed(versions):
            lines.append(f"차수 {version.get('bid_pbanc_ord') or '000'} · {version.get('detected_at') or '-'}")
        lines.append("\n[이전값 → 현재값]")
        for change in comparison.get("changes") or []:
            lines.append(f"{change['label']}\n  {change['before']} → {change['after']}")
        browser.setPlainText("\n".join(lines))
        layout.addWidget(browser)
