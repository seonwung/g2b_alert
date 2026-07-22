import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from g2b_alert.controller.saved_bids_controller import SavedBidsControllerMixin
from g2b_alert.model.entities import Bid, PreSpecification


class SavedBidsControllerTest(unittest.TestCase):
    def test_directly_looked_up_prespec_uses_prespec_save_flow(self):
        pre_spec = PreSpecification(
            category="service",
            title="탄소중립 설비투자",
            pre_spec_no="R26BD00251411",
            agency="기관",
            demand_agency="수요기관",
            link="https://www.g2b.go.kr/specification-file",
        )
        controller = SavedBidsControllerMixin()
        controller.view = SimpleNamespace(get_lookup_notice=Mock(return_value=pre_spec))
        controller._save_pre_specification = Mock()

        controller.save_lookup_notice()

        controller._save_pre_specification.assert_called_once_with(pre_spec)

    def test_saving_bid_starts_attachment_download(self):
        bid = Bid(
            category="goods",
            title="탄소중립 설비투자",
            bid_no="R26BK01639445",
            bid_ord="000",
            agency="기관",
            demand_agency="수요기관",
            link="",
            raw={"ntceSpecDocUrl1": "https://example.com/file"},
        )
        controller = SavedBidsControllerMixin()
        controller.bid_repository = SimpleNamespace(
            save_bid=Mock(return_value=(7, True))
        )
        controller.view = SimpleNamespace(show_warning=Mock(), show_error=Mock(), show_info=Mock())
        controller.logger = Mock()
        controller.log = Mock()
        controller.refresh_saved_bids = Mock()
        controller.start_saved_result_monitor_if_needed = Mock()
        controller._download_saved_notice_attachments_async = Mock()

        controller._save_bid(bid)

        controller._download_saved_notice_attachments_async.assert_called_once_with(
            bid, overwrite=False
        )


if __name__ == "__main__":
    unittest.main()
