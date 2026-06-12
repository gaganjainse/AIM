from __future__ import annotations

from repositories.db_utils import db_cursor, fetch_all, fetch_one
from functools import lru_cache

DEFAULT_SETTINGS = {
    "system_name": "AIM",
    "attendance_limit": "75",
    "login_tagline": "Track attendance without the clutter",
    "year": "2026-27",
    "teacher_calendar_policy": "current_week_only",
    "semester_start_date": "2026-01-01",
    "semester_end_date": "2026-12-31",
    "backup_retention_days": "30",
    "max_login_attempts": "5",
    "login_lock_minutes": "15",
}

POLICY_LABEL_TO_VALUE = {
    "Current week only": "current_week_only",
    "Current month only": "current_month_only",
    "Current semester only": "current_semester_only",
}


def ensure_default_settings(cursor) -> bool:
    cursor.execute("SELECT setting_name, setting_value FROM settings")
    existing = {row["setting_name"]: row["setting_value"] for row in cursor.fetchall()}
    changed = False

    if "year" not in existing and "semester_name" in existing:
        cursor.execute("INSERT INTO settings (setting_name, setting_value) VALUES (%s, %s)", ("year", existing["semester_name"]))
        existing["year"] = existing["semester_name"]
        changed = True

    if "teacher_calendar_policy" in existing:
        normalized = POLICY_LABEL_TO_VALUE.get(existing["teacher_calendar_policy"], existing["teacher_calendar_policy"])
        if normalized != existing["teacher_calendar_policy"]:
            cursor.execute("UPDATE settings SET setting_value=%s WHERE setting_name='teacher_calendar_policy'", (normalized,))
            changed = True

    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            cursor.execute("INSERT INTO settings (setting_name, setting_value) VALUES (%s, %s)", (key, value))
            changed = True

    return changed


def list_users():
    return fetch_all(
        """
        SELECT u.id, u.username, u.email, r.role_name
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        ORDER BY u.username
        """
    )


def list_roles():
    return fetch_all("SELECT * FROM roles ORDER BY role_name")


def username_exists(username: str):
    return fetch_one("SELECT 1 FROM users WHERE username=%s", (username,)) is not None


def create_user(username: str, password_hash: str, email: str | None, role_id: int):
    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute(
            "INSERT INTO users (username, password, email, email_notifications) VALUES (%s, %s, %s, %s)",
            (username, password_hash, email, 1 if email else 0),
        )
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)", (user_id, role_id))
        return cursor, user_id


def get_user_username(user_id: int):
    row = fetch_one("SELECT username FROM users WHERE id=%s", (user_id,))
    return row["username"] if row else None


def delete_user(user_id: int):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))


def reset_user_password(user_id: int, password_hash: str):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("UPDATE users SET password=%s WHERE id=%s", (password_hash, user_id))



@lru_cache(maxsize=1)
def _log_columns() -> set[str]:
    try:
        from repositories.db_utils import db_cursor
        with db_cursor(dictionary=False) as (_, cursor):
            cursor.execute(
                """
                SELECT COLUMN_NAME
                FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = 'logs'
                """
            )
            columns = {row[0] for row in cursor.fetchall()}
        return columns
    except Exception:
        return {"user_id", "action", "ip_address", "time"}


def list_logs(page: int = 1, per_page: int = 20, q: str | None = None):
    offset = max(page - 1, 0) * per_page
    where = ""
    params: list = []
    if q:
        where = "WHERE (COALESCE(u.username, CONCAT('User #', l.user_id)) LIKE %s OR l.action LIKE %s)"
        like = f"%{q}%"
        params = [like, like]

    columns = _log_columns()
    has_target = {"target_table", "target_id"}.issubset(columns)
    target_select = "l.target_table, l.target_id" if has_target else "NULL AS target_table, NULL AS target_id"

    sql = f"""
        SELECT COALESCE(u.username, CONCAT('User #', l.user_id)) AS username,
               l.action,
               {target_select},
               l.ip_address,
               l.time
        FROM logs l
        LEFT JOIN users u ON l.user_id = u.id
        {where}
        ORDER BY l.time DESC, l.id DESC
        LIMIT %s OFFSET %s
    """
    params.extend([per_page, offset])
    return fetch_all(sql, tuple(params))


def count_logs(q: str | None = None) -> int:
    where = ""
    params: list = []
    if q:
        where = "WHERE (COALESCE(u.username, CONCAT('User #', l.user_id)) LIKE %s OR l.action LIKE %s)"
        like = f"%{q}%"
        params = [like, like]
    row = fetch_one(
        f"""
        SELECT COUNT(*) AS total
        FROM logs l
        LEFT JOIN users u ON l.user_id = u.id
        {where}
        """,
        tuple(params),
    )
    return int(row["total"]) if row else 0


def backup_retention_days(default: int = 30):
    row = fetch_one("SELECT setting_value FROM settings WHERE setting_name='backup_retention_days' LIMIT 1")
    try:
        return max(1, int(row["setting_value"])) if row and row.get("setting_value") else default
    except (TypeError, ValueError):
        return default


def get_settings_rows():
    return fetch_all("SELECT setting_name, setting_value FROM settings ORDER BY setting_name")


def get_setting_value(setting_name: str):
    row = fetch_one("SELECT setting_value FROM settings WHERE setting_name=%s LIMIT 1", (setting_name,))
    return row["setting_value"] if row else None


def upsert_setting(setting_name: str, setting_value: str):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute(
            """
            INSERT INTO settings (setting_name, setting_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)
            """,
            (setting_name, setting_value),
        )
    try:
        from repositories.system_repository import clear_settings_cache
        clear_settings_cache()
    except Exception:
        pass


def mark_notifications_read(user_id: int):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("UPDATE notifications SET is_read = TRUE WHERE user_id=%s", (user_id,))


def clear_logs():
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("DELETE FROM logs")



def list_permissions():
    return fetch_all("SELECT * FROM permissions ORDER BY permission_name")


def get_role_permissions(role_id: int):
    rows = fetch_all(
        """
        SELECT p.permission_name AS name, p.id
        FROM permissions p
        JOIN role_permissions rp ON p.id = rp.permission_id
        WHERE rp.role_id = %s
        ORDER BY p.permission_name
        """,
        (role_id,),
    )
    return rows


def set_role_permissions(role_id: int, permission_ids: list[int]):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("DELETE FROM role_permissions WHERE role_id=%s", (role_id,))
        for permission_id in permission_ids:
            cursor.execute(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s)",
                (role_id, permission_id),
            )
