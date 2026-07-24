"""PySide6 modal dialogs for details and email management."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from .qt_common import (
    Card,
    DraggableDialog,
    FlowLayout,
    HelpIcon,
    button,
    clear_layout,
    muted,
    setup_table,
    show_app_message,
)
from .resources import local_icon
from ..model.notice_detail_model import format_amount, format_datetime


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


class SmtpTestDialog(DraggableDialog):
    """SMTP connection and test-mail actions in the Figma modal layout."""

    def __init__(
        self,
        payload_factory,
        on_test_connection,
        on_send_test,
        default_recipient="",
        parent=None,
    ):
        super().__init__(parent)
        self.payload_factory = payload_factory
        self.on_test_connection = on_test_connection
        self.on_send_test = on_send_test
        self._active_test = ""

        self.setObjectName("smtpTestDialog")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(428, 318)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        card = Card()
        card.setObjectName("smtpTestCard")
        card.layout.setContentsMargins(24, 18, 24, 20)
        card.layout.setSpacing(12)
        outer.addWidget(card)

        header = QHBoxLayout()
        title = QLabel("SMTP 연결 테스트")
        title.setProperty("dialogTitle", True)
        header.addWidget(title)
        header.addStretch()
        close_button = button(
            "",
            self.reject,
            height=30,
            icon="close-tab-S.svg",
        )
        close_button.setProperty("modalClose", True)
        close_button.setToolTip("닫기")
        header.addWidget(close_button)
        card.layout.addLayout(header)

        self.connection_button = button(
            "SMTP 연결 확인",
            self.start_connection_test,
            primary=True,
        )
        self.connection_button.setFixedWidth(186)
        card.layout.addWidget(
            self.connection_button,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )

        card.layout.addSpacing(23)
        section = QLabel("이메일 발송 테스트")
        section.setProperty("dialogSection", True)
        card.layout.addWidget(section)
        card.layout.addSpacing(8)

        send_row = QHBoxLayout()
        send_row.setSpacing(8)
        self.recipient = QLineEdit(default_recipient)
        self.recipient.setPlaceholderText("수신 이메일주소 입력")
        self.recipient.returnPressed.connect(self.start_send_test)
        send_row.addWidget(self.recipient, 1)
        self.send_button = button(
            "발송",
            self.start_send_test,
            primary=True,
        )
        self.send_button.setFixedWidth(80)
        send_row.addWidget(self.send_button)
        card.layout.addLayout(send_row)

        self.status = QLabel("")
        self.status.setProperty("smtpTestStatus", True)
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(36)
        card.layout.addWidget(self.status)
        card.layout.addStretch()

    def _payload(self):
        payload = self.payload_factory()
        payload["test_recipient"] = self.recipient.text().strip()
        return payload

    def _set_busy(self, busy):
        self.connection_button.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        self.recipient.setEnabled(not busy)

    def start_connection_test(self):
        self._active_test = "connection"
        self.status.clear()
        self._set_busy(True)
        self.on_test_connection(self._payload(), self.finish_test)

    def start_send_test(self):
        self._active_test = "send"
        self.status.clear()
        self._set_busy(True)
        self.on_send_test(self._payload(), self.finish_test)

    def finish_test(self, result):
        self._set_busy(False)
        succeeded = bool(result.get("ok"))
        self.status.setProperty(
            "testResult",
            "success" if succeeded else "error",
        )
        if succeeded:
            message = (
                "메일을 성공적으로 발송했습니다"
                if self._active_test == "send"
                else "SMTP 서버에 정상적으로 연결되었습니다"
            )
        else:
            message = result.get("message", "테스트에 실패했습니다.")
        self.status.setText(message)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)


class NoticeDetailDialog(DraggableDialog):
    def __init__(self, detail, on_open_link, parent=None):
        super().__init__(parent)
        self.detail = detail
        self.setWindowTitle(f"공고 상세 - {detail.get('reference', '')}")
        self.setObjectName("noticeDetailDialog")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(False)
        self.setFixedSize(680, 570)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        card = Card()
        card.setObjectName("noticeDetailCard")
        card.layout.setContentsMargins(20, 18, 20, 20)
        card.layout.setSpacing(10)
        outer.addWidget(card)
        root = card.layout
        header = QHBoxLayout()
        header.setSpacing(5)
        caption = QLabel("공고 상세")
        caption.setProperty("noticeCaption", True)
        header.addWidget(caption)
        header.addStretch()
        close_button = button(
            "",
            self.reject,
            height=24,
            icon="close-tab-S.svg",
        )
        close_button.setProperty("noticeClose", True)
        close_button.setToolTip("닫기")
        header.addWidget(close_button)
        root.addLayout(header)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel(f"[{detail.get('stage', '-')}] {detail.get('title', '-')}")
        title.setProperty("noticeTitle", True)
        title.setWordWrap(True)
        title_row.addWidget(title, 1)
        if detail.get("link"):
            notice_link = button(
                "공고 바로가기",
                lambda: on_open_link(detail["link"]),
                primary=True,
                height=32,
            )
            notice_link.setProperty("noticeLink", True)
            notice_link.setFixedWidth(112)
            title_row.addWidget(notice_link)
        root.addLayout(title_row)

        tabs = QTabWidget()
        tabs.setObjectName("noticeDetailTabs")
        tabs.setMovable(True)
        tabs.addTab(
            self._key_value(
                self._prepare_basic_rows(detail.get("basic_rows", []))
            ),
            "기본정보",
        )
        tabs.addTab(self._key_value(detail.get("schedule_rows", [])), "일정")
        tabs.addTab(self._opinions(), f"규격 의견 ({len(detail.get('opinions', []))})")
        tabs.addTab(self._results(), "개찰 · 낙찰")
        tabs.addTab(self._attachments(on_open_link), "첨부파일")
        tabs.addTab(self._changes(), "변경 이력")
        root.addWidget(tabs, 1)

    @staticmethod
    def _display(value):
        return str(value or "").strip() or "-"

    @classmethod
    def _prepare_basic_rows(cls, rows):
        """Apply Figma-only grouping without changing the detail model."""
        rows = list(rows)
        contact_labels = {"담당자", "담당자 이름", "담당자 연락처"}
        contact_values = {
            str(label): cls._display(value)
            for label, value in rows
            if str(label) in contact_labels
        }
        prepared = []
        contact_added = False
        for label, value in rows:
            label = str(label)
            if label == "추적 상태":
                continue
            if label in contact_labels:
                if contact_added:
                    continue
                name = contact_values.get(
                    "담당자 이름",
                    contact_values.get("담당자", "-"),
                )
                phone = contact_values.get("담당자 연락처", "-")
                parts = [part for part in (name, phone) if part != "-"]
                prepared.append(("담당자 정보", " · ".join(parts) or "-"))
                contact_added = True
                continue
            prepared.append((label, value))
        return prepared

    def _key_value(self, rows):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(2, 12, 6, 8)
        grid.setHorizontalSpacing(26)
        grid.setVerticalSpacing(6)
        for row_index, (label, value) in enumerate(rows):
            key = QLabel(str(label))
            key.setProperty("noticeDetailKey", True)
            value_label = QLabel(self._display(value))
            value_label.setProperty("noticeDetailValue", True)
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            grid.addWidget(key, row_index, 0)
            grid.addWidget(value_label, row_index, 1)
        grid.setColumnMinimumWidth(0, 126)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(len(rows), 1)
        scroll.setWidget(content)
        return scroll

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
        setup_table(
            table,
            ["상태", "업체명", "사업자번호", "금액", "낙찰률", "순위", "개찰일시"],
            [66, 135, 100, 82, 55, 42, 100],
        )
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
        setup_table(table, ["구분", "파일명", "URL"], [80, 210, 270])
        rows = self.detail.get("attachments", [])
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate((row.get("kind", "첨부파일"), row.get("name"), row.get("url") or "-")):
                table.setItem(row_index, column_index, QTableWidgetItem(self._display(value)))
        table.cellDoubleClicked.connect(lambda row, _column: rows[row].get("url") and on_open_link(rows[row]["url"]))
        return table

    def _changes(self):
        versions = self.detail.get("versions", [])
        comparisons = self.detail.get("version_comparisons", [])
        if not comparisons and versions:
            comparisons = [
                {}
                for _version in versions[:-1]
            ] + [self.detail.get("comparison", {})]
        return EmbeddedVersionHistory(versions, comparisons)


class EmailSettingsDialog(QWidget):
    """Embedded email settings panel matching the supplied Figma screen."""

    def __init__(self, settings, recipients, keyword_recipient_ids, password_state,
                 history_data, on_save, on_refresh_history, on_clear_history,
                 on_test_connection,
                 on_send_test, on_register_recipient=None,
                 on_delete_recipient=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.on_save = on_save
        self.on_refresh_history = on_refresh_history
        self.on_clear_history = on_clear_history
        self.on_test_connection = on_test_connection
        self.on_send_test = on_send_test
        self.on_register_recipient = on_register_recipient
        self.on_delete_recipient = on_delete_recipient
        self.rows = []
        self.deleted_recipient_ids = set()
        self.setObjectName("emailSettingsPanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        top = QHBoxLayout()
        top.setSpacing(12)

        sender = Card()
        sender_header = QHBoxLayout()
        sender_header.setSpacing(6)
        sender_header.addWidget(
            self._section_title(
                "공용 발신 계정",
                "알림 메일을 발송할 공용 SMTP 계정입니다. 서버, 포트, 발신 주소와 앱 비밀번호를 저장하면 키워드 감시와 저장 공고 알림에 공통으로 사용됩니다.",
            )
        )
        sender_header.addStretch()
        self.send_button = button("이메일 테스트", self.open_smtp_test, height=30)
        self.send_button.setProperty("emailLink", True)
        sender_header.addWidget(self.send_button)
        sender.layout.addLayout(sender_header)

        self.host = QLineEdit(settings.smtp_host)
        self.host.setPlaceholderText("서버명 입력")
        self.port = QLineEdit(str(settings.smtp_port))
        self.port.setPlaceholderText("포트번호 입력")
        self.username = QLineEdit(settings.smtp_username)
        self.username.setPlaceholderText("발신 이메일 주소 입력")
        self.sender_name = QLineEdit(settings.smtp_sender_name)
        self.sender_name.setPlaceholderText("발신자 이름 입력")
        self.password = QLineEdit()
        self.password.setPlaceholderText("앱 비밀번호(공백 없이) 입력")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        sender_grid = QGridLayout()
        sender_grid.setContentsMargins(0, 0, 0, 0)
        sender_grid.setHorizontalSpacing(8)
        sender_grid.setVerticalSpacing(8)
        sender_grid.addWidget(self._field_group("SMTP 서버", self.host), 0, 0, 1, 2)
        sender_grid.addWidget(self._field_group("포트", self.port), 0, 2)
        sender_grid.addWidget(self._field_group("발신 주소", self.username), 1, 0, 1, 2)
        sender_grid.addWidget(self._field_group("발신자명", self.sender_name), 1, 2)
        sender_grid.addWidget(self._field_group("앱 비밀번호", self.password), 2, 0, 1, 3)
        sender_grid.setColumnStretch(0, 1)
        sender_grid.setColumnStretch(1, 1)
        sender_grid.setColumnStretch(2, 1)
        sender.layout.addLayout(sender_grid)
        self.password_state = muted(password_state)
        sender.layout.addWidget(self.password_state)
        self.save_button = button("저장", self.save, primary=True)
        sender.layout.addWidget(self.save_button)

        # Kept as hidden compatibility fields for the existing payload and
        # signal/slot paths.
        self.test_recipient = QLineEdit(settings.smtp_username, self)
        self.connection_button = button("SMTP 연결 테스트", self.start_connection_test)
        self.connection_button.setParent(self)
        self.test_recipient.setVisible(False)
        self.connection_button.setVisible(False)
        self.smtp_test_dialog = None
        self.smtp_test_overlay = None
        top.addWidget(sender, 2)

        recipients_card = Card()
        recipients_card.layout.addWidget(
            self._section_title(
                "수신자 설정",
                "키워드 감시와 저장 공고 알림에서 선택할 공통 수신자 주소록입니다. 여기서 등록한 수신자는 각 감시 조건과 저장 공고의 수신 설정에서 선택할 수 있습니다.",
            )
        )
        recipients_card.layout.addWidget(
            muted("공통 주소록에 등록한 수신자는 감시 조건과 저장 공고에서 선택할 수 있습니다.")
        )
        recipient_inputs = QHBoxLayout()
        recipient_inputs.setSpacing(8)
        self.new_organization = QLineEdit()
        self.new_organization.setPlaceholderText("소속 입력")
        self.new_name = QLineEdit()
        self.new_name.setPlaceholderText("이름 입력")
        self.new_email = QLineEdit()
        self.new_email.setPlaceholderText("이메일주소 입력")
        recipient_inputs.addWidget(self._field_group("소속", self.new_organization), 1)
        recipient_inputs.addWidget(self._field_group("이름", self.new_name), 1)
        recipient_inputs.addWidget(self._field_group("이메일주소", self.new_email), 2)
        register_group = QVBoxLayout()
        register_group.setContentsMargins(0, 0, 0, 0)
        register_group.setSpacing(4)
        register_group.addWidget(QLabel(" "))
        self.register_button = button("등록", self.register_recipient, primary=True)
        register_group.addWidget(self.register_button)
        recipient_inputs.addLayout(register_group)
        recipients_card.layout.addLayout(recipient_inputs)

        self.recipient_scroll = QScrollArea()
        self.recipient_scroll.setWidgetResizable(True)
        self.recipient_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recipient_scroll.setMinimumHeight(116)
        self.recipient_scroll.setProperty("recipientList", True)
        self.recipient_list_widget = QWidget()
        self.recipient_list_layout = FlowLayout(
            self.recipient_list_widget,
            margin=0,
            horizontal_spacing=8,
            vertical_spacing=8,
        )
        self.recipient_scroll.setWidget(self.recipient_list_widget)
        recipients_card.layout.addWidget(self.recipient_scroll, 1)
        top.addWidget(recipients_card, 3)
        root.addLayout(top, 5)

        history = Card()
        history_header = QHBoxLayout()
        history_header.addWidget(self._section_title("최근 이메일 발송 기록"))
        history_header.addStretch()
        history_header.addWidget(button("기록 새로고침", self.refresh_history, height=30))
        history_header.addWidget(
            button(
                "기록 지우기",
                self.clear_history,
                delete=True,
                height=30,
            )
        )
        history.layout.addLayout(history_header)
        self.history_summary = muted("")
        self.history_summary.setVisible(False)
        self.history_table = QTableWidget()
        self.history_table.setObjectName("emailHistoryTable")
        setup_table(
            self.history_table,
            ["처리 시각", "수신자", "이벤트", "상태", "재시도", "오류"],
            [120, 165, 95, 65, 55, 250],
        )
        history.layout.addWidget(self.history_table)
        root.addWidget(history, 4)

        for recipient in recipients:
            self.add_recipient(
                dict(recipient),
                recipient["id"] in set(keyword_recipient_ids),
                render=False,
            )
        self._render_recipients()
        self.render_history(history_data)

    @staticmethod
    def _section_title(text, tooltip=""):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label = QLabel(text)
        label.setProperty("role", "section")
        layout.addWidget(label)
        if tooltip:
            layout.addWidget(HelpIcon(tooltip))
        layout.addStretch()
        return container

    @staticmethod
    def _field_group(label_text, field):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(label_text)
        label.setProperty("fieldLabel", True)
        layout.addWidget(label)
        layout.addWidget(field)
        return container

    def register_recipient(self):
        organization = self.new_organization.text().strip()
        name = self.new_name.text().strip()
        email = self.new_email.text().strip()
        if not name or "@" not in email:
            show_app_message(
                self,
                "입력 확인",
                "수신자 이름과 올바른 이메일주소를 입력해 주세요.",
                kind="warning",
            )
            return
        recipient = {"organization": organization, "name": name, "email": email}
        if self.on_register_recipient:
            result = self.on_register_recipient(recipient)
            if not result.get("ok"):
                show_app_message(
                    self,
                    "등록 실패",
                    result.get("error", "수신자를 등록하지 못했습니다."),
                    kind="error",
                )
                return
            recipient = result.get("recipient", recipient)
        self.add_recipient(recipient)
        self.new_organization.clear()
        self.new_name.clear()
        self.new_email.clear()
        self.new_organization.setFocus()

    def add_recipient(self, recipient=None, keyword_enabled=False, render=True):
        recipient = recipient or {}
        self.rows.append({
            "id": recipient.get("id"),
            "name": str(recipient.get("name", "") or ""),
            "email": str(recipient.get("email", "") or ""),
            "organization": str(recipient.get("organization", "") or ""),
            "memo": recipient.get("memo", ""),
            "keyword_enabled": bool(keyword_enabled),
            "is_default": bool(recipient.get("is_default")),
        })
        if render:
            self._render_recipients()

    def _render_recipients(self):
        clear_layout(self.recipient_list_layout)
        if not self.rows:
            self.recipient_list_layout.addWidget(muted("등록된 수신자가 없습니다."))
            return
        for row in self.rows:
            chip = QFrame()
            chip.setProperty("recipientChip", True)
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(12, 4, 5, 4)
            chip_layout.setSpacing(6)
            organization = row["organization"] or "소속 없음"
            chip_layout.addWidget(QLabel(f"{organization} {row['name']} · {row['email']}"))
            remove = button(
                "",
                lambda current=row: self.remove_recipient(current),
                height=24,
                icon="close-tab-S.svg",
            )
            remove.setProperty("chipRemove", True)
            remove.setToolTip("수신자 삭제")
            chip_layout.addWidget(remove)
            self.recipient_list_layout.addWidget(chip)

    def remove_recipient(self, row):
        if row.get("id") and self.on_delete_recipient:
            result = self.on_delete_recipient(row["id"])
            if not result.get("ok"):
                show_app_message(
                    self,
                    "삭제 실패",
                    result.get("error", "수신자를 삭제하지 못했습니다."),
                    kind="error",
                )
                return
        if row.get("id"):
            if not self.on_delete_recipient:
                self.deleted_recipient_ids.add(row["id"])
        if row in self.rows:
            self.rows.remove(row)
        self._render_recipients()

    def _payload(self):
        self.test_recipient.setText(self.username.text().strip())
        return {
            "smtp_host": self.host.text().strip(),
            "smtp_port": self.port.text().strip(),
            "smtp_username": self.username.text().strip(),
            "old_username": self.settings.smtp_username,
            "smtp_sender_name": self.sender_name.text().strip(),
            "password": self.password.text().strip(),
            "deleted_recipient_ids": set(self.deleted_recipient_ids),
            "recipients": [{
                "id": row["id"],
                "name": row["name"].strip(),
                "email": row["email"].strip(),
                "organization": row["organization"].strip(),
                "memo": row["memo"],
                "keyword_enabled": row["keyword_enabled"],
                "is_default": row["is_default"],
            } for row in self.rows],
        }

    def _test_payload(self):
        result = self._payload()
        result["test_recipient"] = self.test_recipient.text().strip()
        return result

    def open_smtp_test(self):
        modal_parent = self.window()
        self.smtp_test_overlay = QWidget(modal_parent)
        self.smtp_test_overlay.setObjectName("modalOverlay")
        self.smtp_test_overlay.setGeometry(modal_parent.rect())
        self.smtp_test_overlay.show()
        self.smtp_test_overlay.raise_()
        self.smtp_test_dialog = SmtpTestDialog(
            payload_factory=self._payload,
            on_test_connection=self.on_test_connection,
            on_send_test=self.on_send_test,
            default_recipient=self.username.text().strip(),
            parent=modal_parent,
        )
        self.smtp_test_dialog.finished.connect(self._close_smtp_test_overlay)
        self.smtp_test_dialog.open()

    def _close_smtp_test_overlay(self):
        if self.smtp_test_overlay is not None:
            self.smtp_test_overlay.deleteLater()
            self.smtp_test_overlay = None

    def _start_test(self, callback):
        self.connection_button.setEnabled(False)
        self.send_button.setEnabled(False)
        callback(self._test_payload(), self.finish_test)

    def start_connection_test(self):
        self._start_test(self.on_test_connection)

    def start_test_email(self):
        self._start_test(self.on_send_test)

    def finish_test(self, result):
        self.connection_button.setEnabled(True)
        self.send_button.setEnabled(True)
        show_app_message(
            self,
            "SMTP 테스트",
            result.get("message", ""),
            kind="info" if result.get("ok") else "error",
        )

    def save(self):
        result = self.on_save(self._payload())
        if not result.get("ok"):
            show_app_message(
                self,
                "저장 실패",
                result.get("error", "설정을 저장하지 못했습니다."),
                kind="error",
            )
            return
        self.password.clear()
        self.deleted_recipient_ids.clear()
        self.password_state.setText(result.get("password_state", self.password_state.text()))
        show_app_message(
            self,
            "저장 완료",
            "SMTP와 수신자 설정을 저장했습니다.",
        )
        self.refresh_history()

    def refresh_history(self):
        self.render_history(self.on_refresh_history())

    def clear_history(self):
        if not show_app_message(
            self,
            "이메일 발송 기록 삭제",
            "완료되거나 실패한 이메일 발송 기록을 모두 지우시겠습니까?\n"
            "현재 대기 중인 이메일은 삭제되지 않습니다.",
            kind="warning",
            question=True,
        ):
            return
        result = self.on_clear_history()
        if not result.get("ok"):
            show_app_message(
                self,
                "삭제 실패",
                result.get("error", "이메일 발송 기록을 지우지 못했습니다."),
                kind="error",
            )
            return
        self.render_history(result["history"])
        show_app_message(
            self,
            "삭제 완료",
            f"이메일 발송 기록 {result.get('deleted', 0)}건을 지웠습니다.",
        )

    def render_history(self, data):
        summary = data["summary"]
        self.history_summary.setText(
            f"대기 {summary['pending'] + summary['sending']}건 · "
            f"성공 {summary['sent']}건 · 실패 {summary['failed']}건"
        )
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


class VersionHistoryDialog(DraggableDialog):
    def __init__(self, row, versions, comparisons, parent=None):
        super().__init__(parent)
        self.row = row
        self.versions = list(versions or [])
        self.comparisons = list(comparisons or [])
        self.setWindowTitle(f"변경공고 이력 - {row.bid_no}")
        self.setObjectName("customContentDialog")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(False)
        self.setFixedSize(820, 650)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        card = Card()
        card.setObjectName("customContentDialogCard")
        outer.addWidget(card)
        layout = card.layout
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        caption = QLabel("변경공고 이력")
        caption.setProperty("historyCaption", True)
        title_column.addWidget(caption)
        title = QLabel(row.title or row.bid_no)
        title.setProperty("historyTitle", True)
        title.setWordWrap(True)
        title_column.addWidget(title)
        reference = QLabel(
            f"{row.bid_no}-{row.bid_ord or '000'} · "
            f"보관 차수 {len(self.versions)}개"
        )
        reference.setProperty("historyReference", True)
        title_column.addWidget(reference)
        header.addLayout(title_column, 1)
        close_button = button(
            "",
            self.reject,
            height=30,
            icon="close-tab-S.svg",
        )
        close_button.setProperty("contentDialogClose", True)
        close_button.setToolTip("닫기")
        header.addWidget(close_button)
        layout.addLayout(header)

        timeline_scroll = QScrollArea()
        timeline_scroll.setObjectName("historyTimeline")
        timeline_scroll.setWidgetResizable(True)
        timeline_scroll.setFrameShape(QFrame.Shape.NoFrame)
        timeline_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        timeline_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        timeline_scroll.setFixedHeight(72)
        timeline_content = QWidget()
        timeline = QHBoxLayout(timeline_content)
        timeline.setContentsMargins(4, 3, 4, 7)
        timeline.setSpacing(8)
        self.step_buttons = []
        for index, version in enumerate(self.versions):
            if index:
                connector = QLabel("→")
                connector.setProperty("historyConnector", True)
                timeline.addWidget(connector)
            order = version.get("bid_pbanc_ord") or "000"
            step = QPushButton(
                f"{order}차\n"
                f"{'최초' if index == 0 else ('현재' if index == len(self.versions) - 1 else f'변경 {index}')}"
            )
            step.setCheckable(True)
            step.setProperty("historyStep", True)
            step.setFixedSize(82, 50)
            step.clicked.connect(
                lambda _checked=False, value=index: self._render_version(value)
            )
            timeline.addWidget(step)
            self.step_buttons.append(step)
        timeline.addStretch()
        timeline_scroll.setWidget(timeline_content)
        layout.addWidget(timeline_scroll)

        self.summary = QLabel()
        self.summary.setProperty("historySummary", True)
        layout.addWidget(self.summary)

        self.change_scroll = QScrollArea()
        self.change_scroll.setObjectName("historyChanges")
        self.change_scroll.setWidgetResizable(True)
        self.change_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.change_content = QWidget()
        self.change_layout = QVBoxLayout(self.change_content)
        self.change_layout.setContentsMargins(2, 2, 6, 6)
        self.change_layout.setSpacing(10)
        self.change_scroll.setWidget(self.change_content)
        layout.addWidget(self.change_scroll, 1)

        if self.versions:
            self._render_version(len(self.versions) - 1)
        else:
            self.summary.setText("보관된 변경 이력이 없습니다.")
            self.change_layout.addStretch()

    def _render_version(self, index):
        if not 0 <= index < len(self.versions):
            return
        for button_index, step in enumerate(self.step_buttons):
            step.setChecked(button_index == index)

        clear_layout(self.change_layout)
        version = self.versions[index]
        order = version.get("bid_pbanc_ord") or "000"
        comparison = (
            self.comparisons[index]
            if index < len(self.comparisons)
            else {}
        )
        changes = list(comparison.get("changes") or [])
        if index == 0:
            self.summary.setText(
                f"{order}차 최초 등록 · "
                f"{format_datetime(version.get('detected_at'))}"
            )
            self.change_layout.addWidget(
                self._empty_card("최초 등록된 공고 원본입니다.")
            )
        else:
            previous_order = (
                self.versions[index - 1].get("bid_pbanc_ord") or "000"
            )
            self.summary.setText(
                f"{previous_order}차 → {order}차 변경사항 · "
                f"총 {len(changes)}건"
            )
            if not changes:
                self.change_layout.addWidget(
                    self._empty_card("표시할 주요 변경사항이 없습니다.")
                )
            for change in changes:
                self.change_layout.addWidget(self._change_card(change))

        original_toggle = button(
            "전체 원본 펼쳐보기",
            height=32,
        )
        original_toggle.setProperty("historyOriginalToggle", True)
        original_toggle.setCheckable(True)
        original = QTextBrowser()
        original.setProperty("historyOriginal", True)
        original.setPlainText(
            json.dumps(
                version.get("raw") or {},
                ensure_ascii=False,
                indent=2,
            )
        )
        original.setVisible(False)

        def toggle_original(checked):
            original.setVisible(checked)
            original_toggle.setText(
                "전체 원본 접기" if checked else "전체 원본 펼쳐보기"
            )

        original_toggle.toggled.connect(toggle_original)
        self.change_layout.addWidget(
            original_toggle,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        self.change_layout.addWidget(original)
        self.change_layout.addStretch()

    @staticmethod
    def _empty_card(text):
        card = QFrame()
        card.setProperty("historyEmptyCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        message = QLabel(text)
        message.setProperty("historyEmptyText", True)
        card_layout.addWidget(message)
        return card

    @staticmethod
    def _change_card(change):
        card = QFrame()
        card.setProperty("historyChangeCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 14)
        card_layout.setSpacing(8)

        heading = QHBoxLayout()
        badge = QLabel(VersionHistoryDialog._change_badge(change))
        badge.setProperty("historyChangeBadge", True)
        badge.setProperty("changeKind", str(change.get("field") or "default"))
        heading.addWidget(badge)
        label = QLabel(str(change.get("label") or "변경 항목"))
        label.setProperty("historyChangeLabel", True)
        heading.addWidget(label)
        heading.addStretch()

        if change.get("field") == "attachments":
            added = list(change.get("attachment_added") or [])
            removed = list(change.get("attachment_removed") or [])
            summary_parts = []
            if added:
                summary_parts.append(f"추가 {len(added)}개")
            if removed:
                summary_parts.append(f"삭제 {len(removed)}개")
            file_summary = QLabel(" · ".join(summary_parts) or "구성 변경")
            file_summary.setProperty("historyFileSummary", True)
            heading.addWidget(file_summary)
        card_layout.addLayout(heading)

        values = QGridLayout()
        values.setContentsMargins(0, 0, 0, 0)
        values.setHorizontalSpacing(12)
        values.setVerticalSpacing(5)
        before_label = QLabel("이전")
        before_label.setProperty("historyValueKey", "before")
        before = QLabel(
            VersionHistoryDialog._display_change_value(change, "before")
        )
        before.setProperty("historyValue", "before")
        before.setWordWrap(True)
        after_label = QLabel("현재")
        after_label.setProperty("historyValueKey", "after")
        after = QLabel(
            VersionHistoryDialog._display_change_value(change, "after")
        )
        after.setProperty("historyValue", "after")
        after.setWordWrap(True)
        values.addWidget(before_label, 0, 0)
        values.addWidget(before, 0, 1)
        values.addWidget(after_label, 1, 0)
        values.addWidget(after, 1, 1)
        values.setColumnStretch(1, 1)
        card_layout.addLayout(values)

        if change.get("field") == "attachments":
            added = list(change.get("attachment_added") or [])
            removed = list(change.get("attachment_removed") or [])
            if added or removed:
                file_toggle = button("파일명 보기", height=28)
                file_toggle.setProperty("historyFileToggle", True)
                file_toggle.setCheckable(True)
                file_details = QFrame()
                file_details.setProperty("historyFileDetails", True)
                details_layout = QVBoxLayout(file_details)
                details_layout.setContentsMargins(12, 9, 12, 9)
                details_layout.setSpacing(4)
                for name in added:
                    item = QLabel(f"+ {name}")
                    item.setProperty("historyFileItem", "added")
                    item.setWordWrap(True)
                    details_layout.addWidget(item)
                for name in removed:
                    item = QLabel(f"− {name}")
                    item.setProperty("historyFileItem", "removed")
                    item.setWordWrap(True)
                    details_layout.addWidget(item)
                file_details.setVisible(False)

                def toggle_files(checked):
                    file_details.setVisible(checked)
                    file_toggle.setText(
                        "파일명 접기" if checked else "파일명 보기"
                    )

                file_toggle.toggled.connect(toggle_files)
                card_layout.addWidget(
                    file_toggle,
                    0,
                    Qt.AlignmentFlag.AlignLeft,
                )
                card_layout.addWidget(file_details)
        return card

    @staticmethod
    def _change_badge(change):
        field = str(change.get("field") or "")
        if field == "attachments":
            return "파일 변경"
        if field == "budget_amount":
            return "금액 변경"
        if field in {
            "bid_close_at",
            "opening_at",
            "consortium_close_at",
        }:
            return "일정 변경"
        return "내용 변경"

    @staticmethod
    def _display_change_value(change, key):
        value = change.get(key)
        if change.get("field") == "budget_amount":
            return format_amount(value)
        if change.get("field") in {
            "bid_close_at",
            "opening_at",
            "consortium_close_at",
        }:
            return format_datetime(value)
        return str(value or "-").replace("T", " ")


class EmbeddedVersionHistory(QWidget):
    """Compact version timeline used inside the notice detail tab."""

    def __init__(self, versions, comparisons, parent=None):
        super().__init__(parent)
        self.versions = list(versions or [])
        self.comparisons = list(comparisons or [])
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 10, 2, 2)
        root.setSpacing(10)

        timeline = QHBoxLayout()
        timeline.setContentsMargins(2, 0, 2, 0)
        timeline.setSpacing(7)
        self.step_buttons = []
        for index, version in enumerate(self.versions):
            if index:
                connector = QLabel("→")
                connector.setProperty("historyConnector", True)
                timeline.addWidget(connector)
            order = version.get("bid_pbanc_ord") or "000"
            step = QPushButton(
                f"{order}차\n"
                f"{'최초' if index == 0 else ('현재' if index == len(self.versions) - 1 else f'변경 {index}')}"
            )
            step.setCheckable(True)
            step.setProperty("historyStep", True)
            step.setFixedSize(76, 46)
            step.clicked.connect(
                lambda _checked=False, value=index: self._render(value)
            )
            timeline.addWidget(step)
            self.step_buttons.append(step)
        timeline.addStretch()
        root.addLayout(timeline)

        self.summary = QLabel()
        self.summary.setProperty("historySummary", True)
        root.addWidget(self.summary)

        scroll = QScrollArea()
        scroll.setObjectName("historyChanges")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.change_layout = QVBoxLayout(content)
        self.change_layout.setContentsMargins(2, 2, 6, 6)
        self.change_layout.setSpacing(9)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        if self.versions:
            self._render(len(self.versions) - 1)
        else:
            self.summary.setText("보관된 변경 이력이 없습니다.")
            self.change_layout.addStretch()

    def _render(self, index):
        if not 0 <= index < len(self.versions):
            return
        for button_index, step in enumerate(self.step_buttons):
            step.setChecked(button_index == index)
        clear_layout(self.change_layout)

        version = self.versions[index]
        order = version.get("bid_pbanc_ord") or "000"
        comparison = (
            self.comparisons[index]
            if index < len(self.comparisons)
            else {}
        )
        changes = list(comparison.get("changes") or [])
        detected_at = format_datetime(version.get("detected_at"))
        if index == 0:
            self.summary.setText(
                f"{order}차 최초 등록 · {detected_at}"
            )
            self.change_layout.addWidget(
                VersionHistoryDialog._empty_card(
                    "최초 등록된 공고 원본입니다."
                )
            )
        else:
            previous_order = (
                self.versions[index - 1].get("bid_pbanc_ord") or "000"
            )
            self.summary.setText(
                f"{previous_order}차 → {order}차 변경사항 · "
                f"총 {len(changes)}건 · {detected_at}"
            )
            if not changes:
                self.change_layout.addWidget(
                    VersionHistoryDialog._empty_card(
                        "표시할 주요 변경사항이 없습니다."
                    )
                )
            for change in changes:
                self.change_layout.addWidget(
                    VersionHistoryDialog._change_card(change)
                )
        self.change_layout.addStretch()
