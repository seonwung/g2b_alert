import tkinter as tk

from g2b_alert.ui import G2BAlertApp


def main():
    root = tk.Tk()
    G2BAlertApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
