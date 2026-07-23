from html import escape


def _email_table_html(title, subtitle, rows, link="", badge=""):
    table_rows = "".join(
        "<tr>"
        f'<th style="width:32%;padding:12px 14px;background:#f6f8fb;color:#52606d;'
        f'font-size:13px;text-align:left;border-bottom:1px solid #e5e9f0;">{escape(label)}</th>'
        f'<td style="padding:12px 14px;color:#172b4d;font-size:14px;line-height:1.5;'
        f'border-bottom:1px solid #e5e9f0;word-break:break-word;">{escape(str(value or "-"))}</td>'
        "</tr>"
        for label, value in rows
    )
    badge_html = ""
    if badge:
        badge_html = (
            '<span style="display:inline-block;margin-top:12px;padding:6px 10px;'
            'background:#e8f2ff;color:#1264d1;border-radius:999px;font-size:12px;'
            f'font-weight:700;">{escape(str(badge))}</span>'
        )
    subtitle_html = ""
    if subtitle:
        subtitle_html = (
            '<div style="margin-top:8px;font-size:13px;opacity:.9;">'
            f'{escape(str(subtitle))}</div>'
        )
    link_html = ""
    if link:
        safe_link = escape(str(link), quote=True)
        link_html = (
            '<div style="padding:22px 24px;text-align:center;">'
            f'<a href="{safe_link}" style="display:inline-block;padding:12px 22px;'
            'background:#1677d2;color:#ffffff;text-decoration:none;border-radius:7px;'
            'font-size:14px;font-weight:700;">나라장터 공고 바로가기</a></div>'
        )
    return (
        '<!doctype html><html><body style="margin:0;padding:0;background:#f1f4f8;'
        'font-family:Arial,\'Malgun Gothic\',sans-serif;color:#172b4d;">'
        '<div style="max-width:680px;margin:0 auto;padding:28px 12px;">'
        '<div style="background:#ffffff;border:1px solid #dfe4ea;border-radius:10px;'
        'overflow:hidden;box-shadow:0 3px 12px rgba(23,43,77,.08);">'
        '<div style="padding:24px;background:#1677d2;color:#ffffff;">'
        '<div style="font-size:12px;letter-spacing:.08em;opacity:.85;">나라장터 알림</div>'
        f'<h1 style="margin:7px 0 0;font-size:21px;line-height:1.35;">{escape(title)}</h1>'
        f'{subtitle_html}'
        f'{badge_html}</div>'
        f'<table role="presentation" style="width:100%;border-collapse:collapse;">{table_rows}</table>'
        f'{link_html}'
        '<div style="padding:15px 24px;background:#f8fafc;color:#7b8794;font-size:11px;'
        'line-height:1.6;">본 메일은 나라장터 알림 프로그램에서 자동 발송되었습니다.</div>'
        '</div></div></body></html>'
    )


class EmailAlertService:
    """Create email events; delivery scheduling belongs to the controller layer."""

    def __init__(self, config, email_repository):
        self.config = config
        self.email_repository = email_repository

    def update_config(self, config):
        self.config = config

    def queue_keyword_bid(self, bid, matched_keywords, rule_ids=()):
        recipients = self.email_repository.get_keyword_rule_email_recipients(rule_ids)
        subject = f"[나라장터 신규 공고] {bid.title}"
        lines = [
            f"공고명: {bid.title}",
            f"공고번호: {bid.bid_no} / 차수: {bid.bid_ord or '000'}",
            f"공고종류: {bid.category_label}",
            f"공고기관: {bid.agency or '-'}",
            f"수요기관: {bid.demand_agency or '-'}",
            f"매칭 키워드: {', '.join(matched_keywords)}",
        ]
        if bid.bid_end_datetime:
            lines.append(f"입찰마감: {bid.bid_end_datetime}")
        if bid.link:
            lines.extend(["", f"공고 링크: {bid.link}"])
        rows = [
            ("사업명", bid.title or "-"),
            ("공고번호", f"{bid.bid_no}-{bid.bid_ord or '000'}"),
            ("공고종류", bid.category_label),
            ("공고기관", bid.agency or "-"),
            ("수요기관", bid.demand_agency or "-"),
            ("매칭 키워드", ", ".join(matched_keywords)),
            ("입찰마감", bid.bid_end_datetime or "-"),
        ]
        return self.email_repository.create_email_event(
            event_key=f"keyword_bid:{bid.unique_id}",
            event_type="keyword_bid",
            source_ref=bid.unique_id,
            subject=subject,
            body="\n".join(lines),
            recipients=recipients,
            body_html=_email_table_html(
                "신규 입찰공고가 등록되었습니다",
                "",
                rows,
                link=bid.link,
                badge="신규 공고",
            ),
        )

    def queue_pre_specification(self, pre_spec, matched_keywords, rule_ids=()):
        recipients = self.email_repository.get_keyword_rule_email_recipients(rule_ids)
        subject = f"[사전규격][신규] {pre_spec.title}"
        lines = [
            f"사업명: {pre_spec.title}",
            f"사전규격등록번호: {pre_spec.pre_spec_no}",
            f"업무구분: {pre_spec.category_label}",
            f"발주기관: {pre_spec.agency or '-'}",
            f"수요기관: {pre_spec.demand_agency or '-'}",
            f"배정예산액: {pre_spec.budget_amount or '-'}",
            f"의견등록 마감: {pre_spec.opinion_end_at or '-'}",
            f"매칭 키워드: {', '.join(matched_keywords)}",
        ]
        rows = [
            ("사업명", pre_spec.title or "-"),
            ("단계", "사전규격"),
            ("사전규격등록번호", pre_spec.pre_spec_no),
            ("업무구분", pre_spec.category_label),
            ("발주기관", pre_spec.agency or "-"),
            ("수요기관", pre_spec.demand_agency or "-"),
            ("배정예산액", pre_spec.budget_amount or "-"),
            ("의견등록 마감", pre_spec.opinion_end_at or "-"),
            ("매칭 키워드", ", ".join(matched_keywords)),
        ]
        return self.email_repository.create_email_event(
            event_key=f"pre_spec:{pre_spec.pre_spec_no}",
            event_type="pre_spec",
            source_ref=pre_spec.pre_spec_no,
            subject=subject,
            body="\n".join(lines),
            recipients=recipients,
            body_html=_email_table_html(
                "신규 사전규격이 공개되었습니다",
                pre_spec.title or pre_spec.pre_spec_no,
                rows,
                link=pre_spec.link,
                badge="사전규격",
            ),
        )

    def queue_pre_spec_transition(self, saved_bid, pre_spec_no):
        recipients = self.email_repository.get_saved_bid_email_recipients(saved_bid.id)
        reference = f"{saved_bid.bid_no}-{saved_bid.bid_ord or '000'}"
        rows = [
            ("사업명", saved_bid.title or "-"),
            ("단계", "입찰공고"),
            ("사전규격등록번호", pre_spec_no),
            ("입찰공고번호", reference),
            ("공고 종류", saved_bid.category_label),
            ("수요기관", saved_bid.demand_agency or "-"),
            ("입찰 마감일시", saved_bid.bid_end_datetime or "-"),
            ("개찰일시", saved_bid.opening_datetime or "-"),
        ]
        body = "\n".join(f"{label}: {value}" for label, value in rows)
        return self.email_repository.create_email_event(
            event_key=f"pre_spec_transition:{saved_bid.id}:{reference}",
            event_type="pre_spec_transition",
            source_ref=reference,
            subject=f"[입찰공고 전환] {saved_bid.title or saved_bid.bid_no}",
            body=body,
            recipients=recipients,
            body_html=_email_table_html(
                "추적 중인 사전규격이 입찰공고로 전환되었습니다",
                saved_bid.title or saved_bid.bid_no,
                rows,
                link=saved_bid.link,
                badge="사전규격 → 입찰공고",
            ),
        )

    def queue_bid_result(self, saved_bid, result):
        recipients = self.email_repository.get_saved_bid_email_recipients(saved_bid.id)
        bid_ref = f"{saved_bid.bid_no}-{saved_bid.bid_ord or '000'}"
        lines = [
            f"공고명: {saved_bid.title or '-'}",
            f"공고번호: {saved_bid.bid_no} / 차수: {saved_bid.bid_ord or '000'}",
            f"낙찰업체: {result.successful_bidder_name or '-'}",
            f"사업자번호: {result.business_number or '-'}",
            f"낙찰금액: {result.successful_bid_amount or '-'}",
            f"낙찰률: {result.successful_bid_rate or '-'}",
            f"상태: {result.result_status or '-'}",
        ]
        if saved_bid.link:
            lines.extend(["", f"공고 링크: {saved_bid.link}"])
        rows = [
            ("사업명", saved_bid.title or "-"),
            ("공고번호", bid_ref),
            ("낙찰·개찰업체", result.successful_bidder_name or "-"),
            ("사업자번호", result.business_number or "-"),
            ("금액", result.successful_bid_amount or "-"),
            ("낙찰률", result.successful_bid_rate or "-"),
            ("순위", result.ranking or "-"),
            ("개찰일시", result.opening_datetime or "-"),
            ("진행상태", result.result_status or "-"),
        ]
        return self.email_repository.create_email_event(
            event_key=f"bid_result:{saved_bid.id}:{result.result_key}",
            event_type="bid_result",
            source_ref=bid_ref,
            subject=f"[나라장터 낙찰정보] {saved_bid.title or saved_bid.bid_no}",
            body="\n".join(lines),
            recipients=recipients,
            body_html=_email_table_html(
                "개찰·낙찰정보가 확인되었습니다",
                saved_bid.title or saved_bid.bid_no,
                rows,
                link=saved_bid.link,
                badge=result.result_status or "결과 확인",
            ),
        )

    def queue_bid_change(self, saved_bid, previous_order, current_order, comparison):
        recipients = self.email_repository.get_saved_bid_email_recipients(saved_bid.id)
        bid_ref = f"{saved_bid.bid_no}-{current_order or '000'}"
        changes = comparison.get("changes") or []
        lines = [
            f"사업명: {saved_bid.title or '-'}",
            f"공고번호: {saved_bid.bid_no}",
            f"차수: {previous_order or '000'} → {current_order or '000'}",
        ]
        rows = [
            ("사업명", saved_bid.title or "-"),
            ("공고번호", saved_bid.bid_no),
            ("변경 차수", f"{previous_order or '000'} → {current_order or '000'}"),
            ("공고 종류", saved_bid.category_label),
            ("수요기관", saved_bid.demand_agency or "-"),
        ]
        for change in changes[:8]:
            lines.append(f"{change['label']}: {change['before']} → {change['after']}")
            rows.append(
                (
                    change["label"],
                    f"{change['before']} → {change['after']}",
                )
            )
        if saved_bid.link:
            lines.extend(["", f"공고 링크: {saved_bid.link}"])
        return self.email_repository.create_email_event(
            event_key=(
                f"bid_change:{saved_bid.id}:"
                f"{previous_order or '000'}:{current_order or '000'}"
            ),
            event_type="bid_change",
            source_ref=bid_ref,
            subject=f"[변경공고] {saved_bid.title or saved_bid.bid_no}",
            body="\n".join(lines),
            recipients=recipients,
            body_html=_email_table_html(
                "입찰공고 변경사항이 확인되었습니다",
                saved_bid.title or saved_bid.bid_no,
                rows,
                link=saved_bid.link,
                badge=f"차수 {previous_order or '000'} → {current_order or '000'}",
            ),
        )
