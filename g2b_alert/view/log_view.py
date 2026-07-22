import re
import tkinter as tk
from datetime import datetime

from .styles import CARD_BG, FONT, FONT_BOLD, GRAY, LOG_BG, LOG_TEXT, PRIMARY_DARK


class LogViewMixin:
    def _build_embedded_log(self, pane, attribute_name, title):
        frame = tk.Frame(pane, bg=CARD_BG, padx=10, pady=7)
        toolbar = tk.Frame(frame, bg=CARD_BG)
        toolbar.pack(fill="x", pady=(0, 5))
        tk.Label(toolbar, text=title, bg=CARD_BG, fg=PRIMARY_DARK, font=FONT_BOLD).pack(
            side="left"
        )
        if not hasattr(self, "log_auto_scroll_var"):
            self.log_auto_scroll_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            toolbar,
            text="자동 스크롤",
            variable=self.log_auto_scroll_var,
            bg=CARD_BG,
            activebackground=CARD_BG,
            font=("맑은 고딕", 8),
        ).pack(side="right", padx=(6, 0))
        if hasattr(self, "close_log_tab"):
            self.make_small_button(toolbar, "탭 닫기", self.close_log_tab, GRAY).pack(
                side="right", padx=(6, 0)
            )
        self.make_small_button(
            toolbar, "파일 열기", self.actions.open_log_file, GRAY
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(toolbar, "지우기", self.clear_log_view, GRAY).pack(
            side="right", padx=(6, 0)
        )
        self.make_small_button(
            toolbar, "이메일", lambda: self.set_log_filter("email"), GRAY
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(
            toolbar, "오류", lambda: self.set_log_filter("error"), GRAY
        ).pack(side="right", padx=(6, 0))
        self.make_small_button(
            toolbar, "전체", lambda: self.set_log_filter("all"), GRAY
        ).pack(side="right", padx=(6, 0))
        log_box = tk.Text(
            frame,
            height=7,
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
        log_box.pack(fill="both", expand=True)
        log_box.config(state="disabled")
        setattr(self, attribute_name, log_box)
        if isinstance(pane, tk.PanedWindow):
            pane.add(frame, minsize=85, stretch="never")
        else:
            frame.pack(fill="both", expand=True, padx=16, pady=12)
        if not hasattr(self, "log_link_count"):
            self.log_link_count = 0

    def log(self, message):
        self.post(lambda: self._append_log(message))

    def _append_log(self, message):
        line = "\n" if message == "" else f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n"
        category = self._classify_log(message)
        self.log_records.append({"line": line, "category": category})
        if len(self.log_records) > 5000:
            self.log_records = self.log_records[-5000:]
        if not self._log_matches_filter(category):
            return
        for log_box in self._get_log_boxes():
            self._insert_log_line(
                log_box,
                line,
                scroll=bool(self.log_auto_scroll_var.get()),
            )

    @staticmethod
    def _classify_log(message):
        text = str(message or "").casefold()
        if any(token in text for token in ("이메일", "메일", "smtp")):
            return "email"
        if any(token in text for token in ("실패", "오류", "error", "exception")):
            return "error"
        if any(token in text for token in ("api", "조회")):
            return "api"
        if "알림" in text:
            return "notification"
        return "info"

    def _log_matches_filter(self, category):
        return self.log_filter == "all" or self.log_filter == category

    def set_log_filter(self, filter_name):
        self.log_filter = filter_name
        self._render_log_records()

    def clear_log_view(self):
        self.log_records.clear()
        self._clear_log_boxes()

    def _clear_log_boxes(self):
        for log_box in self._get_log_boxes():
            log_box.config(state="normal")
            log_box.delete("1.0", "end")
            log_box.config(state="disabled")

    def _render_log_records(self):
        self._clear_log_boxes()
        records = [
            record
            for record in self.log_records
            if self._log_matches_filter(record["category"])
        ]
        for log_box in self._get_log_boxes():
            for record in records:
                self._insert_log_line(log_box, record["line"], scroll=False)
            if records and self.log_auto_scroll_var.get():
                log_box.see("end")

    def _get_log_boxes(self):
        log_box = getattr(self, "search_log_box", None)
        return [log_box] if self._widget_exists(log_box) else []

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
            log_box.tag_bind(
                tag_name, "<Button-1>", lambda _event, link=url: self.actions.open_link(link)
            )
            log_box.tag_bind(
                tag_name, "<Enter>", lambda _event, box=log_box: box.config(cursor="hand2")
            )
            log_box.tag_bind(
                tag_name, "<Leave>", lambda _event, box=log_box: box.config(cursor="")
            )
            last_end = end
        if last_end < len(line):
            log_box.insert("end", line[last_end:])
        if scroll:
            log_box.see("end")
        log_box.config(state="disabled")
