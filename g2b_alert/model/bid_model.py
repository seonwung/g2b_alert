from datetime import datetime, timedelta

from .entities import CATEGORY_LABELS
from .keyword_matcher import (
    KeywordRules,
    match_keyword_rule_details,
    match_keywords,
)


class BidMonitorService:
    """Run one bid-monitoring cycle without threads or UI callbacks."""

    def __init__(self, bid_api, bid_repository, pre_spec_api=None):
        self.bid_api = bid_api
        self.bid_repository = bid_repository
        self.pre_spec_api = pre_spec_api

    def check_once(
        self,
        config,
        keywords,
        checked_at=None,
        *,
        use_last_check=True,
        record_cycle=True,
        skip_seen=True,
        mark_seen=None,
    ):
        if mark_seen is None:
            mark_seen = skip_seen
        checked_at = checked_at or datetime.now()
        begin_time = self._get_begin_time(config, checked_at, use_last_check=use_last_check)
        alerts = []
        category_reports = []
        all_success = True

        for category in config.selected_categories:
            if self._target_enabled(keywords, category, "bid_lifecycle", fallback=True):
                source_alerts, report = self._check_bid_category(
                    category,
                    begin_time,
                    checked_at,
                    keywords,
                    skip_seen,
                    mark_seen,
                )
                alerts.extend(source_alerts)
                category_reports.append(report)
                all_success = all_success and report["status"] == "success"

            prespec_enabled = self._target_enabled(
                keywords,
                category,
                "prespec",
                fallback=bool(getattr(config, "prespec_search_enabled", False)),
            )
            if prespec_enabled and self.pre_spec_api:
                source_alerts, report = self._check_prespec_category(
                    category,
                    begin_time,
                    checked_at,
                    keywords,
                    skip_seen,
                    mark_seen,
                )
                alerts.extend(source_alerts)
                category_reports.append(report)
                all_success = all_success and report["status"] == "success"

        if all_success and record_cycle:
            self.bid_repository.set_last_check_time(checked_at.isoformat())

        return {
            "checked_at": checked_at,
            "begin_time": begin_time,
            "all_success": all_success,
            "alerts": alerts,
            "new_alert_count": sum(1 for alert in alerts if alert.get("notify", True)),
            "category_reports": category_reports,
        }

    def _check_bid_category(
        self,
        category,
        begin_time,
        checked_at,
        keywords,
        skip_seen,
        mark_seen,
    ):
        label = CATEGORY_LABELS.get(category, category)
        try:
            bids = self.bid_api.fetch_bids(category, begin_time, checked_at)
            total_count = self.bid_api.last_total_count
        except Exception as error:
            return [], {
                "category": category,
                "label": label,
                "status": "failed",
                "error": error,
            }

        alerts = []
        for bid in bids:
            if not bid.bid_no or (
                skip_seen and self.bid_repository.is_bid_seen(bid.unique_id)
            ):
                continue
            match = self._match_item(bid, keywords, "bid")
            if not match:
                continue
            if mark_seen:
                self.bid_repository.mark_bid_seen(bid.unique_id)
            alerts.append(
                {
                    "bid": bid,
                    "matched_keywords": match["keywords"],
                    "matched_rule_ids": match.get("rule_ids", []),
                    "matched_rule_names": match.get("rule_names", []),
                    "notify": match["notify"],
                    "track": match["track"],
                }
            )
        return alerts, {
            "category": category,
            "label": label,
            "status": "success",
            "count": len(bids),
            "total_count": total_count,
        }

    def _check_prespec_category(
        self,
        category,
        begin_time,
        checked_at,
        keywords,
        skip_seen,
        mark_seen,
    ):
        label = f"사전규격·{CATEGORY_LABELS.get(category, category)}"
        try:
            pre_specs = self.pre_spec_api.fetch_pre_specifications(
                category,
                begin_time,
                checked_at,
            )
            total_count = self.pre_spec_api.last_total_count
        except Exception as error:
            return [], {
                "category": category,
                "label": label,
                "status": "failed",
                "error": error,
            }

        alerts = []
        for pre_spec in pre_specs:
            if not pre_spec.pre_spec_no or (
                skip_seen and self.bid_repository.is_bid_seen(pre_spec.unique_id)
            ):
                continue
            match = self._match_item(pre_spec, keywords, "prespec")
            if not match:
                continue
            if mark_seen:
                self.bid_repository.mark_bid_seen(pre_spec.unique_id)
            alerts.append(
                {
                    "bid": pre_spec,
                    "matched_keywords": match["keywords"],
                    "matched_rule_ids": match.get("rule_ids", []),
                    "matched_rule_names": match.get("rule_names", []),
                    "notify": match["notify"],
                    "track": False,
                }
            )
        return alerts, {
            "category": category,
            "label": label,
            "status": "success",
            "count": len(pre_specs),
            "total_count": total_count,
        }

    @staticmethod
    def _match_item(item, keywords, source):
        if isinstance(keywords, KeywordRules):
            match = match_keyword_rule_details(item, keywords, source)
            if not match:
                return None
            return {
                "keywords": list(match.keywords),
                "notify": match.notify,
                "track": match.track,
                "rule_ids": list(match.rule_ids),
                "rule_names": list(match.rule_names),
            }
        matched_keywords = match_keywords(item, keywords)
        if not matched_keywords:
            return None
        return {"keywords": matched_keywords, "notify": True, "track": False, "rule_ids": [], "rule_names": []}

    @staticmethod
    def _target_enabled(keywords, category, target, fallback=False):
        if not isinstance(keywords, KeywordRules) or not keywords.conditions:
            return fallback
        return any(
            category in condition.categories and target in condition.targets
            for condition in keywords.conditions
        )

    def _get_begin_time(self, config, checked_at, use_last_check=True):
        last_check_text = self.bid_repository.get_last_check_time() if use_last_check else ""
        if last_check_text:
            try:
                last_check = datetime.fromisoformat(last_check_text)
                return last_check - timedelta(minutes=int(config.overlap_minutes))
            except (TypeError, ValueError):
                pass
        return checked_at - timedelta(minutes=int(config.bootstrap_minutes))
