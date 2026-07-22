import tkinter as tk
from tkinter import messagebox, ttk

from .saved_bid_detail_view import SavedBidDetailWindow
from .styles import CARD_BG, DANGER, FONT, GRAY, PRIMARY, SUB_TEXT, SUCCESS, TEXT, WARNING


CATEGORY_FILTERS = {
    "전체 업무": "",
    "용역": "service",
    "물품": "goods",
    "공사": "works",
    "외자·기타": "etc",
}


class SavedBidsViewMixin:
    def _build_saved_bids_page(self, parent):
        lookup_frame = self.make_card(parent, "입찰공고·사전규격 직접 조회")
        tk.Label(lookup_frame, text="조회 종류", **self.label_style).grid(
            row=0, column=0, sticky="w"
        )
        tk.Label(lookup_frame, text="공고번호 또는 나라장터 URL", **self.label_style).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        tk.Label(
            lookup_frame,
            text="예: R25BK01234567-000 / R26BD00251411 / 상세·규격서 URL",
            **self.sub_label_style,
        ).grid(row=0, column=2, columnspan=2, sticky="w", padx=(8, 0))
        self.lookup_type_combo = ttk.Combobox(
            lookup_frame,
            values=("자동 판별", "입찰공고", "사전규격"),
            state="readonly",
            width=11,
        )
        self.lookup_type_combo.set("자동 판별")
        self.lookup_type_combo.grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.lookup_bid_no_entry = tk.Entry(lookup_frame, width=32, **self.entry_style)
        self.lookup_bid_no_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(5, 0))
        self.lookup_bid_no_entry.bind(
            "<Return>", lambda _event: self.actions.lookup_notice_by_no()
        )
        self.lookup_bid_btn = self.make_small_button(
            lookup_frame, "조회", self.actions.lookup_notice_by_no, PRIMARY
        )
        self.lookup_bid_btn.grid(row=1, column=2, padx=(8, 0), pady=(5, 0))
        save_lookup_bid_button = self.make_small_button(
            lookup_frame, "조회 항목 저장", self.actions.save_lookup_notice, SUCCESS
        )
        save_lookup_bid_button.grid(row=1, column=3, padx=(8, 0), pady=(5, 0))
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
        lookup_frame.grid_columnconfigure(1, weight=1)
        self.lookup_notice = None

        list_frame = self.make_card(parent, "저장된 공고")
        toolbar = tk.Frame(list_frame, bg=CARD_BG)
        toolbar.pack(fill="x", pady=(0, 8))
        self.saved_search_entry = tk.Entry(toolbar, width=28, **self.entry_style)
        self.saved_search_entry.pack(side="left")
        self.saved_search_entry.bind(
            "<Return>", lambda _event: self.actions.refresh_saved_bids()
        )
        self.make_small_button(toolbar, "검색", self.actions.refresh_saved_bids, GRAY).pack(
            side="left", padx=(6, 0)
        )
        self.make_small_button(toolbar, "새로고침", self.actions.refresh_saved_bids, GRAY).pack(
            side="left", padx=(6, 0)
        )
        self.make_small_button(
            toolbar, "상세", self.actions.show_saved_bid_detail, GRAY
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(
            toolbar, "변경이력", self.actions.show_notice_version_history, GRAY
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(toolbar, "링크 열기", self.actions.open_saved_bid_link, GRAY).pack(
            side="right", padx=(6, 0)
        )
        self.make_small_button(
            toolbar, "이메일 수신자", self.actions.open_saved_bid_recipients, GRAY
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(
            toolbar, "낙찰정보 즉시 조회", self.actions.check_saved_results_now, PRIMARY
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(
            toolbar, "추적 시작/중지", self.actions.toggle_saved_bid_monitoring, WARNING
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(
            toolbar, "완전 삭제", self.actions.permanently_delete_saved_bid, DANGER
        ).pack(side="right", padx=(6, 0))

        filter_frame = tk.Frame(list_frame, bg=CARD_BG)
        filter_frame.pack(fill="x", pady=(0, 8))
        tk.Label(filter_frame, text="필터", **self.label_style).pack(side="left", padx=(0, 8))
        self.saved_category_filter = ttk.Combobox(
            filter_frame,
            values=tuple(CATEGORY_FILTERS),
            state="readonly",
            width=11,
        )
        self.saved_category_filter.set("전체 업무")
        self.saved_category_filter.pack(side="left", padx=(0, 6))
        self.saved_stage_filter = ttk.Combobox(
            filter_frame,
            values=(
                "전체 단계",
                "사전규격",
                "입찰공고",
                "개찰결과",
                "낙찰결과",
                "유찰·취소",
                "계약완료",
            ),
            state="readonly",
            width=11,
        )
        self.saved_stage_filter.set("전체 단계")
        self.saved_stage_filter.pack(side="left", padx=(0, 6))
        self.saved_tracking_filter = ttk.Combobox(
            filter_frame,
            values=("전체 추적상태", "추적 중", "일시정지"),
            state="readonly",
            width=12,
        )
        self.saved_tracking_filter.set("전체 추적상태")
        self.saved_tracking_filter.pack(side="left", padx=(0, 6))
        for combo in (
            self.saved_category_filter,
            self.saved_stage_filter,
            self.saved_tracking_filter,
        ):
            combo.bind("<<ComboboxSelected>>", lambda _event: self.actions.refresh_saved_bids())
        self.make_small_button(
            filter_frame, "필터 초기화", self.reset_saved_filters, GRAY
        ).pack(side="left")

        options_frame = tk.Frame(list_frame, bg=CARD_BG)
        options_frame.pack(fill="x", pady=(0, 8))
        tk.Label(options_frame, text="낙찰정보 감시 주기", **self.label_style).pack(side="left")
        self.result_interval_entry = tk.Entry(options_frame, width=8, **self.entry_style)
        self.result_interval_entry.pack(side="left", padx=(8, 4))
        self.result_interval_entry.insert(0, self.initial_state.result_interval)
        tk.Label(
            options_frame,
            text="분마다 저장 공고의 낙찰정보를 확인",
            **self.sub_label_style,
        ).pack(side="left", padx=(0, 10))
        self.make_small_button(
            options_frame, "주기 적용", self.actions.apply_saved_result_interval, GRAY
        ).pack(side="left", padx=(0, 12))

        alert_option_frame = tk.Frame(list_frame, bg=CARD_BG)
        alert_option_frame.pack(fill="x", pady=(0, 8))
        self.notify_all_results_var = tk.BooleanVar(
            value=self.initial_state.notify_all_opening_results
        )
        notify_all_results_check = tk.Checkbutton(
            alert_option_frame,
            text="새 낙찰정보 발견 시 윈도우/미확인 알림",
            variable=self.notify_all_results_var,
            command=self.actions.save_result_notification_setting,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=PRIMARY,
            selectcolor=CARD_BG,
            font=FONT,
            cursor="hand2",
        )
        notify_all_results_check.pack(side="left")
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
        columns = (
            "stage",
            "no",
            "title",
            "category",
            "demand",
            "bid_end",
            "opening",
            "last_check",
            "monitoring",
            "result",
        )
        self.saved_sort_column = "last_check"
        self.saved_sort_descending = True
        self.saved_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        headings = {
            "stage": "단계",
            "no": "공고번호",
            "title": "공고명",
            "category": "업무",
            "demand": "수요기관",
            "bid_end": "입찰마감",
            "opening": "개찰일시",
            "last_check": "최근 조회시도",
            "monitoring": "조회대상",
            "result": "결과",
        }
        widths = {
            "stage": 82,
            "no": 145,
            "title": 230,
            "category": 62,
            "demand": 130,
            "bid_end": 105,
            "opening": 105,
            "last_check": 115,
            "monitoring": 55,
            "result": 125,
        }
        for column in columns:
            self.saved_tree.heading(
                column,
                text=headings[column],
                command=lambda selected=column: self.change_saved_sort(selected),
            )
            self.saved_tree.column(column, width=widths[column], anchor="w", stretch=column == "title")
        self.saved_headings = headings
        self._refresh_saved_heading_labels()
        for tag, background, foreground in (
            ("사전규격", "#E8F2FF", "#1D4ED8"),
            ("입찰공고", "#FFF4E5", "#A65300"),
            ("개찰결과", "#F1EAFE", "#6D28D9"),
            ("낙찰결과", "#E8F7EF", "#047857"),
            ("유찰·취소", "#FDECEC", "#B91C1C"),
            ("계약완료", "#EEF1F4", "#4B5563"),
        ):
            self.saved_tree.tag_configure(tag, background=background, foreground=foreground)
        self.saved_tree.grid(row=0, column=0, sticky="nsew")
        self.saved_tree.bind("<Double-1>", lambda _event: self.actions.show_saved_bid_detail())
        saved_scroll = tk.Scrollbar(table_frame, orient="vertical", command=self.saved_tree.yview)
        saved_scroll.grid(row=0, column=1, sticky="ns")
        saved_horizontal_scroll = tk.Scrollbar(
            table_frame, orient="horizontal", command=self.saved_tree.xview
        )
        saved_horizontal_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self.saved_tree.configure(
            yscrollcommand=saved_scroll.set,
            xscrollcommand=saved_horizontal_scroll.set,
        )
    def finish_lookup_notice(self, notice, error, duplicate=None):
        self.lookup_bid_btn.config(state="normal", text="조회")
        if error:
            self.lookup_result_var.set(f"조회 실패: {error}")
            messagebox.showerror("조회 실패", f"공고 조회에 실패했습니다.\n\n{error}")
            return
        if not notice:
            self.lookup_result_var.set(
                "조회 결과가 없습니다. 조회 종류와 공고번호·사전규격등록번호를 확인해 주세요."
            )
            return
        self.lookup_notice = notice
        duplicate_text = (
            "\n저장 상태: 동일 번호가 이미 저장되어 있습니다."
            if duplicate
            else "\n저장 상태: 새로 저장할 수 있습니다."
        )
        if hasattr(notice, "pre_spec_no"):
            detail = (
                f"사전규격등록번호: {notice.pre_spec_no} / "
                f"수요기관: {notice.demand_agency or '-'}"
            )
        else:
            detail = (
                f"공고번호: {notice.bid_no} / 차수: {notice.bid_ord or '000'} / "
                f"수요기관: {notice.demand_agency or '-'}"
            )
        self.lookup_result_var.set(
            f"[{notice.category_label}] {notice.title}\n{detail}{duplicate_text}"
        )

    def select_saved_bid(self, saved_id):
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

    def get_lookup_reference(self):
        return self.lookup_bid_no_entry.get().strip()

    def get_lookup_type(self):
        return {
            "입찰공고": "bid",
            "사전규격": "prespec",
        }.get(self.lookup_type_combo.get(), "auto")

    def set_lookup_reference(self, value):
        self.lookup_bid_no_entry.delete(0, "end")
        self.lookup_bid_no_entry.insert(0, value)

    def get_lookup_notice(self):
        return self.lookup_notice

    def begin_lookup_notice(self):
        self.lookup_bid_btn.config(state="disabled", text="조회 중")
        self.lookup_result_var.set("공고 정보를 조회하는 중입니다.")
        self.lookup_notice = None

    def get_saved_search_text(self):
        return self.saved_search_entry.get().strip()

    def get_saved_filters(self):
        stage = self.saved_stage_filter.get()
        tracking_labels = {
            "추적 중": "active",
            "일시정지": "paused",
        }
        return {
            "category": CATEGORY_FILTERS.get(self.saved_category_filter.get(), ""),
            "stage": "" if stage == "전체 단계" else stage,
            "tracking": tracking_labels.get(self.saved_tracking_filter.get(), ""),
        }

    def reset_saved_filters(self):
        self.saved_category_filter.set("전체 업무")
        self.saved_stage_filter.set("전체 단계")
        self.saved_tracking_filter.set("전체 추적상태")
        self.actions.refresh_saved_bids()

    def get_saved_sort(self):
        return self.saved_sort_column, self.saved_sort_descending

    def change_saved_sort(self, column):
        if self.saved_sort_column == column:
            self.saved_sort_descending = not self.saved_sort_descending
        else:
            self.saved_sort_column = column
            self.saved_sort_descending = False
        self._refresh_saved_heading_labels()
        self.actions.refresh_saved_bids()

    def _refresh_saved_heading_labels(self):
        for column, label in self.saved_headings.items():
            suffix = ""
            if column == self.saved_sort_column:
                suffix = " ▼" if self.saved_sort_descending else " ▲"
            self.saved_tree.heading(column, text=f"{label}{suffix}")

    def render_saved_bids(self, rows):
        for item in self.saved_tree.get_children():
            self.saved_tree.delete(item)
        self.saved_bid_rows.clear()
        for row in rows:
            item_id = f"saved_{row.id}"
            stage = row.stage_label()
            reference = (
                row.pre_spec_no
                if row.pre_spec_no and row.status == "pre_spec"
                else f"{row.bid_no}-{row.bid_ord or '000'}"
            )
            values = (
                f"[{stage}]",
                reference,
                self.truncate_text(row.title, 36),
                row.category_label if hasattr(row, "category_label") else row.category,
                self.truncate_text(row.demand_agency, 18),
                self._short_datetime(row.bid_end_datetime),
                self._short_datetime(row.opening_datetime),
                self._short_datetime(row.last_result_check_at),
                "ON" if row.monitoring_enabled else "OFF",
                row.progress_status(),
            )
            self.saved_tree.insert("", "end", iid=item_id, values=values, tags=(stage,))
            self.saved_bid_rows[item_id] = row

    def set_saved_monitor_status(self, text):
        self.saved_monitor_status_var.set(text)

    def get_result_interval_text(self):
        return self.result_interval_entry.get().strip()

    def set_saved_result_status(self, text):
        self.saved_result_status_var.set(text)

    def show_saved_bid_detail(self, detail):
        return SavedBidDetailWindow(self.root, detail, self.actions.open_link)

    def show_notice_version_history(self, row, versions, comparison):
        window = tk.Toplevel(self.root)
        window.title(f"변경공고 이력 - {row.bid_no}")
        window.geometry("780x580")
        window.minsize(680, 460)
        window.configure(bg=CARD_BG)
        header = tk.Frame(window, bg=CARD_BG, padx=14, pady=12)
        header.pack(fill="x")
        tk.Label(
            header,
            text=row.title or row.bid_no,
            bg=CARD_BG,
            fg=TEXT,
            font=("맑은 고딕", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        current = comparison.get("current")
        previous = comparison.get("previous")
        summary = (
            f"보관 차수 {len(versions)}개 / "
            f"현재 {current.get('bid_pbanc_ord') or '000' if current else '-'}"
        )
        if previous and current:
            summary += (
                f" / 비교 {previous.get('bid_pbanc_ord') or '000'}"
                f" → {current.get('bid_pbanc_ord') or '000'}"
            )
        tk.Label(
            header,
            text=summary,
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=("맑은 고딕", 9),
            anchor="w",
        ).pack(fill="x", pady=(3, 0))

        text_frame = tk.Frame(window, bg=CARD_BG, padx=14)
        text_frame.pack(fill="both", expand=True, pady=(0, 12))
        scroll = tk.Scrollbar(text_frame)
        scroll.pack(side="right", fill="y")
        box = tk.Text(
            text_frame,
            bg="#F8FAFC",
            fg=TEXT,
            font=FONT,
            wrap="word",
            relief="solid",
            bd=1,
            yscrollcommand=scroll.set,
            padx=12,
            pady=10,
        )
        box.pack(side="left", fill="both", expand=True)
        scroll.config(command=box.yview)

        box.insert("end", "[차수별 원본]\n")
        for version in reversed(versions):
            marker = "현재" if version.get("is_current") else "이전"
            box.insert(
                "end",
                f"• {version.get('bid_pbanc_ord') or '000'} [{marker}] "
                f"감지 {self._short_datetime(version.get('detected_at'))}\n",
            )
        box.insert("end", "\n[이전값 → 현재값]\n")
        changes = comparison.get("changes") or []
        if not previous:
            box.insert("end", "비교할 이전 차수가 없습니다.\n")
        elif not changes:
            box.insert("end", "선택한 비교 항목에서 변경사항이 없습니다.\n")
        else:
            for change in changes:
                box.insert(
                    "end",
                    f"• {change['label']}\n"
                    f"  이전: {change['before']}\n"
                    f"  현재: {change['after']}\n\n",
                )
        box.config(state="disabled")

    def _short_datetime(self, value):
        value = str(value or "")
        if len(value) >= 16 and value[4:5] == "-":
            return value[:16].replace("T", " ")
        if len(value) >= 12 and value[:12].isdigit():
            return f"{value[:4]}-{value[4:6]}-{value[6:8]} {value[8:10]}:{value[10:12]}"
        return value[:16] if value else "-"

    def render_saved_result_auto_check(self, summary):
        checked = summary["checked"]
        failed = summary.get("failed", 0)
        no_result = summary.get("no_result", 0)
        new_results = summary["new_results"]
        checked_at = summary["checked_at"].strftime("%Y-%m-%d %H:%M:%S")
        self.saved_result_status_var.set(
            f"최근 자동 조회: {checked_at} / 대상 {checked}건 / "
            f"결과 없음 {no_result}건 / 실패 {failed}건 / 새 결과 {new_results}건"
        )

    def render_saved_result_check(self, summary, error):
        if error:
            self.saved_result_status_var.set("낙찰정보 조회 실패")
            messagebox.showerror("조회 실패", f"낙찰정보 조회에 실패했습니다.\n\n{error}")
            return
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
