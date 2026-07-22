import queue
import tkinter as tk


class UiDispatcher:
    """Runs worker callbacks only from Tkinter's main thread."""

    def __init__(self, root, poll_interval_ms=50):
        self.root = root
        self.poll_interval_ms = poll_interval_ms
        self.callbacks = queue.Queue()
        self.running = True
        self.root.after(self.poll_interval_ms, self._poll)

    def post(self, callback):
        if self.running:
            self.callbacks.put(callback)

    def stop(self):
        self.running = False
        while True:
            try:
                self.callbacks.get_nowait()
            except queue.Empty:
                break

    def _poll(self):
        if not self.running:
            return
        while True:
            try:
                callback = self.callbacks.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except tk.TclError:
                if not self.running:
                    return
                raise
        if self.running:
            self.root.after(self.poll_interval_ms, self._poll)
