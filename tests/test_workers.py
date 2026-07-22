"""Tests for conservative controller-layer polling workers."""

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from g2b_alert.controller.bid_monitor_worker import BidMonitorWorker
from g2b_alert.controller.bid_monitor_controller import BidMonitorControllerMixin
from g2b_alert.controller.result_monitor_worker import ResultMonitorWorker


class StopAfterFirstWait:
    def __init__(self, worker, events):
        self.worker = worker
        self.events = events

    def wait(self, seconds):
        self.events.append(("wait", seconds))
        self.worker.running = False


class BidService:
    def __init__(self, events):
        self.events = events

    def check_once(self, _config, _keywords):
        self.events.append("check")
        return {"ok": True}


class WorkerTest(unittest.TestCase):
    def test_enabled_keyword_rules_resume_with_the_existing_selection(self):
        controller = BidMonitorControllerMixin()
        controller.read_config_from_screen = Mock(
            return_value=SimpleNamespace(
                api_key="key",
                keyword_rules=[{"enabled": True}],
            )
        )
        controller.start = Mock(return_value=True)
        controller.log = Mock()
        controller.view = SimpleNamespace(set_all_keyword_monitoring=Mock())

        controller.resume_keyword_monitoring_if_needed()

        controller.start.assert_called_once_with(
            enable_all=False,
            warn_api_volume=False,
        )
        controller.log.assert_called_once()

    @patch("g2b_alert.controller.bid_monitor_worker.time.monotonic")
    def test_bid_worker_keeps_interval_anchored_to_initial_cycle(self, monotonic):
        monotonic.side_effect = [0.0, 0.0, 5.0, 5.0]
        events = []
        worker = BidMonitorWorker(
            SimpleNamespace(interval="1"),
            ["FIDS"],
            lambda: BidService(events),
            lambda _summary: events.append("complete"),
            lambda _error: events.append("error"),
        )
        worker.running = True
        worker.stop_event = StopAfterFirstWait(worker, events)

        worker._loop()

        self.assertEqual(["check", "complete", ("wait", 55.0)], events)

    def test_new_keyword_first_check_does_not_record_or_shift_regular_cycle(self):
        calls = []

        class CustomService:
            @staticmethod
            def check_once(_config, _keywords, **kwargs):
                calls.append(kwargs)
                return {"ok": True}

        worker = BidMonitorWorker(
            SimpleNamespace(interval="5"),
            ["old"],
            lambda: CustomService(),
            lambda _summary: None,
            lambda _error: None,
        )
        result = worker.check_custom(
            SimpleNamespace(interval="5"),
            ["new"],
            lambda: CustomService(),
        )

        self.assertEqual({"ok": True}, result)
        self.assertEqual(
            {
                "use_last_check": False,
                "record_cycle": False,
                "skip_seen": False,
                "mark_seen": True,
            },
            calls[0],
        )

    def test_result_worker_skips_overlapping_cycle(self):
        shared_lock = threading.Lock()
        service_called = []
        worker = ResultMonitorWorker(
            SimpleNamespace(interval="1", result_interval="1"),
            lambda _counts: service_called.append(True),
            lambda _summary: None,
            lambda _error: None,
            check_lock=shared_lock,
        )

        shared_lock.acquire()
        try:
            self.assertFalse(worker.check_once())
        finally:
            shared_lock.release()
        self.assertEqual([], service_called)

    def test_result_worker_can_be_woken_for_immediate_check(self):
        worker = ResultMonitorWorker(
            SimpleNamespace(interval="60", result_interval="60"),
            lambda _counts: None,
            lambda _summary: None,
            lambda _error: None,
        )
        worker.running = True

        worker.request_check()

        self.assertTrue(worker.stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
