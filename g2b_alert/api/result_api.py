from .bid_api import fetch_all_pages
from ..model.entities import BidResult


RESULT_BASE_URL = "https://apis.data.go.kr/1230000/as/ScsbidInfoService"

RESULT_ENDPOINTS = {
    "service": "/getOpengResultListInfoServc",
    "goods": "/getOpengResultListInfoThng",
    "works": "/getOpengResultListInfoCnstwk",
    "etc": "/getOpengResultListInfoEtc",
}


def first_value(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def split_opening_company_info(value):
    """Split the API's ``업체명^사업자번호^대표자명`` summary field."""
    parts = [part.strip() for part in str(value or "").split("^")]
    company_name = parts[0] if parts else ""
    business_number = parts[1] if len(parts) > 1 else ""
    return company_name, business_number


class ResultApiService:
    def __init__(self, api_key, timeout_seconds=30, num_of_rows=100):
        self.api_key = "".join((api_key or "").split())
        self.timeout_seconds = timeout_seconds
        self.num_of_rows = num_of_rows

    def fetch_results(self, saved_bid):
        category = saved_bid.category or "service"
        endpoint = RESULT_ENDPOINTS.get(category, RESULT_ENDPOINTS["service"])
        url = RESULT_BASE_URL + endpoint
        params = {
            "serviceKey": self.api_key,
            "bidNtceNo": saved_bid.bid_no,
            "bidNtceOrd": saved_bid.bid_ord or "",
            "inqryDiv": "4",
            "pageNo": "1",
            "numOfRows": str(self.num_of_rows),
            "type": "json",
        }
        items, _total_count = fetch_all_pages(
            url,
            params,
            self.timeout_seconds,
            "나라장터 낙찰정보 API",
        )
        results = [self._normalize(item) for item in items]
        return list({result.result_key: result for result in results}.values())

    def _normalize(self, item):
        opening_company_name, opening_business_number = split_opening_company_info(
            item.get("opengCorpInfo")
        )
        return BidResult(
            result_type=first_value(item, "rsltTyNm", "opengRsltDivNm", "bidClsfcNoNm", "bidNtceNm"),
            opening_datetime=first_value(item, "rlOpengDt", "inptDt", "opengDt", "opengDate"),
            successful_bidder_name=first_value(
                item,
                "sucsfbidCorpNm",
                "fnlSucsfCorpNm",
                "bidwinnrNm",
                "prcbdrNm",
                "entrpsNm",
            ) or opening_company_name,
            business_number=first_value(
                item,
                "sucsfbidBizrno",
                "fnlSucsfBizrno",
                "bizrno",
                "prcbdrBizrno",
            ) or opening_business_number,
            successful_bid_amount=first_value(
                item,
                "sucsfbidAmt",
                "fnlSucsfAmt",
                "bidprcAmt",
                "bidAmt",
            ),
            successful_bid_rate=first_value(item, "sucsfbidRate", "bidRate", "sucsfbidLwltRate"),
            ranking=first_value(item, "bidRank", "rank", "prcbdrRank"),
            result_status=first_value(
                item,
                "bidwinnrSlctnAplBssNm",
                "opengRsltNm",
                "rsltSttusNm",
                "bidResultNm",
                "progrsDivCdNm",
            ),
            raw=item,
        )
