from __future__ import annotations

from repositories.db_utils import db_cursor, fetch_all, fetch_one


def list_students():
    return fetch_all("SELECT * FROM students ORDER BY roll")


def get_attendance_for_date(attendance_date: str):
    rows = fetch_all(
        """
        SELECT student_id, status
        FROM attendance
        WHERE date=%s
        """,
        (attendance_date,),
    )
    return {row["student_id"]: row["status"] for row in rows}


def save_attendance(student_id: int, attendance_date: str, status: str):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute(
            """
            INSERT INTO attendance (student_id, date, status)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE status=%s
            """,
            (student_id, attendance_date, status, status),
        )


def daily_totals(attendance_date):
    return fetch_one(
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


def attendance_count_for_date(attendance_date):
    row = fetch_one("SELECT COUNT(*) AS count FROM attendance WHERE date=%s", (attendance_date,))
    return row["count"] if row else 0


def attendance_exists_notification(user_id: int, message: str, attendance_date):
    return fetch_one(
        """
        SELECT 1 FROM notifications
        WHERE user_id=%s AND message=%s AND DATE(time)=%s
        LIMIT 1
        """,
        (user_id, message, attendance_date),
    ) is not None


def monthly_averages_for_year():
    return fetch_all(
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


def students_by_status_for_date(attendance_date, status: str):
    return fetch_all(
        """
        SELECT s.id, s.roll, s.first_name, s.last_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date=%s AND a.status=%s
        ORDER BY s.first_name, s.last_name
        """,
        (attendance_date, status),
    )


def attendance_events():
    return fetch_all(
        """
        SELECT date,
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) AS absent,
               SUM(CASE WHEN status='Leave' THEN 1 ELSE 0 END) AS leave_count,
               COUNT(status) AS total
        FROM attendance
        GROUP BY date
        """
    )



def get_student_id_by_roll(roll: str):
    row = fetch_one("SELECT id FROM students WHERE roll=%s LIMIT 1", (roll,))
    return row["id"] if row else None


def attendance_exists(student_id: int, attendance_date: str) -> bool:
    row = fetch_one("SELECT 1 FROM attendance WHERE student_id=%s AND date=%s LIMIT 1", (student_id, attendance_date))
    return row is not None
