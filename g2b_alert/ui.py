import os
import re
import webbrowser
import tkinter as tk
from tkinter import messagebox

from .app_logger import setup_logger
from .config_manager import AppConfig, SEEN_FILE, STATE_FILE, load_config, save_config
from .g2b_client import CATEGORY_LABELS, ENDPOINTS
from .keyword_matcher import parse_keywords
from .notifier import WindowsNotifier
from .scheduler import BidScheduler


APP_BG = "#F3F6FB"
CARD_BG = "#FFFFFF"
PRIMARY = "#2563EB"
PRIMARY_DARK = "#1D4ED8"
SUCCESS = "#10B981"
DANGER = "#EF4444"
WARNING = "#F59E0B"
GRAY = "#6B7280"
DISABLED_BLUE = "#93C5FD"
STOP_RED = "#DC2626"
TEXT = "#111827"
SUB_TEXT = "#6B7280"
BORDER = "#D8E0EA"
INPUT_BG = "#F9FAFB"
LOG_BG = "#0F172A"
LOG_TEXT = "#D1D5DB"

RECOMMENDED_INTERVAL_MINUTES = 5
MIN_INTERVAL_MINUTES = 1
FONT = ("\ub9d1\uc740 \uace0\ub515", 10)
FONT_BOLD = ("\ub9d1\uc740 \uace0\ub515", 10, "bold")


class G2BAlertApp:
    def __init__(self, root):
        self.root = root
        self.root.title("\ub098\ub77c\uc7a5\ud130 \ud0a4\uc6cc\ub4dc \uc54c\ub9bc")
        self.root.geometry("780x780")
        self.root.minsize(720, 720)
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

        self.label_style = {"bg": CARD_BG, "fg": TEXT, "font": FONT_BOLD}
        self.sub_label_style = {"bg": CARD_BG, "fg": SUB_TEXT, "font": ("\ub9d1\uc740 \uace0\ub515", 9)}
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

        self._build_ui()
        self.update_running_ui(False)
        self.log("\ud504\ub85c\uadf8\ub7a8 \uc900\ube44 \uc644\ub8cc")
        self.logger.info("Program started.")

    def _build_ui(self):
        header = tk.Frame(self.root, bg=PRIMARY, height=86)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="\ub098\ub77c\uc7a5\ud130 \ud0a4\uc6cc\ub4dc \uc54c\ub9bc",
            bg=PRIMARY,
            fg="white",
            font=("\ub9d1\uc740 \uace0\ub515", 19, "bold"),
        ).pack(anchor="w", padx=22, pady=(15, 2))

        tk.Label(
            header,
            text="\uc785\ucc30\uacf5\uace0\ub97c \uc8fc\uae30\uc801\uc73c\ub85c \ud655\uc778\ud558\uace0 \ud0a4\uc6cc\ub4dc\uac00 \ub9e4\uce6d\ub418\uba74 \uc708\ub3c4\uc6b0 \uc54c\ub9bc\uc744 \ud45c\uc2dc\ud569\ub2c8\ub2e4.",
            bg=PRIMARY,
            fg="#DBEAFE",
            font=("\ub9d1\uc740 \uace0\ub515", 9),
        ).pack(anchor="w", padx=24)

        main = tk.Frame(self.root, bg=APP_BG)
        main.pack(fill="both", expand=True)
        self._build_basic_settings(main)
        self._build_keyword_settings(main)
        self._build_action_buttons(main)
        self._build_status(main)
        self._build_log(main)

    def _build_basic_settings(self, parent):
        basic_frame = self.make_card(parent, "\uae30\ubcf8 \uc124\uc815")
        tk.Label(basic_frame, text="\uacf5\uacf5\ub370\uc774\ud130\ud3ec\ud138 API \ud0a4", **self.label_style).grid(
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
            text="\ubcf4\uae30",
            command=self.toggle_api_key,
            bg="#E5EDFF",
            fg=PRIMARY_DARK,
            activebackground="#D7E4FF",
            activeforeground=PRIMARY_DARK,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("\ub9d1\uc740 \uace0\ub515", 9, "bold"),
            padx=10,
            pady=4,
        )
        self.api_key_toggle_btn.grid(row=0, column=1, padx=(8, 0))

        tk.Label(basic_frame, text="\ud655\uc778 \uc8fc\uae30", **self.label_style).grid(row=2, column=0, sticky="w", pady=(2, 5))
        interval_frame = tk.Frame(basic_frame, bg=CARD_BG)
        interval_frame.grid(row=3, column=0, columnspan=4, sticky="w")
        self.interval_entry = tk.Entry(interval_frame, width=10, **self.entry_style)
        self.interval_entry.pack(side="left")
        self.interval_entry.insert(0, str(self.config.interval))
        tk.Label(interval_frame, text="\ubd84\ub9c8\ub2e4 \ud655\uc778\ud569\ub2c8\ub2e4. 5\ubd84 \uad8c\uc7a5 / \ucd5c\uc18c 1\ubd84", **self.sub_label_style).pack(side="left", padx=(8, 0))

        tk.Label(basic_frame, text="\uc870\ud68c\ud560 \uacf5\uace0 \uc885\ub958", **self.label_style).grid(row=4, column=0, sticky="w", pady=(15, 5))
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

        basic_frame.grid_columnconfigure(0, weight=1)

    def _build_keyword_settings(self, parent):
        keyword_frame = self.make_card(parent, "\ud0a4\uc6cc\ub4dc \uc124\uc815")
        tk.Label(
            keyword_frame,
            text="\uc27c\ud45c \ub610\ub294 \uc904\ubc14\uafc8\uc73c\ub85c \uad6c\ubd84\ud574\uc11c \uc785\ub825\ud558\uc138\uc694.\n\ud0a4\uc6cc\ub4dc\ub098 \uc870\ud68c \uc885\ub958\ub97c \ubc14\uafbc \uacbd\uc6b0, \ud544\uc694\ud558\uba74 [\ud655\uc778 \uae30\ub85d \ucd08\uae30\ud654] \ud6c4 \ub2e4\uc2dc \uc2dc\uc791\ud558\uc138\uc694.",
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

        self.start_btn = self.make_button(action_frame, "\uc2dc\uc791", self.start, PRIMARY, width=12)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = self.make_button(action_frame, "\uc911\uc9c0", self.stop, GRAY, width=12)
        self.stop_btn.config(state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.test_btn = self.make_button(action_frame, "\uc54c\ub9bc \ud14c\uc2a4\ud2b8", self.test_alert, SUCCESS, width=13)
        self.test_btn.pack(side="left", padx=(0, 8))
        self.reset_btn = self.make_button(action_frame, "\ud655\uc778 \uae30\ub85d \ucd08\uae30\ud654", self.reset_records, DANGER, width=16)
        self.reset_btn.pack(side="left", padx=(0, 8))

    def _build_status(self, parent):
        status_frame = tk.Frame(parent, bg=APP_BG)
        status_frame.pack(fill="x", padx=16, pady=(4, 8))
        self.status_var = tk.StringVar(value="\uc0c1\ud0dc: \ub300\uae30 \uc911")
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg="#E0ECFF",
            fg=PRIMARY_DARK,
            anchor="w",
            padx=12,
            pady=8,
            font=FONT_BOLD,
        )
        self.status_label.pack(fill="x")

    def _build_log(self, parent):
        log_frame = tk.LabelFrame(
            parent,
            text="\ub85c\uadf8",
            bg=CARD_BG,
            fg=PRIMARY_DARK,
            padx=10,
            pady=10,
            font=("\ub9d1\uc740 \uace0\ub515", 11, "bold"),
            relief="solid",
            bd=1,
        )
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        log_toolbar = tk.Frame(log_frame, bg=CARD_BG)
        log_toolbar.pack(fill="x", pady=(0, 8))
        self.detach_log_btn = self.make_small_button(log_toolbar, "\ubd84\ub9ac", self.open_detached_log, PRIMARY)
        self.detach_log_btn.pack(side="left", padx=(0, 6))
        self.fullscreen_log_btn = self.make_small_button(log_toolbar, "\uc804\uccb4\ud654\uba74", self.open_fullscreen_log, SUCCESS)
        self.fullscreen_log_btn.pack(side="left", padx=(0, 6))
        self.clear_log_btn = self.make_small_button(log_toolbar, "\ud654\uba74 \ub85c\uadf8 \uc9c0\uc6b0\uae30", self.clear_log, WARNING)
        self.clear_log_btn.pack(side="right")

        log_inner = tk.Frame(log_frame, bg=CARD_BG)
        log_inner.pack(fill="both", expand=True)
        log_scroll = tk.Scrollbar(log_inner)
        log_scroll.pack(side="right", fill="y")
        self.log_box = tk.Text(
            log_inner,
            height=12,
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
        self.log_box.pack(side="left", fill="both", expand=True)
        self.log_link_count = 0
        self.log_box.config(state="disabled")
        log_scroll.config(command=self.log_box.yview)

    def make_card(self, parent, title):
        frame = tk.LabelFrame(parent, text=title, bg=CARD_BG, fg=PRIMARY_DARK, padx=14, pady=12, font=("\ub9d1\uc740 \uace0\ub515", 11, "bold"), relief="solid", bd=1)
        frame.pack(fill="x", padx=16, pady=8)
        return frame

    def make_button(self, parent, text, command, bg_color, width=13):
        return tk.Button(parent, text=text, command=command, width=width, bg=bg_color, fg="white", activebackground=bg_color, activeforeground="white", disabledforeground="#E5E7EB", relief="flat", bd=0, cursor="hand2", font=FONT_BOLD, padx=8, pady=7)

    def make_small_button(self, parent, text, command, bg_color):
        return tk.Button(parent, text=text, command=command, bg=bg_color, fg="white", activebackground=bg_color, activeforeground="white", disabledforeground="#E5E7EB", relief="flat", bd=0, cursor="hand2", font=("\ub9d1\uc740 \uace0\ub515", 9, "bold"), padx=9, pady=4)

    def log(self, msg):
        self.root.after(0, lambda: self._append_log(msg))
        if msg:
            self.logger.info(msg)

    def set_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(f"\uc0c1\ud0dc: {msg}"))

    def clear_log(self):
        for log_box in self._get_log_boxes():
            log_box.config(state="normal")
            log_box.delete("1.0", "end")
            log_box.config(state="disabled")
        self.log("\ud654\uba74 \ub85c\uadf8\ub97c \uc9c0\uc6e0\uc2b5\ub2c8\ub2e4.")

    def toggle_api_key(self):
        self.api_key_visible = not self.api_key_visible
        self.api_key_entry.config(show="" if self.api_key_visible else "*")
        self.api_key_toggle_btn.config(text="\uc228\uae30\uae30" if self.api_key_visible else "\ubcf4\uae30")

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
            "\ub85c\uadf8 \ubd84\ub9ac\ucc3d",
            geometry="900x540",
            minsize=(720, 420),
        )

    def open_fullscreen_log(self):
        self._open_log_window(
            "fullscreen_log_window",
            "fullscreen_log_box",
            "\ub85c\uadf8 \uc804\uccb4\ud654\uba74",
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
        self.make_small_button(toolbar, "\ub2eb\uae30", on_close, GRAY).pack(side="right")

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
            self.log(f"\ub9c1\ud06c \uc5f4\uae30 \uc2e4\ud328: {error}")

    def get_selected_categories(self):
        return [category for category, var in self.category_vars.items() if var.get()]

    def read_config_from_screen(self):
        return AppConfig(
            api_key="".join(self.api_key_entry.get().split()),
            keywords=self.keyword_text.get("1.0", "end").strip(),
            interval=self.interval_entry.get().strip(),
            selected_categories=self.get_selected_categories(),
            bootstrap_minutes=int(self.config.bootstrap_minutes),
            overlap_minutes=int(self.config.overlap_minutes),
            request_timeout_seconds=int(self.config.request_timeout_seconds),
            num_of_rows=int(self.config.num_of_rows),
        )

    def start(self):
        config = self.read_config_from_screen()
        keywords = parse_keywords(config.keywords)
        if not config.api_key:
            messagebox.showwarning("\ud655\uc778", "API \ud0a4\ub97c \uc785\ub825\ud574 \uc8fc\uc138\uc694.")
            return
        if not keywords:
            messagebox.showwarning("\ud655\uc778", "\ud0a4\uc6cc\ub4dc\ub97c \ud558\ub098 \uc774\uc0c1 \uc785\ub825\ud574 \uc8fc\uc138\uc694.")
            return
        if not config.selected_categories:
            messagebox.showwarning("\ud655\uc778", "\uc870\ud68c\ud560 \uacf5\uace0 \uc885\ub958\ub97c \ud558\ub098 \uc774\uc0c1 \uc120\ud0dd\ud574 \uc8fc\uc138\uc694.")
            return
        try:
            interval = int(config.interval)
        except ValueError:
            messagebox.showwarning("\ud655\uc778", "\ud655\uc778 \uc8fc\uae30\ub294 \uc22b\uc790\ub85c \uc785\ub825\ud574 \uc8fc\uc138\uc694.")
            return
        if interval < MIN_INTERVAL_MINUTES:
            messagebox.showwarning("\ud655\uc778", f"\ud655\uc778 \uc8fc\uae30\ub294 \ucd5c\uc18c {MIN_INTERVAL_MINUTES}\ubd84 \uc774\uc0c1\uc73c\ub85c \uc785\ub825\ud574 \uc8fc\uc138\uc694.")
            return

        estimated_calls = int(1440 / interval) * len(config.selected_categories)
        if interval < RECOMMENDED_INTERVAL_MINUTES or estimated_calls > 1000:
            result = messagebox.askyesno(
                "API \ud638\ucd9c\ub7c9 \ud655\uc778",
                f"\ud604\uc7ac \uc124\uc815\uc740 \ud558\ub8e8 \uc57d {estimated_calls:,}\ud68c API\ub97c \ud638\ucd9c\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.\n\n"
                f"- \ud655\uc778 \uc8fc\uae30: {interval}\ubd84\n"
                f"- \uc870\ud68c \uc885\ub958: {len(config.selected_categories)}\uac1c\n\n"
                "5\ubd84 \ubbf8\ub9cc \uc8fc\uae30\ub294 API \ud638\ucd9c\ub7c9\uc774 \ub9ce\uc544\uc9c8 \uc218 \uc788\uc2b5\ub2c8\ub2e4.\n"
                "\uadf8\ub798\ub3c4 \uc774 \uc124\uc815\uc73c\ub85c \uc2dc\uc791\ud560\uae4c\uc694?",
            )
            if not result:
                return

        self.config = config
        save_config(config)
        self.scheduler = BidScheduler(config, keywords, self.log, self.set_status, WindowsNotifier(logger=self.logger), self.logger)
        if not self.scheduler.start():
            messagebox.showwarning("\ud655\uc778", "\uc774\uc804 \uac10\uc2dc \uc791\uc5c5\uc774 \uc544\uc9c1 \uc885\ub8cc \uc911\uc785\ub2c8\ub2e4. \uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\uc791\ud574 \uc8fc\uc138\uc694.")
            return

        self.update_running_ui(True)
        self.set_status("\uac10\uc2dc \uc911")
        self.log("\uac10\uc2dc \uc2dc\uc791")
        self.log(f"\ud0a4\uc6cc\ub4dc: {', '.join(keywords)}")
        self.log(f"\ud655\uc778 \uc8fc\uae30: {interval}\ubd84")
        self.log(f"\uc608\uc0c1 API \ud638\ucd9c\ub7c9: \ud558\ub8e8 \uc57d {estimated_calls:,}\ud68c")
        selected_labels = [CATEGORY_LABELS.get(category, category) for category in config.selected_categories]
        self.log(f"\uc870\ud68c \uc885\ub958: {', '.join(selected_labels)}")

    def stop(self):
        if self.scheduler:
            self.scheduler.stop()
        self.update_running_ui(False)
        self.set_status("\ub300\uae30 \uc911")
        self.log("\uac10\uc2dc \uc911\uc9c0")

    def test_alert(self):
        WindowsNotifier(logger=self.logger).send("\ub098\ub77c\uc7a5\ud130 \uc54c\ub9bc \ud14c\uc2a4\ud2b8", "\uc708\ub3c4\uc6b0 \uc54c\ub9bc\uc774 \uc815\uc0c1 \uc791\ub3d9\ud569\ub2c8\ub2e4.")
        self.log("\uc54c\ub9bc \ud14c\uc2a4\ud2b8 \uc2e4\ud589")

    def reset_records(self):
        if self.scheduler and self.scheduler.running:
            messagebox.showwarning("\ud655\uc778", "\uac10\uc2dc \uc911\uc5d0\ub294 \ucd08\uae30\ud654\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.\n\uba3c\uc800 \uc911\uc9c0 \ubc84\ud2bc\uc744 \ub20c\ub7ec\uc8fc\uc138\uc694.")
            return
        result = messagebox.askyesno(
            "\ud655\uc778 \uae30\ub85d \ucd08\uae30\ud654",
            "\uc774\ubbf8 \ud655\uc778\ud55c \uacf5\uace0 \uae30\ub85d\uacfc \ub9c8\uc9c0\ub9c9 \uc870\ud68c \uc2dc\uac01\uc744 \uc0ad\uc81c\ud560\uae4c\uc694?\n\n"
            "\ud0a4\uc6cc\ub4dc\ub97c \ubc14\uafbc \ub4a4 \uae30\uc874 \uacf5\uace0\ub97c \ub2e4\uc2dc \ud655\uc778\ud558\uace0 \uc2f6\uc744 \ub54c \uc0ac\uc6a9\ud558\ub294 \uae30\ub2a5\uc785\ub2c8\ub2e4.",
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
                self.log(f"{file_path} \uc0ad\uc81c \uc2e4\ud328: {error}")
                messagebox.showerror("\uc624\ub958", f"{file_path} \uc0ad\uc81c\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.\n\n{error}")
                return

        if deleted_files:
            self.log("\ud655\uc778 \uae30\ub85d \ucd08\uae30\ud654 \uc644\ub8cc")
            self.set_status("\ud655\uc778 \uae30\ub85d \ucd08\uae30\ud654 \uc644\ub8cc")
            messagebox.showinfo("\uc644\ub8cc", "\ud655\uc778 \uae30\ub85d\uc774 \ucd08\uae30\ud654\ub418\uc5c8\uc2b5\ub2c8\ub2e4.")
        else:
            self.log("\ucd08\uae30\ud654\ud560 \ud655\uc778 \uae30\ub85d\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.")
            self.set_status("\ucd08\uae30\ud654\ud560 \uae30\ub85d \uc5c6\uc74c")
            messagebox.showinfo("\uc644\ub8cc", "\uc0ad\uc81c\ud560 \ud655\uc778 \uae30\ub85d\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.")

    def update_running_ui(self, is_running):
        state = "disabled" if is_running else "normal"
        self.keyword_text.config(state=state)
        self.api_key_entry.config(state=state)
        self.interval_entry.config(state=state)
        self.api_key_toggle_btn.config(state=state)
        for cb in self.category_checks:
            cb.config(state=state)
        if is_running:
            self.start_btn.config(state="disabled", text="\uac10\uc2dc \uc911", bg=DISABLED_BLUE, activebackground=DISABLED_BLUE)
            self.stop_btn.config(state="normal", text="\uc911\uc9c0", bg=STOP_RED, activebackground=STOP_RED)
            self.reset_btn.config(state="disabled")
        else:
            self.start_btn.config(state="normal", text="\uc2dc\uc791", bg=PRIMARY, activebackground=PRIMARY)
            self.stop_btn.config(state="disabled", text="\uc911\uc9c0", bg=GRAY, activebackground=GRAY)
            self.reset_btn.config(state="normal")
