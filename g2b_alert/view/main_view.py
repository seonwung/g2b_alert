import tkinter as tk
from tkinter import messagebox, ttk

from ..presentation.contracts import MainViewState, ViewActionsProtocol

from .bid_monitor_view import BidMonitorViewMixin
from .log_view import LogViewMixin
from .keyword_popup_view import KeywordPopupView
from .recent_alert_view import RecentAlertViewMixin
from .saved_bids_view import SavedBidsViewMixin
from .email_recipient_view import SavedBidRecipientWindow
from .email_settings_view import EmailSettingsWindow
from .styles import (
    APP_BG,
    BORDER,
    CARD_BG,
    DISABLED_BLUE,
    FONT,
    FONT_BOLD,
    GRAY,
    INPUT_BG,
    PRIMARY,
    STOP_RED,
    SUB_TEXT,
    TEXT,
)
from .ui_dispatcher import UiDispatcher


class MainViewMixin:
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
        header = tk.Frame(
            self.root,
            bg=CARD_BG,
            height=68,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        self.settings_tab_button = self.make_small_button(
            header, "기본 설정 열기", self.toggle_settings_tab, GRAY
        )
        self.settings_tab_button.pack(side="right", padx=22, pady=17)

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

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        main = tk.Frame(self.notebook, bg=APP_BG)
        saved_page = tk.Frame(self.notebook, bg=APP_BG)
        self.settings_page = tk.Frame(self.notebook, bg=APP_BG)
        self.log_page = tk.Frame(self.notebook, bg=APP_BG)
        self.notebook.add(main, text="키워드 감시")
        self.notebook.add(saved_page, text="저장 공고")
        main_pane = tk.PanedWindow(main, orient="vertical", sashwidth=7, bg=BORDER, bd=0)
        main_pane.pack(fill="both", expand=True)
        main_content = tk.Frame(main_pane, bg=APP_BG)
        main_pane.add(main_content, minsize=410, stretch="never")
        self._build_status(main_content)
        self._build_keyword_settings(main_content)
        self._build_action_buttons(main_content)
        alert_content = tk.Frame(main_pane, bg=APP_BG)
        main_pane.add(alert_content, minsize=300, stretch="always")
        self._build_recent_alerts(alert_content)

        saved_content = tk.Frame(saved_page, bg=APP_BG)
        saved_content.pack(fill="both", expand=True)
        self._build_saved_bids_page(saved_content)
        settings_toolbar = tk.Frame(self.settings_page, bg=APP_BG)
        settings_toolbar.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(
            settings_toolbar,
            text="기본 설정",
            bg=APP_BG,
            fg=TEXT,
            font=FONT_BOLD,
        ).pack(side="left")
        self.make_small_button(
            settings_toolbar, "탭 닫기", self.close_settings_tab, GRAY
        ).pack(side="right")
        settings_content = tk.Frame(self.settings_page, bg=APP_BG)
        settings_content.pack(fill="both", expand=True, padx=6, pady=6)
        self._build_basic_settings(settings_content)
        self._build_embedded_log(self.log_page, "search_log_box", "통합 로그")
        self.log_box = self.search_log_box

    def show_log_tab(self):
        if str(self.log_page) not in self.notebook.tabs():
            self.notebook.add(self.log_page, text="로그")
        self.notebook.select(self.log_page)
        if hasattr(self, "log_tab_button"):
            self.log_tab_button.config(text="로그 탭 닫기")

    def close_log_tab(self):
        if str(self.log_page) in self.notebook.tabs():
            self.notebook.forget(self.log_page)
        if hasattr(self, "log_tab_button"):
            self.log_tab_button.config(text="로그 탭 열기")

    def show_settings_tab(self):
        if str(self.settings_page) not in self.notebook.tabs():
            self.notebook.add(self.settings_page, text="기본 설정")
        self.notebook.select(self.settings_page)
        self.settings_tab_button.config(text="기본 설정 닫기")

    def close_settings_tab(self):
        if str(self.settings_page) in self.notebook.tabs():
            self.notebook.forget(self.settings_page)
        self.settings_tab_button.config(text="기본 설정 열기")

    def toggle_settings_tab(self):
        if str(self.settings_page) in self.notebook.tabs():
            self.close_settings_tab()
        else:
            self.show_settings_tab()

    def toggle_log_tab(self):
        if str(self.log_page) in self.notebook.tabs():
            self.close_log_tab()
        else:
            self.show_log_tab()

    def make_card(self, parent, title):
        frame = tk.LabelFrame(
            parent,
            text=title,
            bg=CARD_BG,
            fg=TEXT,
            padx=14,
            pady=10,
            font=("맑은 고딕", 11, "bold"),
            relief="solid",
            bd=1,
        )
        frame.pack(fill="x", padx=16, pady=6)
        return frame

    def make_button(self, parent, text, command, bg_color, width=13):
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=bg_color,
            fg="white",
            activebackground=bg_color,
            activeforeground="white",
            disabledforeground="#E5E7EB",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=FONT_BOLD,
            padx=8,
            pady=7,
        )

    def make_small_button(self, parent, text, command, bg_color):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg="white",
            activebackground=bg_color,
            activeforeground="white",
            disabledforeground="#E5E7EB",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("맑은 고딕", 9, "bold"),
            padx=9,
            pady=4,
        )

    def post(self, callback):
        if self.closing:
            return
        self.ui_dispatcher.post(callback)

    def set_status(self, message):
        self.post(lambda: self.status_var.set(f"상태: {message}"))

    def show_info(self, title, message, parent=None):
        messagebox.showinfo(title, message, parent=parent)

    def show_warning(self, title, message, parent=None):
        messagebox.showwarning(title, message, parent=parent)

    def show_error(self, title, message, parent=None):
        messagebox.showerror(title, message, parent=parent)

    def ask_yes_no(self, title, message, parent=None):
        return messagebox.askyesno(title, message, parent=parent)

    def open_email_settings_window(self, **kwargs):
        return EmailSettingsWindow(self.root, **kwargs)

    def open_saved_bid_recipient_window(self, **kwargs):
        return SavedBidRecipientWindow(self.root, **kwargs)

    def show_keyword_popup(self, bid, keywords):
        self.close_keyword_popup()
        self.keyword_popup = KeywordPopupView(self.root, bid, keywords)

    def close_keyword_popup(self):
        if self.keyword_popup:
            self.keyword_popup.close()
            self.keyword_popup = None

    def update_running_ui(self, is_running):
        state = "disabled" if is_running else "normal"
        self.add_keyword_btn.config(state="normal")
        self.api_key_entry.config(state=state)
        self.interval_entry.config(state=state)
        self.api_key_toggle_btn.config(state=state)
        if is_running:
            self.start_btn.config(
                state="disabled", text="전체 감시 중", bg=DISABLED_BLUE, activebackground=DISABLED_BLUE
            )
            self.stop_btn.config(state="normal", text="전체 감시 중지", bg=STOP_RED, activebackground=STOP_RED)
            self.reset_btn.config(state="disabled")
        else:
            self.start_btn.config(state="normal", text="전체 감시 시작", bg=PRIMARY, activebackground=PRIMARY)
            self.stop_btn.config(state="disabled", text="전체 감시 중지", bg=GRAY, activebackground=GRAY)
            self.reset_btn.config(state="normal")


class MainView(
    MainViewMixin,
    BidMonitorViewMixin,
    RecentAlertViewMixin,
    SavedBidsViewMixin,
    LogViewMixin,
):
    """Tkinter-only view composed from feature-specific view mixins."""

    def __init__(
        self,
        root,
        actions: ViewActionsProtocol,
        initial_state: MainViewState,
    ):
        self.root = root
        self.root.title("나라장터 키워드 알림")
        self.root.geometry("1080x940")
        self.root.minsize(960, 840)
        self.root.resizable(True, True)
        self.root.configure(bg=APP_BG)
        self.actions = actions
        self.initial_state = initial_state
        self.closing = False
        self.api_key_visible = False
        self.log_records = []
        self.log_filter = "all"
        self.saved_bid_rows = {}
        self.keyword_popup = None
        self.ui_dispatcher = UiDispatcher(root)

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

    def stop_dispatcher(self):
        self.closing = True
        self.ui_dispatcher.stop()

    def destroy(self):
        self.root.destroy()

    def set_close_handler(self, callback):
        self.root.protocol("WM_DELETE_WINDOW", callback)

    def schedule(self, delay_ms, callback):
        self.root.after(delay_ms, callback)
