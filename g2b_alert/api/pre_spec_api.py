import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, parse_qsl, unquote, urlencode, urlparse, urlunparse

import requests

from .bid_api import parse_items, parse_total_count
from .http_client import request_json
from ..model.entities import PreSpecification


BASE_URL = "https://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService"

ENDPOINTS = {
    "service": "/getPublicPrcureThngInfoServcPPSSrch",
    "goods": "/getPublicPrcureThngInfoThngPPSSrch",
    "works": "/getPublicPrcureThngInfoCnstwkPPSSrch",
    "etc": "/getPublicPrcureThngInfoFrgcptPPSSrch",
}

OPINION_ENDPOINTS = {
    "service": "/getPublicPrcureThngOpinionInfoServc",
    "goods": "/getPublicPrcureThngOpinionInfoThng",
    "works": "/getPublicPrcureThngOpinionInfoCnstwk",
    "etc": "/getPublicPrcureThngOpinionInfoFrgcpt",
}


class PreSpecificationApi:
    def __init__(self, api_key, timeout_seconds=30, num_of_rows=100):
        self.api_key = "".join((api_key or "").split())
        self.timeout_seconds = timeout_seconds
        self.num_of_rows = num_of_rows
        self.last_total_count = 0

    def fetch_pre_specifications(self, category, begin_time, end_time):
        endpoint = ENDPOINTS[category]
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": str(self.num_of_rows),
            "inqryDiv": "1",
            "inqryBgnDt": begin_time.strftime("%Y%m%d%H%M"),
            "inqryEndDt": end_time.strftime("%Y%m%d%H%M"),
            "type": "json",
        }
        data = request_json(
            BASE_URL + endpoint,
            params,
            self.timeout_seconds,
            "나라장터 사전규격 API",
        )
        self.last_total_count = parse_total_count(data)
        return [self._normalize(category, item) for item in parse_items(data)]

    def fetch_pre_specification_by_no(self, reference, category_hint=None):
        pre_spec_no = extract_pre_spec_reference(reference)
        if not pre_spec_no:
            return None

        categories = [category_hint] if category_hint in ENDPOINTS else list(ENDPOINTS)
        for category in categories:
            params = {
                "serviceKey": self.api_key,
                "pageNo": "1",
                "numOfRows": str(self.num_of_rows),
                "inqryDiv": "2",
                "bfSpecRgstNo": pre_spec_no,
                "type": "json",
            }
            data = request_json(
                BASE_URL + ENDPOINTS[category],
                params,
                self.timeout_seconds,
                "나라장터 사전규격 API",
            )
            self.last_total_count = parse_total_count(data)
            for item in parse_items(data):
                found = self._normalize(category, item)
                if found.pre_spec_no.casefold() == pre_spec_no.casefold():
                    return found
        return None

    def fetch_pre_specification_detail(self, reference, category_hint=None):
        pre_spec = self.fetch_pre_specification_by_no(reference, category_hint)
        if not pre_spec:
            return None

        raw = dict(pre_spec.raw or {})
        opinions = self.fetch_opinions(pre_spec.category, pre_spec.pre_spec_no)
        attachment_urls = []
        for index in range(1, 6):
            url_key = f"specDocFileUrl{index}"
            if raw.get(url_key):
                attachment_urls.append((raw, f"specDocFileNm{index}", raw[url_key]))
        for opinion in opinions:
            opinion_raw = opinion["raw"]
            for index in range(1, 6):
                url_key = f"specDocOpninFileUrl{index}"
                if opinion_raw.get(url_key):
                    opinion_raw[url_key] = complete_opinion_attachment_url(
                        opinion_raw[url_key],
                        opinion.get("opinion_no"),
                    )
                    attachment_urls.append(
                        (opinion_raw, f"specDocOpninFileNm{index}", opinion_raw[url_key])
                    )

        if attachment_urls:
            with ThreadPoolExecutor(max_workers=min(5, len(attachment_urls))) as executor:
                filenames = list(
                    executor.map(
                        lambda row: self._resolve_download_filename(row[2]),
                        attachment_urls,
                    )
                )
            for (target, name_key, _url), filename in zip(attachment_urls, filenames):
                if filename:
                    target[name_key] = filename

        return {"pre_spec": pre_spec, "raw": raw, "opinions": opinions}

    def fetch_opinions(self, category, pre_spec_no):
        endpoint = OPINION_ENDPOINTS.get(category)
        if not endpoint or not pre_spec_no:
            return []
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": str(self.num_of_rows),
            "inqryDiv": "2",
            "bfSpecRgstNo": pre_spec_no,
            "type": "json",
        }
        data = request_json(
            BASE_URL + endpoint,
            params,
            self.timeout_seconds,
            "나라장터 사전규격 의견 API",
        )
        return [self._normalize_opinion(item) for item in parse_items(data)]

    @staticmethod
    def _normalize_opinion(item):
        return {
            "opinion_no": _first(item, "opninNo"),
            "reply_no": _first(item, "rplyNo"),
            "title": _first(item, "opninTitl"),
            "organization": _first(item, "mkngCorpNm"),
            "author": _first(item, "mkrNm"),
            "submitted_at": _first(item, "inptDt"),
            "content": _first(item, "opninCntnts"),
            "raw": dict(item),
        }

    def _resolve_download_filename(self, url):
        try:
            response = requests.get(url, stream=True, timeout=self.timeout_seconds)
            response.raise_for_status()
            return filename_from_content_disposition(
                response.headers.get("Content-Disposition", "")
            )
        except requests.exceptions.RequestException:
            return ""
        finally:
            response_to_close = locals().get("response")
            if response_to_close is not None:
                response_to_close.close()

    @staticmethod
    def _normalize(category, item):
        return PreSpecification(
            category=category,
            title=_first(
                item,
                "bfSpecNm",
                "prdctClsfcNoNm",
                "prdctNm",
                "bizNm",
                "itemNm",
            ),
            pre_spec_no=_first(item, "bfSpecRgstNo"),
            agency=_first(item, "orderInsttNm", "ordInsttNm", "ntceInsttNm"),
            demand_agency=_first(
                item,
                "rlDminsttNm",
                "dminsttNm",
                "dmndInsttNm",
                "orderInsttNm",
                "ordInsttNm",
            ),
            link=_first(
                item,
                "bfSpecDtlUrl",
                "detailUrl",
                "g2bLink",
                "specDocFileUrl1",
            ),
            budget_amount=_first(item, "asignBdgtAmt", "bdgtAmt"),
            published_at=_first(item, "rgstDt", "bfSpecRgstDt", "rcptDt"),
            opinion_start_at=_first(item, "opnBgnDt", "opninRgstBgnDt"),
            opinion_end_at=_first(item, "opnEndDt", "opninRgstClseDt"),
            raw=item,
        )


def _first(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def extract_pre_spec_reference(value):
    text = unquote(str(value or "")).strip()
    if not text:
        return ""

    parsed = urlparse(text)
    if parsed.scheme and parsed.netloc:
        query = {key.casefold(): values for key, values in parse_qs(parsed.query).items()}
        for key in ("bfspecrgstno", "bfspecregno"):
            values = query.get(key) or []
            if values and str(values[0]).strip():
                return str(values[0]).strip()
        text = f"{parsed.path} {parsed.query} {parsed.fragment}"

    match = re.search(r"([A-Za-z]\d{2}BD\d+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return re.sub(r"\s+", "", text)


def looks_like_pre_spec_reference(value):
    reference = extract_pre_spec_reference(value)
    return bool(re.fullmatch(r"[A-Za-z]\d{2}BD\d+", reference, flags=re.IGNORECASE))


def filename_from_content_disposition(value):
    header = str(value or "")
    extended = re.search(r"filename\*\s*=\s*[^']*''([^;]+)", header, flags=re.IGNORECASE)
    if extended:
        return unquote(extended.group(1).strip().strip('"'))
    regular = re.search(r"filename\s*=\s*([^;]+)", header, flags=re.IGNORECASE)
    if not regular:
        return ""
    return unquote(regular.group(1).strip().strip('"'))


def complete_opinion_attachment_url(url, opinion_no):
    """Repair an incomplete BFOPNN URL returned by the G2B opinion API."""
    text = str(url or "").strip()
    number = str(opinion_no or "").strip()
    if not text or not number:
        return text

    parsed = urlparse(text)
    params = parse_qsl(parsed.query, keep_blank_values=True)
    names = {name.casefold() for name, _value in params}
    if "filetype" not in names or not any(
        name.casefold() == "filetype" and value.upper() == "BFOPNN"
        for name, value in params
    ):
        return text
    if "opnnsqno" not in names:
        params.append(("opnnSqno", number))
    return urlunparse(parsed._replace(query=urlencode(params)))
