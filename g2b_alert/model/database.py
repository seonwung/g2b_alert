import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .storage_paths import get_persistent_data_dir
from .repositories.bid_repository import BidRepository
from .repositories.email_repository import EmailRepository
from .repositories.result_repository import ResultRepository


DB_FILE = get_persistent_data_dir() / "g2b_alert.db"


def now_text():
    return datetime.now().isoformat(timespec="seconds")


class G2BDatabase:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()
        self.bids = BidRepository(self)
        self.results = ResultRepository(self)
        self.email = EmailRepository(self)

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
                    pre_spec_no TEXT NOT NULL DEFAULT '',
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

                CREATE TABLE IF NOT EXISTS notice_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    saved_bid_id INTEGER NOT NULL,
                    bid_pbanc_no TEXT NOT NULL,
                    bid_pbanc_ord TEXT NOT NULL DEFAULT '',
                    raw_json TEXT NOT NULL DEFAULT '{}',
                    notice_name TEXT,
                    bid_close_at TEXT,
                    opening_at TEXT,
                    consortium_close_at TEXT,
                    budget_amount TEXT,
                    demand_institution_name TEXT,
                    registered_at TEXT,
                    detected_at TEXT NOT NULL,
                    is_current INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(saved_bid_id) REFERENCES saved_bids(id) ON DELETE CASCADE,
                    UNIQUE(saved_bid_id, bid_pbanc_no, bid_pbanc_ord)
                );

                CREATE INDEX IF NOT EXISTS idx_notice_versions_current
                    ON notice_versions(saved_bid_id, is_current, detected_at);

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
                    organization TEXT NOT NULL DEFAULT '',
                    memo TEXT NOT NULL DEFAULT '',
                    is_default INTEGER NOT NULL DEFAULT 0,
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

                CREATE TABLE IF NOT EXISTS keyword_rule_settings (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT '',
                    recipient_configured INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS keyword_rule_recipient_map (
                    rule_id TEXT NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(rule_id, recipient_id),
                    FOREIGN KEY(rule_id) REFERENCES keyword_rule_settings(rule_id) ON DELETE CASCADE,
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
                    body_html TEXT NOT NULL DEFAULT '',
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

                CREATE TABLE IF NOT EXISTS seen_bid_alerts (
                    bid_unique_id TEXT PRIMARY KEY,
                    alerted_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS monitor_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            email_event_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(email_events)").fetchall()
            }
            if "body_html" not in email_event_columns:
                connection.execute(
                    "ALTER TABLE email_events ADD COLUMN body_html TEXT NOT NULL DEFAULT ''"
                )
            recipient_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(recipients)").fetchall()
            }
            for column, definition in (
                ("organization", "TEXT NOT NULL DEFAULT ''"),
                ("memo", "TEXT NOT NULL DEFAULT ''"),
                ("is_default", "INTEGER NOT NULL DEFAULT 0"),
            ):
                if column not in recipient_columns:
                    connection.execute(f"ALTER TABLE recipients ADD COLUMN {column} {definition}")
            keyword_rule_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(keyword_rule_settings)").fetchall()
            }
            if "recipient_configured" not in keyword_rule_columns:
                connection.execute(
                    "ALTER TABLE keyword_rule_settings ADD COLUMN recipient_configured INTEGER NOT NULL DEFAULT 0"
                )
            saved_bid_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(saved_bids)").fetchall()
            }
            if "pre_spec_no" not in saved_bid_columns:
                connection.execute(
                    "ALTER TABLE saved_bids ADD COLUMN pre_spec_no TEXT NOT NULL DEFAULT ''"
                )
            connection.execute(
                """
                INSERT OR IGNORE INTO notice_versions (
                    saved_bid_id, bid_pbanc_no, bid_pbanc_ord, raw_json, notice_name,
                    bid_close_at, opening_at, consortium_close_at, budget_amount,
                    demand_institution_name, registered_at, detected_at, is_current
                )
                SELECT
                    id, bid_pbanc_no, bid_pbanc_ord, COALESCE(raw_json, '{}'), bid_name,
                    bid_end_datetime, opening_datetime, '', budget_amount,
                    demand_organization_name, saved_at, saved_at, 1
                FROM saved_bids
                WHERE status <> 'pre_spec'
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO keyword_settings (id, name, keywords, email_enabled, updated_at)
                VALUES (1, '기본 키워드 감시', '', 0, ?)
                """,
                (now_text(),),
            )
