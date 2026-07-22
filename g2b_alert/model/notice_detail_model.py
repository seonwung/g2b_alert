import re


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
        ("사업금액", saved_bid.budget_amount),
        ("품목상세", _first(current_raw, "prdctDtlList")),
        ("담당자", _first(current_raw, "ofclNm")),
        ("담당자 연락처", _first(current_raw, "ofclTelNo")),
        ("관련 입찰공고번호", _first(current_raw, "bidNtceNoList")),
        ("계약방법", saved_bid.contract_method),
        ("입찰방식", saved_bid.bid_method),
        ("추적 상태", "추적 중" if saved_bid.monitoring_enabled else "중지"),
        ("이메일 수신자", f"{recipient_count}명"),
        ("저장일시", saved_bid.saved_at),
    ]
    schedule_rows = [
        ("사전규격 공개일시", _first(current_raw, "rgstDt", "bfSpecRgstDt")),
        ("접수일시", _first(current_raw, "rcptDt")),
        ("의견 제출 시작", saved_bid.bid_start_datetime),
        (
            "의견 제출 마감",
            _first(
                current_raw,
                "opninRgstClseDt",
                "opnnSbmsnClseDt",
                "bfSpecOpnnClseDt",
            )
            if is_pre_spec
            else saved_bid.bid_end_datetime,
        ),
        ("납품기한", _first(current_raw, "dlvrTmlmtDt")),
        ("납품일수", _first(current_raw, "dlvrDaynum")),
    ] if is_pre_spec else [
        ("입찰서 제출 시작", saved_bid.bid_start_datetime),
        ("입찰서 제출 마감", saved_bid.bid_end_datetime),
        (
            "제안서 제출 마감",
            _first(current_raw, "prpslDocRcptEndDt", "prpslEndDt", "presntnOprtnDt"),
        ),
        (
            "공동수급협정서 마감",
            current_version.get("consortium_close_at")
            or _first(
                current_raw,
                "cmmnSpldmdAgrmntClseDt",
                "cmmnSpldmdAgrmntDocRcptDt",
            ),
        ),
        ("개찰일시", saved_bid.opening_datetime),
        ("개찰장소", _first(current_raw, "opengPlce", "opengPlace")),
        ("공고 등록일시", _first(current_raw, "rgstDt", "bidNtceDt")),
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
            ("의견 제출 마감", _first(current_raw, "opninRgstClseDt")),
            ("등록된 의견", f"{len(opinions)}건"),
        ],
        "opinions": opinions,
        "results": [
            {
                "status": result.get("result_status") or "-",
                "company": result.get("successful_bidder_name") or "-",
                "business_number": result.get("business_number") or "-",
                "amount": result.get("successful_bid_amount") or "-",
                "rate": result.get("successful_bid_rate") or "-",
                "ranking": result.get("ranking") or "-",
                "opening_at": result.get("opening_datetime") or "-",
                "detected_at": result.get("detected_at") or "-",
            }
            for result in results
        ],
        "attachments": attachments,
        "versions": versions,
        "comparison": comparison,
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
