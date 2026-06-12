from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps
from typing import Callable

from flask import abort, session

from repositories.permission_repository import user_has_permission
from repositories.system_repository import get_setting

ROLE_DEFAULT_PERMISSIONS: dict[str, set[str]] = {
    "teacher": {"mark_attendance", "view_reports", "export_reports"},
}

_POLICY_LABELS: dict[str, str] = {
    "current_week_only": "Current week only",
    "current_month_only": "Current month only",
    "current_semester_only": "Current semester only",
}

_SCOPE_LABELS: dict[str, str] = {
    "current_week_only": "current week",
    "current_month_only": "current month",
    "current_semester_only": "current semester",
}

_POLICY_ALIASES: dict[str, str] = {
    "current week only": "current_week_only",
    "current month only": "current_month_only",
    "current semester only": "current_semester_only",
}


def normalize_teacher_policy(value: str | None) -> str:
    raw = (value or "current_week_only").strip().lower()
    return _POLICY_ALIASES.get(raw, raw if raw in _POLICY_LABELS else "current_week_only")


def teacher_calendar_policy_label() -> str:
    return _POLICY_LABELS.get(normalize_teacher_policy(get_setting("teacher_calendar_policy")), "Current week only")


def teacher_calendar_scope_label() -> str:
    return _SCOPE_LABELS.get(normalize_teacher_policy(get_setting("teacher_calendar_policy")), "current week")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def teacher_edit_window(today: date | None = None) -> tuple[date, date, str]:
    today = today or date.today()
    policy = normalize_teacher_policy(get_setting("teacher_calendar_policy"))
    semester_start = _parse_date(get_setting("semester_start_date"))
    semester_end = _parse_date(get_setting("semester_end_date"))

    if policy == "current_month_only":
        start = today.replace(day=1)
    elif policy == "current_semester_only":
        start = semester_start or today.replace(month=1, day=1)
    else:
        start = today - timedelta(days=today.weekday())

    if semester_start and start < semester_start:
        start = semester_start

    end = today
    if semester_end and semester_end < end:
        end = semester_end

    if start > end:
        start = end

    return start, end, policy


def teacher_policy_range_text() -> str:
    start, end, _ = teacher_edit_window()
    return f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"


def get_system_settings() -> dict:
    settings: dict = {}
    try:
        from repositories.system_repository import fetch_settings_map
        settings = fetch_settings_map()
    except Exception:
        settings = {}
    return settings


def get_setting_value(setting_name: str, default: str | None = None) -> str | None:
    return get_setting(setting_name, default)


def has_permission(permission_name: str) -> bool:
    role = session.get("role")
    if role == "admin":
        return True
    if role in ROLE_DEFAULT_PERMISSIONS and permission_name in ROLE_DEFAULT_PERMISSIONS[role]:
        return True
    user_id = session.get("user_id")
    if not user_id:
        return False
    return user_has_permission(int(user_id), permission_name)


def permission_required(permission: str) -> Callable:
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_permission(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
