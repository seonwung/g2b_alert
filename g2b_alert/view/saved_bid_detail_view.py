import tkinter as tk
from tkinter import ttk

from .email_common import make_dialog_button
from .styles import APP_BG, CARD_BG, FONT, FONT_BOLD, GRAY, PRIMARY, SUB_TEXT, TEXT


class SavedBidDetailWindow:
    def __init__(self, root, detail, on_open_link):
        self.detail = detail
        self.on_open_link = on_open_link
        self.attachment_rows = {}

        self.window = tk.Toplevel(root)
        self.window.title(f"공고 상세 - {detail['reference']}")
        self.window.geometry("920x720")
        self.window.minsize(780, 600)
        self.window.configure(bg=APP_BG)
        self.window.transient(root)

        self._build_header()
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self._add_key_value_tab(notebook, "기본정보", detail["basic_rows"])
        self._add_key_value_tab(notebook, "일정", detail["schedule_rows"])
        self._add_opinion_tab(notebook)
        self._add_result_tab(notebook)
        self._add_attachment_tab(notebook)
        self._add_change_tab(notebook)

    def _build_header(self):
        frame = tk.Frame(self.window, bg=CARD_BG, padx=16, pady=14)
        frame.pack(fill="x", padx=14, pady=14)
        title_row = tk.Frame(frame, bg=CARD_BG)
        title_row.pack(fill="x")
        tk.Label(
            title_row,
            text=f"[{self.detail['stage']}] {self.detail['title']}",
            bg=CARD_BG,
            fg=TEXT,
            font=("맑은 고딕", 15, "bold"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        if self.detail.get("link"):
            make_dialog_button(
                title_row,
                "나라장터에서 보기",
                lambda: self.on_open_link(self.detail["link"]),
                PRIMARY,
            ).pack(side="right")
        tk.Label(
            frame,
            text=self.detail["reference"],
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=FONT,
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

    def _add_key_value_tab(self, notebook, title, rows):
        frame = tk.Frame(notebook, bg=CARD_BG, padx=12, pady=12)
        notebook.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=("field", "value"), show="headings")
        tree.heading("field", text="항목")
        tree.heading("value", text="내용")
        tree.column("field", width=210, anchor="w", stretch=False)
        tree.column("value", width=610, anchor="w")
        for label, value in rows:
            tree.insert("", "end", values=(label, self._display(value)))
        self._pack_tree(frame, tree)

    def _add_result_tab(self, notebook):
        frame = tk.Frame(notebook, bg=CARD_BG, padx=12, pady=12)
        notebook.add(frame, text="개찰·낙찰")
        columns = (
            "status",
            "company",
            "business_number",
            "amount",
            "rate",
            "ranking",
            "opening_at",
        )
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        headings = {
            "status": "상태",
            "company": "업체명",
            "business_number": "사업자번호",
            "amount": "금액",
            "rate": "투찰·낙찰률",
            "ranking": "순위",
            "opening_at": "개찰일시",
        }
        widths = {
            "status": 110,
            "company": 190,
            "business_number": 120,
            "amount": 120,
            "rate": 90,
            "ranking": 65,
            "opening_at": 145,
        }
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="w")
        for result in self.detail["results"]:
            tree.insert("", "end", values=tuple(result[column] for column in columns))
        if not self.detail["results"]:
            tree.insert("", "end", values=("결과 없음", "-", "-", "-", "-", "-", "-"))
        self._pack_tree(frame, tree, horizontal=True)

    def _add_opinion_tab(self, notebook):
        frame = tk.Frame(notebook, bg=CARD_BG, padx=12, pady=12)
        notebook.add(frame, text=f"규격서 의견 ({len(self.detail['opinions'])})")
        summary = " / ".join(
            f"{label}: {self._display(value)}"
            for label, value in self.detail["opinion_summary_rows"]
        )
        tk.Label(
            frame,
            text=summary,
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=FONT,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 8))
        inner = tk.Frame(frame, bg=CARD_BG)
        inner.pack(fill="both", expand=True)
        scroll = tk.Scrollbar(inner)
        scroll.pack(side="right", fill="y")
        box = tk.Text(
            inner,
            bg="#F8FAFC",
            fg=TEXT,
            font=FONT,
            wrap="word",
            relief="solid",
            bd=1,
            padx=12,
            pady=10,
            yscrollcommand=scroll.set,
        )
        box.pack(side="left", fill="both", expand=True)
        scroll.config(command=box.yview)
        if not self.detail["opinions"]:
            box.insert("end", "등록된 규격서 의견이 없습니다.\n")
        for index, opinion in enumerate(self.detail["opinions"], start=1):
            reply_no = str(opinion.get("reply_no") or "0")
            kind = "기관 답변" if reply_no not in {"", "0"} else "규격서 의견"
            box.insert("end", f"[{kind} {index}] {self._display(opinion.get('title'))}\n")
            box.insert(
                "end",
                f"의견번호: {self._display(opinion.get('opinion_no'))} / "
                f"답변번호: {self._display(opinion.get('reply_no'))}\n",
            )
            box.insert(
                "end",
                f"작성기관·업체: {self._display(opinion.get('organization'))} / "
                f"작성자: {self._display(opinion.get('author'))} / "
                f"작성일시: {self._display(opinion.get('submitted_at'))}\n\n",
            )
            box.insert("end", f"{self._display(opinion.get('content'))}\n")
            if index < len(self.detail["opinions"]):
                box.insert("end", "\n" + "─" * 70 + "\n\n")
        box.config(state="disabled")

    def _add_attachment_tab(self, notebook):
        frame = tk.Frame(notebook, bg=CARD_BG, padx=12, pady=12)
        notebook.add(frame, text="첨부파일")
        tk.Label(
            frame,
            text="URL이 있는 첨부파일은 더블클릭하면 원문 링크를 엽니다.",
            bg=CARD_BG,
            fg=SUB_TEXT,
            font=FONT,
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        inner = tk.Frame(frame, bg=CARD_BG)
        inner.pack(fill="both", expand=True)
        tree = ttk.Treeview(inner, columns=("kind", "name", "url"), show="headings")
        tree.heading("kind", text="구분")
        tree.heading("name", text="파일명")
        tree.heading("url", text="원문 URL")
        tree.column("kind", width=115, anchor="w")
        tree.column("name", width=330, anchor="w")
        tree.column("url", width=390, anchor="w")
        for index, attachment in enumerate(self.detail["attachments"]):
            item_id = f"attachment_{index}"
            tree.insert(
                "",
                "end",
                iid=item_id,
                values=(attachment.get("kind", "첨부파일"), attachment["name"], attachment["url"] or "-"),
            )
            self.attachment_rows[item_id] = attachment
        if not self.detail["attachments"]:
            tree.insert("", "end", values=("-", "등록된 첨부파일 정보가 없습니다.", "-"))
        tree.bind("<Double-1>", lambda _event: self._open_selected_attachment(tree))
        self._pack_tree(inner, tree, horizontal=True)

    def _open_selected_attachment(self, tree):
        selected = tree.selection()
        if not selected:
            return
        attachment = self.attachment_rows.get(selected[0])
        if attachment and attachment.get("url"):
            self.on_open_link(attachment["url"])

    def _add_change_tab(self, notebook):
        frame = tk.Frame(notebook, bg=CARD_BG, padx=12, pady=12)
        notebook.add(frame, text="변경이력")
        box = tk.Text(
            frame,
            bg="#F8FAFC",
            fg=TEXT,
            font=FONT,
            wrap="word",
            relief="solid",
            bd=1,
            padx=12,
            pady=10,
        )
        box.pack(fill="both", expand=True)
        versions = self.detail["versions"]
        comparison = self.detail["comparison"]
        box.insert("end", "[차수별 원본]\n")
        for version in reversed(versions):
            marker = "현재" if version.get("is_current") else "이전"
            box.insert(
                "end",
                f"• {version.get('bid_pbanc_ord') or '000'} [{marker}] "
                f"{self._display(version.get('detected_at'))}\n",
            )
        box.insert("end", "\n[최근 차수 비교]\n")
        changes = comparison.get("changes") or []
        if not comparison.get("previous"):
            box.insert("end", "비교할 이전 차수가 없습니다.\n")
        elif not changes:
            box.insert("end", "선택한 항목에서 변경사항이 없습니다.\n")
        else:
            for change in changes:
                box.insert(
                    "end",
                    f"• {change['label']}\n"
                    f"  이전: {change['before']}\n"
                    f"  현재: {change['after']}\n\n",
                )
        box.config(state="disabled")

    @staticmethod
    def _pack_tree(parent, tree, horizontal=False):
        tree.pack(side="left", fill="both", expand=True)
        vertical = tk.Scrollbar(parent, orient="vertical", command=tree.yview)
        vertical.pack(side="right", fill="y")
        tree.configure(yscrollcommand=vertical.set)
        if horizontal:
            # Treeview columns remain accessible on smaller displays through width resizing.
            for column in tree["columns"]:
                tree.column(column, stretch=True)

    @staticmethod
    def _display(value):
        text = str(value or "").strip()
        return text if text else "-"
