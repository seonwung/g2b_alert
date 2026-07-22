import json
from datetime import datetime

from ..entities import Bid, PreSpecification, SavedBid


class BidRepository:
    def __init__(self, database):
        self.database = database

    def connect(self):
        return self.database.connect()

    @staticmethod
    def _now_text():
        return datetime.now().isoformat(timespec="seconds")

    def is_bid_seen(self, bid_unique_id):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM seen_bid_alerts WHERE bid_unique_id = ?",
                (bid_unique_id,),
            ).fetchone()
        return row is not None

    def mark_bid_seen(self, bid_unique_id):
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO seen_bid_alerts (bid_unique_id, alerted_at) VALUES (?, ?)",
                (bid_unique_id, self._now_text()),
            )

    def get_last_check_time(self):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM monitor_state WHERE key = 'last_check_time'"
            ).fetchone()
        return row["value"] if row else ""

    def set_last_check_time(self, value):
        current = self._now_text()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO monitor_state (key, value, updated_at)
                VALUES ('last_check_time', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (str(value), current),
            )

    def get_monitor_state(self, key, default=""):
        """Return monitor progress persisted across application sessions."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM monitor_state WHERE key = ?",
                (key,),
            ).fetchone()
        return row["value"] if row else default

    def set_monitor_state(self, key, value):
        """Persist a heartbeat that also survives an unclean shutdown."""
        current = self._now_text()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO monitor_state (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, str(value), current),
            )

    def get_result_monitor_last_success_time(self):
        return self.get_monitor_state("result_monitor_last_success_at")

    def set_result_monitor_last_success_time(self, value):
        self.set_monitor_state("result_monitor_last_success_at", value)

    def set_result_monitor_last_cycle_time(self, value):
        self.set_monitor_state("result_monitor_last_cycle_at", value)

    def reset_bid_monitor_state(self):
        with self.connect() as connection:
            seen = connection.execute("DELETE FROM seen_bid_alerts").rowcount
            state = connection.execute(
                "DELETE FROM monitor_state WHERE key = 'last_check_time'"
            ).rowcount
        return seen + state

    def save_bid(self, bid: Bid):
        saved_at = self._now_text()
        bid_ord = bid.bid_ord or ""
        raw_json = json.dumps(bid.raw or {}, ensure_ascii=False)
        values = {
            "bid_pbanc_no": bid.bid_no,
            "bid_pbanc_ord": bid_ord,
            "category": bid.category,
            "bid_name": bid.title,
            "organization_name": bid.agency,
            "demand_organization_name": bid.demand_agency,
            "bid_method": bid.bid_method,
            "contract_method": bid.contract_method,
            "budget_amount": str(bid.budget_amount or ""),
            "bid_start_datetime": bid.bid_start_datetime,
            "bid_end_datetime": bid.bid_end_datetime,
            "opening_datetime": bid.opening_datetime,
            "detail_url": bid.link,
            "raw_json": raw_json,
            "updated_at": saved_at,
        }
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM saved_bids WHERE bid_pbanc_no = ? AND bid_pbanc_ord = ?",
                (bid.bid_no, bid_ord),
            ).fetchone()
            if existing:
                self._update_saved_bid(connection, existing["id"], values, include_order=False)
                self._record_notice_version(connection, existing["id"], values, is_current=True)
                return existing["id"], False

            tracked = connection.execute(
                """
                SELECT id, bid_pbanc_ord
                FROM saved_bids
                WHERE bid_pbanc_no = ?
                ORDER BY id
                LIMIT 1
                """,
                (bid.bid_no,),
            ).fetchone()
            if tracked:
                saved_bid_id = tracked["id"]
                is_newer = self._is_newer_order(bid_ord, tracked["bid_pbanc_ord"] or "")
                if is_newer:
                    connection.execute(
                        "UPDATE notice_versions SET is_current = 0 WHERE saved_bid_id = ?",
                        (saved_bid_id,),
                    )
                    self._update_saved_bid(connection, saved_bid_id, values, include_order=True)
                self._record_notice_version(
                    connection,
                    saved_bid_id,
                    values,
                    is_current=is_newer,
                )
                return saved_bid_id, False

            values["saved_at"] = saved_at
            cursor = connection.execute(
                """
                INSERT INTO saved_bids (
                    bid_pbanc_no, bid_pbanc_ord, category, bid_name, organization_name,
                    demand_organization_name, bid_method, contract_method, budget_amount,
                    bid_start_datetime, bid_end_datetime, opening_datetime, detail_url,
                    raw_json, saved_at, updated_at
                )
                VALUES (
                    :bid_pbanc_no, :bid_pbanc_ord, :category, :bid_name, :organization_name,
                    :demand_organization_name, :bid_method, :contract_method, :budget_amount,
                    :bid_start_datetime, :bid_end_datetime, :opening_datetime, :detail_url,
                    :raw_json, :saved_at, :updated_at
                )
                """,
                values,
            )
            self._record_notice_version(connection, cursor.lastrowid, values, is_current=True)
            return cursor.lastrowid, True

    def save_pre_specification(self, pre_spec: PreSpecification):
        current = self._now_text()
        synthetic_no = f"PRESPEC:{pre_spec.pre_spec_no}"
        raw_json = json.dumps(pre_spec.raw or {}, ensure_ascii=False)
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM saved_bids WHERE pre_spec_no = ?",
                (pre_spec.pre_spec_no,),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE saved_bids
                    SET category = ?, bid_name = ?, organization_name = ?,
                        demand_organization_name = ?, budget_amount = ?,
                        bid_start_datetime = ?, bid_end_datetime = ?,
                        detail_url = ?, raw_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        pre_spec.category,
                        pre_spec.title,
                        pre_spec.agency,
                        pre_spec.demand_agency,
                        pre_spec.budget_amount,
                        pre_spec.opinion_start_at,
                        pre_spec.opinion_end_at,
                        pre_spec.link,
                        raw_json,
                        current,
                        existing["id"],
                    ),
                )
                return existing["id"], False
            cursor = connection.execute(
                """
                INSERT INTO saved_bids (
                    bid_pbanc_no, bid_pbanc_ord, pre_spec_no, category, bid_name,
                    organization_name, demand_organization_name, budget_amount,
                    bid_start_datetime, bid_end_datetime, opening_datetime,
                    detail_url, raw_json, saved_at, updated_at,
                    monitoring_enabled, status
                )
                VALUES (?, '', ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, 1, 'pre_spec')
                """,
                (
                    synthetic_no,
                    pre_spec.pre_spec_no,
                    pre_spec.category,
                    pre_spec.title,
                    pre_spec.agency,
                    pre_spec.demand_agency,
                    pre_spec.budget_amount,
                    pre_spec.opinion_start_at,
                    pre_spec.opinion_end_at,
                    pre_spec.link,
                    raw_json,
                    current,
                    current,
                ),
            )
            return cursor.lastrowid, True

    def find_saved_pre_specification(self, pre_spec_no):
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT saved_bids.*, '' AS current_result_status
                FROM saved_bids
                WHERE pre_spec_no = ?
                LIMIT 1
                """,
                ((pre_spec_no or "").strip(),),
            ).fetchone()
        return SavedBid.from_row(row) if row else None

    def transition_pre_specification(self, saved_bid_id, bid: Bid):
        current = self._now_text()
        raw_json = json.dumps(bid.raw or {}, ensure_ascii=False)
        values = {
            "bid_pbanc_no": bid.bid_no,
            "bid_pbanc_ord": bid.bid_ord or "",
            "category": bid.category,
            "bid_name": bid.title,
            "organization_name": bid.agency,
            "demand_organization_name": bid.demand_agency,
            "bid_method": bid.bid_method,
            "contract_method": bid.contract_method,
            "budget_amount": str(bid.budget_amount or ""),
            "bid_start_datetime": bid.bid_start_datetime,
            "bid_end_datetime": bid.bid_end_datetime,
            "opening_datetime": bid.opening_datetime,
            "detail_url": bid.link,
            "raw_json": raw_json,
            "updated_at": current,
        }
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE saved_bids
                SET bid_pbanc_no = :bid_pbanc_no,
                    bid_pbanc_ord = :bid_pbanc_ord,
                    category = :category,
                    bid_name = :bid_name,
                    organization_name = :organization_name,
                    demand_organization_name = :demand_organization_name,
                    bid_method = :bid_method,
                    contract_method = :contract_method,
                    budget_amount = :budget_amount,
                    bid_start_datetime = :bid_start_datetime,
                    bid_end_datetime = :bid_end_datetime,
                    opening_datetime = :opening_datetime,
                    detail_url = :detail_url,
                    raw_json = :raw_json,
                    status = 'saved',
                    updated_at = :updated_at
                WHERE id = :saved_bid_id AND status = 'pre_spec'
                """,
                {**values, "saved_bid_id": saved_bid_id},
            )
            connection.execute(
                "UPDATE notice_versions SET is_current = 0 WHERE saved_bid_id = ?",
                (saved_bid_id,),
            )
            self._record_notice_version(connection, saved_bid_id, values, is_current=True)
        return self.find_saved_bid(bid.bid_no, bid.bid_ord)

    @staticmethod
    def _is_newer_order(candidate, current):
        if candidate == current:
            return False
        if candidate.isdigit() and current.isdigit():
            return int(candidate) > int(current)
        if candidate and not current:
            return True
        return candidate > current

    @staticmethod
    def _update_saved_bid(connection, saved_bid_id, values, include_order):
        order_assignment = "bid_pbanc_ord = :bid_pbanc_ord," if include_order else ""
        connection.execute(
            f"""
            UPDATE saved_bids
            SET {order_assignment}
                category = :category,
                bid_name = :bid_name,
                organization_name = :organization_name,
                demand_organization_name = :demand_organization_name,
                bid_method = :bid_method,
                contract_method = :contract_method,
                budget_amount = :budget_amount,
                bid_start_datetime = :bid_start_datetime,
                bid_end_datetime = :bid_end_datetime,
                opening_datetime = :opening_datetime,
                detail_url = :detail_url,
                raw_json = :raw_json,
                updated_at = :updated_at
            WHERE id = :saved_bid_id
            """,
            {**values, "saved_bid_id": saved_bid_id},
        )

    @staticmethod
    def _record_notice_version(connection, saved_bid_id, values, is_current):
        try:
            raw = json.loads(values["raw_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            raw = {}
        consortium_close_at = (
            raw.get("cmmnSpldmdAgrmntClseDt")
            or raw.get("cmmnSpldmdAgrmntDocRcptDt")
            or ""
        )
        registered_at = raw.get("rgstDt") or raw.get("bidNtceDt") or values.get("updated_at", "")
        connection.execute(
            """
            INSERT INTO notice_versions (
                saved_bid_id, bid_pbanc_no, bid_pbanc_ord, raw_json, notice_name,
                bid_close_at, opening_at, consortium_close_at, budget_amount,
                demand_institution_name, registered_at, detected_at, is_current
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(saved_bid_id, bid_pbanc_no, bid_pbanc_ord) DO UPDATE SET
                is_current = excluded.is_current
            """,
            (
                saved_bid_id,
                values["bid_pbanc_no"],
                values["bid_pbanc_ord"],
                values["raw_json"],
                values["bid_name"],
                values["bid_end_datetime"],
                values["opening_datetime"],
                consortium_close_at,
                values["budget_amount"],
                values["demand_organization_name"],
                registered_at,
                values["updated_at"],
                1 if is_current else 0,
            ),
        )

    def list_notice_versions(self, saved_bid_id):
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM notice_versions
                WHERE saved_bid_id = ?
                ORDER BY detected_at, id
                """,
                (saved_bid_id,),
            ).fetchall()
        versions = []
        for row in rows:
            version = dict(row)
            try:
                version["raw"] = json.loads(version.get("raw_json") or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                version["raw"] = {}
            versions.append(version)
        return versions

    def find_saved_bid(self, bid_no, bid_ord=""):
        bid_no = (bid_no or "").strip()
        bid_ord = (bid_ord or "").strip()
        if not bid_no:
            return None
        params = [bid_no]
        order_filter = ""
        if bid_ord:
            order_filter = "AND bid_pbanc_ord = ?"
            params.append(bid_ord)
        with self.connect() as connection:
            row = connection.execute(
                f"""
                SELECT saved_bids.*,
                       (
                           SELECT result_status
                           FROM bid_results
                           WHERE bid_results.saved_bid_id = saved_bids.id
                             AND COALESCE(result_status, '') <> ''
                           ORDER BY detected_at DESC, id DESC
                           LIMIT 1
                       ) AS current_result_status
                FROM saved_bids
                WHERE bid_pbanc_no = ?
                {order_filter}
                ORDER BY bid_pbanc_ord DESC, id DESC
                LIMIT 1
                """,
                params,
            ).fetchone()
        return SavedBid.from_row(row) if row else None

    def list_saved_bids(self, search_text=""):
        search_text = (search_text or "").strip()
        params = []
        where = ""
        if search_text:
            where = """
                WHERE bid_pbanc_no LIKE ?
                   OR bid_name LIKE ?
                   OR organization_name LIKE ?
                   OR demand_organization_name LIKE ?
            """
            pattern = f"%{search_text}%"
            params = [pattern, pattern, pattern, pattern]
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT saved_bids.*,
                       (
                           SELECT result_status
                           FROM bid_results
                           WHERE bid_results.saved_bid_id = saved_bids.id
                             AND COALESCE(result_status, '') <> ''
                           ORDER BY detected_at DESC, id DESC
                           LIMIT 1
                       ) AS current_result_status
                FROM saved_bids
                {where}
                ORDER BY saved_at DESC
                """,
                params,
            ).fetchall()
        return [SavedBid.from_row(row) for row in rows]

    def delete_saved_bid(self, saved_bid_id):
        with self.connect() as connection:
            connection.execute("DELETE FROM saved_bids WHERE id = ?", (saved_bid_id,))

    def set_monitoring_enabled(self, saved_bid_id, enabled):
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE saved_bids
                SET monitoring_enabled = ?,
                    status = CASE
                        WHEN ? = 1 AND status = 'archived' THEN 'saved'
                        ELSE status
                    END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    1 if enabled else 0,
                    1 if enabled else 0,
                    self._now_text(),
                    saved_bid_id,
                ),
            )

    def update_result_check_time(self, saved_bid_id, result_found=False):
        current = self._now_text()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE saved_bids
                SET last_result_check_at = ?,
                    result_found_at = CASE WHEN ? THEN COALESCE(result_found_at, ?) ELSE result_found_at END,
                    status = CASE WHEN ? THEN 'result_found' ELSE status END,
                    updated_at = ?
                WHERE id = ?
                """,
                (current, 1 if result_found else 0, current, 1 if result_found else 0, current, saved_bid_id),
            )

    def list_monitoring_bids(self):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM saved_bids WHERE monitoring_enabled = 1 ORDER BY saved_at"
            ).fetchall()
        return [SavedBid.from_row(row) for row in rows]
