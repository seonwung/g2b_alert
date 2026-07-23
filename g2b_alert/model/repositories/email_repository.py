from datetime import datetime

class EmailRepository:
    def __init__(self, database):
        self.database = database

    def connect(self):
        return self.database.connect()

    @staticmethod
    def _now_text():
        return datetime.now().isoformat(timespec="seconds")

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
                (keywords or "", 1 if email_enabled else 0, self._now_text()),
            )

    def list_recipients(self, active_only=True):
        where = "WHERE active = 1" if active_only else ""
        with self.connect() as connection:
            return connection.execute(
                f"""
                SELECT * FROM recipients
                {where}
                ORDER BY is_default DESC, name COLLATE NOCASE, email COLLATE NOCASE
                """
            ).fetchall()

    def save_recipient(
        self,
        name,
        email,
        recipient_id=None,
        organization="",
        memo="",
        is_default=False,
    ):
        current = self._now_text()
        name = (name or "").strip()
        email = (email or "").strip().lower()
        organization = (organization or "").strip()
        memo = (memo or "").strip()
        with self.connect() as connection:
            if recipient_id:
                connection.execute(
                    """
                    UPDATE recipients
                    SET name = ?, email = ?, organization = ?, memo = ?,
                        is_default = ?, active = 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        email,
                        organization,
                        memo,
                        1 if is_default else 0,
                        current,
                        recipient_id,
                    ),
                )
                return int(recipient_id)
            existing = connection.execute(
                "SELECT id FROM recipients WHERE email = ? COLLATE NOCASE",
                (email,),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE recipients
                    SET name = ?, organization = ?, memo = ?, is_default = ?,
                        active = 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        organization,
                        memo,
                        1 if is_default else 0,
                        current,
                        existing["id"],
                    ),
                )
                return existing["id"]
            cursor = connection.execute(
                """
                INSERT INTO recipients (
                    name, email, organization, memo, is_default,
                    active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    name,
                    email,
                    organization,
                    memo,
                    1 if is_default else 0,
                    current,
                    current,
                ),
            )
            return cursor.lastrowid

    def deactivate_recipient(self, recipient_id):
        with self.connect() as connection:
            connection.execute(
                "UPDATE recipients SET active = 0, updated_at = ? WHERE id = ?",
                (self._now_text(), recipient_id),
            )
            connection.execute("DELETE FROM keyword_recipient_map WHERE recipient_id = ?", (recipient_id,))
            connection.execute("DELETE FROM keyword_rule_recipient_map WHERE recipient_id = ?", (recipient_id,))
            connection.execute("DELETE FROM saved_bid_recipient_map WHERE recipient_id = ?", (recipient_id,))

    def sync_keyword_rules(self, rules):
        """Keep persistent recipient targets aligned with config-backed rules."""
        current = self._now_text()
        rows = [
            (str(rule.get("id") or ""), str(rule.get("name") or rule.get("keyword") or ""), current)
            for rule in rules or [] if str(rule.get("id") or "")
        ]
        active_ids = {row[0] for row in rows}
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO keyword_rule_settings (rule_id, name, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(rule_id) DO UPDATE SET name=excluded.name, updated_at=excluded.updated_at
                """,
                rows,
            )
            stored = connection.execute("SELECT rule_id FROM keyword_rule_settings").fetchall()
            stale = [row["rule_id"] for row in stored if row["rule_id"] not in active_ids]
            connection.executemany("DELETE FROM keyword_rule_settings WHERE rule_id = ?", [(value,) for value in stale])

    def get_keyword_rule_recipient_ids(self, rule_id):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT recipient_id FROM keyword_rule_recipient_map WHERE rule_id = ?",
                (str(rule_id),),
            ).fetchall()
        return {row["recipient_id"] for row in rows}

    def set_keyword_rule_recipients(self, rule_id, recipient_ids):
        current = self._now_text()
        recipient_ids = {int(value) for value in recipient_ids}
        with self.connect() as connection:
            connection.execute(
                "UPDATE keyword_rule_settings SET recipient_configured = 1, updated_at = ? WHERE rule_id = ?",
                (current, str(rule_id)),
            )
            connection.execute("DELETE FROM keyword_rule_recipient_map WHERE rule_id = ?", (str(rule_id),))
            connection.executemany(
                "INSERT INTO keyword_rule_recipient_map (rule_id, recipient_id, created_at) VALUES (?, ?, ?)",
                [(str(rule_id), value, current) for value in sorted(recipient_ids)],
            )

    def get_keyword_rule_email_recipients(self, rule_ids):
        rule_ids = tuple(dict.fromkeys(str(value) for value in rule_ids if value))
        if not rule_ids:
            return self.get_keyword_email_recipients()
        placeholders = ",".join("?" for _ in rule_ids)
        with self.connect() as connection:
            configured = connection.execute(
                f"SELECT COUNT(*) AS count FROM keyword_rule_settings WHERE rule_id IN ({placeholders}) AND recipient_configured = 1",
                rule_ids,
            ).fetchone()["count"]
            if not configured:
                return self.get_keyword_email_recipients()
            mapped = connection.execute(
                f"""
                SELECT DISTINCT r.* FROM recipients r
                JOIN keyword_rule_recipient_map m ON m.recipient_id = r.id
                WHERE m.rule_id IN ({placeholders}) AND r.active = 1
                ORDER BY r.name COLLATE NOCASE
                """,
                rule_ids,
            ).fetchall()
        if configured == len(rule_ids):
            return mapped
        # Unconfigured legacy rules continue using the former global recipients.
        combined = {row["id"]: row for row in mapped}
        combined.update({row["id"]: row for row in self.get_keyword_email_recipients()})
        return sorted(combined.values(), key=lambda row: (row["name"].casefold(), row["email"].casefold()))

    def get_keyword_recipient_ids(self):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT recipient_id FROM keyword_recipient_map WHERE keyword_setting_id = 1"
            ).fetchall()
        return {row["recipient_id"] for row in rows}

    def set_keyword_recipients(self, recipient_ids):
        current = self._now_text()
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
        current = self._now_text()
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

    def create_email_event(
        self, event_key, event_type, source_ref, subject, body, recipients, body_html=""
    ):
        current = self._now_text()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO email_events (
                    event_key, event_type, source_ref, subject, body, body_html, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_key, event_type, source_ref, subject, body, body_html or "", current),
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
                (self._now_text(),),
            )

    def claim_next_email_delivery(self):
        current = self._now_text()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT d.*, e.event_key, e.event_type, e.subject, e.body, e.body_html
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
        current = self._now_text()
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
