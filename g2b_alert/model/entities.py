import json
from datetime import datetime
from dataclasses import dataclass, field


CATEGORY_LABELS = {
    "service": "용역",
    "goods": "물품",
    "works": "공사",
    "etc": "기타",
}


@dataclass(frozen=True)
class Bid:
    """A bid announcement used by monitoring and persistence rules."""

    category: str
    title: str
    bid_no: str
    bid_ord: str
    agency: str
    demand_agency: str
    link: str
    bid_method: str = ""
    contract_method: str = ""
    budget_amount: str = ""
    bid_start_datetime: str = ""
    bid_end_datetime: str = ""
    opening_datetime: str = ""
    raw: dict = field(default_factory=dict, compare=False)

    @property
    def category_label(self):
        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def unique_id(self):
        return f"{self.bid_no}-{self.bid_ord or '000'}"


@dataclass(frozen=True)
class PreSpecification:
    category: str
    title: str
    pre_spec_no: str
    agency: str
    demand_agency: str
    link: str
    budget_amount: str = ""
    published_at: str = ""
    opinion_start_at: str = ""
    opinion_end_at: str = ""
    raw: dict = field(default_factory=dict, compare=False)

    @property
    def category_label(self):
        category = CATEGORY_LABELS.get(self.category, self.category)
        return f"사전규격·{category}"

    @property
    def unique_id(self):
        return f"prespec:{self.pre_spec_no}"


@dataclass(frozen=True)
class SavedBid:
    """A persisted bid with monitoring state."""

    id: int
    bid_no: str
    bid_ord: str
    category: str
    title: str
    agency: str
    demand_agency: str
    bid_method: str
    contract_method: str
    budget_amount: str
    bid_start_datetime: str
    bid_end_datetime: str
    opening_datetime: str
    link: str
    raw: dict
    saved_at: str
    updated_at: str
    monitoring_enabled: bool
    status: str
    last_result_check_at: str = ""
    result_found_at: str = ""
    current_result_status: str = ""
    pre_spec_no: str = ""

    @property
    def category_label(self):
        return CATEGORY_LABELS.get(self.category, self.category)

    @property
    def unique_id(self):
        return f"{self.bid_no}-{self.bid_ord or '000'}"

    @classmethod
    def from_row(cls, row):
        try:
            raw = json.loads(row["raw_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            raw = {}
        return cls(
            id=int(row["id"]),
            bid_no=row["bid_pbanc_no"] or "",
            bid_ord=row["bid_pbanc_ord"] or "",
            category=row["category"] or "service",
            title=row["bid_name"] or "",
            agency=row["organization_name"] or "",
            demand_agency=row["demand_organization_name"] or "",
            bid_method=row["bid_method"] or "",
            contract_method=row["contract_method"] or "",
            budget_amount=row["budget_amount"] or "",
            bid_start_datetime=row["bid_start_datetime"] or "",
            bid_end_datetime=row["bid_end_datetime"] or "",
            opening_datetime=row["opening_datetime"] or "",
            link=row["detail_url"] or "",
            raw=raw,
            saved_at=row["saved_at"] or "",
            updated_at=row["updated_at"] or "",
            monitoring_enabled=bool(row["monitoring_enabled"]),
            status=row["status"] or "",
            last_result_check_at=row["last_result_check_at"] or "",
            result_found_at=row["result_found_at"] or "",
            current_result_status=(
                row["current_result_status"] or ""
                if "current_result_status" in row.keys()
                else ""
            ),
            pre_spec_no=(
                row["pre_spec_no"] or ""
                if "pre_spec_no" in row.keys()
                else ""
            ),
        )

    def progress_status(self, now=None):
        """Return a user-facing status derived from results and bid dates."""
        if self.pre_spec_no and self.status == "pre_spec":
            opinion_end = _parse_g2b_datetime(self.bid_end_datetime)
            now = now or datetime.now()
            if opinion_end and now < opinion_end:
                return "사전규격 의견 접수 중"
            if opinion_end:
                return "입찰공고 전환 대기"
            return "사전규격 추적 중"
        if self.current_result_status:
            return self.current_result_status
        if self.result_found_at:
            return "개찰·낙찰 결과 있음"

        now = now or datetime.now()
        bid_start = _parse_g2b_datetime(self.bid_start_datetime)
        bid_end = _parse_g2b_datetime(self.bid_end_datetime)
        opening = _parse_g2b_datetime(self.opening_datetime)

        if bid_start and now < bid_start:
            return "입찰 개시 전"
        if bid_end and now < bid_end:
            return "입찰 진행 중"
        if opening and now < opening:
            return "개찰 대기"
        if opening and now >= opening:
            return "개찰 결과 대기"
        if bid_end and now >= bid_end:
            return "입찰 마감"
        return "일정 확인 필요"

    def stage_label(self):
        if self.pre_spec_no and self.status == "pre_spec":
            return "사전규격"
        status_text = f"{self.current_result_status} {self.status}".lower()
        if "취소" in status_text or "유찰" in status_text:
            return "유찰·취소"
        if "계약" in status_text:
            return "계약완료"
        if "낙찰" in status_text or "선정" in status_text:
            return "낙찰결과"
        if self.result_found_at or "개찰" in status_text or "결과" in status_text:
            return "개찰결과"
        return "입찰공고"

def _parse_g2b_datetime(value):
    text = str(value or "").strip()
    for date_format in (
        "%Y%m%d%H%M%S",
        "%Y%m%d%H%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class BidResult:
    """A normalized opening or award result returned by the G2B API."""

    result_type: str = ""
    opening_datetime: str = ""
    successful_bidder_name: str = ""
    business_number: str = ""
    successful_bid_amount: str = ""
    successful_bid_rate: str = ""
    ranking: str = ""
    result_status: str = ""
    raw: dict = field(default_factory=dict, compare=False)

    @property
    def result_key(self):
        parts = (
            self.result_type,
            self.opening_datetime,
            self.business_number,
            self.successful_bidder_name,
            self.ranking,
            self.result_status,
        )
        return "|".join(str(part or "").strip() for part in parts)
