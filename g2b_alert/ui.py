import os
import re
import threading
import webbrowser
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

from .app_logger import setup_logger
from .config_manager import AppConfig, SEEN_FILE, STATE_FILE, load_config, save_config
from .database import DB_FILE, G2BDatabase
from .email_service import EmailAlertService
from .email_ui import EmailSettingsWindow, SavedBidRecipientWindow
from .g2b_client import CATEGORY_LABELS, ENDPOINTS, G2BClient
from .keyword_matcher import parse_keywords
from .notifier import WindowsNotifier
from .result_service import ResultMonitorService, SavedResultScheduler
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
        self.root.geometry("920x940")
        self.root.minsize(860, 840)
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
        self.keyword_window = None
        self.manual_check_running = False
        self.result_check_running = False
        self.saved_result_scheduler = None
        self.database = G2BDatabase()
        self.database.sync_keyword_setting(self.config.keywords, self.config.keyword_email_enabled)
        self.email_alert_service = EmailAlertService(self.config, self.database, self.log, self.logger)
        self.saved_bid_rows = {}

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
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.update_running_ui(False)
        self.email_alert_service.start()
        self.root.after(500, self.start_saved_result_monitor_if_needed)
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
        header = tk.Frame(self.root, bg=CARD_BG, height=68, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="나라장터 키워드 알림",
            bg=CARD_BG,
            fg=TEXT,
            font=("맑은 고딕", 17, "bold"),
        ).pack(anchor="w", padx=22, pady=(9, 1))

        tk.Label(
            header,
            text="입찰공고를 주기적으로 확인하고 키워드가 매칭되면 윈도우 알림을 표시합니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=("맑은 고딕", 9),
        ).pack(anchor="w", padx=24)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)
        main = tk.Frame(notebook, bg=APP_BG)
        saved_page = tk.Frame(notebook, bg=APP_BG)
        notebook.add(main, text="키워드 감시")
        notebook.add(saved_page, text="저장 공고")
        self._build_status(main)
        self._build_basic_settings(main)
        self._build_keyword_settings(main)
        self._build_action_buttons(main)
        self._build_recent_alerts(main)
        self._build_saved_bids_page(saved_page)
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

        tk.Label(basic_frame, text="키워드 감시 주기", **self.label_style).grid(row=2, column=0, sticky="w", pady=(2, 5))
        interval_frame = tk.Frame(basic_frame, bg=CARD_BG)
        interval_frame.grid(row=3, column=0, columnspan=4, sticky="w")
        self.interval_entry = tk.Entry(interval_frame, width=10, **self.entry_style)
        self.interval_entry.pack(side="left")
        self.interval_entry.insert(0, str(self.config.interval))
        tk.Label(interval_frame, text="분마다 새 입찰공고를 확인합니다. 5분 권장 / 최소 1분", **self.sub_label_style).pack(side="left", padx=(8, 0))

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
            height=2,
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

        email_frame = tk.Frame(keyword_frame, bg=CARD_BG)
        email_frame.pack(fill="x", pady=(8, 0))
        self.keyword_email_var = tk.BooleanVar(value=bool(self.config.keyword_email_enabled))
        self.keyword_email_check = tk.Checkbutton(
            email_frame,
            text="신규 공고 이메일 알림 사용",
            variable=self.keyword_email_var,
            command=self.toggle_keyword_email_notifications,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=PRIMARY,
            selectcolor=CARD_BG,
            font=FONT,
            cursor="hand2",
        )
        self.keyword_email_check.pack(side="left")
        self.make_small_button(email_frame, "SMTP·수신자 관리", self.open_email_settings, GRAY).pack(side="left", padx=(10, 0))

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
        status_frame.pack(fill="x", padx=16, pady=(8, 4))
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
        self.save_alert_bid_btn = self.make_small_button(alert_toolbar, "선택한 공고 저장", self.save_selected_alert_bid, SUCCESS)
        self.save_alert_bid_btn.pack(side="right", padx=(6, 0))
        self.clear_alerts_btn = self.make_small_button(alert_toolbar, "목록 지우기", self.clear_recent_alerts, GRAY)
        self.clear_alerts_btn.pack(side="right")

        alert_table_frame = tk.Frame(alert_frame, bg=CARD_BG)
        alert_table_frame.pack(fill="x")

        columns = ("time", "category", "title", "keywords", "link")
        self.alert_tree = ttk.Treeview(alert_table_frame, columns=columns, show="headings", height=5)
        self.alert_tree.heading("time", text="시간")
        self.alert_tree.heading("category", text="종류")
        self.alert_tree.heading("title", text="공고명")
        self.alert_tree.heading("keywords", text="키워드")
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

        alert_scroll = tk.Scrollbar(alert_table_frame, orient="vertical", command=self.alert_tree.yview)
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

    def _build_saved_bids_page(self, parent):
        lookup_frame = self.make_card(parent, "공고번호 직접 조회")
        tk.Label(lookup_frame, text="입찰공고번호", **self.label_style).grid(row=0, column=0, sticky="w")
        tk.Label(lookup_frame, text="차수", **self.label_style).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.lookup_bid_no_entry = tk.Entry(lookup_frame, width=32, **self.entry_style)
        self.lookup_bid_no_entry.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.lookup_bid_ord_entry = tk.Entry(lookup_frame, width=10, **self.entry_style)
        self.lookup_bid_ord_entry.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(5, 0))
        self.lookup_bid_btn = self.make_small_button(lookup_frame, "조회", self.lookup_bid_by_no, PRIMARY)
        self.lookup_bid_btn.grid(row=1, column=2, padx=(8, 0), pady=(5, 0))
        self.save_lookup_bid_btn = self.make_small_button(lookup_frame, "조회 공고 저장", self.save_lookup_bid, SUCCESS)
        self.save_lookup_bid_btn.grid(row=1, column=3, padx=(8, 0), pady=(5, 0))
        self.lookup_result_var = tk.StringVar(value="조회된 공고가 없습니다.")
        tk.Label(
            lookup_frame,
            textvariable=self.lookup_result_var,
            bg=CARD_BG,
            fg=SUB_TEXT,
            anchor="w",
            justify="left",
            font=("맑은 고딕", 9),
            wraplength=780,
        ).grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        lookup_frame.grid_columnconfigure(0, weight=1)
        self.lookup_bid = None

        list_frame = self.make_card(parent, "저장된 공고")
        toolbar = tk.Frame(list_frame, bg=CARD_BG)
        toolbar.pack(fill="x", pady=(0, 8))
        self.saved_search_entry = tk.Entry(toolbar, width=28, **self.entry_style)
        self.saved_search_entry.pack(side="left")
        self.make_small_button(toolbar, "검색", self.refresh_saved_bids, GRAY).pack(side="left", padx=(6, 0))
        self.make_small_button(toolbar, "새로고침", self.refresh_saved_bids, GRAY).pack(side="left", padx=(6, 0))
        self.make_small_button(toolbar, "상세", self.show_saved_bid_detail, GRAY).pack(side="right", padx=(6, 0))
        self.make_small_button(toolbar, "링크 열기", self.open_saved_bid_link, GRAY).pack(side="right", padx=(6, 0))
        self.make_small_button(toolbar, "이메일 수신자", self.open_saved_bid_recipients, GRAY).pack(side="right", padx=(6, 0))
        self.make_small_button(toolbar, "낙찰정보 즉시 조회", self.check_saved_results_now, PRIMARY).pack(side="right", padx=(6, 0))
        self.make_small_button(toolbar, "조회대상 전환", self.toggle_saved_bid_monitoring, WARNING).pack(side="right", padx=(6, 0))
        self.make_small_button(toolbar, "삭제", self.delete_saved_bid, DANGER).pack(side="right")

        options_frame = tk.Frame(list_frame, bg=CARD_BG)
        options_frame.pack(fill="x", pady=(0, 8))
        tk.Label(options_frame, text="낙찰정보 감시 주기", **self.label_style).pack(side="left")
        self.result_interval_entry = tk.Entry(options_frame, width=8, **self.entry_style)
        self.result_interval_entry.pack(side="left", padx=(8, 4))
        self.result_interval_entry.insert(0, str(getattr(self.config, "result_interval", self.config.interval)))
        tk.Label(options_frame, text="분마다 저장 공고의 낙찰정보를 확인", **self.sub_label_style).pack(side="left", padx=(0, 10))
        self.make_small_button(options_frame, "주기 적용", self.apply_saved_result_interval, GRAY).pack(side="left", padx=(0, 12))

        alert_option_frame = tk.Frame(list_frame, bg=CARD_BG)
        alert_option_frame.pack(fill="x", pady=(0, 8))
        self.notify_all_results_var = tk.BooleanVar(value=bool(self.config.notify_all_opening_results))
        self.notify_all_results_check = tk.Checkbutton(
            alert_option_frame,
            text="새 낙찰정보 발견 시 윈도우/미확인 알림",
            variable=self.notify_all_results_var,
            command=self.save_result_notification_setting,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=PRIMARY,
            selectcolor=CARD_BG,
            font=FONT,
            cursor="hand2",
        )
        self.notify_all_results_check.pack(side="left")
        tk.Label(
            alert_option_frame,
            text="이메일은 공고별 [이메일 수신자] 지정 여부로 별도 전송됩니다.",
            **self.sub_label_style,
        ).pack(side="left", padx=(8, 0))

        self.saved_monitor_status_var = tk.StringVar(value="낙찰정보 자동 감시: 중지 / 조회대상 0건")
        tk.Label(
            list_frame,
            textvariable=self.saved_monitor_status_var,
            bg=CARD_BG,
            fg=TEXT,
            anchor="w",
            font=("맑은 고딕", 9, "bold"),
        ).pack(fill="x", pady=(0, 4))

        self.saved_result_status_var = tk.StringVar(value="낙찰정보 조회 전입니다.")
        tk.Label(
            list_frame,
            textvariable=self.saved_result_status_var,
            bg=CARD_BG,
            fg=SUB_TEXT,
            anchor="w",
            font=("맑은 고딕", 9),
        ).pack(fill="x", pady=(0, 8))

        table_frame = tk.Frame(list_frame, bg=CARD_BG)
        table_frame.pack(fill="both", expand=True)
        columns = ("no", "title", "demand", "bid_end", "opening", "status", "last_check", "monitoring", "result")
        self.saved_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        headings = {
            "no": "공고번호",
            "title": "공고명",
            "demand": "수요기관",
            "bid_end": "입찰마감",
            "opening": "개찰일시",
            "status": "상태",
            "last_check": "최근 조회시도",
            "monitoring": "조회대상",
            "result": "결과",
        }
        widths = {
            "no": 145,
            "title": 230,
            "demand": 130,
            "bid_end": 105,
            "opening": 105,
            "status": 80,
            "last_check": 115,
            "monitoring": 55,
            "result": 55,
        }
        for column in columns:
            self.saved_tree.heading(column, text=headings[column])
            self.saved_tree.column(column, width=widths[column], anchor="w", stretch=column == "title")
        self.saved_tree.pack(side="left", fill="both", expand=True)
        self.saved_tree.bind("<Double-1>", lambda event: self.show_saved_bid_detail())
        saved_scroll = tk.Scrollbar(table_frame, orient="vertical", command=self.saved_tree.yview)
        saved_scroll.pack(side="right", fill="y")
        self.saved_tree.configure(yscrollcommand=saved_scroll.set)
        self.refresh_saved_bids()

    def make_card(self, parent, title):
        frame = tk.LabelFrame(parent, text=title, bg=CARD_BG, fg=TEXT, padx=14, pady=10, font=("맑은 고딕", 11, "bold"), relief="solid", bd=1)
        frame.pack(fill="x", padx=16, pady=6)
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

    def mark_result_alert(self, notification):
        self.root.after(0, lambda: self._record_result_alert(notification))

    def _record_result_alert(self, notification):
        self._mark_unread_alert()
        self.refresh_saved_bids()
        result = notification.get("result") or {}
        saved_bid = notification.get("saved_bid")
        title = saved_bid["bid_name"] if saved_bid else "저장 공고"
        self.log(f"낙찰정보 알림: {title} / {result.get('successful_bidder_name') or '결과 등록'}")

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
        display_keywords = list(matched_keywords)
        keyword_summary = self._format_keyword_summary(display_keywords)
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
            "keywords": display_keywords,
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
        return f"{first_keyword} 외 {len(keywords) - 1}개"

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

    def save_selected_alert_bid(self):
        record = self.get_selected_alert_record()
        if not record or not record.get("bid"):
            messagebox.showinfo("확인", "저장할 공고를 선택해 주세요.")
            return
        self._save_bid(record["bid"])

    def lookup_bid_by_no(self):
        if self.result_check_running:
            messagebox.showinfo("확인", "다른 조회가 실행 중입니다.")
            return
        config = self.read_config_from_screen()
        if not config.api_key:
            messagebox.showwarning("확인", "API 키를 입력해 주세요.")
            return
        bid_no = self.lookup_bid_no_entry.get().strip()
        bid_ord = self.lookup_bid_ord_entry.get().strip()
        if not bid_no:
            messagebox.showwarning("확인", "입찰공고번호를 입력해 주세요.")
            return

        self.lookup_bid_btn.config(state="disabled", text="조회 중")
        self.lookup_result_var.set("공고를 조회하는 중입니다.")
        self.lookup_bid = None

        def run_lookup():
            try:
                client = G2BClient(
                    config.api_key,
                    timeout_seconds=int(config.request_timeout_seconds),
                    num_of_rows=int(config.num_of_rows),
                )
                bid = client.fetch_bid_by_no(bid_no, bid_ord)
                self.root.after(0, lambda: self._finish_lookup_bid(bid, None))
            except Exception as error:
                self.logger.exception("Bid lookup failed.")
                self.root.after(0, lambda: self._finish_lookup_bid(None, error))

        threading.Thread(target=run_lookup, daemon=True).start()

    def _finish_lookup_bid(self, bid, error):
        self.lookup_bid_btn.config(state="normal", text="조회")
        if error:
            self.lookup_result_var.set(f"조회 실패: {error}")
            messagebox.showerror("조회 실패", f"공고 조회에 실패했습니다.\n\n{error}")
            return
        if not bid:
            self.lookup_result_var.set("조회 결과가 없습니다. 공고번호, 차수, 공고 유형별 API 지원 여부를 확인해 주세요.")
            return
        self.lookup_bid = bid
        self.lookup_result_var.set(
            f"[{bid.category_label}] {bid.title}\n"
            f"공고번호: {bid.bid_no} / 차수: {bid.bid_ord or '000'} / 수요기관: {bid.demand_agency or '-'}"
        )

    def save_lookup_bid(self):
        if not self.lookup_bid:
            messagebox.showinfo("확인", "먼저 공고번호로 조회해 주세요.")
            return
        self._save_bid(self.lookup_bid)

    def _save_bid(self, bid):
        if not bid.bid_no:
            messagebox.showwarning("확인", "공고번호가 없는 공고는 저장할 수 없습니다.")
            return
        try:
            saved_id, created = self.database.save_bid(bid)
        except Exception as error:
            self.logger.exception("Save bid failed.")
            messagebox.showerror("저장 실패", f"공고 저장에 실패했습니다.\n\n{error}")
            return
        self.refresh_saved_bids()
        if created:
            self.log(f"저장 완료: {bid.bid_no} / {bid.title}")
            messagebox.showinfo("저장 완료", "공고를 저장했습니다.")
        else:
            self.log(f"이미 저장된 공고 갱신: {bid.bid_no}")
            messagebox.showinfo("저장 완료", "이미 저장된 공고라 정보를 갱신했습니다.")
        self._select_saved_bid(saved_id)
        self.start_saved_result_monitor_if_needed()

    def refresh_saved_bids(self):
        if not hasattr(self, "saved_tree"):
            return
        search_text = self.saved_search_entry.get().strip() if hasattr(self, "saved_search_entry") else ""
        for item in self.saved_tree.get_children():
            self.saved_tree.delete(item)
        self.saved_bid_rows.clear()
        try:
            rows = self.database.list_saved_bids(search_text)
        except Exception as error:
            self.logger.exception("Could not load saved bids.")
            self.log(f"저장 공고 목록 조회 실패: {error}")
            return
        monitoring_count = 0
        for row in rows:
            item_id = f"saved_{row['id']}"
            result_text = "있음" if row["result_found_at"] else "-"
            if row["monitoring_enabled"]:
                monitoring_count += 1
            values = (
                f"{row['bid_pbanc_no']}-{row['bid_pbanc_ord'] or '000'}",
                self._truncate_text(row["bid_name"], 36),
                self._truncate_text(row["demand_organization_name"], 18),
                self._short_datetime(row["bid_end_datetime"]),
                self._short_datetime(row["opening_datetime"]),
                row["status"],
                self._short_datetime(row["last_result_check_at"]),
                "ON" if row["monitoring_enabled"] else "OFF",
                result_text,
            )
            self.saved_tree.insert("", "end", iid=item_id, values=values)
            self.saved_bid_rows[item_id] = row
        self._update_saved_monitor_status(monitoring_count, len(rows))

    def _update_saved_monitor_status(self, monitoring_count=None, total_count=None):
        if not hasattr(self, "saved_monitor_status_var"):
            return
        if monitoring_count is None or total_count is None:
            monitoring_count, total_count = self._get_saved_monitor_counts()
        interval = self._get_result_interval(default="-")
        running = bool(self.saved_result_scheduler and self.saved_result_scheduler.running)
        running_text = "작동 중" if running else "중지"
        self.saved_monitor_status_var.set(
            f"낙찰정보 자동 감시: {running_text} / "
            f"주기: {interval}분 / "
            f"조회대상 {monitoring_count}건 / 저장 공고 {total_count}건"
        )

    def _get_saved_monitor_counts(self):
        try:
            rows = self.database.list_saved_bids("")
        except Exception:
            rows = list(self.saved_bid_rows.values())
        return sum(1 for row in rows if row["monitoring_enabled"]), len(rows)

    def _get_result_interval(self, default=1):
        try:
            interval = int(str(self.result_interval_entry.get()).strip())
        except Exception:
            try:
                interval = int(getattr(self.config, "result_interval", self.config.interval))
            except Exception:
                return default
        return max(MIN_INTERVAL_MINUTES, interval)

    def apply_saved_result_interval(self):
        config = self._read_result_monitor_config(show_warning=True)
        if not config:
            return
        if self.saved_result_scheduler and self.saved_result_scheduler.running:
            self.saved_result_scheduler.update_config(config)
        else:
            self.start_saved_result_monitor_if_needed(show_warning=True)
        self._update_saved_monitor_status()
        self.log(f"낙찰정보 감시 주기 변경: {config.result_interval}분")
        messagebox.showinfo("주기 적용", f"저장 공고 낙찰정보 감시 주기를 {config.result_interval}분으로 적용했습니다.")

    def save_result_notification_setting(self):
        try:
            config = self.read_config_from_screen()
            self.config = config
            save_config(config)
            if self.saved_result_scheduler and self.saved_result_scheduler.running:
                self.saved_result_scheduler.update_config(config)
            self.log(f"새 낙찰정보 알림: {'ON' if config.notify_all_opening_results else 'OFF'}")
        except Exception:
            self.logger.exception("Could not save result notification setting.")

    def _select_saved_bid(self, saved_id):
        item_id = f"saved_{saved_id}"
        if item_id in self.saved_tree.get_children():
            self.saved_tree.selection_set(item_id)
            self.saved_tree.focus(item_id)
            self.saved_tree.see(item_id)

    def get_selected_saved_bid(self):
        selected = self.saved_tree.selection()
        if not selected:
            return None
        return self.saved_bid_rows.get(selected[0])

    def _short_datetime(self, value):
        value = str(value or "")
        if len(value) >= 16 and value[4:5] == "-":
            return value[:16].replace("T", " ")
        if len(value) >= 12 and value[:12].isdigit():
            return f"{value[:4]}-{value[4:6]}-{value[6:8]} {value[8:10]}:{value[10:12]}"
        return value[:16] if value else "-"

    def _format_amount(self, value):
        text = str(value or "").strip()
        if not text:
            return "-"
        normalized = re.sub(r"[^\d.-]", "", text)
        if not normalized or normalized in {"-", ".", "-."}:
            return text
        try:
            number = float(normalized)
        except ValueError:
            return text
        if number.is_integer():
            return f"{int(number):,}원"
        return f"{number:,.2f}원"

    def delete_saved_bid(self):
        row = self.get_selected_saved_bid()
        if not row:
            messagebox.showinfo("확인", "삭제할 공고를 선택해 주세요.")
            return
        if not messagebox.askyesno("삭제 확인", "선택한 저장 공고와 관련 낙찰정보를 삭제할까요?"):
            return
        try:
            self.database.delete_saved_bid(row["id"])
        except Exception as error:
            self.logger.exception("Delete saved bid failed.")
            messagebox.showerror("삭제 실패", f"삭제에 실패했습니다.\n\n{error}")
            return
        self.refresh_saved_bids()
        self.log(f"저장 공고 삭제: {row['bid_pbanc_no']}")
        self.start_saved_result_monitor_if_needed()

    def toggle_saved_bid_monitoring(self):
        row = self.get_selected_saved_bid()
        if not row:
            messagebox.showinfo("확인", "조회대상 여부를 변경할 공고를 선택해 주세요.")
            return
        enabled = not bool(row["monitoring_enabled"])
        try:
            self.database.set_monitoring_enabled(row["id"], enabled)
        except Exception as error:
            self.logger.exception("Monitoring toggle failed.")
            messagebox.showerror("변경 실패", f"모니터링 설정 변경에 실패했습니다.\n\n{error}")
            return
        self.refresh_saved_bids()
        self._select_saved_bid(row["id"])
        self.log(f"저장 공고 낙찰정보 조회대상 {'ON' if enabled else 'OFF'}: {row['bid_pbanc_no']}")
        self.start_saved_result_monitor_if_needed(show_warning=True)
        messagebox.showinfo(
            "조회대상 변경",
            f"선택한 공고를 낙찰정보 자동 감시 대상에서 {'포함' if enabled else '제외'}했습니다.\n\n"
            f"조회대상 ON인 공고는 {self._get_result_interval()}분마다 낙찰정보 API로 확인합니다.\n"
            "새 낙찰정보가 발견되면 윈도우 알림과 미확인 배지로 알려줍니다.",
        )

    def start_saved_result_monitor_if_needed(self, show_warning=False):
        monitoring_count, total_count = self._get_saved_monitor_counts()
        if monitoring_count == 0:
            self.stop_saved_result_monitor()
            self._update_saved_monitor_status(monitoring_count, total_count)
            return False

        config = self._read_result_monitor_config(show_warning=show_warning)
        if not config:
            self._update_saved_monitor_status(monitoring_count, total_count)
            return False

        if self.saved_result_scheduler and self.saved_result_scheduler.running:
            self.saved_result_scheduler.update_config(config)
            self._update_saved_monitor_status(monitoring_count, total_count)
            return True

        self.saved_result_scheduler = SavedResultScheduler(
            config,
            self.database,
            self.log,
            self.mark_result_alert,
            self.handle_saved_result_auto_check_complete,
            WindowsNotifier(logger=self.logger),
            self.logger,
            self.email_alert_service,
        )
        self.saved_result_scheduler.start()
        self._update_saved_monitor_status(monitoring_count, total_count)
        self.log(f"저장 공고 낙찰정보 자동 감시 시작: {config.result_interval}분마다 / 조회대상 {monitoring_count}건")
        return True

    def stop_saved_result_monitor(self):
        if self.saved_result_scheduler:
            self.saved_result_scheduler.stop()
            self.saved_result_scheduler = None

    def _read_result_monitor_config(self, show_warning=False):
        config = self.read_config_from_screen()
        if not config.api_key:
            if show_warning:
                messagebox.showwarning("확인", "낙찰정보 자동 감시를 시작하려면 API 키를 입력해 주세요.")
            return None
        try:
            interval = int(str(self.result_interval_entry.get()).strip())
        except ValueError:
            if show_warning:
                messagebox.showwarning("확인", "낙찰정보 자동 감시 주기는 숫자로 입력해 주세요.")
            return None
        if interval < MIN_INTERVAL_MINUTES:
            if show_warning:
                messagebox.showwarning("확인", f"낙찰정보 자동 감시 주기는 최소 {MIN_INTERVAL_MINUTES}분 이상이어야 합니다.")
            return None
        config.result_interval = str(interval)
        self.config = config
        save_config(config)
        return config

    def handle_saved_result_auto_check_complete(self, summary):
        self.root.after(0, lambda: self._finish_saved_result_auto_check(summary))

    def _finish_saved_result_auto_check(self, summary):
        self.refresh_saved_bids()
        checked = summary["checked"]
        failed = summary.get("failed", 0)
        no_result = summary.get("no_result", 0)
        new_results = summary["new_results"]
        checked_at = summary["checked_at"].strftime("%Y-%m-%d %H:%M:%S")
        self.saved_result_status_var.set(
            f"최근 자동 조회: {checked_at} / 대상 {checked}건 / "
            f"결과 없음 {no_result}건 / 실패 {failed}건 / 새 결과 {new_results}건"
        )
        if new_results:
            self.set_status(f"낙찰정보 자동 감시 / 새 결과 {new_results}건")

    def open_saved_bid_link(self):
        row = self.get_selected_saved_bid()
        if not row:
            messagebox.showinfo("확인", "링크를 열 공고를 선택해 주세요.")
            return
        if not row["detail_url"]:
            messagebox.showinfo("확인", "선택한 공고에 링크가 없습니다.")
            return
        self.open_log_link(row["detail_url"])

    def show_saved_bid_detail(self):
        row = self.get_selected_saved_bid()
        if not row:
            messagebox.showinfo("확인", "상세보기할 공고를 선택해 주세요.")
            return
        email_recipient_count = len(self.database.get_saved_bid_recipient_ids(row["id"]))
        detail = (
            f"공고명: {row['bid_name'] or '-'}\n"
            f"공고번호: {row['bid_pbanc_no']} / 차수: {row['bid_pbanc_ord'] or '000'}\n"
            f"공고기관: {row['organization_name'] or '-'}\n"
            f"수요기관: {row['demand_organization_name'] or '-'}\n"
            f"입찰방식: {row['bid_method'] or '-'}\n"
            f"계약방법: {row['contract_method'] or '-'}\n"
            f"예산금액: {self._format_amount(row['budget_amount'])}\n"
            f"입찰마감: {self._short_datetime(row['bid_end_datetime'])}\n"
            f"개찰일시: {self._short_datetime(row['opening_datetime'])}\n"
            f"낙찰정보 조회대상: {'ON' if row['monitoring_enabled'] else 'OFF'}\n"
            f"낙찰정보 이메일 수신자: {email_recipient_count}명\n"
            f"낙찰정보 자동 감시 주기: {self._get_result_interval()}분\n"
            f"최근 낙찰정보 API 조회 시도: {self._short_datetime(row['last_result_check_at'])}\n"
            f"DB 파일: {DB_FILE}"
        )
        messagebox.showinfo("저장 공고 상세", detail)

    def check_saved_results_now(self):
        if self.result_check_running:
            messagebox.showinfo("확인", "낙찰정보 조회가 이미 실행 중입니다.")
            return
        config = self.read_config_from_screen()
        if not config.api_key:
            messagebox.showwarning("확인", "API 키를 입력해 주세요.")
            return
        self.config = config
        save_config(config)

        self.result_check_running = True
        self.set_status("낙찰정보 조회 중")
        if hasattr(self, "saved_result_status_var"):
            self.saved_result_status_var.set("낙찰정보를 조회하는 중입니다.")
        self._update_saved_monitor_status()
        self.log("저장 공고 낙찰정보 즉시 조회 시작")

        def run_check():
            try:
                monitor = ResultMonitorService(
                    config,
                    database=self.database,
                    notifier=WindowsNotifier(logger=self.logger),
                    logger=self.logger,
                    email_alert_service=self.email_alert_service,
                )
                summary = monitor.check_saved_bids(on_log=self.log)
                self.root.after(0, lambda: self._finish_saved_result_check(summary, None))
            except Exception as error:
                self.logger.exception("Saved result check failed.")
                self.root.after(0, lambda: self._finish_saved_result_check(None, error))

        threading.Thread(target=run_check, daemon=True).start()

    def _finish_saved_result_check(self, summary, error):
        self.result_check_running = False
        if error:
            self.log(f"낙찰정보 조회 실패: {error}")
            self.set_status("낙찰정보 조회 실패")
            if hasattr(self, "saved_result_status_var"):
                self.saved_result_status_var.set("낙찰정보 조회 실패")
            self._update_saved_monitor_status()
            messagebox.showerror("조회 실패", f"낙찰정보 조회에 실패했습니다.\n\n{error}")
            return
        self.refresh_saved_bids()
        for notification in summary["notifications"]:
            if self.config.windows_notifications_enabled:
                WindowsNotifier(logger=self.logger).send(notification["title"], notification["message"])
            self.log(notification["message"])
        checked = summary["checked"]
        failed = summary.get("failed", 0)
        no_result = summary.get("no_result", 0)
        new_results = summary["new_results"]
        checked_at = summary["checked_at"].strftime("%Y-%m-%d %H:%M:%S")
        status_text = (
            f"최근 낙찰정보 조회: {checked_at} / 대상 {checked}건 / "
            f"결과 없음 {no_result}건 / 실패 {failed}건 / 새 결과 {new_results}건"
        )
        if checked == 0:
            status_text += " / 조회대상 ON인 저장 공고가 없습니다."
        elif new_results == 0 and failed == 0 and no_result == 0:
            status_text += " / 새 결과 없음"
        if hasattr(self, "saved_result_status_var"):
            self.saved_result_status_var.set(status_text)
        for report in summary.get("reports", []):
            self.log(self._format_result_report(report))
        self.log(f"낙찰정보 조회 완료: 대상 {checked}건 / 결과 없음 {no_result}건 / 실패 {failed}건 / 새 결과 {new_results}건")
        self.set_status(f"낙찰정보 조회 완료 / 대상 {checked}건 / 새 결과 {new_results}건")
        detail_text = self._format_result_report_summary(summary)
        messagebox.showinfo("조회 완료", f"{status_text}\n\n{detail_text}" if detail_text else status_text)

    def _format_result_report(self, report):
        bid_no = report.get("bid_no") or "-"
        bid_ord = report.get("bid_ord") or "000"
        reason = report.get("reason") or "-"
        status = report.get("status")
        if status == "failed":
            label = "조회 실패"
        elif status == "no_result":
            label = "결과 없음"
        else:
            label = "결과 확인"
        return f"낙찰정보 {label}: {bid_no} / 차수 {bid_ord} - {reason}"

    def _format_result_report_summary(self, summary):
        reports = summary.get("reports", [])
        if not reports:
            return ""
        lines = [self._format_result_report(report) for report in reports[:8]]
        if len(reports) > 8:
            lines.append(f"... 외 {len(reports) - 8}건")
        return "\n".join(lines)

    def show_keyword_dropdown(self, item_id):
        record = self.recent_alerts.get(item_id)
        if not record:
            return

        self.hide_keyword_dropdown()
        keywords = record["keywords"]
        if not keywords:
            return

        bid = record.get("bid")
        title = self._truncate_text(getattr(bid, "title", ""), 70)

        window = tk.Toplevel(self.root)
        window.title("매칭 키워드")
        window.configure(bg=APP_BG)
        window.geometry("360x260")
        window.minsize(300, 180)
        window.transient(self.root)

        def on_close():
            self.keyword_window = None
            if self._widget_exists(window):
                window.destroy()

        frame = tk.Frame(window, bg=CARD_BG, padx=12, pady=12)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        toolbar = tk.Frame(frame, bg=CARD_BG)
        toolbar.pack(fill="x", pady=(0, 8))
        tk.Label(toolbar, text="매칭 키워드", bg=CARD_BG, fg=PRIMARY_DARK, font=FONT_BOLD).pack(side="left")
        self.make_small_button(toolbar, "닫기", on_close, GRAY).pack(side="right")

        tk.Label(
            frame,
            text=title or "선택한 공고",
            bg=CARD_BG,
            fg=SUB_TEXT,
            anchor="w",
            justify="left",
            font=("맑은 고딕", 9),
            wraplength=310,
        ).pack(fill="x", pady=(0, 8))

        list_frame = tk.Frame(frame, bg=CARD_BG)
        list_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        keyword_list = tk.Listbox(
            list_frame,
            bg=INPUT_BG,
            fg=TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=PRIMARY,
            activestyle="none",
            font=("맑은 고딕", 10),
            yscrollcommand=scrollbar.set,
        )
        keyword_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=keyword_list.yview)
        for index, keyword in enumerate(keywords, start=1):
            keyword_list.insert("end", f"{index}. {keyword}")

        window.bind("<Escape>", lambda event: on_close())
        window.protocol("WM_DELETE_WINDOW", on_close)
        self.keyword_window = window
        window.lift()
        window.focus_force()

    def hide_keyword_dropdown(self):
        if self._widget_exists(self.keyword_window):
            self.keyword_window.destroy()
        self.keyword_window = None

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

    def toggle_keyword_email_notifications(self):
        enabled = bool(self.keyword_email_var.get())
        config = self.read_config_from_screen()
        self.config = config
        self.database.sync_keyword_setting(config.keywords, enabled)
        save_config(config)
        self.email_alert_service.update_config(config)
        self.log(f"신규 공고 이메일 알림: {'ON' if enabled else 'OFF'}")
        if enabled:
            recipient_count = len(self.database.get_keyword_email_recipients())
            if not config.smtp_username or recipient_count == 0:
                messagebox.showinfo(
                    "이메일 설정 필요",
                    "이메일 알림을 사용하려면 SMTP 앱 비밀번호와 키워드 알림 수신자를 설정해 주세요.",
                )
                self.open_email_settings()

    def open_email_settings(self):
        config = self.read_config_from_screen()
        self.config = config
        self.database.sync_keyword_setting(config.keywords, config.keyword_email_enabled)
        EmailSettingsWindow(
            self.root,
            config,
            self.database,
            self.handle_email_settings_saved,
            self.logger,
        )

    def handle_email_settings_saved(self, config):
        self.config = config
        self.email_alert_service.update_config(config)
        self.log("SMTP 및 이메일 수신자 설정 저장 완료")

    def open_saved_bid_recipients(self):
        row = self.get_selected_saved_bid()
        if not row:
            messagebox.showinfo("확인", "이메일 수신자를 지정할 저장 공고를 선택해 주세요.")
            return
        SavedBidRecipientWindow(
            self.root,
            self.database,
            row,
            lambda count: self.log(
                f"저장 공고 이메일 수신자 변경: {row['bid_pbanc_no']} / {count}명"
            ),
        )

    def get_selected_categories(self):
        return [category for category, var in self.category_vars.items() if var.get()]

    def read_config_from_screen(self):
        return AppConfig(
            api_key="".join(self.api_key_entry.get().split()),
            keywords=self.keyword_text.get("1.0", "end").strip(),
            interval=self.interval_entry.get().strip(),
            result_interval=self.result_interval_entry.get().strip() if hasattr(self, "result_interval_entry") else str(getattr(self.config, "result_interval", self.config.interval)),
            selected_categories=self.get_selected_categories(),
            windows_notifications_enabled=bool(self.windows_notification_var.get()),
            bootstrap_minutes=int(self.config.bootstrap_minutes),
            overlap_minutes=int(self.config.overlap_minutes),
            request_timeout_seconds=int(self.config.request_timeout_seconds),
            num_of_rows=int(self.config.num_of_rows),
            result_monitoring_enabled=False,
            notify_all_opening_results=bool(self.notify_all_results_var.get()),
            notify_each_opening_company=bool(self.config.notify_each_opening_company),
            company_name=self.config.company_name,
            business_number=self.config.business_number,
            representative_name=self.config.representative_name,
            keyword_email_enabled=bool(self.keyword_email_var.get()),
            smtp_host=self.config.smtp_host,
            smtp_port=int(self.config.smtp_port),
            smtp_username=self.config.smtp_username,
            smtp_sender_name=self.config.smtp_sender_name,
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
            messagebox.showwarning("확인", "키워드 감시 주기는 숫자로 입력해 주세요.")
            return None
        if interval < MIN_INTERVAL_MINUTES:
            messagebox.showwarning("확인", f"키워드 감시 주기는 최소 {MIN_INTERVAL_MINUTES}분 이상으로 입력해 주세요.")
            return None

        estimated_calls = int(1440 / interval) * len(config.selected_categories)
        if warn_api_volume and (interval < RECOMMENDED_INTERVAL_MINUTES or estimated_calls > 1000):
            result = messagebox.askyesno(
                "API 호출량 확인",
                f"현재 설정은 하루 약 {estimated_calls:,}회 API를 호출할 수 있습니다.\n\n"
                f"- 키워드 감시 주기: {interval}분\n"
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
        self.database.sync_keyword_setting(config.keywords, config.keyword_email_enabled)
        self.email_alert_service.update_config(config)
        self.scheduler = BidScheduler(
            config,
            keywords,
            self.log,
            self.set_status,
            self.mark_unread_alert,
            self.set_check_summary,
            WindowsNotifier(logger=self.logger),
            self.logger,
            self.email_alert_service,
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
        self.log(f"키워드 감시 주기: {interval}분")
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
        self.database.sync_keyword_setting(config.keywords, config.keyword_email_enabled)
        self.email_alert_service.update_config(config)
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
                self.email_alert_service,
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

    def close(self):
        if self.scheduler:
            self.scheduler.stop()
        self.stop_saved_result_monitor()
        self.email_alert_service.stop()
        self.root.destroy()

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
