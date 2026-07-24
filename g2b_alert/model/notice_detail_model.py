import re

from .notice_version_model import compare_latest_versions


def format_amount(value):
    """Format a numeric amount with thousands separators."""
    text = str(value or "").strip()
    if not text:
        return "-"
    suffix = ""
    if text.endswith("원"):
        text = text[:-1].strip()
        suffix = "원"
    normalized = text.replace(",", "").replace(" ", "")
    if re.fullmatch(r"[+-]?\d+", normalized):
        return f"{int(normalized):,}{suffix}"
    if re.fullmatch(r"[+-]?\d+\.\d+", normalized):
        integer, fraction = normalized.split(".", 1)
        return f"{int(integer):,}.{fraction}{suffix}"
    return str(value)


def format_datetime(value):
    """Return a compact, human-readable date/time without ISO's T separator."""
    text = str(value or "").strip()
    if not text:
        return "-"
    iso_match = re.match(
        r"^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2}))?",
        text,
    )
    if iso_match:
        year, month, day, hour, minute = iso_match.groups()
        if hour is not None:
            return f"{year}-{month}-{day} {hour}:{minute}"
        return f"{year}-{month}-{day}"
    compact = re.sub(r"\D", "", text)
    if len(compact) >= 12:
        return (
            f"{compact[:4]}-{compact[4:6]}-{compact[6:8]} "
            f"{compact[8:10]}:{compact[10:12]}"
        )
    if len(compact) == 8:
        return f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}"
    return text.replace("T", " ")


def format_product_details(value):
    """Turn G2B's caret-delimited product list into readable lines."""
    text = str(value or "").strip()
    if not text or text == "-":
        return "-"
    records = re.findall(r"\[([^\]]+)\]", text)
    if not records:
        records = [
            item
            for item in re.split(r"\^{2,}|\r?\n", text)
            if item.strip()
        ]
    lines = []
    for record in records:
        fields = [
            field.strip(" []")
            for field in str(record).split("^")
            if field.strip(" []")
        ]
        if len(fields) >= 3 and fields[0].isdigit():
            sequence, product_number = fields[0], fields[1]
            product_name = " · ".join(fields[2:])
            line = f"{sequence}. {product_name}"
            if product_number:
                line += f" (품목번호 {product_number})"
            lines.append(line)
        else:
            cleaned = " · ".join(fields)
            if cleaned:
                lines.append(cleaned)
    return "\n".join(lines) or text.replace("^", " · ")


def _format_comparison_values(comparison):
    amount_tokens = ("금액", "가격", "예산", "추정가")
    date_tokens = ("일시", "일자", "마감", "시작", "종료")
    formatted = dict(comparison or {})
    formatted["changes"] = [
        {
            **change,
            "before": (
                format_amount(change.get("before"))
                if any(token in str(change.get("label", "")) for token in amount_tokens)
                else (
                    format_datetime(change.get("before"))
                    if any(token in str(change.get("label", "")) for token in date_tokens)
                    else change.get("before")
                )
            ),
            "after": (
                format_amount(change.get("after"))
                if any(token in str(change.get("label", "")) for token in amount_tokens)
                else (
                    format_datetime(change.get("after"))
                    if any(token in str(change.get("label", "")) for token in date_tokens)
                    else change.get("after")
                )
            ),
        }
        for change in (comparison or {}).get("changes", [])
    ]
    return formatted


def build_notice_detail(
    saved_bid,
    versions,
    results,
    comparison,
    recipient_count=0,
    pre_spec_detail=None,
):
    raw = saved_bid.raw or {}
    current_version = comparison.get("current") or (versions[-1] if versions else {})
    current_raw = (
        (pre_spec_detail or {}).get("raw")
        or current_version.get("raw")
        or raw
    )
    is_pre_spec = bool(
        getattr(saved_bid, "pre_spec_no", "")
        and getattr(saved_bid, "status", "") == "pre_spec"
    )
    opinions = list((pre_spec_detail or {}).get("opinions") or [])
    basic_rows = [
        ("사업명", saved_bid.title),
        ("현재 단계", saved_bid.stage_label()),
        ("사전규격등록번호", getattr(saved_bid, "pre_spec_no", "")),
        ("공고번호", "" if is_pre_spec else saved_bid.bid_no),
        ("차수", "" if is_pre_spec else saved_bid.bid_ord or "000"),
        ("공고 종류", saved_bid.category_label),
        ("업무구분", _first(current_raw, "bsnsDivNm")),
        ("참조번호", _first(current_raw, "refNo")),
        ("공고기관", saved_bid.agency),
        ("수요기관", saved_bid.demand_agency),
        ("사업금액", format_amount(saved_bid.budget_amount)),
        (
            "품목상세",
            format_product_details(_first(current_raw, "prdctDtlList")),
        ),
        ("담당자", _first(current_raw, "ofclNm")),
        ("담당자 연락처", _first(current_raw, "ofclTelNo")),
        ("관련 입찰공고번호", _first(current_raw, "bidNtceNoList")),
        ("계약방법", saved_bid.contract_method),
        ("입찰방식", saved_bid.bid_method),
        ("추적 상태", "추적 중" if saved_bid.monitoring_enabled else "중지"),
        ("이메일 수신자", f"{recipient_count}명"),
        ("저장일시", format_datetime(saved_bid.saved_at)),
    ]
    schedule_rows = [
        ("사전규격 공개일시", format_datetime(_first(current_raw, "rgstDt", "bfSpecRgstDt"))),
        ("접수일시", format_datetime(_first(current_raw, "rcptDt"))),
        ("의견 제출 시작", format_datetime(saved_bid.bid_start_datetime)),
        (
            "의견 제출 마감",
            format_datetime(
                _first(
                    current_raw,
                    "opninRgstClseDt",
                    "opnnSbmsnClseDt",
                    "bfSpecOpnnClseDt",
                )
                if is_pre_spec
                else saved_bid.bid_end_datetime
            ),
        ),
        ("납품기한", format_datetime(_first(current_raw, "dlvrTmlmtDt"))),
        ("납품일수", _first(current_raw, "dlvrDaynum")),
    ] if is_pre_spec else [
        ("입찰서 제출 시작", format_datetime(saved_bid.bid_start_datetime)),
        ("입찰서 제출 마감", format_datetime(saved_bid.bid_end_datetime)),
        (
            "제안서 제출 마감",
            format_datetime(
                _first(
                    current_raw,
                    "prpslDocRcptEndDt",
                    "prpslEndDt",
                    "presntnOprtnDt",
                )
            ),
        ),
        (
            "공동수급협정서 마감",
            format_datetime(
                current_version.get("consortium_close_at")
                or _first(
                    current_raw,
                    "cmmnSpldmdAgrmntClseDt",
                    "cmmnSpldmdAgrmntDocRcptDt",
                )
            ),
        ),
        ("개찰일시", format_datetime(saved_bid.opening_datetime)),
        ("개찰장소", _first(current_raw, "opengPlce", "opengPlace")),
        ("공고 등록일시", format_datetime(_first(current_raw, "rgstDt", "bidNtceDt"))),
    ]
    main_kind = "사전규격 첨부" if is_pre_spec else "공고 첨부"
    attachments = [
        {"kind": main_kind, **attachment}
        for attachment in extract_attachments(current_raw)
    ]
    for index, opinion in enumerate(opinions, start=1):
        opinion_no = opinion.get("opinion_no") or str(index)
        attachments.extend(
            {"kind": f"의견 {opinion_no} 첨부", **attachment}
            for attachment in extract_attachments(opinion.get("raw"))
        )
    return {
        "title": saved_bid.title or saved_bid.bid_no,
        "stage": saved_bid.stage_label(),
        "reference": (
            f"사전규격 {getattr(saved_bid, 'pre_spec_no', '')}"
            if is_pre_spec
            else f"{saved_bid.bid_no}-{saved_bid.bid_ord or '000'}"
        ),
        "link": saved_bid.link,
        "basic_rows": basic_rows,
        "schedule_rows": schedule_rows,
        "opinion_summary_rows": [
            ("사전규격등록번호", getattr(saved_bid, "pre_spec_no", "")),
            ("의견 제출 마감", format_datetime(_first(current_raw, "opninRgstClseDt"))),
            ("등록된 의견", f"{len(opinions)}건"),
        ],
        "opinions": opinions,
        "results": [
            {
                "status": result.get("result_status") or "-",
                "company": result.get("successful_bidder_name") or "-",
                "business_number": result.get("business_number") or "-",
                "amount": format_amount(result.get("successful_bid_amount")),
                "rate": result.get("successful_bid_rate") or "-",
                "ranking": result.get("ranking") or "-",
                "opening_at": format_datetime(result.get("opening_datetime")),
                "detected_at": format_datetime(result.get("detected_at")),
            }
            for result in results
        ],
        "attachments": attachments,
        "versions": versions,
        "version_comparisons": [
            _format_comparison_values(
                compare_latest_versions(versions[: index + 1])
            )
            for index in range(len(versions))
        ],
        "comparison": _format_comparison_values(comparison),
    }


def extract_attachments(raw):
    raw = raw or {}
    names = {}
    urls = {}
    for key, value in raw.items():
        if value in (None, ""):
            continue
        lowered = str(key).lower()
        suffix_match = re.search(r"(\d+)$", lowered)
        suffix = suffix_match.group(1) if suffix_match else lowered
        if any(token in lowered for token in ("filename", "filenm", "docnm", "specfilenm")):
            names[suffix] = str(value).strip()
        elif any(token in lowered for token in ("fileurl", "docurl", "specdocurl", "atchurl")):
            urls[suffix] = str(value).strip()

    attachments = []
    seen_urls = set()
    for suffix in dict.fromkeys((*names.keys(), *urls.keys())):
        url = urls.get(suffix, "").strip()
        if url and url in seen_urls:
            continue
        name = names.get(suffix) or _filename_from_url(url)
        if not name or name.casefold() in {"downloadfile.do", "download.do"}:
            name = f"첨부파일 {suffix}" if str(suffix).isdigit() else "첨부파일"
        attachments.append({"name": name, "url": url})
        if url:
            seen_urls.add(url)
    return attachments


def _filename_from_url(url):
    text = str(url or "").split("?", 1)[0].rstrip("/")
    return text.rsplit("/", 1)[-1] if "/" in text else ""


def _first(raw, *keys):
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return str(value)
    return "-"
