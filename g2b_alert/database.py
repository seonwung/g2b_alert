import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .g2b_client import BidItem
from .paths import get_persistent_data_dir


DB_FILE = get_persistent_data_dir() / "g2b_alert.db"


def now_text():
    return datetime.now().isoformat(timespec="seconds")


class G2BDatabase:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self):
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS saved_bids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bid_pbanc_no TEXT NOT NULL,
                    bid_pbanc_ord TEXT NOT NULL DEFAULT '',
                    category TEXT,
                    bid_name TEXT,
                    organization_name TEXT,
                    demand_organization_name TEXT,
                    bid_method TEXT,
                    contract_method TEXT,
                    budget_amount TEXT,
                    bid_start_datetime TEXT,
                    bid_end_datetime TEXT,
                    opening_datetime TEXT,
                    detail_url TEXT,
                    raw_json TEXT,
                    saved_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    monitoring_enabled INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'saved',
                    last_result_check_at TEXT,
                    result_found_at TEXT,
                    UNIQUE(bid_pbanc_no, bid_pbanc_ord)
                );

                CREATE TABLE IF NOT EXISTS bid_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    saved_bid_id INTEGER NOT NULL,
                    bid_pbanc_no TEXT NOT NULL,
                    bid_pbanc_ord TEXT NOT NULL DEFAULT '',
                    result_type TEXT,
                    opening_datetime TEXT,
                    successful_bidder_name TEXT,
                    business_number TEXT,
                    successful_bid_amount TEXT,
                    successful_bid_rate TEXT,
                    ranking TEXT,
                    result_status TEXT,
                    result_key TEXT NOT NULL,
                    raw_json TEXT,
                    detected_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(saved_bid_id) REFERENCES saved_bids(id) ON DELETE CASCADE,
                    UNIQUE(saved_bid_id, result_key)
                );

                CREATE TABLE IF NOT EXISTS notification_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    saved_bid_id INTEGER NOT NULL,
                    notification_type TEXT NOT NULL,
                    notification_key TEXT NOT NULL,
                    message TEXT,
                    notified_at TEXT NOT NULL,
                    FOREIGN KEY(saved_bid_id) REFERENCES saved_bids(id) ON DELETE CASCADE,
                    UNIQUE(saved_bid_id, notification_type, notification_key)
                );

                CREATE TABLE IF NOT EXISTS keyword_settings (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    keywords TEXT NOT NULL DEFAULT '',
                    email_enabled INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS recipients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS keyword_recipient_map (
                    keyword_setting_id INTEGER NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(keyword_setting_id, recipient_id),
                    FOREIGN KEY(keyword_setting_id) REFERENCES keyword_settings(id) ON DELETE CASCADE,
                    FOREIGN KEY(recipient_id) REFERENCES recipients(id)
                );

                CREATE TABLE IF NOT EXISTS saved_bid_recipient_map (
                    saved_bid_id INTEGER NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(saved_bid_id, recipient_id),
                    FOREIGN KEY(saved_bid_id) REFERENCES saved_bids(id) ON DELETE CASCADE,
                    FOREIGN KEY(recipient_id) REFERENCES recipients(id)
                );

                CREATE TABLE IF NOT EXISTS email_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_key TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    source_ref TEXT,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS email_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    recipient_name TEXT NOT NULL,
                    recipient_email TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    next_attempt_at TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(event_id, recipient_id),
                    FOREIGN KEY(event_id) REFERENCES email_events(id) ON DELETE CASCADE,
                    FOREIGN KEY(recipient_id) REFERENCES recipients(id)
                );

                CREATE INDEX IF NOT EXISTS idx_email_deliveries_queue
                    ON email_deliveries(status, next_attempt_at, created_at);
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO keyword_settings (id, name, keywords, email_enabled, updated_at)
                VALUES (1, '기본 키워드 감시', '', 0, ?)
                """,
                (now_text(),),
            )

    def save_bid(self, bid: BidItem):
        saved_at = now_text()
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
                connection.execute(
                    """
                    UPDATE saved_bids
                    SET category = :category,
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
                    WHERE bid_pbanc_no = :bid_pbanc_no AND bid_pbanc_ord = :bid_pbanc_ord
                    """,
                    values,
                )
                return existing["id"], False

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
            return cursor.lastrowid, True

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
            return connection.execute(
                f"""
                SELECT *
                FROM saved_bids
                {where}
                ORDER BY saved_at DESC
                """,
                params,
            ).fetchall()

    def get_saved_bid(self, saved_bid_id):
        with self.connect() as connection:
            return connection.execute("SELECT * FROM saved_bids WHERE id = ?", (saved_bid_id,)).fetchone()

    def delete_saved_bid(self, saved_bid_id):
        with self.connect() as connection:
            connection.execute("DELETE FROM saved_bids WHERE id = ?", (saved_bid_id,))

    def set_monitoring_enabled(self, saved_bid_id, enabled):
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE saved_bids
                SET monitoring_enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (1 if enabled else 0, now_text(), saved_bid_id),
            )

    def update_result_check_time(self, saved_bid_id, result_found=False):
        current = now_text()
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
            return connection.execute(
                "SELECT * FROM saved_bids WHERE monitoring_enabled = 1 ORDER BY saved_at"
            ).fetchall()

    def save_result(self, saved_bid, result):
        current = now_text()
        result_key = result.get("result_key") or build_result_key(result)
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO bid_results (
                    saved_bid_id, bid_pbanc_no, bid_pbanc_ord, result_type, opening_datetime,
                    successful_bidder_name, business_number, successful_bid_amount,
                    successful_bid_rate, ranking, result_status, result_key, raw_json,
                    detected_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    saved_bid["id"],
                    saved_bid["bid_pbanc_no"],
                    saved_bid["bid_pbanc_ord"],
                    result.get("result_type", ""),
                    result.get("opening_datetime", ""),
                    result.get("successful_bidder_name", ""),
                    result.get("business_number", ""),
                    result.get("successful_bid_amount", ""),
                    result.get("successful_bid_rate", ""),
                    result.get("ranking", ""),
                    result.get("result_status", ""),
                    result_key,
                    json.dumps(result.get("raw") or {}, ensure_ascii=False),
                    current,
                    current,
                ),
            )
            if cursor.rowcount == 0:
                connection.execute(
                    """
                    UPDATE bid_results
                    SET result_status = ?,
                        raw_json = ?,
                        updated_at = ?
                    WHERE saved_bid_id = ? AND result_key = ?
                    """,
                    (
                        result.get("result_status", ""),
                        json.dumps(result.get("raw") or {}, ensure_ascii=False),
                        current,
                        saved_bid["id"],
                        result_key,
                    ),
                )
                return False
            return True

    def record_notification(self, saved_bid_id, notification_type, notification_key, message):
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO notification_history (
                    saved_bid_id, notification_type, notification_key, message, notified_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (saved_bid_id, notification_type, notification_key, message, now_text()),
            )
            return cursor.rowcount > 0

    def sync_keyword_setting(self, keywords, email_enabled):
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO keyword_settings (id, name, keywords, email_enabled, updated_at)
                VALUES (1, '기본 키워드 감시', ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    keywords = excluded.keywords,
                    email_enabled = excluded.email_enabled,
                    updated_at = excluded.updated_at
                """,
                (keywords or "", 1 if email_enabled else 0, now_text()),
            )

    def list_recipients(self, active_only=True):
        where = "WHERE active = 1" if active_only else ""
        with self.connect() as connection:
            return connection.execute(
                f"SELECT * FROM recipients {where} ORDER BY name COLLATE NOCASE, email COLLATE NOCASE"
            ).fetchall()

    def save_recipient(self, name, email, recipient_id=None):
        current = now_text()
        name = (name or "").strip()
        email = (email or "").strip().lower()
        with self.connect() as connection:
            if recipient_id:
                connection.execute(
                    """
                    UPDATE recipients
                    SET name = ?, email = ?, active = 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (name, email, current, recipient_id),
                )
                return int(recipient_id)
            existing = connection.execute(
                "SELECT id FROM recipients WHERE email = ? COLLATE NOCASE",
                (email,),
            ).fetchone()
            if existing:
                connection.execute(
                    "UPDATE recipients SET name = ?, active = 1, updated_at = ? WHERE id = ?",
                    (name, current, existing["id"]),
                )
                return existing["id"]
            cursor = connection.execute(
                """
                INSERT INTO recipients (name, email, active, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?)
                """,
                (name, email, current, current),
            )
            return cursor.lastrowid

    def deactivate_recipient(self, recipient_id):
        with self.connect() as connection:
            connection.execute(
                "UPDATE recipients SET active = 0, updated_at = ? WHERE id = ?",
                (now_text(), recipient_id),
            )
            connection.execute("DELETE FROM keyword_recipient_map WHERE recipient_id = ?", (recipient_id,))
            connection.execute("DELETE FROM saved_bid_recipient_map WHERE recipient_id = ?", (recipient_id,))

    def get_keyword_recipient_ids(self):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT recipient_id FROM keyword_recipient_map WHERE keyword_setting_id = 1"
            ).fetchall()
        return {row["recipient_id"] for row in rows}

    def set_keyword_recipients(self, recipient_ids):
        current = now_text()
        recipient_ids = {int(recipient_id) for recipient_id in recipient_ids}
        with self.connect() as connection:
            connection.execute("DELETE FROM keyword_recipient_map WHERE keyword_setting_id = 1")
            connection.executemany(
                """
                INSERT INTO keyword_recipient_map (keyword_setting_id, recipient_id, created_at)
                VALUES (1, ?, ?)
                """,
                [(recipient_id, current) for recipient_id in sorted(recipient_ids)],
            )

    def get_saved_bid_recipient_ids(self, saved_bid_id):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT recipient_id FROM saved_bid_recipient_map WHERE saved_bid_id = ?",
                (saved_bid_id,),
            ).fetchall()
        return {row["recipient_id"] for row in rows}

    def set_saved_bid_recipients(self, saved_bid_id, recipient_ids):
        current = now_text()
        recipient_ids = {int(recipient_id) for recipient_id in recipient_ids}
        with self.connect() as connection:
            connection.execute("DELETE FROM saved_bid_recipient_map WHERE saved_bid_id = ?", (saved_bid_id,))
            connection.executemany(
                """
                INSERT INTO saved_bid_recipient_map (saved_bid_id, recipient_id, created_at)
                VALUES (?, ?, ?)
                """,
                [(saved_bid_id, recipient_id, current) for recipient_id in sorted(recipient_ids)],
            )

    def get_keyword_email_recipients(self):
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT r.*
                FROM recipients r
                JOIN keyword_recipient_map m ON m.recipient_id = r.id
                JOIN keyword_settings k ON k.id = m.keyword_setting_id
                WHERE k.id = 1 AND k.email_enabled = 1 AND r.active = 1
                ORDER BY r.name COLLATE NOCASE
                """
            ).fetchall()

    def get_saved_bid_email_recipients(self, saved_bid_id):
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT r.*
                FROM recipients r
                JOIN saved_bid_recipient_map m ON m.recipient_id = r.id
                WHERE m.saved_bid_id = ? AND r.active = 1
                ORDER BY r.name COLLATE NOCASE
                """,
                (saved_bid_id,),
            ).fetchall()

    def create_email_event(self, event_key, event_type, source_ref, subject, body, recipients):
        current = now_text()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO email_events (
                    event_key, event_type, source_ref, subject, body, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_key, event_type, source_ref, subject, body, current),
            )
            if cursor.rowcount == 0:
                return False, 0
            event_id = cursor.lastrowid
            delivery_rows = [
                (
                    event_id,
                    recipient["id"],
                    recipient["name"],
                    recipient["email"],
                    current,
                    current,
                )
                for recipient in recipients
            ]
            connection.executemany(
                """
                INSERT INTO email_deliveries (
                    event_id, recipient_id, recipient_name, recipient_email,
                    status, retry_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'pending', 0, ?, ?)
                """,
                delivery_rows,
            )
            return True, len(delivery_rows)

    def reset_interrupted_email_deliveries(self):
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE email_deliveries
                SET status = 'pending', updated_at = ?
                WHERE status = 'sending'
                """,
                (now_text(),),
            )

    def claim_next_email_delivery(self):
        current = now_text()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT d.*, e.event_key, e.event_type, e.subject, e.body
                FROM email_deliveries d
                JOIN email_events e ON e.id = d.event_id
                WHERE d.status = 'pending'
                  AND (d.next_attempt_at IS NULL OR d.next_attempt_at <= ?)
                ORDER BY d.created_at, d.id
                LIMIT 1
                """,
                (current,),
            ).fetchone()
            if not row:
                return None
            updated = connection.execute(
                """
                UPDATE email_deliveries
                SET status = 'sending', updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (current, row["id"]),
            )
            return row if updated.rowcount else None

    def mark_email_delivery_sent(self, delivery_id):
        current = now_text()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE email_deliveries
                SET status = 'sent', sent_at = ?, last_error = NULL,
                    next_attempt_at = NULL, updated_at = ?
                WHERE id = ?
                """,
                (current, current, delivery_id),
            )

    def mark_email_delivery_failed(self, delivery_id, error_message, max_retries=3, retry_delay_seconds=60):
        from datetime import timedelta

        current_time = datetime.now()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT retry_count FROM email_deliveries WHERE id = ?",
                (delivery_id,),
            ).fetchone()
            if not row:
                return
            retry_count = int(row["retry_count"]) + 1
            final_failure = retry_count >= max_retries
            next_attempt = None
            if not final_failure:
                next_attempt = (current_time + timedelta(seconds=retry_delay_seconds)).isoformat(timespec="seconds")
            connection.execute(
                """
                UPDATE email_deliveries
                SET status = ?, retry_count = ?, last_error = ?,
                    next_attempt_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    "failed" if final_failure else "pending",
                    retry_count,
                    str(error_message or "")[:1000],
                    next_attempt,
                    current_time.isoformat(timespec="seconds"),
                    delivery_id,
                ),
            )

    def get_email_delivery_summary(self):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM email_deliveries GROUP BY status"
            ).fetchall()
        summary = {"pending": 0, "sending": 0, "sent": 0, "failed": 0}
        summary.update({row["status"]: row["count"] for row in rows})
        return summary

    def list_recent_email_deliveries(self, limit=100):
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT d.*, e.event_type, e.subject
                FROM email_deliveries d
                JOIN email_events e ON e.id = d.event_id
                ORDER BY d.updated_at DESC, d.id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()


def build_result_key(result):
    parts = [
        result.get("result_type", ""),
        result.get("opening_datetime", ""),
        result.get("business_number", ""),
        result.get("successful_bidder_name", ""),
        result.get("ranking", ""),
        result.get("result_status", ""),
    ]
    return "|".join(str(part or "").strip() for part in parts)
