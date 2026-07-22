import tkinter as tk
from tkinter import messagebox

from .email_common import make_dialog_button
from .styles import APP_BG, CARD_BG, FONT, FONT_BOLD, GRAY, SUB_TEXT, SUCCESS, TEXT


class SavedBidRecipientWindow:
    def __init__(self, root, saved_bid, recipients, mapped_ids, on_save):
        self.on_save = on_save
        self.window = tk.Toplevel(root)
        self.window.title("저장 공고 이메일 수신자")
        self.window.geometry("470x460")
        self.window.minsize(420, 360)
        self.window.configure(bg=APP_BG)
        self.window.transient(root)

        frame = tk.Frame(self.window, bg=CARD_BG, padx=14, pady=14)
        frame.pack(fill="both", expand=True, padx=14, pady=14)
        tk.Label(
            frame,
            text=saved_bid.title or saved_bid.bid_no,
            bg=CARD_BG,
            fg=TEXT,
            anchor="w",
            justify="left",
            wraplength=410,
            font=FONT_BOLD,
        ).pack(fill="x", pady=(0, 4))
        tk.Label(
            frame,
            text="체크한 수신자에게 이 공고의 변경·개찰·낙찰정보를 이메일로 보냅니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            anchor="w",
            font=("맑은 고딕", 9),
        ).pack(fill="x", pady=(0, 10))

        self.recipient_vars = {}
        list_frame = tk.Frame(frame, bg=CARD_BG)
        list_frame.pack(fill="both", expand=True)
        if not recipients:
            tk.Label(
                list_frame,
                text="등록된 공통 수신자가 없습니다.\n키워드 설정의 [SMTP·수신자 관리]에서 먼저 등록해 주세요.",
                bg=CARD_BG,
                fg=SUB_TEXT,
                justify="center",
                font=FONT,
            ).pack(expand=True)
        for recipient in recipients:
            selected = (
                recipient["id"] in mapped_ids
                or (not mapped_ids and bool(recipient["is_default"]))
            )
            var = tk.BooleanVar(value=selected)
            self.recipient_vars[recipient["id"]] = var
            organization = f" / {recipient['organization']}" if recipient["organization"] else ""
            memo = f" / {recipient['memo']}" if recipient["memo"] else ""
            default = " [기본]" if recipient["is_default"] else ""
            tk.Checkbutton(
                list_frame,
                text=(
                    f"{recipient['name']}  <{recipient['email']}>"
                    f"{organization}{memo}{default}"
                ),
                variable=var,
                bg=CARD_BG,
                fg=TEXT,
                activebackground=CARD_BG,
                selectcolor=CARD_BG,
                anchor="w",
                cursor="hand2",
                font=FONT,
            ).pack(fill="x", pady=3)

        footer = tk.Frame(frame, bg=CARD_BG)
        footer.pack(fill="x", pady=(10, 0))
        make_dialog_button(footer, "저장", self.save, SUCCESS).pack(side="right")
        make_dialog_button(footer, "닫기", self.window.destroy, GRAY).pack(
            side="right", padx=(0, 6)
        )

    def save(self):
        selected_ids = [recipient_id for recipient_id, var in self.recipient_vars.items() if var.get()]
        if not self.on_save(selected_ids):
            return
        messagebox.showinfo(
            "저장 완료",
            f"공고 추적 이메일 수신자 {len(selected_ids)}명을 연결했습니다.",
            parent=self.window,
        )
        self.window.destroy()
