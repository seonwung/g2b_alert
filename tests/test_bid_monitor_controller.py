import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from g2b_alert.controller.bid_monitor_controller import BidMonitorControllerMixin
from g2b_alert.model.config import AppConfig
from g2b_alert.model.entities import Bid


class BidMonitorControllerTest(unittest.TestCase):
    def test_controller_derives_monitor_config_from_raw_view_rows(self):
        controller = BidMonitorControllerMixin()
        controller.config = AppConfig()
        controller.view = SimpleNamespace(
            get_monitor_form=lambda: {
                "api_key": " key with spaces ",
                "keyword_rules": [
                    {
                        "id": "rule-1",
                        "keyword": "server",
                        "operator": "and",
                        "categories": ["goods"],
                        "targets": ["bid_lifecycle", "prespec"],
                        "enabled": True,
                    },
                    {
                        "id": "rule-2",
                        "keyword": "used",
                        "operator": "exclude",
                        "categories": ["goods"],
                        "targets": ["bid_lifecycle"],
                        "enabled": False,
                    },
                ],
                "interval": "7",
                "result_interval": "11",
                "windows_notifications_enabled": True,
                "notify_all_opening_results": False,
                "keyword_email_enabled": True,
                "attachment_download_dir": "files",
            }
        )

        config = controller.read_config_from_screen()

        self.assertEqual("keywithspaces", config.api_key)
        self.assertEqual("server", config.and_keywords)
        self.assertEqual("used", config.exclude_keywords)
        self.assertEqual(["goods"], config.selected_categories)
        self.assertTrue(config.prespec_search_enabled)
        self.assertEqual("7", config.interval)
        self.assertEqual("11", config.result_interval)

    def test_daily_call_estimate_counts_each_selected_api_target(self):
        config = SimpleNamespace(
            keyword_rules=[
                {
                    "enabled": True,
                    "categories": ["service", "goods", "works", "etc"],
                    "targets": ["bid_lifecycle"],
                },
                {
                    "enabled": True,
                    "categories": ["service", "goods", "works", "etc"],
                    "targets": ["prespec"],
                },
            ],
            selected_categories=["service", "goods", "works", "etc"],
            prespec_search_enabled=True,
        )

        estimated = BidMonitorControllerMixin._estimate_daily_keyword_calls(config, 5)

        self.assertEqual(2304, estimated)

    def test_keyword_match_stays_in_recent_alerts_until_user_saves_it(self):
        controller = BidMonitorControllerMixin()
        controller.config = SimpleNamespace(
            interval="5",
            windows_notifications_enabled=False,
        )
        controller.bid_repository = SimpleNamespace(save_bid=Mock())
        controller.email_alert_service = SimpleNamespace(
            queue_keyword_bid=Mock(return_value=(False, 0))
        )
        controller.attachment_downloader = SimpleNamespace(download_for_notice=Mock())
        controller.mark_unread_alert = Mock()
        controller.log = Mock()
        controller.logger = Mock()
        controller.view = SimpleNamespace(set_check_summary=Mock())
        bid = Bid(
            category="service",
            title="BIS 구축",
            bid_no="R-1",
            bid_ord="000",
            agency="기관",
            demand_agency="수요기관",
            link="",
        )
        summary = {
            "category_reports": [],
            "alerts": [
                {
                    "bid": bid,
                    "matched_keywords": ["BIS"],
                    "notify": True,
                    "track": False,
                }
            ],
            "all_success": True,
            "checked_at": datetime(2026, 7, 20, 12, 0),
            "new_alert_count": 1,
        }

        controller._handle_bid_check_complete(summary)

        controller.bid_repository.save_bid.assert_not_called()
        controller.attachment_downloader.download_for_notice.assert_not_called()
        controller.mark_unread_alert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
