import re
from dataclasses import dataclass


def normalize(text):
    text = str(text).lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[-_/.,(){}\[\]:;]", "", text)
    return text.strip()


def parse_keywords(raw_text):
    raw_text = raw_text.replace("\n", ",")
    return [keyword.strip() for keyword in raw_text.split(",") if keyword.strip()]


@dataclass(frozen=True)
class KeywordRules:
    and_keywords: tuple[str, ...] = ()
    or_keywords: tuple[str, ...] = ()
    exclude_keywords: tuple[str, ...] = ()
    conditions: tuple["KeywordCondition", ...] = ()

    @property
    def positive_keywords(self):
        return self.and_keywords + self.or_keywords


@dataclass(frozen=True)
class KeywordCondition:
    keyword: str
    rule_id: str = ""
    name: str = ""
    operator: str = "or"
    categories: tuple[str, ...] = ("service", "goods", "works", "etc")
    targets: tuple[str, ...] = ("bid_lifecycle",)


@dataclass(frozen=True)
class KeywordMatch:
    keywords: tuple[str, ...]
    rule_ids: tuple[str, ...] = ()
    rule_names: tuple[str, ...] = ()
    notify: bool = True
    track: bool = False


def parse_keyword_rules(and_text="", or_text="", exclude_text=""):
    return KeywordRules(
        and_keywords=tuple(parse_keywords(and_text or "")),
        or_keywords=tuple(parse_keywords(or_text or "")),
        exclude_keywords=tuple(parse_keywords(exclude_text or "")),
    )


def parse_keyword_condition_rules(rows):
    conditions = []
    for row in rows or []:
        if not bool(row.get("enabled", True)):
            continue
        operator = str(row.get("operator", "or") or "or").lower()
        if operator not in {"and", "or", "exclude"}:
            operator = "or"
        categories = row.get("categories")
        if not isinstance(categories, (list, tuple)):
            legacy_category = str(row.get("category", "all") or "all").lower()
            categories = (
                ("service", "goods", "works", "etc")
                if legacy_category == "all"
                else (legacy_category,)
            )
        categories = tuple(
            category
            for category in categories
            if category in {"service", "goods", "works", "etc"}
        )
        targets = row.get("targets")
        if not isinstance(targets, (list, tuple)):
            legacy_target = str(row.get("target", "bid") or "bid").lower()
            targets = ("prespec",) if legacy_target == "prespec" else ("bid_lifecycle",)
        targets = tuple(
            target for target in targets if target in {"prespec", "bid_lifecycle"}
        )
        for keyword in parse_keywords(str(row.get("keyword", "") or "")):
            conditions.append(
                KeywordCondition(
                    rule_id=str(row.get("id") or ""),
                    name=str(row.get("name") or row.get("keyword") or ""),
                    keyword=keyword,
                    operator=operator,
                    categories=categories,
                    targets=targets,
                )
            )
    return KeywordRules(
        and_keywords=tuple(row.keyword for row in conditions if row.operator == "and"),
        or_keywords=tuple(row.keyword for row in conditions if row.operator == "or"),
        exclude_keywords=tuple(row.keyword for row in conditions if row.operator == "exclude"),
        conditions=tuple(conditions),
    )


def match_keyword_rule_details(item, rules, source="bid"):
    if not rules.conditions:
        keywords = match_keyword_rules(item, rules)
        return KeywordMatch(tuple(keywords)) if keywords else None

    category = str(getattr(item, "category", "") or "").lower()
    applicable = [
        row
        for row in rules.conditions
        if category in row.categories
        and (
            (source == "prespec" and "prespec" in row.targets)
            or (source == "bid" and "bid_lifecycle" in row.targets)
        )
    ]
    if not applicable:
        return None

    search_text = normalize(
        " ".join(
            [
                getattr(item, "title", ""),
                getattr(item, "agency", ""),
                getattr(item, "demand_agency", ""),
            ]
        )
    )
    excluded = [row for row in applicable if row.operator == "exclude"]
    if any(normalize(row.keyword) in search_text for row in excluded):
        return None

    and_rows = [row for row in applicable if row.operator == "and"]
    or_rows = [row for row in applicable if row.operator == "or"]
    matched_and = [row for row in and_rows if normalize(row.keyword) in search_text]
    matched_or = [row for row in or_rows if normalize(row.keyword) in search_text]
    if len(matched_and) != len(and_rows) or (or_rows and not matched_or):
        return None
    matched = matched_and + matched_or
    if not matched:
        return None
    return KeywordMatch(
        keywords=tuple(row.keyword for row in matched),
        rule_ids=tuple(dict.fromkeys(row.rule_id for row in matched if row.rule_id)),
        rule_names=tuple(dict.fromkeys(row.name for row in matched if row.name)),
        notify=True,
        track=False,
    )


def match_keyword_rules(bid, rules):
    search_text = f"{bid.title} {bid.agency} {bid.demand_agency}"
    normalized_search_text = normalize(search_text)
    if any(normalize(keyword) in normalized_search_text for keyword in rules.exclude_keywords):
        return []
    if rules.and_keywords and not all(
        normalize(keyword) in normalized_search_text for keyword in rules.and_keywords
    ):
        return []
    matched_or = [
        keyword for keyword in rules.or_keywords if normalize(keyword) in normalized_search_text
    ]
    if rules.or_keywords and not matched_or:
        return []
    if not rules.and_keywords and not rules.or_keywords:
        return []
    return list(rules.and_keywords) + matched_or


def match_keywords(bid, keywords):
    return match_keyword_rules(bid, KeywordRules(or_keywords=tuple(keywords)))
