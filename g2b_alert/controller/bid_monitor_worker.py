import threading
import time


class BidMonitorWorker:
    """Controller-layer worker preserving completion-then-wait polling."""

    def __init__(self, config, keywords, service_factory, on_complete, on_error):
        self.config = config
        self.keywords = keywords
        self.service_factory = service_factory
        self.on_complete = on_complete
        self.on_error = on_error
        self.running = False
        self.stop_event = threading.Event()
        self.worker = None
        self.check_lock = threading.Lock()
        self.state_lock = threading.Lock()

    def update(self, config, keywords, service_factory):
        with self.state_lock:
            self.config = config
            self.keywords = keywords
            self.service_factory = service_factory

    def start(self):
        if self.worker is not None and self.worker.is_alive():
            return False
        self.running = True
        self.stop_event.clear()
        self.worker = threading.Thread(target=self._loop, daemon=True, name="bid-monitor-worker")
        self.worker.start()
        return True

    def stop(self):
        self.running = False
        self.stop_event.set()

    def wait(self, timeout=None):
        if self.worker and self.worker.is_alive():
            self.worker.join(timeout=timeout)

    def _loop(self):
        next_due = time.monotonic()
        while self.running:
            wait_seconds = next_due - time.monotonic()
            if wait_seconds > 0:
                self.stop_event.wait(wait_seconds)
                if not self.running:
                    break
            if not self.check_once():
                self.stop_event.wait(0.1)
                continue
            with self.state_lock:
                interval_seconds = int(self.config.interval) * 60
            next_due += interval_seconds
            now = time.monotonic()
            while next_due <= now:
                next_due += interval_seconds

    def check_once(self):
        if not self.check_lock.acquire(blocking=False):
            return False
        try:
            with self.state_lock:
                config = self.config
                keywords = self.keywords
                service_factory = self.service_factory
            summary = service_factory().check_once(config, keywords)
        except Exception as error:
            self.on_error(error)
        else:
            self.on_complete(summary)
        finally:
            self.check_lock.release()
        return True

    def check_custom(self, config, keywords, service_factory):
        with self.check_lock:
            return service_factory().check_once(
                config,
                keywords,
                use_last_check=False,
                record_cycle=False,
                skip_seen=False,
                mark_seen=True,
            )
