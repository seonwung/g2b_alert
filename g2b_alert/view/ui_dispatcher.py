"""Thread-safe dispatch to the Qt event loop (with a tiny legacy test adapter)."""

import queue

from PySide6.QtCore import QObject, Signal


class _SignalBridge(QObject):
    requested = Signal(object)

    def __init__(self):
        super().__init__()
        self.requested.connect(self._run)

    @staticmethod
    def _run(callback):
        callback()


class UiDispatcher:
    def __init__(self, root, poll_interval_ms=50):
        self.running = True
        self.root = root
        self.callbacks = queue.Queue()
        self._legacy = hasattr(root, "after")
        if self._legacy:
            root.after(poll_interval_ms, self._poll)
        else:
            self.bridge = _SignalBridge()

    def post(self, callback):
        if not self.running:
            return
        if self._legacy:
            self.callbacks.put(callback)
        else:
            self.bridge.requested.emit(callback)

    def stop(self):
        self.running = False
        while not self.callbacks.empty():
            try:
                self.callbacks.get_nowait()
            except queue.Empty:
                break
    def _poll(self):
        if not self.running:
            return
        while True:
            try:
                self.callbacks.get_nowait()()
            except queue.Empty:
                break
