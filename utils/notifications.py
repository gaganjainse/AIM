from __future__ import annotations

import logging
import threading
from typing import Optional

from flask import current_app

from repositories.system_repository import fetch_notification_profile
from utils.email import send_email

logger = logging.getLogger(__name__)

PREF_COLUMNS: dict[str, str] = {
    "password_change": "password_change",
    "low_attendance": "low_attendance",
    "new_student": "new_student",
    "attendance_saved": "attendance_saved",
    "system_alerts": "system_alerts",
    "login_alerts": "login_alerts",
    "attendance_updates": "attendance_updates",
    "role_changes": "role_changes",
    "account_locked": "account_locked",
    "backup_completed": "backup_completed",
}


def ensure_user_notification_settings(cursor, user_id: int) -> None:
    cursor.execute(
        """
        INSERT INTO user_notification_settings (user_id)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE user_id = user_id
        """,
        (user_id,),
    )


def get_notification_profile(user_id: int) -> dict:
    return fetch_notification_profile(user_id)


def create_notification(
    user_id: int,
    message: str,
    *,
    pref_key: str | None = None,
    email_subject: str | None = None,
    email_body: str | None = None,
) -> bool:
    try:
        from database.db import get_db_connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                (user_id, message),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.error("Notification insert error: %s", exc, exc_info=True)
        return False

    if pref_key and email_subject and email_body:
        profile = get_notification_profile(user_id)
        pref_enabled = bool(profile.get("email_notifications")) and bool(profile.get(pref_key, True))
        recipient = profile.get("email")
        if pref_enabled and recipient:
            try:
                app = current_app._get_current_object()
            except Exception:
                app = None
            if app is not None:
                def _send_async() -> None:
                    with app.app_context():
                        send_email(recipient, email_subject, email_body)
                threading.Thread(target=_send_async, daemon=True).start()
            else:
                send_email(recipient, email_subject, email_body)
    return True
