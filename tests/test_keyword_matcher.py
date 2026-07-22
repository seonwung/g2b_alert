import unittest

from g2b_alert.model.entities import Bid
from g2b_alert.model.keyword_matcher import (
    match_keyword_rule_details,
    match_keyword_rules,
    parse_keyword_condition_rules,
    parse_keyword_rules,
)


class KeywordRuleTest(unittest.TestCase):
    def _bid(self, title):
        return Bid(
            category="service",
            title=title,
            bid_no="R-1",
            bid_ord="000",
            agency="수원시",
            demand_agency="수원시",
            link="",
        )

    def test_requires_all_and_and_at_least_one_or_keyword(self):
        rules = parse_keyword_rules("수원, BIS", "버스정보, 정류장", "유지보수")
        self.assertEqual(
            ["수원", "BIS", "버스정보"],
            match_keyword_rules(self._bid("수원 BIS 버스정보 구축사업"), rules),
        )
        self.assertEqual([], match_keyword_rules(self._bid("수원 버스정보 구축사업"), rules))
        self.assertEqual([], match_keyword_rules(self._bid("수원 BIS 교통 구축사업"), rules))

    def test_exclude_keyword_has_priority(self):
        rules = parse_keyword_rules("수원", "BIS", "유지보수")
        self.assertEqual([], match_keyword_rules(self._bid("수원 BIS 유지보수"), rules))

    def test_allows_and_only_or_or_only_rules(self):
        self.assertTrue(match_keyword_rules(self._bid("수원 BIS"), parse_keyword_rules("수원, BIS")))
        self.assertTrue(match_keyword_rules(self._bid("수원 BIS"), parse_keyword_rules("", "BIS")))

    def test_row_rules_filter_category_and_expose_notification_and_tracking(self):
        rules = parse_keyword_condition_rules(
            [
                {"keyword": "수원", "operator": "and", "categories": ["service", "goods"], "targets": ["bid_lifecycle"], "enabled": True},
                {"keyword": "BIS", "operator": "or", "categories": ["service", "goods"], "targets": ["bid_lifecycle"], "enabled": True},
                {"keyword": "유지보수", "operator": "exclude", "categories": ["service"], "targets": ["bid_lifecycle"], "enabled": True},
            ]
        )
        matched = match_keyword_rule_details(self._bid("수원 BIS 구축"), rules)
        self.assertEqual(("수원", "BIS"), matched.keywords)
        self.assertTrue(matched.notify)
        self.assertFalse(matched.track)
        self.assertIsNone(match_keyword_rule_details(self._bid("수원 BIS 유지보수"), rules))

    def test_disabled_row_is_not_included_in_monitoring(self):
        rules = parse_keyword_condition_rules(
            [{"keyword": "BIS", "operator": "or", "categories": ["service"], "targets": ["bid_lifecycle"], "enabled": False}]
        )
        self.assertIsNone(match_keyword_rule_details(self._bid("BIS 구축"), rules))

    def test_prespec_and_bid_lifecycle_are_separate_targets(self):
        rules = parse_keyword_condition_rules(
            [{"keyword": "BIS", "operator": "or", "categories": ["service"], "targets": ["prespec"], "enabled": True}]
        )
        self.assertIsNone(match_keyword_rule_details(self._bid("BIS 구축"), rules, "bid"))
        self.assertIsNotNone(match_keyword_rule_details(self._bid("BIS 구축"), rules, "prespec"))


if __name__ == "__main__":
    unittest.main()
