from dataclasses import dataclass
from datetime import datetime

import requests


BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"

CATEGORY_LABELS = {
    "service": "\uc6a9\uc5ed",
    "goods": "\ubb3c\ud488",
    "works": "\uacf5\uc0ac",
    "etc": "\uae30\ud0c0",
}

ENDPOINTS = {
    "service": "/getBidPblancListInfoServc",
    "goods": "/getBidPblancListInfoThng",
    "works": "/getBidPblancListInfoCnstwk",
    "etc": "/getBidPblancListInfoEtc",
}


@dataclass
class BidItem:
    category: str
    title: str
    bid_no: str
    bid_ord: str
    agency: str
    demand_agency: str
    link: str

    @property
    def category_label(self):
        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def unique_id(self):
        return f"{self.bid_no}_{self.bid_ord or '000'}"


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


class G2BClient:
    def __init__(self, api_key, timeout_seconds=30, num_of_rows=100):
        self.api_key = "".join(api_key.split())
        self.timeout_seconds = timeout_seconds
        self.num_of_rows = num_of_rows

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

        response = requests.get(url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        return [self._to_bid_item(category, item) for item in parse_items(response.json())]

    def _to_bid_item(self, category, item):
        return BidItem(
            category=category,
            title=item.get("bidNtceNm", ""),
            bid_no=item.get("bidNtceNo", ""),
            bid_ord=item.get("bidNtceOrd", ""),
            agency=item.get("ntceInsttNm", ""),
            demand_agency=item.get("dminsttNm", ""),
            link=item.get("bidNtceDtlUrl", ""),
        )
