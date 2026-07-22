import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from g2b_alert.controller.saved_result_controller import SavedResultControllerMixin


class SavedResultControllerTest(unittest.TestCase):
    def test_transition_downloads_full_bid_attachments(self):
        transitioned = SimpleNamespace(
            id=3,
            title="탄소중립 설비투자",
            bid_no="R26BK01639445",
            bid_ord="000",
        )
        controller = SavedResultControllerMixin()
        controller.config = SimpleNamespace(windows_notifications_enabled=False)
        controller.email_alert_service = SimpleNamespace(
            queue_pre_spec_transition=Mock(return_value=(False, 0))
        )
        controller._download_saved_notice_attachments_async = Mock()
        controller.mark_unread_alert = Mock()
        controller.log = Mock()
        controller.refresh_saved_bids = Mock()

        controller._process_result_summary(
            {
                "transition_events": [
                    {
                        "saved_bid": transitioned,
                        "pre_spec_no": "R26BD00251411",
                        "message": "입찰공고 전환",
                        "should_notify": False,
                    }
                ]
            }
        )

        controller._download_saved_notice_attachments_async.assert_called_once_with(
            transitioned
        )

    def test_change_event_overwrites_local_attachments(self):
        changed = SimpleNamespace(
            id=4,
            title="변경공고",
            bid_no="R26BK1",
            bid_ord="001",
        )
        controller = SavedResultControllerMixin()
        controller.config = SimpleNamespace(windows_notifications_enabled=False)
        controller.email_alert_service = SimpleNamespace(
            queue_bid_change=Mock(return_value=(False, 0))
        )
        controller._download_saved_notice_attachments_async = Mock()
        controller.mark_unread_alert = Mock()
        controller.log = Mock()
        controller.refresh_saved_bids = Mock()

        controller._process_result_summary(
            {
                "change_events": [
                    {
                        "saved_bid": changed,
                        "previous_order": "000",
                        "current_order": "001",
                        "comparison": {"changes": []},
                        "message": "변경공고",
                        "should_notify": False,
                    }
                ]
            }
        )

        controller._download_saved_notice_attachments_async.assert_called_once_with(
            changed, overwrite=True
        )


if __name__ == "__main__":
    unittest.main()
