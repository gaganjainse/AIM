from __future__ import annotations

from repositories.db_utils import db_cursor, fetch_all, fetch_one


def get_records_per_page_setting(default: int = 10) -> int:
    row = fetch_one("SELECT setting_value FROM settings WHERE setting_name='records_per_page' LIMIT 1")
    try:
        return max(1, int(row["setting_value"])) if row and row.get("setting_value") else default
    except (TypeError, ValueError):
        return default


def list_students(page: int, per_page: int, query: str | None = None):
    offset = (page - 1) * per_page
    if query:
        like = f"%{query}%"
        total = fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM students
            WHERE roll LIKE %s OR first_name LIKE %s OR last_name LIKE %s
            """,
            (like, like, like),
        )["total"]
        rows = fetch_all(
            """
            SELECT *
            FROM students
            WHERE roll LIKE %s OR first_name LIKE %s OR last_name LIKE %s
            ORDER BY roll
            LIMIT %s OFFSET %s
            """,
            (like, like, like, per_page, offset),
        )
    else:
        total = fetch_one("SELECT COUNT(*) AS total FROM students")["total"]
        rows = fetch_all("SELECT * FROM students ORDER BY roll LIMIT %s OFFSET %s", (per_page, offset))
    return total, rows


def student_exists_by_roll(roll: str, exclude_id: int | None = None) -> bool:
    if exclude_id is None:
        row = fetch_one("SELECT 1 FROM students WHERE roll=%s", (roll,))
    else:
        row = fetch_one("SELECT 1 FROM students WHERE roll=%s AND id<>%s", (roll, exclude_id))
    return row is not None


def create_student(roll: str, first_name: str, last_name: str):
    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute("INSERT INTO students (roll, first_name, last_name) VALUES (%s, %s, %s)", (roll, first_name, last_name))
        return cursor.lastrowid


def update_student(student_id: int, roll: str, first_name: str, last_name: str):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("UPDATE students SET roll=%s, first_name=%s, last_name=%s WHERE id=%s", (roll, first_name, last_name, student_id))


def delete_student(student_id: int):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("DELETE FROM students WHERE id=%s", (student_id,))


def get_student(student_id: int):
    return fetch_one("SELECT * FROM students WHERE id=%s", (student_id,))


def get_student_name(student_id: int):
    return fetch_one("SELECT roll, first_name, last_name FROM students WHERE id=%s", (student_id,))


def get_student_profile_stats(student_id: int):
    return fetch_all(
        """
        SELECT status, COUNT(*) AS count
        FROM attendance
        WHERE student_id=%s
        GROUP BY status
        """,
        (student_id,),
    )


def get_student_attendance_records(student_id: int):
    return fetch_all(
        """
        SELECT date, status
        FROM attendance
        WHERE student_id=%s
        ORDER BY date
        """,
        (student_id,),
    )



def get_student_by_roll(roll: str):
    return fetch_one("SELECT id, roll, first_name, last_name FROM students WHERE roll=%s LIMIT 1", (roll,))
