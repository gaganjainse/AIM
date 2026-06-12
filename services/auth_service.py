from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Optional

from flask import current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash as werkzeug_check, generate_password_hash as werkzeug_generate

from config import Config
from repositories.auth_repository import (
    clear_session_token,
    find_user_for_login,
    get_account_profile,
    get_login_activity,
    get_password_hash,
    get_permissions,
    get_session_token,
    increment_failed_attempts,
    lock_account,
    set_login_success,
    update_password,
    update_preferences,
    update_theme,
    upsert_notification_settings,
)
from repositories.system_repository import get_setting
from routes.permissions import ROLE_DEFAULT_PERMISSIONS, teacher_calendar_policy_label, teacher_policy_range_text
from utils.notifications import create_notification

logger = logging.getLogger(__name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s'.-]{0,49}$")

# ── Argon2id Password Hasher ────────────────────────────────────────────────
from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import VerifyMismatchError

_argon2 = _Argon2Hasher(
    time_cost=Config.ARGON2_TIME_COST,
    memory_cost=Config.ARGON2_MEMORY_COST,
    parallelism=Config.ARGON2_PARALLELISM,
)


def _hash_password(password: str) -> str:
    """Hash password with Argon2id."""
    return _argon2.hash(password)


def _verify_password(stored_hash: str, provided: str) -> bool:
    """Verify password. Supports both Argon2id and legacy Werkzeug PBKDF2."""
    if stored_hash.startswith("$argon2"):
        try:
            return _argon2.verify(stored_hash, provided)
        except VerifyMismatchError:
            return False
    # Legacy Werkzeug hash
    return werkzeug_check(stored_hash, provided)


def password_policy_error(password: str) -> str | None:
    if len(password or "") < 8:
        return "Password must be at least 8 characters long."
    if not any(ch.isdigit() for ch in password):
        return "Password must contain at least one number."
    if not any(ch.isupper() for ch in password):
        return "Password must contain at least one uppercase letter."
    if not any(ch.islower() for ch in password):
        return "Password must contain at least one lowercase letter."
    # Check against breached password database
    from utils.crypto import is_password_breached
    if is_password_breached(password):
        return "This password has been found in a data breach. Please choose a different password."
    return None


def valid_username(username: str) -> bool:
    return bool(USERNAME_RE.fullmatch(username or ""))


def valid_person_name(value: str) -> bool:
    return bool(NAME_RE.fullmatch(value or ""))


def login_required_session_check() -> bool:
    if not session.get("user_id"):
        return False
    if session.get("server_boot_id") != current_app.config.get("SERVER_BOOT_ID"):
        session.clear()
        return False
    token = get_session_token(int(session["user_id"]))
    if not token or token != session.get("session_token"):
        session.clear()
        return False
    return True


def session_status_response() -> tuple[dict, int]:
    user_id = session.get("user_id")
    if not user_id or session.get("server_boot_id") != current_app.config.get("SERVER_BOOT_ID"):
        session.clear()
        return {"active": False}, 401
    token = get_session_token(int(user_id))
    if not token or token != session.get("session_token"):
        session.clear()
        return {"active": False}, 401
    return {"active": True}, 200


def login_user() -> str:
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Username and password are required.")
            return render_template("login.html")

        user = find_user_for_login(username)
        max_attempts = int(get_setting("max_login_attempts", Config.MAX_LOGIN_ATTEMPTS) or Config.MAX_LOGIN_ATTEMPTS)
        lock_minutes = int(get_setting("login_lock_minutes", Config.LOGIN_LOCK_MINUTES) or Config.LOGIN_LOCK_MINUTES)

        if not user:
            flash("Invalid login")
            return render_template("login.html")

        locked_until = user.get("locked_until")
        if locked_until and locked_until > datetime.now():
            flash(f"Account locked until {locked_until.strftime('%Y-%m-%d %H:%M:%S')}.")
            return render_template("login.html")

        if _verify_password(user["password"], password):
            token = str(uuid.uuid4())
            previous_ip = user.get("last_ip")
            new_ip = request.remote_addr
            session.permanent = True
            session["user"] = user["username"]
            session["user_id"] = user["id"]
            session["role"] = user["role_name"] if user.get("role_name") else "teacher"
            session["theme"] = user.get("theme", "light") or "light"
            session["records_per_page"] = user.get("records_per_page") or 10
            session["session_token"] = token
            session["server_boot_id"] = current_app.config.get("SERVER_BOOT_ID")

            set_login_success(user["id"], new_ip, token)

            if previous_ip and previous_ip != new_ip:
                create_notification(
                    user["id"],
                    f"New login detected from IP {new_ip}",
                    pref_key="login_alerts",
                    email_subject="New Login Detected",
                    email_body=(
                        f"Your account was logged in from a new IP address: {new_ip}.\n"
                        f"If this was not you, change your password immediately."
                    ),
                )
            logger.info("User %s logged in from %s", username, new_ip)
            flash("Logged in successfully")
            return redirect(url_for("dashboard.dashboard"))

        attempts = int(user.get("failed_login_attempts") or 0) + 1
        if attempts >= max_attempts:
            lock_account(user["id"], attempts, lock_minutes)
            create_notification(
                user["id"],
                "Your account was locked due to multiple failed login attempts.",
                pref_key="account_locked",
                email_subject="Account Locked",
                email_body=(
                    f"Your account was locked after too many failed login attempts.\n"
                    f"It will unlock after {lock_minutes} minutes."
                ),
            )
            flash(f"Account locked for {lock_minutes} minutes after too many failed attempts.")
            logger.warning("Account locked for user %s after %d failed attempts", username, attempts)
        else:
            increment_failed_attempts(user["id"], attempts)
            flash("Invalid login")
            logger.info("Failed login for user %s (attempt %d)", username, attempts)

    return render_template("login.html")


def logout_user() -> str:
    try:
        if session.get("user_id"):
            clear_session_token(int(session["user_id"]), request.remote_addr, "Logged out")
    finally:
        session.clear()
    return redirect(url_for("auth.login"))


def toggle_theme() -> str:
    user_id = int(session["user_id"])
    current_theme = session.get("theme", "light")
    new_theme = "dark" if current_theme == "light" else "light"
    update_theme(user_id, new_theme, request.remote_addr)
    session["theme"] = new_theme
    flash("Theme updated.")
    return redirect(request.referrer or url_for("dashboard.dashboard"))


def account_page() -> str:
    user = get_account_profile(int(session["user_id"]))
    if not user:
        flash("Account not found.")
        return redirect(url_for("auth.login"))

    login_activity = get_login_activity(int(session["user_id"]))
    permissions = get_permissions(int(session["user_id"]))

    role = (user or {}).get("role") or session.get("role") or "teacher"
    permissions = sorted(set(permissions) | set(ROLE_DEFAULT_PERMISSIONS.get(role, set())))
    teacher_policy_label = teacher_calendar_policy_label()
    teacher_policy_range = teacher_policy_range_text()
    if role == "teacher":
        permissions.append(f"attendance edit: {teacher_policy_label}")

    return render_template(
        "account.html",
        user=user,
        permissions=permissions,
        login_activity=login_activity,
        teacher_policy_label=teacher_policy_label,
        teacher_policy_range=teacher_policy_range,
    )


def logout_other_sessions() -> str:
    from repositories.db_utils import db_cursor
    token = str(uuid.uuid4())
    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute(
            "UPDATE users SET session_token = %s WHERE id = %s",
            (token, session["user_id"]),
        )
        from utils.logger import log_action_on_cursor
        log_action_on_cursor(
            cursor, "Logged out other sessions",
            user_id=session["user_id"],
            ip_address=request.remote_addr,
            target_table="users",
            target_id=session["user_id"],
        )
    from repositories.auth_repository import get_session_token
    get_session_token.cache_clear()
    session["session_token"] = token
    flash("Other sessions were signed out.")
    return redirect(url_for("auth.account"))


def change_password_page() -> str:
    user = get_account_profile(int(session["user_id"]))
    login_activity = get_login_activity(int(session["user_id"]))
    return render_template("change_password.html", user=user, login_activity=login_activity)


def preferences_page() -> str:
    user = get_account_profile(int(session["user_id"]))
    return render_template("preferences.html", user=user)


def change_password() -> str:
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")

    policy_error = password_policy_error(new_password)
    if policy_error:
        flash(policy_error)
        return redirect(url_for("auth.change_password"))

    password_hash = get_password_hash(int(session["user_id"]))
    if not password_hash or not _verify_password(password_hash, current_password):
        flash("Current password is incorrect.")
        return redirect(url_for("auth.change_password"))

    new_hash = _hash_password(new_password)
    update_password(int(session["user_id"]), new_hash, request.remote_addr)
    create_notification(
        int(session["user_id"]),
        "Your password was changed.",
        pref_key="password_change",
        email_subject="Password Changed",
        email_body="Your password was changed successfully. If this was not you, contact the administrator.",
    )
    flash("Password updated successfully")
    return redirect(url_for("auth.change_password"))


def update_account_preferences() -> str:
    theme = (request.form.get("theme") or "light").strip().lower()
    records = request.form.get("records_per_page")
    email = request.form.get("email", "").strip() or None
    email_notifications = request.form.get("email_notifications")

    if theme not in {"light", "dark"}:
        flash("Invalid theme selection.")
        return redirect(url_for("auth.preferences"))

    try:
        records_int = int(records)
    except (TypeError, ValueError):
        flash("Records per page must be a number.")
        return redirect(url_for("auth.preferences"))

    records_int = max(5, min(records_int, 100))
    email_notifications = 1 if email_notifications == "1" else 0

    update_preferences(int(session["user_id"]), theme, records_int, email, email_notifications, request.remote_addr)
    session["theme"] = theme
    session["records_per_page"] = records_int

    create_notification(
        int(session["user_id"]),
        "Your account preferences were updated.",
        pref_key="system_alerts",
        email_subject="Preferences Updated",
        email_body="Your account preferences were updated successfully.",
    )
    flash("Preferences updated", "success")
    return redirect(url_for("auth.preferences"))


def update_notification_preferences() -> str:
    toggles = {
        "low_attendance": request.form.get("low_attendance") == "1",
        "password_change": request.form.get("password_change") == "1",
        "new_student": request.form.get("new_student") == "1",
        "attendance_saved": request.form.get("attendance_saved") == "1",
        "system_alerts": request.form.get("system_alerts") == "1",
        "login_alerts": request.form.get("login_alerts") == "1",
        "attendance_updates": request.form.get("attendance_updates") == "1",
        "role_changes": request.form.get("role_changes") == "1",
        "account_locked": request.form.get("account_locked") == "1",
        "backup_completed": request.form.get("backup_completed") == "1",
    }
    upsert_notification_settings(int(session["user_id"]), toggles, request.remote_addr)
    create_notification(
        int(session["user_id"]),
        "Your notification settings were updated.",
        pref_key="system_alerts",
        email_subject="Notification Settings Updated",
        email_body="Your notification preferences were updated successfully.",
    )
    flash("Notification settings updated", "success")
    return redirect(url_for("auth.preferences"))
