import json
import re


COMPARISON_FIELDS = (
    ("notice_name", "사업명"),
    ("bid_close_at", "입찰 마감일시"),
    ("opening_at", "개찰일시"),
    ("consortium_close_at", "공동수급 마감일시"),
    ("budget_amount", "사업금액"),
    ("demand_institution_name", "수요기관"),
)


def compare_latest_versions(versions):
    if not versions:
        return {"previous": None, "current": None, "changes": []}

    current = next((version for version in reversed(versions) if version.get("is_current")), versions[-1])
    candidates = [version for version in versions if version.get("id") != current.get("id")]
    previous = max(candidates, key=_version_sort_key) if candidates else None
    if not previous:
        return {"previous": None, "current": current, "changes": []}

    changes = []
    for field, label in COMPARISON_FIELDS:
        before = _display_value(previous.get(field))
        after = _display_value(current.get(field))
        if _normalize(before) != _normalize(after):
            changes.append({"field": field, "label": label, "before": before, "after": after})

    previous_raw = _raw(previous)
    current_raw = _raw(current)
    for field, label, extractor in (
        ("qualification", "참가자격", _qualification),
        ("cancellation", "취소 여부", _cancellation),
    ):
        before = _display_value(extractor(previous_raw))
        after = _display_value(extractor(current_raw))
        if _normalize(before) != _normalize(after):
            changes.append({"field": field, "label": label, "before": before, "after": after})

    if _normalize(_attachments(previous_raw)) != _normalize(_attachments(current_raw)):
        previous_files = _attachment_names(previous_raw)
        current_files = _attachment_names(current_raw)
        previous_keys = {_normalize(value): value for value in previous_files}
        current_keys = {_normalize(value): value for value in current_files}
        added = [
            value
            for key, value in current_keys.items()
            if key not in previous_keys
        ]
        removed = [
            value
            for key, value in previous_keys.items()
            if key not in current_keys
        ]
        changes.append(
            {
                "field": "attachments",
                "label": "첨부파일",
                "before": f"{len(previous_files)}개",
                "after": f"{len(current_files)}개",
                "attachment_added": added,
                "attachment_removed": removed,
            }
        )

    return {"previous": previous, "current": current, "changes": changes}


def _version_sort_key(version):
    order = str(version.get("bid_pbanc_ord") or "")
    numeric_order = int(order) if order.isdigit() else -1
    return numeric_order, str(version.get("detected_at") or ""), int(version.get("id") or 0)


def _raw(version):
    raw = version.get("raw")
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(version.get("raw_json") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _qualification(raw):
    for key in (
        "bidPrtcptQlfctRgstDt",
        "prtcptPsblRgnNm",
        "bidPrtcptLmtYn",
        "rgstTyNm",
    ):
        value = raw.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _attachments(raw):
    values = []
    for key, value in raw.items():
        lowered = str(key).lower()
        if not value or not any(token in lowered for token in ("file", "doc", "atch", "spec")):
            continue
        if "url" in lowered or "nm" in lowered or "name" in lowered:
            values.append(str(value).strip())
    return ", ".join(dict.fromkeys(value for value in values if value))


def _attachment_names(raw):
    names = []
    urls = []
    for key, value in raw.items():
        if value in (None, ""):
            continue
        lowered = str(key).lower()
        text = str(value).strip()
        if any(token in lowered for token in ("filename", "filenm", "docnm")):
            names.append(text)
        elif "url" in lowered and any(
            token in lowered for token in ("file", "doc", "atch", "spec")
        ):
            urls.append(text)
    names = list(dict.fromkeys(names))
    if names:
        return names
    url_count = len(dict.fromkeys(urls))
    return [
        f"첨부파일 {index}"
        for index in range(1, url_count + 1)
    ]


def _cancellation(raw):
    values = []
    for key in ("bidNtceSttusNm", "ntceKindNm", "cancelYn", "bidNtceCancelYn"):
        value = raw.get(key)
        if value not in (None, ""):
            values.append(str(value))
    return " / ".join(values)


def _normalize(value):
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _display_value(value):
    text = str(value or "").strip()
    return text if text else "-"
