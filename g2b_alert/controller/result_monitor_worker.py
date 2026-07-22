import threading


class ResultMonitorWorker:
    """Controller-layer scheduler for saved-bid result checks."""

    def __init__(self, config, service_factory, on_complete, on_error, check_lock=None):
        self.config = config
        self.service_factory = service_factory
        self.on_complete = on_complete
        self.on_error = on_error
        self.error_counts = {}
        self.running = False
        self.stop_event = threading.Event()
        self.worker = None
        self.check_lock = check_lock or threading.Lock()

    def start(self):
        if self.worker is not None and self.worker.is_alive():
            return False
        self.running = True
        self.stop_event.clear()
        self.worker = threading.Thread(target=self._loop, daemon=True, name="result-monitor-worker")
        self.worker.start()
        return True

    def stop(self):
        self.running = False
        self.stop_event.set()

    def wait(self, timeout=None):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=timeout)

    def update_config(self, config):
        self.config = config

    def request_check(self):
        """Wake the worker so newly enabled bids are checked immediately."""
        if self.running:
            self.stop_event.set()

    def _loop(self):
        while self.running:
            self.check_once()
            interval = max(1, int(getattr(self.config, "result_interval", self.config.interval)))
            self.stop_event.wait(interval * 60)
            if self.running:
                self.stop_event.clear()

    def check_once(self):
        if not self.check_lock.acquire(blocking=False):
            return False
        try:
            summary = self.service_factory(self.error_counts).check_saved_bids()
        except Exception as error:
            self.on_error(error)
        else:
            self.on_complete(summary)
        finally:
            self.check_lock.release()
        return True
