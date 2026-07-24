from .bid_api import fetch_all_pages
from ..model.entities import Bid


BASE_URL = "https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService"

ENDPOINTS = {
    "service": "/getCntrctProcssIntgOpenServc",
    "goods": "/getCntrctProcssIntgOpenThng",
    "works": "/getCntrctProcssIntgOpenCnstwk",
    "etc": "/getCntrctProcssIntgOpenFrgcpt",
}


class ContractProcessApi:
    def __init__(self, api_key, timeout_seconds=30, num_of_rows=100):
        self.api_key = "".join((api_key or "").split())
        self.timeout_seconds = timeout_seconds
        self.num_of_rows = num_of_rows

    def find_bid_for_pre_specification(self, pre_spec_no, category):
        endpoint = ENDPOINTS.get(category, ENDPOINTS["service"])
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": str(self.num_of_rows),
            "inqryDiv": "1",
            "bfSpecRgstNo": pre_spec_no,
            "type": "json",
        }
        items, _total_count = fetch_all_pages(
            BASE_URL + endpoint,
            params,
            self.timeout_seconds,
            "나라장터 계약과정통합공개 API",
        )
        candidates = []
        for item in items:
            bid_no = _first(item, "bidNtceNo", "bidPbancNo")
            if not bid_no:
                continue
            candidates.append(
                Bid(
                    category=category,
                    title=_first(item, "bidNtceNm", "bidPbancNm", "bfSpecNm"),
                    bid_no=bid_no,
                    bid_ord=_first(item, "bidNtceOrd", "bidPbancOrd"),
                    agency=_first(item, "ntceInsttNm", "ordInsttNm"),
                    demand_agency=_first(item, "dminsttNm", "dmndInsttNm"),
                    link=_first(item, "bidNtceDtlUrl", "detailUrl"),
                    bid_method=_first(item, "bidMethdNm"),
                    contract_method=_first(item, "cntrctCnclsMthdNm"),
                    budget_amount=_first(item, "presmptPrce", "asignBdgtAmt"),
                    bid_start_datetime=_first(item, "bidBeginDt"),
                    bid_end_datetime=_first(item, "bidClseDt"),
                    opening_datetime=_first(item, "opengDt"),
                    raw=item,
                )
            )
        if not candidates:
            return None
        candidates = list(
            {candidate.unique_id: candidate for candidate in candidates}.values()
        )
        return max(candidates, key=lambda bid: _order_key(bid.bid_ord))


def _first(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _order_key(value):
    text = str(value or "")
    return int(text) if text.isdigit() else -1
