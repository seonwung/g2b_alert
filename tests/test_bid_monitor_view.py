import unittest

from g2b_alert.view.bid_monitor_view import BidMonitorViewMixin
from g2b_alert.view.styles import STOP_RED


class FakeValue:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeWidget:
    def __init__(self):
        self.options = {}

    def config(self, **kwargs):
        self.options.update(kwargs)


class BidMonitorViewTest(unittest.TestCase):
    def test_running_rule_button_renders_without_runtime_name_errors(self):
        row = {
            "enabled_var": FakeValue(True),
            "monitor": FakeWidget(),
            "entry": FakeWidget(),
            "operator": FakeWidget(),
            "category_checks": [FakeWidget(), FakeWidget()],
            "target": FakeWidget(),
            "remove": FakeWidget(),
        }

        BidMonitorViewMixin()._render_keyword_monitor_button(row)

        self.assertEqual("감시 중지", row["monitor"].options["text"])
        self.assertEqual(STOP_RED, row["monitor"].options["bg"])
        self.assertEqual("disabled", row["entry"].options["state"])
        self.assertEqual("disabled", row["target"].options["state"])


if __name__ == "__main__":
    unittest.main()
