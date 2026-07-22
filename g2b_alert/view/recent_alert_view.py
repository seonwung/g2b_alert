import tkinter as tk
from datetime import datetime
from tkinter import ttk

from .styles import CARD_BG, GRAY, SUB_TEXT, SUCCESS, TEXT


class RecentAlertViewMixin:
    """Render and expose selection from the recent-alert table."""

    def _build_recent_alerts(self, parent):
        frame = tk.LabelFrame(
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
        frame.pack(fill="both", expand=True, padx=16, pady=(4, 8))
        toolbar = tk.Frame(frame, bg=CARD_BG)
        toolbar.pack(fill="x", pady=(0, 8))
        tk.Label(
            toolbar,
            text="매칭 키워드는 해당 칸을 클릭하면 펼쳐집니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=("맑은 고딕", 9),
        ).pack(side="left")
        self.make_small_button(
            toolbar, "선택한 공고 링크 열기", self.actions.open_selected_alert_link, GRAY
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(
            toolbar, "선택한 공고 저장", self.actions.save_selected_alert_bid, SUCCESS
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(toolbar, "목록 지우기", self.actions.clear_recent_alerts, GRAY).pack(side="right")

        table = tk.Frame(frame, bg=CARD_BG)
        table.pack(fill="both", expand=True)
        columns = ("time", "category", "title", "keywords", "link")
        self.alert_tree = ttk.Treeview(table, columns=columns, show="headings", height=12)
        headings = {"time": "시간", "category": "종류", "title": "공고명", "keywords": "키워드", "link": "링크"}
        widths = {"time": 70, "category": 70, "title": 330, "keywords": 140, "link": 70}
        for column in columns:
            self.alert_tree.heading(column, text=headings[column])
            self.alert_tree.column(column, width=widths[column], anchor="w", stretch=column == "title")
        self.alert_tree.pack(side="left", fill="both", expand=True)
        self.alert_tree.bind("<ButtonRelease-1>", self._on_alert_click)
        self.alert_tree.bind("<Double-1>", self._on_alert_double_click)
        self.alert_tree.bind("<Return>", lambda _event: self.actions.open_selected_alert_link())
        scroll = tk.Scrollbar(table, orient="vertical", command=self.alert_tree.yview)
        scroll.pack(side="right", fill="y")
        self.alert_tree.configure(yscrollcommand=scroll.set)

    def add_recent_alert(self, item_id, bid, keywords):
        summary = self._format_keyword_summary(keywords)
        values = (
            datetime.now().strftime("%H:%M"),
            bid.category_label,
            self.truncate_text(bid.title, 42),
            summary,
            "열기" if bid.link else "-",
        )
        self.alert_tree.insert("", 0, iid=item_id, values=values)

    def remove_recent_alert_rows(self, item_ids):
        for item_id in item_ids:
            if item_id in self.alert_tree.get_children():
                self.alert_tree.delete(item_id)

    def clear_recent_alert_rows(self):
        self.remove_recent_alert_rows(self.alert_tree.get_children())

    def get_selected_alert_id(self):
        selected = self.alert_tree.selection()
        return selected[0] if selected else None

    def select_first_alert(self):
        items = self.alert_tree.get_children()
        if not items:
            return None
        self.alert_tree.selection_set(items[0])
        self.alert_tree.focus(items[0])
        self.alert_tree.see(items[0])
        return items[0]

    def set_unread_alert_count(self, count):
        if count:
            self.unread_alert_btn.config(text=f"미확인 {count}")
            if not self.unread_alert_btn.winfo_ismapped():
                self.unread_alert_btn.grid(row=0, column=2, rowspan=3, sticky="e", padx=12)
        else:
            self.unread_alert_btn.grid_forget()

    def _on_alert_click(self, event):
        row_id = self.alert_tree.identify_row(event.y)
        if row_id:
            self.alert_tree.selection_set(row_id)
            self.alert_tree.focus(row_id)
        if row_id and self.alert_tree.identify_column(event.x) == "#4":
            self.actions.show_alert_keywords(row_id)

    def _on_alert_double_click(self, event):
        if self.alert_tree.identify_column(event.x) == "#4":
            row_id = self.alert_tree.identify_row(event.y) or self.alert_tree.focus()
            if row_id:
                self.actions.show_alert_keywords(row_id)
            return
        self.actions.open_selected_alert_link()

    @staticmethod
    def _format_keyword_summary(keywords):
        if not keywords:
            return "-"
        first = RecentAlertViewMixin.truncate_text(str(keywords[0]), 12)
        return first if len(keywords) == 1 else f"{first} 외 {len(keywords) - 1}개"

    @staticmethod
    def truncate_text(text, max_length):
        text = str(text or "")
        return text if len(text) <= max_length else text[: max_length - 3] + "..."
