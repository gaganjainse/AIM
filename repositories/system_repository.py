from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from flask import current_app

from repositories.db_utils import db_cursor

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS: dict[str, str] = {
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

LEGACY_ALIASES: dict[str, str] = {
    "semester_name": "year",
}


def fetch_settings_rows() -> list[dict]:
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute("SELECT setting_name, setting_value FROM settings ORDER BY setting_name")
        return cursor.fetchall()


@lru_cache(maxsize=1)
def fetch_settings_map() -> dict[str, str]:
    rows = fetch_settings_rows()
    settings = {row["setting_name"]: row["setting_value"] for row in rows}
    for legacy, modern in LEGACY_ALIASES.items():
        if modern not in settings and legacy in settings:
            settings[modern] = settings[legacy]
        if legacy not in settings and modern in settings:
            settings[legacy] = settings[modern]
    return settings


def clear_settings_cache() -> None:
    fetch_settings_map.cache_clear()


def get_setting(setting_name: str, default: str | None = None) -> str | None:
    try:
        settings = fetch_settings_map()
        return settings.get(setting_name, default)
    except Exception:
        return default


def fetch_unread_notifications(user_id: int, limit: int = 5) -> list[dict]:
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT id, message, is_read, time
            FROM notifications
            WHERE user_id=%s AND is_read=FALSE
            ORDER BY time DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        return cursor.fetchall()


def fetch_notification_profile(user_id: int) -> dict:
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT
                u.email,
                COALESCE(u.email_notifications, TRUE) AS email_notifications,
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
            LEFT JOIN user_notification_settings uns ON uns.user_id = u.id
            WHERE u.id = %s
            """,
            (user_id,),
        )
        return cursor.fetchone() or {}


def fetch_permissions(user_id: int) -> list[str]:
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
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
        return [row["name"] for row in cursor.fetchall()]


def fetch_login_activity(user_id: int, limit: int = 5) -> list[dict]:
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
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
        return cursor.fetchall()


def ensure_default_settings(cursor) -> bool:
    cursor.execute("SELECT setting_name, setting_value FROM settings")
    existing = {row["setting_name"]: row["setting_value"] for row in cursor.fetchall()}
    changed = False

    if "year" not in existing and "semester_name" in existing:
        cursor.execute(
            "INSERT INTO settings (setting_name, setting_value) VALUES (%s, %s)",
            ("year", existing["semester_name"]),
        )
        existing["year"] = existing["semester_name"]
        changed = True

    if "teacher_calendar_policy" in existing:
        value = existing["teacher_calendar_policy"]
        normalized = {
            "Current week only": "current_week_only",
            "Current month only": "current_month_only",
            "Current semester only": "current_semester_only",
        }.get(value, value)
        if normalized != value:
            cursor.execute("UPDATE settings SET setting_value=%s WHERE setting_name='teacher_calendar_policy'", (normalized,))
            changed = True

    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            cursor.execute("INSERT INTO settings (setting_name, setting_value) VALUES (%s, %s)", (key, value))
            changed = True

    return changed
