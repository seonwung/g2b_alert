import tkinter as tk


def make_dialog_button(parent, text, command, color):
    """Create the compact button shared by email dialog views."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg="white",
        activebackground=color,
        activeforeground="white",
        relief="flat",
        bd=0,
        cursor="hand2",
        font=("맑은 고딕", 9, "bold"),
        padx=10,
        pady=5,
    )
