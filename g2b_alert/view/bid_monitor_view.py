import tkinter as tk
from datetime import timedelta
from tkinter import ttk

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
    PRIMARY_DARK,
    STATUS_BG,
    SUB_TEXT,
    SUCCESS,
    TEXT,
    WARNING,
)

CATEGORY_LABELS = {"service": "용역", "goods": "물품", "works": "공사", "etc": "기타"}


class BidMonitorViewMixin:
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

        tk.Label(basic_frame, text="키워드 감시 주기", **self.label_style).grid(
            row=2, column=0, sticky="w", pady=(2, 5)
        )
        interval_frame = tk.Frame(basic_frame, bg=CARD_BG)
        interval_frame.grid(row=3, column=0, columnspan=4, sticky="w")
        self.interval_entry = tk.Entry(interval_frame, width=10, **self.entry_style)
        self.interval_entry.pack(side="left")
        self.interval_entry.insert(0, str(self.config.interval))
        tk.Label(
            interval_frame,
            text="분마다 새 입찰공고를 확인합니다. 5분 권장 / 최소 1분",
            **self.sub_label_style,
        ).pack(side="left", padx=(8, 0))

        tk.Label(basic_frame, text="조회할 공고 종류", **self.label_style).grid(
            row=4, column=0, sticky="w", pady=(15, 5)
        )
        self.category_vars = {}
        self.category_checks = []
        category_frame = tk.Frame(basic_frame, bg=CARD_BG)
        category_frame.grid(row=5, column=0, columnspan=4, sticky="w")

        for category in CATEGORY_LABELS:
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
        windows_notification_check = tk.Checkbutton(
            basic_frame,
            text="윈도우 알림 사용",
            variable=self.windows_notification_var,
            command=self.controller.toggle_windows_notifications,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=PRIMARY,
            selectcolor=CARD_BG,
            font=FONT,
            cursor="hand2",
        )
        windows_notification_check.grid(row=6, column=0, sticky="w", pady=(12, 0))

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
        keyword_email_check = tk.Checkbutton(
            email_frame,
            text="신규 공고 이메일 알림 사용",
            variable=self.keyword_email_var,
            command=self.controller.toggle_keyword_email_notifications,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=PRIMARY,
            selectcolor=CARD_BG,
            font=FONT,
            cursor="hand2",
        )
        keyword_email_check.pack(side="left")
        self.make_small_button(
            email_frame, "SMTP·수신자 관리", self.controller.open_email_settings, GRAY
        ).pack(side="left", padx=(10, 0))

    def _build_action_buttons(self, parent):
        action_frame = tk.Frame(parent, bg=APP_BG)
        action_frame.pack(fill="x", padx=16, pady=(6, 4))

        self.start_btn = self.make_button(action_frame, "시작", self.controller.start, PRIMARY, width=12)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = self.make_button(action_frame, "중지", self.controller.stop, GRAY, width=12)
        self.stop_btn.config(state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.check_now_btn = self.make_button(action_frame, "즉시 찾기", self.controller.check_now, GRAY, width=12)
        self.check_now_btn.pack(side="left", padx=(0, 8))
        test_button = self.make_button(
            action_frame, "알림 테스트", self.controller.test_alert, SUCCESS, width=13
        )
        test_button.pack(side="left", padx=(0, 8))
        log_window_button = self.make_button(
            action_frame, "로그창 띄우기", self.open_detached_log, GRAY, width=14
        )
        log_window_button.pack(side="left", padx=(0, 8))
        self.reset_btn = self.make_button(action_frame, "확인 기록 초기화", self.controller.reset_records, DANGER, width=16)
        self.reset_btn.pack(side="left", padx=(0, 8))

    def _build_status(self, parent):
        status_frame = tk.Frame(parent, bg=STATUS_BG, highlightbackground=BORDER, highlightthickness=1)
        status_frame.pack(fill="x", padx=16, pady=(8, 4))
        self.status_var = tk.StringVar(value="상태: 대기 중")
        self.last_check_var = tk.StringVar(value="마지막 확인: -")
        self.next_check_var = tk.StringVar(value="다음 확인 예정: -")
        self.monitor_summary_var = tk.StringVar(value="감시 조건: 대기 중")
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg=STATUS_BG,
            fg=SUCCESS,
            anchor="w",
            padx=12,
            pady=6,
            font=FONT_BOLD,
        )
        status_label.grid(row=0, column=0, sticky="w")
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
            command=self.controller.acknowledge_alerts,
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

    def set_check_summary(self, checked_at, new_alert_count, all_success, interval):
        self.post(lambda: self._set_check_summary(checked_at, new_alert_count, all_success, interval))

    def _set_check_summary(self, checked_at, new_alert_count, all_success, interval):
        if all_success:
            self.last_check_var.set(f"마지막 확인: {checked_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            self.last_check_var.set("마지막 확인: 일부 조회 실패")
        if interval > 0:
            next_check_at = checked_at + timedelta(minutes=interval)
            self.next_check_var.set(f"다음 확인 예정: {next_check_at.strftime('%Y-%m-%d %H:%M')}")
        else:
            self.next_check_var.set("다음 확인 예정: -")
        if new_alert_count:
            self.status_var.set(f"상태: 최근 확인 완료 / 새 알림 {new_alert_count}건")

    def set_monitor_summary(self, summary):
        self.monitor_summary_var.set(summary)

    def toggle_api_key(self):
        self.api_key_visible = not self.api_key_visible
        self.api_key_entry.config(show="" if self.api_key_visible else "*")
        self.api_key_toggle_btn.config(text="숨기기" if self.api_key_visible else "보기")

    def finish_manual_check(self):
        self.check_now_btn.config(state="normal", text="즉시 찾기")

    def start_manual_check(self):
        self.check_now_btn.config(state="disabled", text="조회 중")

    def get_monitor_form(self):
        return {
            "api_key": self.api_key_entry.get(),
            "keywords": self.keyword_text.get("1.0", "end").strip(),
            "interval": self.interval_entry.get().strip(),
            "result_interval": self.result_interval_entry.get().strip(),
            "selected_categories": [key for key, var in self.category_vars.items() if var.get()],
            "windows_notifications_enabled": bool(self.windows_notification_var.get()),
            "notify_all_opening_results": bool(self.notify_all_results_var.get()),
            "keyword_email_enabled": bool(self.keyword_email_var.get()),
        }

    def set_next_check_pending(self):
        self.next_check_var.set("다음 확인 예정: 조회 완료 후 표시")

    def clear_next_check(self):
        self.next_check_var.set("다음 확인 예정: -")
