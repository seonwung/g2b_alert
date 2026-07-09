import os
import re
import threading
import webbrowser
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

from .app_logger import setup_logger
from .config_manager import AppConfig, SEEN_FILE, STATE_FILE, load_config, save_config
from .g2b_client import CATEGORY_LABELS, ENDPOINTS
from .keyword_matcher import parse_keywords
from .notifier import WindowsNotifier
from .scheduler import BidScheduler


APP_BG = "#F6F7F9"
CARD_BG = "#FFFFFF"
PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"
SUCCESS = "#059669"
DANGER = "#DC2626"
WARNING = "#D97706"
GRAY = "#4B5563"
DISABLED_BLUE = "#9CA3AF"
STOP_RED = "#DC2626"
TEXT = "#1F2937"
SUB_TEXT = "#6B7280"
BORDER = "#D7DCE3"
INPUT_BG = "#F8FAFC"
LOG_BG = "#111827"
LOG_TEXT = "#D1D5DB"
STATUS_BG = "#F9FAFB"

RECOMMENDED_INTERVAL_MINUTES = 5
MIN_INTERVAL_MINUTES = 1
FONT = ("맑은 고딕", 10)
FONT_BOLD = ("맑은 고딕", 10, "bold")


class G2BAlertApp:
    def __init__(self, root):
        self.root = root
        self.root.title("나라장터 키워드 알림")
        self.root.geometry("920x980")
        self.root.minsize(860, 900)
        self.root.resizable(True, True)
        self.root.configure(bg=APP_BG)

        self.logger = setup_logger()
        self.config = load_config()
        self.scheduler = None
        self.api_key_visible = False
        self.detached_log_window = None
        self.detached_log_box = None
        self.fullscreen_log_window = None
        self.fullscreen_log_box = None
        self.unread_alert_count = 0
        self.recent_alerts = {}
        self.recent_alert_seq = 0
        self.keyword_dropdown = None
        self.manual_check_running = False

        self.label_style = {"bg": CARD_BG, "fg": TEXT, "font": FONT_BOLD}
        self.sub_label_style = {"bg": CARD_BG, "fg": SUB_TEXT, "font": ("맑은 고딕", 9)}
        self.entry_style = {
            "bg": INPUT_BG,
            "fg": TEXT,
            "relief": "solid",
            "bd": 1,
            "highlightthickness": 1,
            "highlightbackground": BORDER,
            "highlightcolor": PRIMARY,
            "insertbackground": TEXT,
            "font": FONT,
        }

        self._configure_tree_style()
        self._build_ui()
        self.update_running_ui(False)
        self.log("프로그램 준비 완료")
        self.logger.info("Program started.")

    def _configure_tree_style(self):
        style = ttk.Style()
        style.configure(
            "Treeview",
            background=CARD_BG,
            foreground=TEXT,
            fieldbackground=CARD_BG,
            bordercolor=BORDER,
            rowheight=26,
            font=("맑은 고딕", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#EEF2F7",
            foreground=TEXT,
            font=("맑은 고딕", 9, "bold"),
        )

    def _build_ui(self):
        header = tk.Frame(self.root, bg=CARD_BG, height=78, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="나라장터 키워드 알림",
            bg=CARD_BG,
            fg=TEXT,
            font=("맑은 고딕", 18, "bold"),
        ).pack(anchor="w", padx=22, pady=(13, 2))

        tk.Label(
            header,
            text="입찰공고를 주기적으로 확인하고 키워드가 매칭되면 윈도우 알림을 표시합니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=("맑은 고딕", 9),
        ).pack(anchor="w", padx=24)

        main = tk.Frame(self.root, bg=APP_BG)
        main.pack(fill="both", expand=True)
        self._build_status(main)
        self._build_basic_settings(main)
        self._build_keyword_settings(main)
        self._build_action_buttons(main)
        self._build_recent_alerts(main)
        self._build_hidden_log()

    def _build_basic_settings(self, parent):
        basic_frame = self.make_card(parent, "기본 설정")
        tk.Label(basic_frame, text="공공데이터포털 API 키", **self.label_style).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        api_frame = tk.Frame(basic_frame, bg=CARD_BG)
        api_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 12))
        api_frame.grid_columnconfigure(0, weight=1)

        self.api_key_entry = tk.Entry(api_frame, show="*", **self.entry_style)
        self.api_key_entry.grid(row=0, column=0, sticky="ew")
        self.api_key_entry.insert(0, self.config.api_key)

        self.api_key_toggle_btn = tk.Button(
            api_frame,
            text="보기",
            command=self.toggle_api_key,
            bg="#E5EDFF",
            fg=PRIMARY_DARK,
            activebackground="#D7E4FF",
            activeforeground=PRIMARY_DARK,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("맑은 고딕", 9, "bold"),
            padx=10,
            pady=4,
        )
        self.api_key_toggle_btn.grid(row=0, column=1, padx=(8, 0))

        tk.Label(basic_frame, text="확인 주기", **self.label_style).grid(row=2, column=0, sticky="w", pady=(2, 5))
        interval_frame = tk.Frame(basic_frame, bg=CARD_BG)
        interval_frame.grid(row=3, column=0, columnspan=4, sticky="w")
        self.interval_entry = tk.Entry(interval_frame, width=10, **self.entry_style)
        self.interval_entry.pack(side="left")
        self.interval_entry.insert(0, str(self.config.interval))
        tk.Label(interval_frame, text="분마다 확인합니다. 5분 권장 / 최소 1분", **self.sub_label_style).pack(side="left", padx=(8, 0))

        tk.Label(basic_frame, text="조회할 공고 종류", **self.label_style).grid(row=4, column=0, sticky="w", pady=(15, 5))
        self.category_vars = {}
        self.category_checks = []
        category_frame = tk.Frame(basic_frame, bg=CARD_BG)
        category_frame.grid(row=5, column=0, columnspan=4, sticky="w")

        for category in ENDPOINTS.keys():
            var = tk.BooleanVar(value=category in self.config.selected_categories)
            self.category_vars[category] = var
            cb = tk.Checkbutton(
                category_frame,
                text=CATEGORY_LABELS.get(category, category),
                variable=var,
                bg=CARD_BG,
                fg=TEXT,
                activebackground=CARD_BG,
                activeforeground=PRIMARY,
                selectcolor=CARD_BG,
                font=FONT,
                cursor="hand2",
            )
            cb.pack(side="left", padx=(0, 20))
            self.category_checks.append(cb)

        self.windows_notification_var = tk.BooleanVar(value=bool(self.config.windows_notifications_enabled))
        self.windows_notification_check = tk.Checkbutton(
            basic_frame,
            text="윈도우 알림 사용",
            variable=self.windows_notification_var,
            command=self.toggle_windows_notifications,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=PRIMARY,
            selectcolor=CARD_BG,
            font=FONT,
            cursor="hand2",
        )
        self.windows_notification_check.grid(row=6, column=0, sticky="w", pady=(12, 0))

        basic_frame.grid_columnconfigure(0, weight=1)

    def _build_keyword_settings(self, parent):
        keyword_frame = self.make_card(parent, "키워드 설정")
        tk.Label(
            keyword_frame,
            text="쉼표 또는 줄바꿈으로 구분해서 입력하세요.\n키워드나 조회 종류를 바꾼 경우, 필요하면 [확인 기록 초기화] 후 다시 시작하세요.",
            justify="left",
            **self.sub_label_style,
        ).pack(anchor="w", pady=(0, 7))

        self.keyword_text = tk.Text(
            keyword_frame,
            height=3,
            bg=INPUT_BG,
            fg=TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=PRIMARY,
            insertbackground=TEXT,
            font=FONT,
            wrap="word",
            padx=8,
            pady=7,
        )
        self.keyword_text.pack(fill="x")
        self.keyword_text.insert("1.0", self.config.keywords)

    def _build_action_buttons(self, parent):
        action_frame = tk.Frame(parent, bg=APP_BG)
        action_frame.pack(fill="x", padx=16, pady=(6, 4))

        self.start_btn = self.make_button(action_frame, "시작", self.start, PRIMARY, width=12)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = self.make_button(action_frame, "중지", self.stop, GRAY, width=12)
        self.stop_btn.config(state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.check_now_btn = self.make_button(action_frame, "즉시 찾기", self.check_now, GRAY, width=12)
        self.check_now_btn.pack(side="left", padx=(0, 8))
        self.test_btn = self.make_button(action_frame, "알림 테스트", self.test_alert, SUCCESS, width=13)
        self.test_btn.pack(side="left", padx=(0, 8))
        self.log_window_btn = self.make_button(action_frame, "로그창 띄우기", self.open_detached_log, GRAY, width=14)
        self.log_window_btn.pack(side="left", padx=(0, 8))
        self.reset_btn = self.make_button(action_frame, "확인 기록 초기화", self.reset_records, DANGER, width=16)
        self.reset_btn.pack(side="left", padx=(0, 8))

    def _build_status(self, parent):
        status_frame = tk.Frame(parent, bg=STATUS_BG, highlightbackground=BORDER, highlightthickness=1)
        status_frame.pack(fill="x", padx=16, pady=(12, 4))
        self.status_var = tk.StringVar(value="상태: 대기 중")
        self.last_check_var = tk.StringVar(value="마지막 확인: -")
        self.next_check_var = tk.StringVar(value="다음 확인 예정: -")
        self.monitor_summary_var = tk.StringVar(value="감시 조건: 대기 중")
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg=STATUS_BG,
            fg=SUCCESS,
            anchor="w",
            padx=12,
            pady=6,
            font=FONT_BOLD,
        )
        self.status_label.grid(row=0, column=0, sticky="w")
        tk.Label(
            status_frame,
            textvariable=self.last_check_var,
            bg=STATUS_BG,
            fg=TEXT,
            anchor="w",
            padx=12,
            pady=3,
            font=("맑은 고딕", 9),
        ).grid(row=1, column=0, sticky="w")
        tk.Label(
            status_frame,
            textvariable=self.next_check_var,
            bg=STATUS_BG,
            fg=TEXT,
            anchor="w",
            padx=12,
            pady=3,
            font=("맑은 고딕", 9),
        ).grid(row=1, column=1, sticky="w")
        tk.Label(
            status_frame,
            textvariable=self.monitor_summary_var,
            bg=STATUS_BG,
            fg=SUB_TEXT,
            anchor="w",
            padx=12,
            pady=3,
            font=("맑은 고딕", 9),
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_columnconfigure(1, weight=1)
        self.unread_alert_btn = tk.Button(
            status_frame,
            text="미확인 0",
            command=self.acknowledge_alerts,
            bg=WARNING,
            fg="white",
            activebackground=WARNING,
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=FONT_BOLD,
            padx=12,
            pady=6,
        )

    def _build_recent_alerts(self, parent):
        alert_frame = tk.LabelFrame(
            parent,
            text="최근 알림",
            bg=CARD_BG,
            fg=TEXT,
            padx=10,
            pady=10,
            font=("맑은 고딕", 11, "bold"),
            relief="solid",
            bd=1,
        )
        alert_frame.pack(fill="x", padx=16, pady=(4, 8))

        alert_toolbar = tk.Frame(alert_frame, bg=CARD_BG)
        alert_toolbar.pack(fill="x", pady=(0, 8))
        tk.Label(
            alert_toolbar,
            text="매칭 키워드는 해당 칸을 클릭하면 펼쳐집니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=("맑은 고딕", 9),
        ).pack(side="left")
        self.open_alert_link_btn = self.make_small_button(alert_toolbar, "선택한 공고 링크 열기", self.open_selected_alert_link, GRAY)
        self.open_alert_link_btn.pack(side="right", padx=(6, 0))
        self.clear_alerts_btn = self.make_small_button(alert_toolbar, "목록 지우기", self.clear_recent_alerts, GRAY)
        self.clear_alerts_btn.pack(side="right")

        columns = ("time", "category", "title", "keywords", "link")
        self.alert_tree = ttk.Treeview(alert_frame, columns=columns, show="headings", height=5)
        self.alert_tree.heading("time", text="시간")
        self.alert_tree.heading("category", text="종류")
        self.alert_tree.heading("title", text="공고명")
        self.alert_tree.heading("keywords", text="매칭 키워드")
        self.alert_tree.heading("link", text="링크")
        self.alert_tree.column("time", width=70, anchor="center", stretch=False)
        self.alert_tree.column("category", width=70, anchor="center", stretch=False)
        self.alert_tree.column("title", width=330, anchor="w")
        self.alert_tree.column("keywords", width=140, anchor="w", stretch=False)
        self.alert_tree.column("link", width=70, anchor="center", stretch=False)
        self.alert_tree.pack(side="left", fill="x", expand=True)
        self.alert_tree.bind("<ButtonRelease-1>", self.handle_alert_tree_click)
        self.alert_tree.bind("<Double-1>", self.handle_alert_tree_double_click)
        self.alert_tree.bind("<Return>", lambda event: self.open_selected_alert_link())

        alert_scroll = tk.Scrollbar(alert_frame, orient="vertical", command=self.alert_tree.yview)
        alert_scroll.pack(side="right", fill="y")
        self.alert_tree.configure(yscrollcommand=alert_scroll.set)

    def _build_hidden_log(self):
        self.log_box = tk.Text(
            self.root,
            height=1,
            bg=LOG_BG,
            fg=LOG_TEXT,
            insertbackground=LOG_TEXT,
            relief="flat",
            bd=0,
            font=FONT,
            wrap="word",
            padx=10,
            pady=8,
        )
        self.log_link_count = 0
        self.log_box.config(state="disabled")

    def make_card(self, parent, title):
        frame = tk.LabelFrame(parent, text=title, bg=CARD_BG, fg=TEXT, padx=14, pady=12, font=("맑은 고딕", 11, "bold"), relief="solid", bd=1)
        frame.pack(fill="x", padx=16, pady=8)
        return frame

    def make_button(self, parent, text, command, bg_color, width=13):
        return tk.Button(parent, text=text, command=command, width=width, bg=bg_color, fg="white", activebackground=bg_color, activeforeground="white", disabledforeground="#E5E7EB", relief="flat", bd=0, cursor="hand2", font=FONT_BOLD, padx=8, pady=7)

    def make_small_button(self, parent, text, command, bg_color):
        return tk.Button(parent, text=text, command=command, bg=bg_color, fg="white", activebackground=bg_color, activeforeground="white", disabledforeground="#E5E7EB", relief="flat", bd=0, cursor="hand2", font=("맑은 고딕", 9, "bold"), padx=9, pady=4)

    def log(self, msg):
        self.root.after(0, lambda: self._append_log(msg))
        if msg:
            self.logger.info(msg)

    def set_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(f"상태: {msg}"))

    def set_check_summary(self, checked_at, new_alert_count, all_success):
        self.root.after(0, lambda: self._set_check_summary(checked_at, new_alert_count, all_success))

    def _set_check_summary(self, checked_at, new_alert_count, all_success):
        if all_success:
            self.last_check_var.set(f"마지막 확인: {checked_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            self.last_check_var.set("마지막 확인: 일부 조회 실패")
        try:
            interval = int(self.config.interval)
        except ValueError:
            interval = 0
        if interval > 0:
            next_check_at = checked_at + timedelta(minutes=interval)
            self.next_check_var.set(f"다음 확인 예정: {next_check_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            self.next_check_var.set("다음 확인 예정: -")
        if new_alert_count:
            self.status_var.set(f"상태: 최근 확인 완료 / 새 알림 {new_alert_count}건")

    def update_monitor_summary(self, config=None, keywords=None):
        config = config or self.config
        if keywords is None:
            keywords = parse_keywords(config.keywords)
        selected_labels = [CATEGORY_LABELS.get(category, category) for category in config.selected_categories]
        notification_text = "ON" if config.windows_notifications_enabled else "OFF"
        if keywords and selected_labels:
            summary = (
                f"감시 조건: 키워드 {len(keywords)}개 / "
                f"{', '.join(selected_labels)} / "
                f"{config.interval}분마다 / 윈도우 알림 {notification_text}"
            )
        else:
            summary = "감시 조건: 대기 중"
        self.monitor_summary_var.set(summary)

    def mark_unread_alert(self, bid=None, matched_keywords=None):
        self.root.after(0, lambda: self._record_alert(bid, matched_keywords or []))

    def _mark_unread_alert(self):
        self.unread_alert_count += 1
        self.unread_alert_btn.config(text=f"미확인 {self.unread_alert_count}")
        if not self.unread_alert_btn.winfo_ismapped():
            self.unread_alert_btn.grid(row=0, column=2, rowspan=3, sticky="e", padx=12)

    def acknowledge_alerts(self):
        self.clear_unread_alerts()
        first_item = self._select_first_alert()
        if first_item:
            self.alert_tree.focus_set()

    def clear_unread_alerts(self):
        self.unread_alert_count = 0
        self.unread_alert_btn.grid_forget()

    def _select_first_alert(self):
        items = self.alert_tree.get_children()
        if not items:
            return None
        first_item = items[0]
        self.alert_tree.selection_set(first_item)
        self.alert_tree.focus(first_item)
        self.alert_tree.see(first_item)
        return first_item

    def _record_alert(self, bid, matched_keywords):
        if bid is not None:
            self._add_recent_alert(bid, matched_keywords)
        if not self.config.windows_notifications_enabled:
            self._mark_unread_alert()

    def _add_recent_alert(self, bid, matched_keywords):
        self.recent_alert_seq += 1
        item_id = f"alert_{self.recent_alert_seq}"
        keyword_summary = self._format_keyword_summary(matched_keywords)
        title = self._truncate_text(bid.title, 42)
        values = (
            datetime.now().strftime("%H:%M"),
            bid.category_label,
            title,
            keyword_summary,
            "열기" if bid.link else "-",
        )
        self.alert_tree.insert("", 0, iid=item_id, values=values)
        self.recent_alerts[item_id] = {
            "bid": bid,
            "keywords": list(matched_keywords),
            "link": bid.link,
        }
        for old_item in self.alert_tree.get_children()[100:]:
            self.alert_tree.delete(old_item)
            self.recent_alerts.pop(old_item, None)

    def _format_keyword_summary(self, keywords):
        if not keywords:
            return "-"
        first_keyword = self._truncate_text(str(keywords[0]), 12)
        if len(keywords) == 1:
            return first_keyword
        return f"{first_keyword} 외 {len(keywords) - 1}개 ▼"

    def _truncate_text(self, text, max_length):
        text = str(text or "")
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def get_selected_alert_record(self):
        selected = self.alert_tree.selection()
        if not selected:
            return None
        return self.recent_alerts.get(selected[0])

    def handle_alert_tree_click(self, event):
        row_id = self.alert_tree.identify_row(event.y)
        column = self.alert_tree.identify_column(event.x)
        if row_id:
            self.alert_tree.selection_set(row_id)
            self.alert_tree.focus(row_id)
        if row_id and column == "#4":
            self.show_keyword_dropdown(row_id)
        else:
            self.hide_keyword_dropdown()

    def handle_alert_tree_double_click(self, event):
        column = self.alert_tree.identify_column(event.x)
        if column == "#4":
            row_id = self.alert_tree.identify_row(event.y) or self.alert_tree.focus()
            if row_id:
                self.show_keyword_dropdown(row_id)
            return
        self.open_selected_alert_link()

    def open_selected_alert_link(self):
        record = self.get_selected_alert_record()
        if not record:
            messagebox.showinfo("확인", "링크를 열 공고를 선택해 주세요.")
            return
        link = record.get("link")
        if not link:
            messagebox.showinfo("확인", "선택한 공고에 링크가 없습니다.")
            return
        self.open_log_link(link)

    def show_keyword_dropdown(self, item_id):
        record = self.recent_alerts.get(item_id)
        if not record:
            return

        self.hide_keyword_dropdown()
        keywords = record["keywords"]
        if not keywords:
            return

        bbox = self.alert_tree.bbox(item_id, "keywords")
        if bbox:
            x, y, width, height = bbox
            root_x = self.alert_tree.winfo_rootx() + x
            root_y = self.alert_tree.winfo_rooty() + y + height
            popup_width = max(width, 180)
        else:
            root_x = self.alert_tree.winfo_pointerx()
            root_y = self.alert_tree.winfo_pointery()
            popup_width = 220

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.configure(bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        popup.geometry(f"{popup_width}x{min(160, 28 * len(keywords) + 14)}+{root_x}+{root_y}")
        popup.transient(self.root)

        list_frame = tk.Frame(popup, bg=CARD_BG, padx=6, pady=6)
        list_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        keyword_list = tk.Listbox(
            list_frame,
            bg=INPUT_BG,
            fg=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=("맑은 고딕", 9),
            activestyle="none",
            yscrollcommand=scrollbar.set,
        )
        keyword_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=keyword_list.yview)
        for keyword in keywords:
            keyword_list.insert("end", keyword)

        popup.bind("<FocusOut>", lambda event: self.hide_keyword_dropdown())
        keyword_list.bind("<Escape>", lambda event: self.hide_keyword_dropdown())
        self.keyword_dropdown = popup
        popup.focus_force()

    def hide_keyword_dropdown(self):
        if self._widget_exists(self.keyword_dropdown):
            self.keyword_dropdown.destroy()
        self.keyword_dropdown = None

    def clear_recent_alerts(self):
        self.hide_keyword_dropdown()
        for item in self.alert_tree.get_children():
            self.alert_tree.delete(item)
        self.recent_alerts.clear()
        self.clear_unread_alerts()

    def toggle_windows_notifications(self):
        enabled = bool(self.windows_notification_var.get())
        self.config.windows_notifications_enabled = enabled
        if self.scheduler:
            self.scheduler.config.windows_notifications_enabled = enabled
        try:
            save_config(self.read_config_from_screen())
        except Exception:
            self.logger.exception("Could not save notification setting.")
        self.update_monitor_summary()
        self.log(f"윈도우 알림: {'ON' if enabled else 'OFF'}")

    def clear_log(self):
        for log_box in self._get_log_boxes():
            log_box.config(state="normal")
            log_box.delete("1.0", "end")
            log_box.config(state="disabled")
        self.log("화면 로그를 지웠습니다.")

    def toggle_api_key(self):
        self.api_key_visible = not self.api_key_visible
        self.api_key_entry.config(show="" if self.api_key_visible else "*")
        self.api_key_toggle_btn.config(text="숨기기" if self.api_key_visible else "보기")

    def _append_log(self, msg):
        from datetime import datetime

        line = "\n" if msg == "" else f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n"
        for log_box in self._get_log_boxes():
            self._insert_log_line(log_box, line)

    def _get_log_boxes(self):
        log_boxes = [self.log_box]
        if self._widget_exists(self.detached_log_box):
            log_boxes.append(self.detached_log_box)
        if self._widget_exists(self.fullscreen_log_box):
            log_boxes.append(self.fullscreen_log_box)
        return log_boxes

    def _widget_exists(self, widget):
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except tk.TclError:
            return False

    def _insert_log_line(self, log_box, line, scroll=True):
        log_box.config(state="normal")
        url_pattern = re.compile(r"https?://[^\s]+")
        last_end = 0
        for match in url_pattern.finditer(line):
            start, end = match.span()
            url = match.group()
            if start > last_end:
                log_box.insert("end", line[last_end:start])
            tag_name = f"log_link_{self.log_link_count}"
            self.log_link_count += 1
            log_box.insert("end", url, tag_name)
            log_box.tag_config(tag_name, foreground="#60A5FA", underline=True)
            log_box.tag_bind(tag_name, "<Button-1>", lambda event, link=url: self.open_log_link(link))
            log_box.tag_bind(tag_name, "<Enter>", lambda event, box=log_box: box.config(cursor="hand2"))
            log_box.tag_bind(tag_name, "<Leave>", lambda event, box=log_box: box.config(cursor=""))
            last_end = end
        if last_end < len(line):
            log_box.insert("end", line[last_end:])
        if scroll:
            log_box.see("end")
        log_box.config(state="disabled")

    def _copy_current_log_to(self, target_log_box):
        content = self.log_box.get("1.0", "end-1c")
        if not content:
            return
        for line in content.splitlines(True):
            self._insert_log_line(target_log_box, line, scroll=False)
        target_log_box.see("end")

    def open_detached_log(self):
        self._open_log_window(
            "detached_log_window",
            "detached_log_box",
            "로그창",
            geometry="900x480",
            minsize=(760, 360),
        )

    def open_fullscreen_log(self):
        self._open_log_window(
            "fullscreen_log_window",
            "fullscreen_log_box",
            "로그 전체화면",
            fullscreen=True,
        )

    def _open_log_window(self, window_attr, box_attr, title, geometry=None, minsize=None, fullscreen=False):
        existing_window = getattr(self, window_attr)
        if self._widget_exists(existing_window):
            existing_window.lift()
            existing_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        window.title(title)
        window.configure(bg=APP_BG)

        def on_close():
            setattr(self, window_attr, None)
            setattr(self, box_attr, None)
            if self._widget_exists(window):
                window.destroy()

        if fullscreen:
            window.attributes("-fullscreen", True)
            window.bind("<Escape>", lambda event: on_close())
        else:
            window.geometry(geometry)
            if minsize:
                window.minsize(*minsize)

        frame = tk.Frame(window, bg=CARD_BG, padx=10, pady=10)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        toolbar = tk.Frame(frame, bg=CARD_BG)
        toolbar.pack(fill="x", pady=(0, 8))
        tk.Label(toolbar, text=title, bg=CARD_BG, fg=PRIMARY_DARK, font=FONT_BOLD).pack(side="left")
        self.make_small_button(toolbar, "닫기", on_close, GRAY).pack(side="right")
        if not fullscreen:
            self.make_small_button(toolbar, "전체화면", self.open_fullscreen_log, GRAY).pack(side="right", padx=(0, 6))

        log_inner = tk.Frame(frame, bg=CARD_BG)
        log_inner.pack(fill="both", expand=True)
        log_scroll = tk.Scrollbar(log_inner)
        log_scroll.pack(side="right", fill="y")
        log_box = tk.Text(
            log_inner,
            bg=LOG_BG,
            fg=LOG_TEXT,
            insertbackground=LOG_TEXT,
            relief="flat",
            bd=0,
            font=FONT,
            wrap="word",
            yscrollcommand=log_scroll.set,
            padx=10,
            pady=8,
        )
        log_box.pack(side="left", fill="both", expand=True)
        log_box.config(state="disabled")
        log_scroll.config(command=log_box.yview)

        setattr(self, window_attr, window)
        setattr(self, box_attr, log_box)
        self._copy_current_log_to(log_box)
        window.protocol("WM_DELETE_WINDOW", on_close)

    def open_log_link(self, link):
        try:
            webbrowser.open(link)
        except Exception as error:
            self.log(f"링크 열기 실패: {error}")

    def get_selected_categories(self):
        return [category for category, var in self.category_vars.items() if var.get()]

    def read_config_from_screen(self):
        return AppConfig(
            api_key="".join(self.api_key_entry.get().split()),
            keywords=self.keyword_text.get("1.0", "end").strip(),
            interval=self.interval_entry.get().strip(),
            selected_categories=self.get_selected_categories(),
            windows_notifications_enabled=bool(self.windows_notification_var.get()),
            bootstrap_minutes=int(self.config.bootstrap_minutes),
            overlap_minutes=int(self.config.overlap_minutes),
            request_timeout_seconds=int(self.config.request_timeout_seconds),
            num_of_rows=int(self.config.num_of_rows),
        )

    def get_validated_monitor_inputs(self, warn_api_volume=True):
        config = self.read_config_from_screen()
        keywords = parse_keywords(config.keywords)
        if not config.api_key:
            messagebox.showwarning("확인", "API 키를 입력해 주세요.")
            return None
        if not keywords:
            messagebox.showwarning("확인", "키워드를 하나 이상 입력해 주세요.")
            return None
        if not config.selected_categories:
            messagebox.showwarning("확인", "조회할 공고 종류를 하나 이상 선택해 주세요.")
            return None
        try:
            interval = int(config.interval)
        except ValueError:
            messagebox.showwarning("확인", "확인 주기는 숫자로 입력해 주세요.")
            return None
        if interval < MIN_INTERVAL_MINUTES:
            messagebox.showwarning("확인", f"확인 주기는 최소 {MIN_INTERVAL_MINUTES}분 이상으로 입력해 주세요.")
            return None

        estimated_calls = int(1440 / interval) * len(config.selected_categories)
        if warn_api_volume and (interval < RECOMMENDED_INTERVAL_MINUTES or estimated_calls > 1000):
            result = messagebox.askyesno(
                "API 호출량 확인",
                f"현재 설정은 하루 약 {estimated_calls:,}회 API를 호출할 수 있습니다.\n\n"
                f"- 확인 주기: {interval}분\n"
                f"- 조회 종류: {len(config.selected_categories)}개\n\n"
                "5분 미만 주기는 API 호출량이 많아질 수 있습니다.\n"
                "그래도 이 설정으로 시작할까요?",
            )
            if not result:
                return None

        return config, keywords, interval, estimated_calls

    def start(self):
        validated = self.get_validated_monitor_inputs(warn_api_volume=True)
        if not validated:
            return
        config, keywords, interval, estimated_calls = validated

        self.config = config
        save_config(config)
        self.scheduler = BidScheduler(
            config,
            keywords,
            self.log,
            self.set_status,
            self.mark_unread_alert,
            self.set_check_summary,
            WindowsNotifier(logger=self.logger),
            self.logger,
        )
        if not self.scheduler.start():
            messagebox.showwarning("확인", "이전 감시 작업이 아직 종료 중입니다. 잠시 후 다시 시작해 주세요.")
            return

        self.update_running_ui(True)
        self.update_monitor_summary(config, keywords)
        self.next_check_var.set("다음 확인 예정: 조회 완료 후 표시")
        self.set_status("감시 중")
        self.log("감시 시작")
        self.log(f"키워드: {', '.join(keywords)}")
        self.log(f"확인 주기: {interval}분")
        self.log(f"예상 API 호출량: 하루 약 {estimated_calls:,}회")
        self.log(f"윈도우 알림: {'ON' if config.windows_notifications_enabled else 'OFF'}")
        selected_labels = [CATEGORY_LABELS.get(category, category) for category in config.selected_categories]
        self.log(f"조회 종류: {', '.join(selected_labels)}")

    def check_now(self):
        if self.manual_check_running:
            messagebox.showinfo("확인", "즉시 조회가 이미 실행 중입니다.")
            return

        validated = self.get_validated_monitor_inputs(warn_api_volume=False)
        if not validated:
            return
        config, keywords, interval, estimated_calls = validated

        self.config = config
        save_config(config)
        self.update_monitor_summary(config, keywords)

        if self.scheduler and self.scheduler.running:
            scheduler = self.scheduler
        else:
            scheduler = BidScheduler(
                config,
                keywords,
                self.log,
                self.set_status,
                self.mark_unread_alert,
                self.set_check_summary,
                WindowsNotifier(logger=self.logger),
                self.logger,
            )

        self.manual_check_running = True
        self.check_now_btn.config(state="disabled", text="조회 중")
        self.set_status("즉시 조회 중")
        self.log("즉시 조회 시작")

        def run_check():
            try:
                scheduler.check_once()
            except Exception as error:
                self.logger.exception("Manual check failed.")
                self.log(f"즉시 조회 실패: {error}")
                self.set_status("즉시 조회 실패")
            finally:
                self.root.after(0, self._finish_manual_check)

        threading.Thread(target=run_check, daemon=True).start()

    def _finish_manual_check(self):
        self.manual_check_running = False
        self.check_now_btn.config(state="normal", text="즉시 찾기")

    def stop(self):
        if self.scheduler:
            self.scheduler.stop()
        self.update_running_ui(False)
        self.set_status("대기 중")
        self.next_check_var.set("다음 확인 예정: -")
        self.update_monitor_summary()
        self.log("감시 중지")

    def test_alert(self):
        if not self.windows_notification_var.get():
            self.log("윈도우 알림이 OFF입니다.")
            messagebox.showinfo("알림 OFF", "윈도우 알림이 꺼져 있습니다.")
            return
        WindowsNotifier(logger=self.logger).send("나라장터 알림 테스트", "윈도우 알림이 정상 작동합니다.")
        self.log("알림 테스트 실행")

    def reset_records(self):
        if self.scheduler and self.scheduler.running:
            messagebox.showwarning("확인", "감시 중에는 초기화할 수 없습니다.\n먼저 중지 버튼을 눌러주세요.")
            return
        result = messagebox.askyesno(
            "확인 기록 초기화",
            "이미 확인한 공고 기록과 마지막 조회 시각을 삭제할까요?\n\n"
            "키워드를 바꾼 뒤 기존 공고를 다시 확인하고 싶을 때 사용하는 기능입니다.",
        )
        if not result:
            return

        deleted_files = []
        for file_path in [SEEN_FILE, STATE_FILE]:
            try:
                if file_path.exists():
                    os.remove(file_path)
                    deleted_files.append(str(file_path))
            except Exception as error:
                self.logger.exception("%s delete failed.", file_path)
                self.log(f"{file_path} 삭제 실패: {error}")
                messagebox.showerror("오류", f"{file_path} 삭제에 실패했습니다.\n\n{error}")
                return

        if deleted_files:
            self.log("확인 기록 초기화 완료")
            self.set_status("확인 기록 초기화 완료")
            messagebox.showinfo("완료", "확인 기록이 초기화되었습니다.")
        else:
            self.log("초기화할 확인 기록이 없습니다.")
            self.set_status("초기화할 기록 없음")
            messagebox.showinfo("완료", "삭제할 확인 기록이 없습니다.")

    def update_running_ui(self, is_running):
        state = "disabled" if is_running else "normal"
        self.keyword_text.config(state=state)
        self.api_key_entry.config(state=state)
        self.interval_entry.config(state=state)
        self.api_key_toggle_btn.config(state=state)
        for cb in self.category_checks:
            cb.config(state=state)
        if is_running:
            self.start_btn.config(state="disabled", text="감시 중", bg=DISABLED_BLUE, activebackground=DISABLED_BLUE)
            self.stop_btn.config(state="normal", text="중지", bg=STOP_RED, activebackground=STOP_RED)
            self.reset_btn.config(state="disabled")
        else:
            self.start_btn.config(state="normal", text="시작", bg=PRIMARY, activebackground=PRIMARY)
            self.stop_btn.config(state="disabled", text="중지", bg=GRAY, activebackground=GRAY)
            self.reset_btn.config(state="normal")
