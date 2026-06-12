from __future__ import annotations

from functools import lru_cache

from repositories.db_utils import db_cursor, fetch_all, fetch_one
from utils.logger import log_action, log_action_on_cursor


def find_user_for_login(username: str):
    return fetch_one(
        """
        SELECT u.id, u.username, u.password, u.email, u.email_notifications,
               u.theme, u.records_per_page, u.last_ip,
               u.failed_login_attempts, u.locked_until, r.role_name
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        WHERE u.username=%s
        """,
        (username,),
    )


@lru_cache(maxsize=4096)
def get_session_token(user_id: int):
    row = fetch_one("SELECT session_token FROM users WHERE id=%s", (user_id,))
    return row["session_token"] if row else None


def set_login_success(user_id: int, new_ip: str, token: str):
    with db_cursor(dictionary=False) as (conn, cursor):
        cursor.execute(
            """
            UPDATE users
            SET failed_login_attempts = 0,
                locked_until = NULL,
                last_login = NOW(),
                last_ip = %s,
                session_token = %s
            WHERE id = %s
            """,
            (new_ip, token, user_id),
        )
        log_action_on_cursor(cursor, "Logged in", user_id=user_id, ip_address=new_ip, target_table="users", target_id=user_id)
    get_session_token.cache_clear()


def increment_failed_attempts(user_id: int, attempts: int):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("UPDATE users SET failed_login_attempts = %s WHERE id = %s", (attempts, user_id))


def lock_account(user_id: int, attempts: int, lock_minutes: int):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute(
            """
            UPDATE users
            SET failed_login_attempts = %s,
                locked_until = DATE_ADD(NOW(), INTERVAL %s MINUTE)
            WHERE id = %s
            """,
            (attempts, lock_minutes, user_id),
        )


def clear_session_token(user_id: int, ip_address: str | None = None, action: str | None = None):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("UPDATE users SET session_token = NULL WHERE id = %s", (user_id,))
        if action:
            log_action_on_cursor(cursor, action, user_id=user_id, ip_address=ip_address, target_table="users", target_id=user_id)
    get_session_token.cache_clear()


def update_theme(user_id: int, theme: str, ip_address: str | None = None):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("UPDATE users SET theme=%s WHERE id=%s", (theme, user_id))
        if ip_address:
            log_action_on_cursor(cursor, "Changed theme", user_id=user_id, ip_address=ip_address, target_table="users", target_id=user_id)


def get_account_profile(user_id: int):
    return fetch_one(
        """
        SELECT
            u.id,
            u.username,
            u.email,
            u.email_notifications,
            r.role_name AS role,
            u.theme,
            u.records_per_page,
            u.created_at,
            u.last_login,
            COALESCE(uns.low_attendance, TRUE) AS low_attendance,
            COALESCE(uns.password_change, TRUE) AS password_change,
            COALESCE(uns.new_student, TRUE) AS new_student,
            COALESCE(uns.attendance_saved, TRUE) AS attendance_saved,
            COALESCE(uns.system_alerts, TRUE) AS system_alerts,
            COALESCE(uns.login_alerts, TRUE) AS login_alerts,
            COALESCE(uns.attendance_updates, TRUE) AS attendance_updates,
            COALESCE(uns.role_changes, TRUE) AS role_changes,
            COALESCE(uns.account_locked, TRUE) AS account_locked,
            COALESCE(uns.backup_completed, TRUE) AS backup_completed
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        LEFT JOIN user_notification_settings uns ON uns.user_id = u.id
        WHERE u.id = %s
        """,
        (user_id,),
    )


def get_login_activity(user_id: int, limit: int = 5):
    return fetch_all(
        """
        SELECT action, ip_address, time
        FROM logs
        WHERE user_id = %s
          AND action IN ('Logged in', 'Logged out', 'Changed password', 'Changed theme', 'Updated account preferences', 'Updated notification settings', 'Logged out other sessions')
        ORDER BY time DESC
        LIMIT %s
        """,
        (user_id, limit),
    )


def get_permissions(user_id: int):
    rows = fetch_all(
        """
        SELECT DISTINCT p.permission_name AS name
        FROM permissions p
        JOIN role_permissions rp ON p.id = rp.permission_id
        JOIN user_roles ur ON ur.role_id = rp.role_id
        WHERE ur.user_id = %s
        ORDER BY p.permission_name
        """,
        (user_id,),
    )
    return [row["name"] for row in rows]


def update_password(user_id: int, password_hash: str, ip_address: str | None = None):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute("UPDATE users SET password=%s WHERE id=%s", (password_hash, user_id))
        if ip_address:
            log_action_on_cursor(cursor, "Changed password", user_id=user_id, ip_address=ip_address, target_table="users", target_id=user_id)


def get_password_hash(user_id: int):
    row = fetch_one("SELECT password FROM users WHERE id=%s", (user_id,))
    return row["password"] if row else None


def update_preferences(user_id: int, theme: str, records_per_page: int, email: str | None, email_notifications: int, ip_address: str | None = None):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute(
            """
            UPDATE users
            SET theme = %s,
                records_per_page = %s,
                email = %s,
                email_notifications = %s
            WHERE id = %s
            """,
            (theme, records_per_page, email, email_notifications, user_id),
        )
        if ip_address:
            log_action_on_cursor(cursor, "Updated account preferences", user_id=user_id, ip_address=ip_address, target_table="users", target_id=user_id)


def upsert_notification_settings(user_id: int, toggles: dict[str, bool], ip_address: str | None = None):
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute(
            """
            INSERT INTO user_notification_settings (
                user_id, low_attendance, password_change, new_student, attendance_saved,
                system_alerts, login_alerts, attendance_updates, role_changes, account_locked, backup_completed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                low_attendance = VALUES(low_attendance),
                password_change = VALUES(password_change),
                new_student = VALUES(new_student),
                attendance_saved = VALUES(attendance_saved),
                system_alerts = VALUES(system_alerts),
                login_alerts = VALUES(login_alerts),
                attendance_updates = VALUES(attendance_updates),
                role_changes = VALUES(role_changes),
                account_locked = VALUES(account_locked),
                backup_completed = VALUES(backup_completed)
            """,
            (
                user_id,
                int(toggles["low_attendance"]),
                int(toggles["password_change"]),
                int(toggles["new_student"]),
                int(toggles["attendance_saved"]),
                int(toggles["system_alerts"]),
                int(toggles["login_alerts"]),
                int(toggles["attendance_updates"]),
                int(toggles["role_changes"]),
                int(toggles["account_locked"]),
                int(toggles["backup_completed"]),
            ),
        )
        if ip_address:
            log_action_on_cursor(cursor, "Updated notification settings", user_id=user_id, ip_address=ip_address, target_table="user_notification_settings", target_id=user_id)
