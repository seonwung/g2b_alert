import tkinter as tk
from tkinter import messagebox, ttk

from ..presentation.contracts import EmailSettingsState
from .email_common import make_dialog_button
from .styles import (
    APP_BG,
    BORDER,
    CARD_BG,
    DANGER,
    FONT,
    FONT_BOLD,
    GRAY,
    INPUT_BG,
    PRIMARY,
    SUB_TEXT,
    SUCCESS,
    TEXT,
)


class EmailSettingsWindow:
    def __init__(
        self,
        root,
        settings: EmailSettingsState,
        recipients,
        keyword_recipient_ids,
        password_state,
        history_data,
        on_save,
        on_refresh_history,
        on_test_connection,
        on_send_test,
    ):
        self.settings = settings
        self.recipients = recipients
        self.keyword_recipient_ids = set(keyword_recipient_ids)
        self.on_save = on_save
        self.on_refresh_history = on_refresh_history
        self.on_test_connection = on_test_connection
        self.on_send_test = on_send_test
        self.rows = []
        self.deleted_recipient_ids = set()

        self.window = tk.Toplevel(root)
        self.window.title("SMTP 및 수신자 관리")
        self.window.geometry("1040x800")
        self.window.minsize(900, 680)
        self.window.configure(bg=APP_BG)
        self.window.transient(root)

        self._build_smtp_section(password_state)
        self._build_recipient_section()
        self._build_history_section()
        self._load_recipients()
        self.render_history(history_data)

    def _entry(self, parent, width=None, show=None):
        return tk.Entry(
            parent,
            width=width,
            show=show,
            bg=INPUT_BG,
            fg=TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=PRIMARY,
            insertbackground=TEXT,
            font=FONT,
        )

    def _section(self, title):
        frame = tk.LabelFrame(
            self.window,
            text=title,
            bg=CARD_BG,
            fg=TEXT,
            padx=12,
            pady=10,
            font=FONT_BOLD,
            relief="solid",
            bd=1,
        )
        frame.pack(fill="x", padx=14, pady=(12, 0))
        return frame

    def _build_smtp_section(self, password_state):
        frame = self._section("공용 발신 계정")
        labels = ("SMTP 서버", "포트", "Gmail 주소", "발신자 이름", "앱 비밀번호")
        for column, label in enumerate(labels):
            tk.Label(frame, text=label, bg=CARD_BG, fg=TEXT, font=FONT_BOLD).grid(
                row=0, column=column, sticky="w", padx=(0, 8)
            )

        self.host_entry = self._entry(frame, width=20)
        self.port_entry = self._entry(frame, width=7)
        self.username_entry = self._entry(frame, width=24)
        self.sender_name_entry = self._entry(frame, width=16)
        self.password_entry = self._entry(frame, width=18, show="*")
        entries = (
            self.host_entry,
            self.port_entry,
            self.username_entry,
            self.sender_name_entry,
            self.password_entry,
        )
        for column, entry in enumerate(entries):
            entry.grid(row=1, column=column, sticky="ew", padx=(0, 8), pady=(5, 0))

        self.host_entry.insert(0, self.settings.smtp_host)
        self.port_entry.insert(0, str(self.settings.smtp_port))
        self.username_entry.insert(0, self.settings.smtp_username)
        self.sender_name_entry.insert(0, self.settings.smtp_sender_name)

        self.credential_state_var = tk.StringVar(value=password_state)
        tk.Label(
            frame,
            textvariable=self.credential_state_var,
            bg=CARD_BG,
            fg=SUB_TEXT,
            anchor="w",
            font=("맑은 고딕", 9),
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(7, 0))
        tk.Label(
            frame,
            text="앱 비밀번호는 config.json과 EXE에 저장되지 않습니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=("맑은 고딕", 9),
        ).grid(row=2, column=4, sticky="e", pady=(7, 0))

        test_frame = tk.Frame(frame, bg=CARD_BG)
        test_frame.grid(row=3, column=0, columnspan=5, sticky="ew", pady=(10, 0))
        tk.Label(test_frame, text="테스트 수신자", bg=CARD_BG, fg=TEXT, font=FONT_BOLD).pack(
            side="left"
        )
        self.test_recipient_entry = self._entry(test_frame, width=28)
        self.test_recipient_entry.pack(side="left", padx=(8, 8))
        username = (self.settings.smtp_username or "").strip()
        self.test_recipient_entry.insert(0, username)
        self.smtp_test_button = make_dialog_button(
            test_frame, "SMTP 연결 테스트", self.start_connection_test, PRIMARY
        )
        self.smtp_test_button.pack(side="left", padx=(0, 6))
        self.send_test_button = make_dialog_button(
            test_frame, "테스트 메일 보내기", self.start_test_email, SUCCESS
        )
        self.send_test_button.pack(side="left")
        self.smtp_test_status_var = tk.StringVar(value="")
        tk.Label(
            frame,
            textvariable=self.smtp_test_status_var,
            bg=CARD_BG,
            fg=SUB_TEXT,
            anchor="w",
            justify="left",
            font=("맑은 고딕", 9),
        ).grid(row=4, column=0, columnspan=5, sticky="ew", pady=(7, 0))
        frame.grid_columnconfigure(2, weight=1)

    def _smtp_test_payload(self):
        return {
            "smtp_host": self.host_entry.get().strip(),
            "smtp_port": self.port_entry.get().strip(),
            "smtp_username": self.username_entry.get().strip(),
            "smtp_sender_name": self.sender_name_entry.get().strip() or "나라장터 알림",
            "password": self.password_entry.get().strip(),
            "test_recipient": self.test_recipient_entry.get().strip(),
        }

    def start_connection_test(self):
        self._start_smtp_test(self.on_test_connection, "SMTP 연결을 확인하는 중입니다.")

    def start_test_email(self):
        self._start_smtp_test(self.on_send_test, "테스트 메일을 발송하는 중입니다.")

    def _start_smtp_test(self, callback, status):
        self.smtp_test_button.config(state="disabled")
        self.send_test_button.config(state="disabled")
        self.smtp_test_status_var.set(status)
        callback(self._smtp_test_payload(), self.finish_smtp_test)

    def finish_smtp_test(self, result):
        self.smtp_test_button.config(state="normal")
        self.send_test_button.config(state="normal")
        self.smtp_test_status_var.set("성공" if result.get("ok") else "실패")
        if result.get("ok"):
            messagebox.showinfo("SMTP 테스트", result["message"], parent=self.window)
        else:
            messagebox.showerror("SMTP 테스트 실패", result["message"], parent=self.window)

    def _build_recipient_section(self):
        frame = self._section("공통 수신자")
        toolbar = tk.Frame(frame, bg=CARD_BG)
        toolbar.pack(fill="x", pady=(0, 7))
        tk.Label(
            toolbar,
            text="주소록에 이름·이메일·소속·메모를 저장하고 공고별 수신자로 연결합니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=("맑은 고딕", 9),
        ).pack(side="left")
        make_dialog_button(toolbar, "행 추가", self.add_empty_row, GRAY).pack(side="right")

        header = tk.Frame(frame, bg=CARD_BG)
        header.pack(fill="x")
        tk.Label(
            header, text="이름", width=14, anchor="w", bg=CARD_BG, fg=TEXT, font=FONT_BOLD
        ).grid(row=0, column=0)
        tk.Label(
            header, text="이메일 주소", anchor="w", bg=CARD_BG, fg=TEXT, font=FONT_BOLD
        ).grid(row=0, column=1, sticky="ew")
        tk.Label(
            header, text="소속", width=14, anchor="w", bg=CARD_BG, fg=TEXT, font=FONT_BOLD
        ).grid(row=0, column=2)
        tk.Label(
            header, text="메모", width=15, anchor="w", bg=CARD_BG, fg=TEXT, font=FONT_BOLD
        ).grid(row=0, column=3)
        tk.Label(
            header, text="키워드", width=7, bg=CARD_BG, fg=TEXT, font=FONT_BOLD
        ).grid(row=0, column=4)
        tk.Label(
            header, text="기본", width=7, bg=CARD_BG, fg=TEXT, font=FONT_BOLD
        ).grid(row=0, column=5)
        header.grid_columnconfigure(1, weight=1)

        self.recipient_rows_frame = tk.Frame(frame, bg=CARD_BG)
        self.recipient_rows_frame.pack(fill="x")

        footer = tk.Frame(frame, bg=CARD_BG)
        footer.pack(fill="x", pady=(9, 0))
        make_dialog_button(footer, "저장", self.save_all, SUCCESS).pack(side="right")
        make_dialog_button(footer, "닫기", self.window.destroy, GRAY).pack(
            side="right", padx=(0, 6)
        )
        self.summary_var = tk.StringVar(value="")
        tk.Label(footer, textvariable=self.summary_var, bg=CARD_BG, fg=SUB_TEXT, font=("맑은 고딕", 9)).pack(side="left")

    def _load_recipients(self):
        for recipient in self.recipients:
            self.add_row(recipient, recipient["id"] in self.keyword_recipient_ids)
        while len(self.rows) < 3:
            self.add_empty_row()

    def add_empty_row(self):
        self.add_row(None, False)

    def add_row(self, recipient, keyword_enabled):
        row_frame = tk.Frame(self.recipient_rows_frame, bg=CARD_BG)
        row_frame.pack(fill="x", pady=2)
        name_entry = self._entry(row_frame, width=14)
        email_entry = self._entry(row_frame)
        organization_entry = self._entry(row_frame, width=14)
        memo_entry = self._entry(row_frame, width=15)
        keyword_var = tk.BooleanVar(value=keyword_enabled)
        default_var = tk.BooleanVar(value=bool(recipient["is_default"]) if recipient else False)
        keyword_check = tk.Checkbutton(
            row_frame,
            variable=keyword_var,
            bg=CARD_BG,
            activebackground=CARD_BG,
            selectcolor=CARD_BG,
            cursor="hand2",
        )
        default_check = tk.Checkbutton(
            row_frame,
            variable=default_var,
            bg=CARD_BG,
            activebackground=CARD_BG,
            selectcolor=CARD_BG,
            cursor="hand2",
        )
        name_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        email_entry.grid(row=0, column=1, padx=(0, 8), sticky="ew")
        organization_entry.grid(row=0, column=2, padx=(0, 8), sticky="ew")
        memo_entry.grid(row=0, column=3, padx=(0, 8), sticky="ew")
        keyword_check.grid(row=0, column=4, padx=(0, 8))
        default_check.grid(row=0, column=5, padx=(0, 8))
        row = {
            "frame": row_frame,
            "id": recipient["id"] if recipient else None,
            "name": name_entry,
            "email": email_entry,
            "organization": organization_entry,
            "memo": memo_entry,
            "keyword": keyword_var,
            "is_default": default_var,
        }
        make_dialog_button(row_frame, "삭제", lambda: self.remove_row(row), DANGER).grid(
            row=0, column=6
        )
        row_frame.grid_columnconfigure(1, weight=1)
        if recipient:
            name_entry.insert(0, recipient["name"])
            email_entry.insert(0, recipient["email"])
            organization_entry.insert(0, recipient["organization"] or "")
            memo_entry.insert(0, recipient["memo"] or "")
        self.rows.append(row)

    def remove_row(self, row):
        if row["id"]:
            self.deleted_recipient_ids.add(row["id"])
        row["frame"].destroy()
        if row in self.rows:
            self.rows.remove(row)

    def save_all(self):
        payload = {
            "smtp_host": self.host_entry.get().strip(),
            "smtp_port": self.port_entry.get().strip(),
            "smtp_username": self.username_entry.get().strip(),
            "smtp_sender_name": self.sender_name_entry.get().strip() or "나라장터 알림",
            "password": self.password_entry.get().strip(),
            "old_username": (self.settings.smtp_username or "").strip(),
            "deleted_recipient_ids": set(self.deleted_recipient_ids),
            "recipients": [
                {
                    "id": row["id"],
                    "name": row["name"].get().strip(),
                    "email": row["email"].get().strip(),
                    "organization": row["organization"].get().strip(),
                    "memo": row["memo"].get().strip(),
                    "keyword_enabled": bool(row["keyword"].get()),
                    "is_default": bool(row["is_default"].get()),
                }
                for row in self.rows
            ],
        }
        result = self.on_save(payload)
        if not result.get("ok"):
            messagebox.showerror("저장 실패", result.get("error") or "설정을 저장하지 못했습니다.", parent=self.window)
            return
        self.password_entry.delete(0, "end")
        self.deleted_recipient_ids.clear()
        self.credential_state_var.set(result["password_state"])
        self.summary_var.set(f"저장 완료 / 키워드 알림 수신자 {result['recipient_count']}명")
        self.refresh_history()

    def _build_history_section(self):
        frame = self._section("최근 이메일 발송 기록")
        self.history_summary_var = tk.StringVar(value="")
        tk.Label(
            frame,
            textvariable=self.history_summary_var,
            bg=CARD_BG,
            fg=SUB_TEXT,
            anchor="w",
            font=("맑은 고딕", 9),
        ).pack(fill="x", pady=(0, 6))
        columns = ("time", "recipient", "type", "status", "retry", "error")
        self.history_tree = ttk.Treeview(frame, columns=columns, show="headings", height=7)
        headings = {
            "time": "처리 시각",
            "recipient": "수신자",
            "type": "이벤트",
            "status": "상태",
            "retry": "재시도",
            "error": "오류",
        }
        widths = {"time": 125, "recipient": 170, "type": 80, "status": 70, "retry": 55, "error": 260}
        for column in columns:
            self.history_tree.heading(column, text=headings[column])
            self.history_tree.column(column, width=widths[column], stretch=column == "error")
        self.history_tree.pack(fill="both", expand=True)
        make_dialog_button(frame, "기록 새로고침", self.refresh_history, GRAY).pack(
            anchor="e", pady=(7, 0)
        )

    def refresh_history(self):
        self.render_history(self.on_refresh_history())

    def render_history(self, history_data):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        summary = history_data["summary"]
        self.history_summary_var.set(
            f"대기 {summary['pending'] + summary['sending']}건 / 성공 {summary['sent']}건 / 최종 실패 {summary['failed']}건"
        )
        status_labels = {"pending": "대기", "sending": "발송 중", "sent": "성공", "failed": "실패"}
        type_labels = {
            "keyword_bid": "신규 공고",
            "pre_spec": "사전규격",
            "pre_spec_transition": "입찰 전환",
            "bid_change": "변경공고",
            "bid_result": "낙찰정보",
        }
        for row in history_data["rows"]:
            self.history_tree.insert(
                "",
                "end",
                values=(
                    (row["updated_at"] or "")[:16].replace("T", " "),
                    row["recipient_email"],
                    type_labels.get(row["event_type"], row["event_type"]),
                    status_labels.get(row["status"], row["status"]),
                    row["retry_count"],
                    (row["last_error"] or "")[:80],
                ),
            )
