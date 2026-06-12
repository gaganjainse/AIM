from __future__ import annotations

from flask import render_template, request, session

from repositories.db_utils import fetch_all


def _like(value: str) -> str:
    return f"%{value}%"


def search_page():
    q = request.args.get("q", "").strip()
    if not q:
        return render_template("search_results.html", q=q, students=[], users=[], logs=[], attendance=[])

    like = _like(q)
    students = fetch_all(
        """
        SELECT id, roll, first_name, last_name
        FROM students
        WHERE roll LIKE %s OR first_name LIKE %s OR last_name LIKE %s
        ORDER BY roll
        LIMIT 50
        """,
        (like, like, like),
    )

    attendance = fetch_all(
        """
        SELECT s.roll, s.first_name, s.last_name, a.date, a.status
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE s.roll LIKE %s OR s.first_name LIKE %s OR s.last_name LIKE %s OR a.status LIKE %s OR a.date LIKE %s
        ORDER BY a.date DESC
        LIMIT 50
        """,
        (like, like, like, like, like),
    )

    users = []
    logs = []
    if session.get("role") == "admin":
        users = fetch_all(
            """
            SELECT u.id, u.username, u.email, r.role_name
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON r.id = ur.role_id
            WHERE u.username LIKE %s OR u.email LIKE %s OR r.role_name LIKE %s
            ORDER BY u.username
            LIMIT 50
            """,
            (like, like, like),
        )
        logs = fetch_all(
            """
            SELECT l.id, COALESCE(u.username, CONCAT('User #', l.user_id)) AS username, l.action, l.target_table, l.target_id, l.ip_address, l.time
            FROM logs l
            LEFT JOIN users u ON u.id = l.user_id
            WHERE COALESCE(u.username, CONCAT('User #', l.user_id)) LIKE %s OR l.action LIKE %s OR COALESCE(l.target_table, '') LIKE %s
            ORDER BY l.time DESC
            LIMIT 50
            """,
            (like, like, like),
        )

    return render_template("search_results.html", q=q, students=students, users=users, logs=logs, attendance=attendance)
