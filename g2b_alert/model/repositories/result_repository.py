import json
from datetime import datetime



class ResultRepository:
    def __init__(self, database):
        self.database = database

    def connect(self):
        return self.database.connect()

    @staticmethod
    def _now_text():
        return datetime.now().isoformat(timespec="seconds")

    def save_result(self, saved_bid, result):
        current = self._now_text()
        result_key = result.result_key
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO bid_results (
                    saved_bid_id, bid_pbanc_no, bid_pbanc_ord, result_type, opening_datetime,
                    successful_bidder_name, business_number, successful_bid_amount,
                    successful_bid_rate, ranking, result_status, result_key, raw_json,
                    detected_at, updated_at
                )
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                FROM saved_bids
                WHERE id = ?
                """,
                (
                    saved_bid.id,
                    saved_bid.bid_no,
                    saved_bid.bid_ord,
                    result.result_type,
                    result.opening_datetime,
                    result.successful_bidder_name,
                    result.business_number,
                    result.successful_bid_amount,
                    result.successful_bid_rate,
                    result.ranking,
                    result.result_status,
                    result_key,
                    json.dumps(result.raw or {}, ensure_ascii=False),
                    current,
                    current,
                    saved_bid.id,
                ),
            )
            if cursor.rowcount == 0:
                parent_exists = connection.execute(
                    "SELECT 1 FROM saved_bids WHERE id = ?",
                    (saved_bid.id,),
                ).fetchone()
                if not parent_exists:
                    return False
                connection.execute(
                    """
                    UPDATE bid_results
                    SET result_status = ?,
                        raw_json = ?,
                        updated_at = ?
                    WHERE saved_bid_id = ? AND result_key = ?
                    """,
                    (
                        result.result_status,
                        json.dumps(result.raw or {}, ensure_ascii=False),
                        current,
                        saved_bid.id,
                        result_key,
                    ),
                )
                return False
            return True

    def list_results(self, saved_bid_id):
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM bid_results
                WHERE saved_bid_id = ?
                ORDER BY detected_at DESC, id DESC
                """,
                (saved_bid_id,),
            ).fetchall()
        results = []
        for row in rows:
            result = dict(row)
            try:
                result["raw"] = json.loads(result.get("raw_json") or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                result["raw"] = {}
            results.append(result)
        return results

    def record_notification(self, saved_bid_id, notification_type, notification_key, message):
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO notification_history (
                    saved_bid_id, notification_type, notification_key, message, notified_at
                )
                SELECT ?, ?, ?, ?, ?
                FROM saved_bids
                WHERE id = ?
                """,
                (
                    saved_bid_id,
                    notification_type,
                    notification_key,
                    message,
                    self._now_text(),
                    saved_bid_id,
                ),
            )
            return cursor.rowcount > 0
