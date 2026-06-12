from __future__ import annotations

from typing import Optional

from repositories.db_utils import fetch_all, fetch_one


def total_students():
    row = fetch_one("SELECT COUNT(*) AS total FROM students")
    return row["total"] if row else 0


def today_summary(today):
    row = fetch_one(
        """
        SELECT
            SUM(status='Present') AS present,
            SUM(status='Absent') AS absent,
            SUM(status='Leave') AS leave_count
        FROM attendance
        WHERE date=%s
        """,
        (today,),
    ) or {}
    return {
        "present": row.get("present") or 0,
        "absent": row.get("absent") or 0,
        "leave": row.get("leave_count") or 0,
    }


def daily_totals(attendance_date):
    row = fetch_one(
        """
        SELECT
            SUM(status='Present') AS present,
            SUM(status='Absent') AS absent,
            SUM(status='Leave') AS leave_count
        FROM attendance
        WHERE date=%s
        """,
        (attendance_date,),
    ) or {}
    return {
        "present": row.get("present") or 0,
        "absent": row.get("absent") or 0,
        "leave_count": row.get("leave_count") or 0,
    }


def attendance_today_count(today):
    row = fetch_one("SELECT COUNT(*) AS count FROM attendance WHERE date=%s", (today,))
    return row["count"] if row else 0


def missing_attendance_notice_exists(user_id: int, today):
    return fetch_one(
        """
        SELECT 1 FROM notifications
        WHERE user_id=%s AND message=%s AND DATE(time)=%s
        LIMIT 1
        """,
        (user_id, "Attendance not marked today", today),
    ) is not None


def monthly_progress():
    rows = fetch_all(
        """
        SELECT MONTH(date) AS month,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present_days,
               COUNT(*) AS total_days
        FROM attendance
        WHERE YEAR(date) = YEAR(CURDATE())
        GROUP BY MONTH(date)
        ORDER BY MONTH(date)
        """
    )
    months = [0] * 12
    for row in rows:
        if row["total_days"]:
            months[row["month"] - 1] = round((row["present_days"] / row["total_days"]) * 100, 2)
    return months


def recent_attendance(limit: int = 5):
    return fetch_all(
        """
        SELECT s.first_name, s.last_name, a.status, a.date
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        ORDER BY a.date DESC, a.id DESC
        LIMIT %s
        """,
        (limit,),
    )


def attendance_for_date(attendance_date, limit: Optional[int] = None):
    query = """
        SELECT s.first_name, s.last_name, s.roll, a.status, a.date
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date=%s
        ORDER BY a.id DESC
    """
    params = [attendance_date]
    if limit is not None:
        query += "\n        LIMIT %s"
        params.append(limit)
    return fetch_all(query, tuple(params))


def all_students_minimal():
    return fetch_all("SELECT id, roll, first_name, last_name FROM students ORDER BY first_name, last_name")


def students_by_status(today, status: str):
    return fetch_all(
        """
        SELECT s.id, s.roll, s.first_name, s.last_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date=%s AND a.status=%s
        ORDER BY s.first_name, s.last_name
        """,
        (today, status),
    )
