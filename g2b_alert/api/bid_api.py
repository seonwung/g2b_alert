from datetime import datetime
import re
from urllib.parse import parse_qs, unquote, urlparse

from .http_client import request_json
from ..model.entities import Bid, CATEGORY_LABELS


BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"

ENDPOINTS = {
    "service": "/getBidPblancListInfoServc",
    "goods": "/getBidPblancListInfoThng",
    "works": "/getBidPblancListInfoCnstwk",
    "etc": "/getBidPblancListInfoEtc",
}


def parse_items(data):
    body = data.get("response", {}).get("body", {})
    items = body.get("items", [])

    if items is None or items == "":
        return []
    if isinstance(items, dict):
        return items.get("item", [items])
    if isinstance(items, list):
        return items
    return []


def parse_total_count(data):
    value = data.get("response", {}).get("body", {}).get("totalCount", 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def split_bid_reference(bid_reference):
    """Split a user-facing ``공고번호-차수`` value for the G2B API."""
    bid_reference = extract_bid_reference(bid_reference)
    match = re.fullmatch(r"(.+)-(\d{3})", bid_reference)
    if match:
        return match.group(1), match.group(2)
    return bid_reference, ""


def extract_bid_reference(value):
    """Extract a bid number and optional order from pasted text or a G2B URL."""
    text = unquote(str(value or "")).strip()
    if not text:
        return ""

    parsed = urlparse(text)
    if parsed.scheme and parsed.netloc:
        query = parse_qs(parsed.query)
        lowered = {key.lower(): values for key, values in query.items()}
        bid_no = _first_query_value(
            lowered,
            "bidntceno",
            "bidpbancno",
            "bidnoticeno",
        )
        bid_ord = _first_query_value(
            lowered,
            "bidntceord",
            "bidpbancord",
            "bidnoticeord",
        )
        if bid_no:
            return f"{bid_no}-{bid_ord}" if re.fullmatch(r"\d{3}", bid_ord or "") else bid_no
        text = f"{parsed.path} {parsed.query} {parsed.fragment}"

    compact = re.sub(r"\s+", "", text)
    reference_match = re.search(r"([A-Za-z]\d{2}[A-Za-z]{2}\d+)(?:-(\d{3}))?", compact)
    if reference_match:
        bid_no, bid_ord = reference_match.groups()
        return f"{bid_no}-{bid_ord}" if bid_ord else bid_no
    return compact


def _first_query_value(query, *keys):
    for key in keys:
        values = query.get(key) or []
        if values and str(values[0]).strip():
            return str(values[0]).strip()
    return ""


class G2BClient:
    def __init__(self, api_key, timeout_seconds=30, num_of_rows=100):
        self.api_key = "".join(api_key.split())
        self.timeout_seconds = timeout_seconds
        self.num_of_rows = num_of_rows
        self.last_total_count = 0

    def fetch_bids(self, category, begin_time: datetime, end_time: datetime):
        url = BASE_URL + ENDPOINTS[category]
        params = {
            "serviceKey": self.api_key,
            "inqryDiv": "1",
            "inqryBgnDt": begin_time.strftime("%Y%m%d%H%M"),
            "inqryEndDt": end_time.strftime("%Y%m%d%H%M"),
            "pageNo": "1",
            "numOfRows": str(self.num_of_rows),
            "type": "json",
        }

        data = request_json(url, params, self.timeout_seconds, "나라장터 입찰공고 API")
        self.last_total_count = parse_total_count(data)
        return [self._to_bid_item(category, item) for item in parse_items(data)]

    def fetch_bid_by_no(self, bid_reference, category_hint=None):
        bid_no, bid_ord = split_bid_reference(bid_reference)
        if not bid_no:
            return None

        categories = [category_hint] if category_hint in ENDPOINTS else list(ENDPOINTS)
        candidates = []
        for category in categories:
            url = BASE_URL + ENDPOINTS[category]
            params = {
                "serviceKey": self.api_key,
                "inqryDiv": "2",
                "bidNtceNo": bid_no,
                "pageNo": "1",
                "numOfRows": str(self.num_of_rows),
                "type": "json",
            }
            data = request_json(url, params, self.timeout_seconds, "나라장터 입찰공고 API")
            for item in parse_items(data):
                found = self._to_bid_item(category, item)
                if found.bid_no != bid_no:
                    continue
                if bid_ord and found.bid_ord and found.bid_ord != bid_ord:
                    continue
                candidates.append(found)
        if not candidates:
            return None
        if bid_ord:
            return candidates[0]
        return max(candidates, key=lambda bid: _bid_order_sort_key(bid.bid_ord))

    def _to_bid_item(self, category, item):
        return Bid(
            category=category,
            title=item.get("bidNtceNm", ""),
            bid_no=item.get("bidNtceNo", ""),
            bid_ord=item.get("bidNtceOrd", ""),
            agency=item.get("ntceInsttNm", ""),
            demand_agency=item.get("dminsttNm", ""),
            link=item.get("bidNtceDtlUrl", ""),
            bid_method=item.get("bidMethdNm", ""),
            contract_method=item.get("cntrctCnclsMthdNm", ""),
            budget_amount=item.get("presmptPrce", "") or item.get("asignBdgtAmt", ""),
            bid_start_datetime=item.get("bidBeginDt", ""),
            bid_end_datetime=item.get("bidClseDt", ""),
            opening_datetime=item.get("opengDt", ""),
            raw=item,
        )


def _bid_order_sort_key(value):
    text = str(value or "")
    return int(text) if text.isdigit() else -1
