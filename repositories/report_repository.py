from __future__ import annotations

from repositories.db_utils import db_cursor, fetch_all, fetch_one
from utils.logger import log_action


def get_attendance_threshold(default: float = 75.0) -> float:
    row = fetch_one("SELECT setting_value FROM settings WHERE setting_name='attendance_limit' LIMIT 1")
    try:
        return float(row["setting_value"]) if row and row.get("setting_value") else default
    except (TypeError, ValueError):
        return default


def all_student_attendance_summary():
    return fetch_all(
        """
        SELECT s.roll, s.first_name, s.last_name,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present_days,
               SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absent_days,
               SUM(CASE WHEN a.status='Leave' THEN 1 ELSE 0 END) AS leave_days,
               SUM(CASE WHEN a.status IN ('Present','Absent') THEN 1 ELSE 0 END) AS total_days
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id
        ORDER BY s.roll
        """
    )


def low_attendance_exists(user_id: int, message: str):
    return fetch_one(
        """
        SELECT 1 FROM notifications
        WHERE user_id=%s AND message=%s AND DATE(time)=CURDATE()
        LIMIT 1
        """,
        (user_id, message),
    ) is not None


def export_log(user_id: int, ip_address: str):
    with db_cursor(dictionary=False) as (_, cursor):
        log_action("Exported attendance report", user_id=user_id, ip_address=ip_address, target_table="attendance", target_id=None)
