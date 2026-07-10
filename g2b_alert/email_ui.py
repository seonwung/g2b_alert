import re
import tkinter as tk
from tkinter import messagebox, ttk

from .config_manager import save_config
from .credential_store import CredentialStoreError, get_smtp_password, save_smtp_password


CARD_BG = "#FFFFFF"
APP_BG = "#F6F7F9"
TEXT = "#1F2937"
SUB_TEXT = "#6B7280"
BORDER = "#D7DCE3"
INPUT_BG = "#F8FAFC"
PRIMARY = "#2563EB"
SUCCESS = "#059669"
DANGER = "#DC2626"
GRAY = "#4B5563"
FONT = ("맑은 고딕", 10)
FONT_BOLD = ("맑은 고딕", 10, "bold")


def valid_email(value):
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", (value or "").strip()))


def make_button(parent, text, command, color):
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg="white",
        activebackground=color,
        activeforeground="white",
        relief="flat",
        bd=0,
        cursor="hand2",
        font=("맑은 고딕", 9, "bold"),
        padx=10,
        pady=5,
    )


class EmailSettingsWindow:
    def __init__(self, root, config, database, on_saved, logger=None):
        self.root = root
        self.config = config
        self.database = database
        self.on_saved = on_saved
        self.logger = logger
        self.rows = []
        self.deleted_recipient_ids = set()

        self.window = tk.Toplevel(root)
        self.window.title("SMTP 및 수신자 관리")
        self.window.geometry("840x720")
        self.window.minsize(760, 620)
        self.window.configure(bg=APP_BG)
        self.window.transient(root)

        self._build_smtp_section()
        self._build_recipient_section()
        self._build_history_section()
        self._load_recipients()
        self.refresh_history()

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

    def _build_smtp_section(self):
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

        self.host_entry.insert(0, getattr(self.config, "smtp_host", "smtp.gmail.com"))
        self.port_entry.insert(0, str(getattr(self.config, "smtp_port", 587)))
        self.username_entry.insert(0, getattr(self.config, "smtp_username", ""))
        self.sender_name_entry.insert(0, getattr(self.config, "smtp_sender_name", "나라장터 알림"))

        password_state = self._password_state_text()
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
        frame.grid_columnconfigure(2, weight=1)

    def _password_state_text(self):
        username = (getattr(self.config, "smtp_username", "") or "").strip()
        if not username:
            return "Windows 자격 증명: SMTP 계정 미설정"
        try:
            saved = bool(get_smtp_password(username))
        except CredentialStoreError as error:
            return f"Windows 자격 증명: 확인 불가 ({error})"
        return "Windows 자격 증명: 앱 비밀번호 저장됨" if saved else "Windows 자격 증명: 앱 비밀번호 없음"

    def _build_recipient_section(self):
        frame = self._section("공통 수신자")
        toolbar = tk.Frame(frame, bg=CARD_BG)
        toolbar.pack(fill="x", pady=(0, 7))
        tk.Label(
            toolbar,
            text="이름과 이메일을 한 번만 저장하고 알림 대상과 연결합니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=("맑은 고딕", 9),
        ).pack(side="left")
        make_button(toolbar, "행 추가", self.add_empty_row, GRAY).pack(side="right")

        header = tk.Frame(frame, bg=CARD_BG)
        header.pack(fill="x")
        tk.Label(header, text="이름", width=18, anchor="w", bg=CARD_BG, fg=TEXT, font=FONT_BOLD).grid(row=0, column=0)
        tk.Label(header, text="이메일 주소", anchor="w", bg=CARD_BG, fg=TEXT, font=FONT_BOLD).grid(row=0, column=1, sticky="ew")
        tk.Label(header, text="키워드 알림", width=12, bg=CARD_BG, fg=TEXT, font=FONT_BOLD).grid(row=0, column=2)
        header.grid_columnconfigure(1, weight=1)

        self.recipient_rows_frame = tk.Frame(frame, bg=CARD_BG)
        self.recipient_rows_frame.pack(fill="x")

        footer = tk.Frame(frame, bg=CARD_BG)
        footer.pack(fill="x", pady=(9, 0))
        make_button(footer, "저장", self.save_all, SUCCESS).pack(side="right")
        make_button(footer, "닫기", self.window.destroy, GRAY).pack(side="right", padx=(0, 6))
        self.summary_var = tk.StringVar(value="")
        tk.Label(footer, textvariable=self.summary_var, bg=CARD_BG, fg=SUB_TEXT, font=("맑은 고딕", 9)).pack(side="left")

    def _load_recipients(self):
        mapped_ids = self.database.get_keyword_recipient_ids()
        recipients = self.database.list_recipients()
        for recipient in recipients:
            self.add_row(recipient, recipient["id"] in mapped_ids)
        while len(self.rows) < 3:
            self.add_empty_row()

    def add_empty_row(self):
        self.add_row(None, False)

    def add_row(self, recipient, keyword_enabled):
        row_frame = tk.Frame(self.recipient_rows_frame, bg=CARD_BG)
        row_frame.pack(fill="x", pady=2)
        name_entry = self._entry(row_frame, width=18)
        email_entry = self._entry(row_frame)
        keyword_var = tk.BooleanVar(value=keyword_enabled)
        keyword_check = tk.Checkbutton(
            row_frame,
            variable=keyword_var,
            bg=CARD_BG,
            activebackground=CARD_BG,
            selectcolor=CARD_BG,
            cursor="hand2",
        )
        name_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        email_entry.grid(row=0, column=1, padx=(0, 8), sticky="ew")
        keyword_check.grid(row=0, column=2, padx=(0, 8))
        row = {
            "frame": row_frame,
            "id": recipient["id"] if recipient else None,
            "name": name_entry,
            "email": email_entry,
            "keyword": keyword_var,
        }
        make_button(row_frame, "삭제", lambda: self.remove_row(row), DANGER).grid(row=0, column=3)
        row_frame.grid_columnconfigure(1, weight=1)
        if recipient:
            name_entry.insert(0, recipient["name"])
            email_entry.insert(0, recipient["email"])
        self.rows.append(row)

    def remove_row(self, row):
        if row["id"]:
            self.deleted_recipient_ids.add(row["id"])
        row["frame"].destroy()
        if row in self.rows:
            self.rows.remove(row)

    def save_all(self):
        host = self.host_entry.get().strip()
        username = self.username_entry.get().strip()
        sender_name = self.sender_name_entry.get().strip() or "나라장터 알림"
        password = self.password_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showwarning("확인", "SMTP 포트는 숫자로 입력해 주세요.", parent=self.window)
            return
        if not host or not username or "@" not in username:
            messagebox.showwarning("확인", "SMTP 서버와 Gmail 주소를 확인해 주세요.", parent=self.window)
            return

        recipient_values = []
        for row in self.rows:
            name = row["name"].get().strip()
            email = row["email"].get().strip().lower()
            if not name and not email:
                continue
            if not name or not valid_email(email):
                messagebox.showwarning("확인", "모든 수신자의 이름과 올바른 이메일 주소를 입력해 주세요.", parent=self.window)
                return
            recipient_values.append((row, name, email))

        old_username = (getattr(self.config, "smtp_username", "") or "").strip()
        if username != old_username and not password:
            messagebox.showwarning("확인", "SMTP 계정을 변경할 때는 해당 계정의 앱 비밀번호도 입력해 주세요.", parent=self.window)
            return
        if password:
            try:
                save_smtp_password(username, password)
            except CredentialStoreError as error:
                messagebox.showerror("저장 실패", str(error), parent=self.window)
                return

        saved_keyword_ids = []
        try:
            for recipient_id in self.deleted_recipient_ids:
                self.database.deactivate_recipient(recipient_id)
            for row, name, email in recipient_values:
                recipient_id = self.database.save_recipient(name, email, row["id"])
                row["id"] = recipient_id
                if row["keyword"].get():
                    saved_keyword_ids.append(recipient_id)
            self.database.set_keyword_recipients(saved_keyword_ids)
        except Exception as error:
            if self.logger:
                self.logger.exception("Could not save email recipients.")
            messagebox.showerror("저장 실패", f"수신자 설정을 저장하지 못했습니다.\n\n{error}", parent=self.window)
            return

        self.config.smtp_host = host
        self.config.smtp_port = port
        self.config.smtp_username = username
        self.config.smtp_sender_name = sender_name
        save_config(self.config)
        self.database.sync_keyword_setting(self.config.keywords, self.config.keyword_email_enabled)
        self.password_entry.delete(0, "end")
        self.deleted_recipient_ids.clear()
        self.credential_state_var.set(self._password_state_text())
        self.summary_var.set(f"저장 완료 / 키워드 알림 수신자 {len(saved_keyword_ids)}명")
        self.on_saved(self.config)
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
        make_button(frame, "기록 새로고침", self.refresh_history, GRAY).pack(anchor="e", pady=(7, 0))

    def refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        summary = self.database.get_email_delivery_summary()
        self.history_summary_var.set(
            f"대기 {summary['pending'] + summary['sending']}건 / 성공 {summary['sent']}건 / 최종 실패 {summary['failed']}건"
        )
        status_labels = {"pending": "대기", "sending": "발송 중", "sent": "성공", "failed": "실패"}
        type_labels = {"keyword_bid": "신규 공고", "bid_result": "낙찰정보"}
        for row in self.database.list_recent_email_deliveries(50):
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


class SavedBidRecipientWindow:
    def __init__(self, root, database, saved_bid, on_saved=None):
        self.database = database
        self.saved_bid = saved_bid
        self.on_saved = on_saved
        self.window = tk.Toplevel(root)
        self.window.title("저장 공고 이메일 수신자")
        self.window.geometry("470x460")
        self.window.minsize(420, 360)
        self.window.configure(bg=APP_BG)
        self.window.transient(root)

        frame = tk.Frame(self.window, bg=CARD_BG, padx=14, pady=14)
        frame.pack(fill="both", expand=True, padx=14, pady=14)
        tk.Label(
            frame,
            text=saved_bid["bid_name"] or saved_bid["bid_pbanc_no"],
            bg=CARD_BG,
            fg=TEXT,
            anchor="w",
            justify="left",
            wraplength=410,
            font=FONT_BOLD,
        ).pack(fill="x", pady=(0, 4))
        tk.Label(
            frame,
            text="체크한 수신자에게 이 공고의 신규 낙찰정보를 이메일로 보냅니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            anchor="w",
            font=("맑은 고딕", 9),
        ).pack(fill="x", pady=(0, 10))

        mapped_ids = database.get_saved_bid_recipient_ids(saved_bid["id"])
        self.recipient_vars = {}
        recipients = database.list_recipients()
        list_frame = tk.Frame(frame, bg=CARD_BG)
        list_frame.pack(fill="both", expand=True)
        if not recipients:
            tk.Label(
                list_frame,
                text="등록된 공통 수신자가 없습니다.\n키워드 설정의 [SMTP·수신자 관리]에서 먼저 등록해 주세요.",
                bg=CARD_BG,
                fg=SUB_TEXT,
                justify="center",
                font=FONT,
            ).pack(expand=True)
        for recipient in recipients:
            var = tk.BooleanVar(value=recipient["id"] in mapped_ids)
            self.recipient_vars[recipient["id"]] = var
            tk.Checkbutton(
                list_frame,
                text=f"{recipient['name']}  <{recipient['email']}>",
                variable=var,
                bg=CARD_BG,
                fg=TEXT,
                activebackground=CARD_BG,
                selectcolor=CARD_BG,
                anchor="w",
                cursor="hand2",
                font=FONT,
            ).pack(fill="x", pady=3)

        footer = tk.Frame(frame, bg=CARD_BG)
        footer.pack(fill="x", pady=(10, 0))
        make_button(footer, "저장", self.save, SUCCESS).pack(side="right")
        make_button(footer, "닫기", self.window.destroy, GRAY).pack(side="right", padx=(0, 6))

    def save(self):
        selected_ids = [recipient_id for recipient_id, var in self.recipient_vars.items() if var.get()]
        self.database.set_saved_bid_recipients(self.saved_bid["id"], selected_ids)
        if self.on_saved:
            self.on_saved(len(selected_ids))
        messagebox.showinfo("저장 완료", f"낙찰정보 이메일 수신자 {len(selected_ids)}명을 연결했습니다.", parent=self.window)
        self.window.destroy()
