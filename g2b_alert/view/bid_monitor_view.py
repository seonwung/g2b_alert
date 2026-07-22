import tkinter as tk
import uuid
from datetime import timedelta
from tkinter import filedialog, ttk

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
    STOP_RED,
    SUB_TEXT,
    SUCCESS,
    TEXT,
    WARNING,
)

CATEGORY_LABELS = {"service": "용역", "goods": "물품", "works": "공사", "etc": "기타"}
OPERATOR_OPTIONS = {"OR": "or", "AND": "and", "제외": "exclude"}
TARGET_OPTIONS = {
    "입찰공고": ("bid_lifecycle",),
    "사전규격": ("prespec",),
    "사전규격 + 입찰공고": ("prespec", "bid_lifecycle"),
}


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
        self.api_key_entry.insert(0, self.initial_state.api_key)

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
        self.interval_entry.insert(0, self.initial_state.interval)
        tk.Label(
            interval_frame,
            text="분마다 새 입찰공고를 확인합니다. 5분 권장 / 최소 1분",
            **self.sub_label_style,
        ).pack(side="left", padx=(8, 0))

        self.windows_notification_var = tk.BooleanVar(
            value=self.initial_state.windows_notifications_enabled
        )
        windows_notification_check = tk.Checkbutton(
            basic_frame,
            text="윈도우 알림 사용",
            variable=self.windows_notification_var,
            command=self.actions.toggle_windows_notifications,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=PRIMARY,
            selectcolor=CARD_BG,
            font=FONT,
            cursor="hand2",
        )
        windows_notification_check.grid(row=4, column=0, sticky="w", pady=(12, 0))
        self.keyword_email_var = tk.BooleanVar(
            value=self.initial_state.keyword_email_enabled
        )
        keyword_email_check = tk.Checkbutton(
            basic_frame,
            text="신규 공고 이메일 알림 사용",
            variable=self.keyword_email_var,
            command=self.actions.toggle_keyword_email_notifications,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=PRIMARY,
            selectcolor=CARD_BG,
            font=FONT,
            cursor="hand2",
        )
        keyword_email_check.grid(row=4, column=1, sticky="w", pady=(12, 0))
        self.make_small_button(
            basic_frame, "SMTP·수신자 관리", self.actions.open_email_settings, GRAY
        ).grid(row=4, column=2, sticky="w", padx=(8, 0), pady=(12, 0))
        tk.Label(
            basic_frame,
            text="알림 채널은 모든 감시 키워드에 공통으로 적용됩니다.",
            **self.sub_label_style,
        ).grid(row=5, column=0, columnspan=4, sticky="w", pady=(4, 0))

        tk.Label(basic_frame, text="첨부파일 자동 저장 경로", **self.label_style).grid(
            row=6, column=0, columnspan=4, sticky="w", pady=(14, 5)
        )
        download_frame = tk.Frame(basic_frame, bg=CARD_BG)
        download_frame.grid(row=7, column=0, columnspan=4, sticky="ew")
        download_frame.grid_columnconfigure(0, weight=1)
        self.attachment_download_dir_entry = tk.Entry(download_frame, **self.entry_style)
        self.attachment_download_dir_entry.grid(row=0, column=0, sticky="ew")
        self.attachment_download_dir_entry.insert(
            0, self.initial_state.attachment_download_dir
        )
        self.attachment_download_dir_entry.bind(
            "<Return>", lambda _event: self._save_typed_attachment_directory()
        )
        self.make_small_button(
            download_frame,
            "폴더 선택",
            self.choose_attachment_download_directory,
            PRIMARY,
        ).grid(row=0, column=1, padx=(8, 0))
        self.make_small_button(
            download_frame,
            "적용",
            self._save_typed_attachment_directory,
            SUCCESS,
        ).grid(row=0, column=2, padx=(6, 0))
        self.make_small_button(
            download_frame,
            "기본 경로",
            self.actions.reset_attachment_download_directory,
            GRAY,
        ).grid(row=0, column=3, padx=(6, 0))
        tk.Label(
            basic_frame,
            text="사업명별 하위 폴더가 이 경로 안에 자동으로 생성됩니다.",
            **self.sub_label_style,
        ).grid(row=8, column=0, columnspan=4, sticky="w", pady=(4, 0))

        basic_frame.grid_columnconfigure(0, weight=1)

    def _build_keyword_settings(self, parent):
        keyword_frame = self.make_card(parent, "키워드 검색조건")
        tk.Label(
            keyword_frame,
            text="검색 결과는 최근 알림에만 표시됩니다. 사용자가 저장한 입찰공고만 같은 공고번호로 개찰·낙찰까지 추적합니다.",
            justify="left",
            **self.sub_label_style,
        ).pack(anchor="w", pady=(0, 7))

        rows_container = tk.Frame(keyword_frame, bg=CARD_BG, height=174)
        rows_container.pack(fill="x")
        rows_container.pack_propagate(False)
        self.keyword_canvas = tk.Canvas(
            rows_container, bg=CARD_BG, highlightthickness=0, bd=0
        )
        rows_scroll = tk.Scrollbar(
            rows_container, orient="vertical", command=self.keyword_canvas.yview
        )
        self.keyword_canvas.configure(yscrollcommand=rows_scroll.set)
        self.keyword_canvas.pack(side="left", fill="both", expand=True)
        rows_scroll.pack(side="right", fill="y")
        self.keyword_rows_frame = tk.Frame(self.keyword_canvas, bg=CARD_BG)
        self.keyword_rows_window = self.keyword_canvas.create_window(
            (0, 0), window=self.keyword_rows_frame, anchor="nw"
        )
        self.keyword_rows_frame.bind(
            "<Configure>",
            lambda _event: self.keyword_canvas.configure(
                scrollregion=self.keyword_canvas.bbox("all")
            ),
        )
        self.keyword_canvas.bind(
            "<Configure>",
            lambda event: self.keyword_canvas.itemconfigure(
                self.keyword_rows_window, width=event.width
            ),
        )
        self.keyword_rows = []
        initial_rules = [dict(rule) for rule in self.initial_state.keyword_rules]
        for rule in initial_rules or [{"keyword": "", "operator": "or"}]:
            self.add_keyword_row(rule)

        controls = tk.Frame(keyword_frame, bg=CARD_BG)
        controls.pack(fill="x", pady=(7, 0))
        self.add_keyword_btn = self.make_small_button(
            controls, "+ 검색조건 추가", self.add_keyword_row, PRIMARY
        )
        self.add_keyword_btn.pack(side="left")

    def add_keyword_row(self, rule=None):
        rule = rule or {}
        frame = tk.Frame(
            self.keyword_rows_frame,
            bg="#F8FAFC",
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=8,
            pady=6,
        )
        frame.pack(fill="x", pady=3, padx=(0, 4))
        entry = tk.Entry(frame, **self.entry_style)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        entry.insert(0, str(rule.get("keyword", "")))
        operator = ttk.Combobox(frame, state="readonly", width=7, values=list(OPERATOR_OPTIONS))
        operator.set(next((label for label, value in OPERATOR_OPTIONS.items() if value == rule.get("operator", "or")), "OR"))
        operator.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        enabled_var = tk.BooleanVar(value=bool(rule.get("enabled", False)))
        monitor = self.make_small_button(frame, "", lambda: self.toggle_keyword_monitor(row), PRIMARY)
        monitor.grid(row=0, column=2, padx=(0, 5))
        remove = self.make_small_button(frame, "삭제", lambda: self.remove_keyword_row(row), DANGER)
        remove.grid(row=0, column=3)

        options = tk.Frame(frame, bg="#F8FAFC")
        options.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        tk.Label(options, text="공고 종류", bg="#F8FAFC", fg=SUB_TEXT, font=FONT_BOLD).pack(side="left")
        legacy_category = rule.get("category", "all")
        selected_categories = rule.get("categories") or (
            list(CATEGORY_LABELS) if legacy_category == "all" else [legacy_category]
        )
        category_vars = {}
        category_checks = []
        for key, label in CATEGORY_LABELS.items():
            var = tk.BooleanVar(value=key in selected_categories)
            category_vars[key] = var
            check = tk.Checkbutton(
                options,
                text=label,
                variable=var,
                bg="#F8FAFC",
                activebackground="#F8FAFC",
                selectcolor="#F8FAFC",
                font=FONT,
            )
            check.pack(side="left", padx=(5, 0))
            category_checks.append(check)
        tk.Label(options, text="검색 대상", bg="#F8FAFC", fg=SUB_TEXT, font=FONT_BOLD).pack(
            side="left", padx=(16, 0)
        )
        legacy_target = rule.get("target", "bid")
        selected_targets = rule.get("targets") or (
            ["prespec"] if legacy_target == "prespec" else ["bid_lifecycle"]
        )
        selected_target_set = set(selected_targets)
        target_label = next(
            (
                label
                for label, values in TARGET_OPTIONS.items()
                if set(values) == selected_target_set
            ),
            "입찰공고",
        )
        target = ttk.Combobox(
            options,
            state="readonly",
            width=25,
            values=list(TARGET_OPTIONS),
        )
        target.set(target_label)
        target.pack(side="left", padx=(6, 0))
        frame.grid_columnconfigure(0, weight=1)
        row = {
            "id": str(rule.get("id") or uuid.uuid4().hex),
            "frame": frame,
            "entry": entry,
            "operator": operator,
            "category_vars": category_vars,
            "category_checks": category_checks,
            "target": target,
            "enabled_var": enabled_var,
            "monitor": monitor,
            "remove": remove,
        }
        self.keyword_rows.append(row)
        self._render_keyword_monitor_button(row)
        self.keyword_rows_frame.update_idletasks()
        self.keyword_canvas.yview_moveto(1.0)

    def remove_keyword_row(self, row):
        if row not in self.keyword_rows:
            return
        self.keyword_rows.remove(row)
        row["frame"].destroy()
        self.actions.keyword_rules_changed()
        if not self.keyword_rows:
            self.add_keyword_row()

    def toggle_keyword_monitor(self, row):
        rule = self._keyword_rule_from_row(row)
        if not rule["keyword"]:
            self.show_warning("확인", "감시할 키워드를 입력해 주세요.")
            row["entry"].focus_set()
            return
        if not rule["categories"]:
            self.show_warning("확인", "공고 종류를 하나 이상 선택해 주세요.")
            return
        if not rule["targets"]:
            self.show_warning("확인", "검색 대상을 하나 이상 선택해 주세요.")
            return
        enabled = not row["enabled_var"].get()
        row["enabled_var"].set(enabled)
        self._render_keyword_monitor_button(row, busy=True)

        def finish():
            if row in self.keyword_rows and row["frame"].winfo_exists():
                self._render_keyword_monitor_button(row)

        rule["enabled"] = enabled
        self.actions.set_keyword_rule_monitoring(rule, enabled, finish)

    def _render_keyword_monitor_button(self, row, busy=False):
        enabled = bool(row["enabled_var"].get())
        if busy:
            text = "적용 중"
        else:
            text = "감시 중지" if enabled else "감시 시작"
        row["monitor"].config(
            state="disabled" if busy else "normal",
            text=text,
            bg=STOP_RED if enabled else PRIMARY,
            activebackground=STOP_RED if enabled else PRIMARY,
        )
        edit_state = "disabled" if enabled else "normal"
        row["entry"].config(state=edit_state)
        row["operator"].config(state="disabled" if enabled else "readonly")
        for check in row["category_checks"]:
            check.config(state=edit_state)
        row["target"].config(state="disabled" if enabled else "readonly")
        row["remove"].config(state=edit_state)

    def set_all_keyword_monitoring(self, enabled):
        for row in self.keyword_rows:
            if row["entry"].get().strip():
                row["enabled_var"].set(bool(enabled))
                self._render_keyword_monitor_button(row)

    def set_keyword_monitoring(self, rule_id, enabled):
        for row in self.keyword_rows:
            if row["id"] == rule_id:
                row["enabled_var"].set(bool(enabled))
                self._render_keyword_monitor_button(row)
                return

    @staticmethod
    def _keyword_rule_from_row(row):
        return {
            "id": row["id"],
            "keyword": row["entry"].get().strip(),
            "operator": OPERATOR_OPTIONS[row["operator"].get()],
            "categories": [key for key, var in row["category_vars"].items() if var.get()],
            "targets": list(TARGET_OPTIONS[row["target"].get()]),
            "enabled": bool(row["enabled_var"].get()),
        }

    def _build_action_buttons(self, parent):
        action_frame = tk.Frame(parent, bg=APP_BG)
        action_frame.pack(fill="x", padx=16, pady=(6, 4))

        monitor_group = tk.LabelFrame(
            action_frame,
            text="전체 키워드 감시",
            bg=CARD_BG,
            fg=TEXT,
            font=FONT_BOLD,
            padx=8,
            pady=7,
        )
        monitor_group.pack(fill="x")
        self.start_btn = self.make_button(
            monitor_group, "전체 감시 시작", self.actions.start, PRIMARY, width=14
        )
        self.start_btn.pack(side="left", padx=(0, 6))
        self.stop_btn = self.make_button(
            monitor_group, "전체 감시 중지", self.actions.stop, GRAY, width=14
        )
        self.stop_btn.config(state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 6))
        self.check_now_btn = self.make_button(
            monitor_group, "전체 즉시 확인", self.actions.check_now, GRAY, width=14
        )
        self.check_now_btn.pack(side="left")

        tool_group = tk.LabelFrame(
            action_frame,
            text="알림·도구",
            bg=CARD_BG,
            fg=TEXT,
            font=FONT_BOLD,
            padx=8,
            pady=7,
        )
        tool_group.pack(fill="x", pady=(6, 0))
        test_button = self.make_button(
            tool_group, "알림 테스트", self.actions.test_alert, SUCCESS, width=12
        )
        test_button.pack(side="left", padx=(0, 6))
        self.log_tab_button = self.make_button(
            tool_group, "로그 탭 열기", self.toggle_log_tab, GRAY, width=13
        )
        self.log_tab_button.pack(side="left")
        self.reset_btn = self.make_button(
            monitor_group, "확인 기록 초기화", self.actions.reset_records, DANGER, width=16
        )
        self.reset_btn.pack(side="left", padx=(6, 0))

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
            command=self.actions.acknowledge_alerts,
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
        self.check_now_btn.config(state="normal", text="전체 즉시 확인")

    def start_manual_check(self):
        self.check_now_btn.config(state="disabled", text="전체 조회 중")

    def get_monitor_form(self):
        keyword_rules = []
        for row in self.keyword_rows:
            rule = self._keyword_rule_from_row(row)
            if rule["keyword"]:
                keyword_rules.append(rule)
        return {
            "api_key": self.api_key_entry.get(),
            "keyword_rules": keyword_rules,
            "interval": self.interval_entry.get().strip(),
            "result_interval": self.result_interval_entry.get().strip(),
            "windows_notifications_enabled": bool(self.windows_notification_var.get()),
            "notify_all_opening_results": bool(self.notify_all_results_var.get()),
            "keyword_email_enabled": bool(self.keyword_email_var.get()),
            "attachment_download_dir": self.attachment_download_dir_entry.get().strip(),
        }

    def choose_attachment_download_directory(self):
        selected = filedialog.askdirectory(
            parent=self.root,
            title="첨부파일 저장 폴더 선택",
            initialdir=self.attachment_download_dir_entry.get().strip() or None,
        )
        if selected:
            self.set_attachment_download_directory(selected)
            self.actions.save_attachment_download_directory(selected)

    def _save_typed_attachment_directory(self):
        self.actions.save_attachment_download_directory(
            self.attachment_download_dir_entry.get().strip()
        )

    def set_attachment_download_directory(self, directory):
        self.attachment_download_dir_entry.delete(0, "end")
        self.attachment_download_dir_entry.insert(0, str(directory or ""))

    def set_next_check_pending(self):
        self.next_check_var.set("다음 확인 예정: 조회 완료 후 표시")

    def clear_next_check(self):
        self.next_check_var.set("다음 확인 예정: -")
