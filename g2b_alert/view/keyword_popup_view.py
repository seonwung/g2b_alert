import tkinter as tk

from .styles import APP_BG, CARD_BG, FONT, FONT_BOLD, INPUT_BG, PRIMARY_DARK, SUB_TEXT, TEXT


class KeywordPopupView:
    def __init__(self, root, bid, keywords):
        self.window = tk.Toplevel(root)
        self.window.title("매칭 키워드")
        self.window.configure(bg=APP_BG)
        self.window.geometry("360x260")
        self.window.minsize(300, 180)
        self.window.transient(root)
        frame = tk.Frame(self.window, bg=CARD_BG, padx=12, pady=12)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(
            frame, text="매칭 키워드", bg=CARD_BG, fg=PRIMARY_DARK, font=FONT_BOLD
        ).pack(anchor="w")
        tk.Label(
            frame,
            text=getattr(bid, "title", "") or "선택한 공고",
            bg=CARD_BG,
            fg=SUB_TEXT,
            anchor="w",
            justify="left",
            font=("맑은 고딕", 9),
            wraplength=310,
        ).pack(fill="x", pady=(4, 8))
        list_frame = tk.Frame(frame, bg=CARD_BG)
        list_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        keyword_list = tk.Listbox(
            list_frame, bg=INPUT_BG, fg=TEXT, font=FONT, yscrollcommand=scrollbar.set
        )
        keyword_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=keyword_list.yview)
        for index, keyword in enumerate(keywords, start=1):
            keyword_list.insert("end", f"{index}. {keyword}")
        self.window.bind("<Escape>", lambda _event: self.close())

    def close(self):
        if self.window.winfo_exists():
            self.window.destroy()
