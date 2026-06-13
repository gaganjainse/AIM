from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from flask import flash, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from config import Config
from repositories.admin_repository import (
    DEFAULT_SETTINGS,
    backup_retention_days,
    clear_logs as clear_logs_repository,
    count_logs,
    delete_user,
    get_role_permissions,
    list_permissions,
    ensure_default_settings,
    get_setting_value,
    get_settings_rows,
    get_user_username,
    list_logs,
    list_roles,
    list_users,
    mark_notifications_read,
    reset_user_password,
    set_role_permissions,
    upsert_setting,
    username_exists,
)
from repositories.system_repository import clear_settings_cache
from utils.notifications import create_notification, ensure_user_notification_settings
from repositories.db_utils import db_cursor
from utils.logger import log_action

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserCreationResult:
    """Result of user creation attempt."""
    success: bool
    user_id: Optional[int] = None
    error_message: Optional[str] = None


def _validate_username(username: str) -> tuple[bool, Optional[str]]:
    """Validate username format.
    
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    if not re.fullmatch(r"^[A-Za-z0-9_.-]{3,50}$", username or ""):
        return False, "Username must be 3-50 characters and can contain letters, numbers, underscore, dot, or dash."
    return True, None


def _validate_password(password: str) -> tuple[bool, Optional[str]]:
    """Validate password against policy.
    
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    from routes.auth import password_policy_error
    error = password_policy_error(password)
    if error:
        return False, error
    return True, None


def _hash_password(password: str) -> str:
    from argon2 import PasswordHasher
    ph = PasswordHasher(time_cost=Config.ARGON2_TIME_COST, memory_cost=Config.ARGON2_MEMORY_COST, parallelism=Config.ARGON2_PARALLELISM)
    return ph.hash(password)


def users_page() -> str:
    return render_template("users.html", users=list_users(), roles=list_roles())


def add_user() -> str:
    from routes.auth import valid_username
    
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    email = request.form.get("email", "").strip() or None
    role_id_raw = request.form.get("role_id", "").strip()

    is_valid, error_msg = _validate_username(username)
    if not is_valid:
        flash(error_msg)
        return redirect(url_for("admin.users"))

    is_valid, error_msg = _validate_password(password)
    if not is_valid:
        flash(error_msg)
        return redirect(url_for("admin.users"))

    try:
        role_id = int(role_id_raw)
    except ValueError:
        flash("Invalid role selected.")
        return redirect(url_for("admin.users"))

    if username_exists(username):
        flash("Username already exists.")
        return redirect(url_for("admin.users"))

    with db_cursor(dictionary=False) as (_, cursor):
        cursor.execute(
            "INSERT INTO users (username, password, email, email_notifications) VALUES (%s, %s, %s, %s)",
            (username, _hash_password(password), email, 1 if email else 0),
        )
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)", (user_id, role_id))
        ensure_user_notification_settings(cursor, user_id)
        log_action(f"Created user {username}", user_id=session["user_id"], ip_address=request.remote_addr, target_table="users")
    create_notification(
        session["user_id"], f"User {username} created",
        pref_key="system_alerts", email_subject="User Created",
        email_body=f"The user account '{username}' was created successfully.",
    )
    flash("User created successfully")
    return redirect(url_for("admin.users"))


def delete_user_page(user_id: int) -> str:
    if user_id == session.get("user_id"):
        flash("You cannot delete your own account.")
        return redirect(url_for("admin.users"))
    username = get_user_username(user_id)
    if not username:
        flash("User not found.")
        return redirect(url_for("admin.users"))
    delete_user(user_id)
    with db_cursor(dictionary=False) as (_, cursor):
        log_action(f"Deleted user {username}", user_id=session["user_id"], ip_address=request.remote_addr, target_table="users")
    create_notification(
        session["user_id"], f"User {username} deleted",
        pref_key="system_alerts", email_subject="User Deleted",
        email_body=f"The user account '{username}' was deleted.",
    )
    flash("User deleted successfully")
    return redirect(url_for("admin.users"))


def reset_password_page(user_id: int) -> str:
    username = get_user_username(user_id)
    if not username:
        flash("User not found.")
        return redirect(url_for("admin.users"))
    temporary_password = _generate_temporary_password()
    reset_user_password(user_id, _hash_password(temporary_password))
    with db_cursor(dictionary=False) as (_, cursor):
        log_action(
            f"Reset password for {username}", user_id=session["user_id"],
            ip_address=request.remote_addr, target_table="users", target_id=user_id,
        )
    create_notification(
        user_id,
        "Your password was reset by an administrator.",
        pref_key="password_change",
        email_subject="Password Reset",
        email_body="Your password was reset by an administrator. Please sign in using the temporary password shared by the administrator and change it immediately.",
    )
    flash(f"Temporary password for {username}: {temporary_password}", "warning")
    return redirect(url_for("admin.users"))


def clear_logs_page() -> str:
    clear_logs_repository()
    flash("System logs cleared successfully")
    return redirect(url_for("admin.logs"))


def logs_page() -> str:
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    per_page = 20
    total_logs = count_logs(q or None)
    total_pages = max((total_logs + per_page - 1) // per_page, 1)
    logs = list_logs(page, per_page, q or None)
    return render_template("logs.html", logs=logs, page=page, total_pages=total_pages, q=q)


def backup_database_page() -> str:
    filename, filepath, ok = _create_backup_file()
    if not ok:
        flash("Backup failed. Make sure mysqldump is available in PATH.")
        return redirect(url_for("admin.settings"))

    # Encrypt backup if encryption key is configured
    checksum = compute_checksum(filepath)
    if Config.BACKUP_ENCRYPTION_KEY:
        enc_path = filepath + ".enc"
        try:
            encrypt_backup(filepath, enc_path)
            os.remove(filepath)  # Remove unencrypted file
            filepath = enc_path
            filename = filename + ".enc"
            logger.info("Backup encrypted: %s (checksum: %s)", filename, checksum)
        except Exception as exc:
            logger.error("Backup encryption failed: %s", exc, exc_info=True)
            flash("Backup created but encryption failed. Check logs.", "warning")

    # Write checksum file
    checksum_path = filepath + ".sha256"
    with open(checksum_path, "w") as f:
        f.write(f"{checksum}  {os.path.basename(filepath)}\n")

    # Retention cleanup
    retention_days = backup_retention_days()
    cutoff = datetime.now().timestamp() - (retention_days * 86400)
    for entry in os.scandir(Config.BACKUP_DIR):
        if not entry.is_file():
            continue
        if entry.path in (filepath, checksum_path):
            continue
        if entry.stat().st_mtime < cutoff:
            try:
                os.remove(entry.path)
            except OSError:
                pass

    with db_cursor(dictionary=False) as (_, cursor):
        log_action("Backup database", user_id=session["user_id"], ip_address=request.remote_addr, target_table="database_backup")
    create_notification(
        session["user_id"], "Database backup completed",
        pref_key="backup_completed", email_subject="Backup Completed",
        email_body=f"Database backup completed successfully. File: {filename} (SHA256: {checksum[:16]}...)",
    )
    flash("Backup created successfully")
    return send_file(filepath, as_attachment=True, download_name=filename)


def restore_database_page() -> str:
    backup_file = request.files.get("backup_file")
    if not backup_file or not backup_file.filename:
        flash("Choose a backup file to restore.")
        return redirect(url_for("admin.backup_restore"))

    filename = secure_filename(backup_file.filename)
    if not filename.lower().endswith(".sql") and not filename.lower().endswith(".sql.enc"):
        flash("Only .sql or .sql.enc backup files are allowed.")
        return redirect(url_for("admin.backup_restore"))

    os.makedirs(Config.BACKUP_DIR, exist_ok=True)
    restore_path = os.path.join(Config.BACKUP_DIR, f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
    backup_file.save(restore_path)

    # Decrypt if encrypted
    if filename.lower().endswith(".enc"):
        decrypted_path = restore_path[:-4]  # Remove .enc
        try:
            decrypt_backup(restore_path, decrypted_path)
            os.remove(restore_path)
            restore_path = decrypted_path
        except Exception as exc:
            logger.error("Backup decryption failed: %s", exc, exc_info=True)
            flash("Backup decryption failed. Check encryption key configuration.")
            return redirect(url_for("admin.backup_restore"))

    # Verify checksum if available
    checksum_path = restore_path + ".sha256"
    if os.path.exists(checksum_path):
        with open(checksum_path) as f:
            expected_checksum = f.read().strip().split()[0]
        if not verify_checksum(restore_path, expected_checksum):
            flash("Backup integrity check failed! The file may be corrupted.")
            logger.error("Backup integrity check failed for %s", filename)
            return redirect(url_for("admin.backup_restore"))

    # Create safety snapshot
    snapshot_name, snapshot_path, snapshot_ok = _create_backup_file(prefix="pre_restore")
    if not snapshot_ok:
        flash("Restore aborted because the safety snapshot could not be created.")
        return redirect(url_for("admin.backup_restore"))

    env = os.environ.copy()
    env["MYSQL_PWD"] = Config.DB_PASSWORD
    mysql_bin = _resolve_mysql_bin("MYSQL_BIN")
    with open(restore_path, "rb") as infile:
        result = subprocess.run(
            [mysql_bin, "-u", Config.DB_USER, Config.DB_NAME],
            stdin=infile, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=env, check=False,
        )

    if result.returncode != 0:
        flash("Restore failed. Make sure mysql is available in PATH and the backup is valid.")
        return redirect(url_for("admin.backup_restore"))

    log_action("Restore database", user_id=session["user_id"], ip_address=request.remote_addr, target_table="database_backup")
    create_notification(
        session["user_id"], "Database restore completed",
        pref_key="system_alerts", email_subject="Database Restored",
        email_body=f"Database restore completed successfully using {filename}.",
    )
    flash("Database restored successfully")
    return redirect(url_for("admin.backup_restore"))


def restore_defaults_page() -> str:
    with db_cursor(dictionary=False) as (_, cursor):
        for key, value in DEFAULT_SETTINGS.items():
            cursor.execute(
                """
                INSERT INTO settings (setting_name, setting_value)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
                """,
                (key, value),
            )
        cursor.execute(
            """
            INSERT INTO settings (setting_name, setting_value)
            VALUES ('semester_name', %s)
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            """,
            (DEFAULT_SETTINGS["year"],),
        )
        log_action("Restored default system settings", user_id=session["user_id"], ip_address=request.remote_addr, target_table="settings")
    clear_settings_cache()
    create_notification(
        session["user_id"], "System settings restored to defaults",
        pref_key="system_alerts", email_subject="System Settings Restored",
        email_body="System settings were restored to their default values.",
    )
    flash("Default settings restored successfully")
    return redirect(url_for("admin.settings"))


def settings_page() -> str:
    with db_cursor(dictionary=True) as (_, cursor):
        if ensure_default_settings(cursor):
            clear_settings_cache()

    if request.method == "POST":
        allowed_keys = {
            "system_name": "text",
            "attendance_limit": "number",
            "login_tagline": "text",
            "year": "text",
            "teacher_calendar_policy": "policy",
            "semester_start_date": "date",
            "semester_end_date": "date",
            "backup_retention_days": "number",
            "max_login_attempts": "number",
            "login_lock_minutes": "number",
        }

        with db_cursor(dictionary=True) as (_, cursor):
            for key, field_type in allowed_keys.items():
                value = request.form.get(key, "").strip()
                if not value:
                    continue
                if field_type == "number":
                    try:
                        value = str(int(value))
                    except ValueError:
                        flash(f"{key.replace('_', ' ').title()} must be a number.")
                        return redirect(url_for("admin.settings"))
                elif key == "year" and not re.fullmatch(r"\d{4}-\d{2}", value):
                    flash("Year must be in YYYY-YY format.")
                    return redirect(url_for("admin.settings"))
                elif field_type == "date":
                    try:
                        datetime.strptime(value, "%Y-%m-%d")
                    except ValueError:
                        flash(f"{key.replace('_', ' ').title()} must be a valid date in YYYY-MM-DD format.")
                        return redirect(url_for("admin.settings"))
                elif field_type == "policy":
                    if value not in {"current_week_only", "current_month_only", "current_semester_only"}:
                        flash("Invalid teacher calendar policy selected.")
                        return redirect(url_for("admin.settings"))
                cursor.execute("UPDATE settings SET setting_value=%s WHERE setting_name=%s", (value, key))

            cursor.execute("SELECT setting_value FROM settings WHERE setting_name='year' LIMIT 1")
            year_row = cursor.fetchone()
            if year_row:
                cursor.execute(
                    """
                    INSERT INTO settings (setting_name, setting_value)
                    VALUES ('semester_name', %s)
                    ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
                    """,
                    (year_row["setting_value"],),
                )
            log_action("Updated system settings", user_id=session["user_id"], ip_address=request.remote_addr, target_table="settings")
        clear_settings_cache()
        create_notification(
            session["user_id"], "System settings updated",
            pref_key="system_alerts", email_subject="System Settings Updated",
            email_body="System settings were updated successfully.",
        )
        flash("Settings saved successfully")
        return redirect(url_for("admin.settings"))

    rows = get_settings_rows()
    settings_map = {row["setting_name"]: row["setting_value"] for row in rows}
    year_value = settings_map.get("year", settings_map.get("semester_name", "2026-27")) or "2026-27"
    if "-" in year_value:
        year_prefix, year_suffix = year_value.split("-", 1)
    else:
        year_prefix, year_suffix = year_value, ""
    return render_template("settings.html", settings=rows, settings_map=settings_map, year_prefix=year_prefix, year_suffix=year_suffix)


def mark_notifications_read_page() -> str:
    mark_notifications_read(session["user_id"])
    return redirect(request.referrer or url_for("dashboard.dashboard"))


def _resolve_mysql_bin(env_var: str) -> str:
    configured = getattr(Config, env_var, "") or ""
    resolved = shutil.which(configured) if configured else None
    return resolved or configured


def _create_backup_file(prefix: str = "backup") -> tuple[str, str, bool]:
    os.makedirs(Config.BACKUP_DIR, exist_ok=True)
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    filepath = os.path.join(Config.BACKUP_DIR, filename)
    env = os.environ.copy()
    env["MYSQL_PWD"] = Config.DB_PASSWORD
    mysqldump_bin = _resolve_mysql_bin("MYSQLDUMP_BIN")
    with open(filepath, "w", encoding="utf-8") as outfile:
        result = subprocess.run(
            [mysqldump_bin, "-u", Config.DB_USER, Config.DB_NAME],
            stdout=outfile, stderr=subprocess.DEVNULL, env=env, check=False,
        )
    return filename, filepath, result.returncode == 0


def list_backup_files() -> list[dict]:
    os.makedirs(Config.BACKUP_DIR, exist_ok=True)
    files = []
    for entry in os.scandir(Config.BACKUP_DIR):
        if not entry.is_file() or not entry.name.endswith(".sql"):
            continue
        if not (entry.name.startswith("backup_") or entry.name.startswith("restore_") or entry.name.startswith("pre_restore_")):
            continue
        files.append({
            "name": entry.name,
            "size": entry.stat().st_size,
            "modified": datetime.fromtimestamp(entry.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return sorted(files, key=lambda item: item["name"], reverse=True)


def roles_page() -> str:
    roles = list_roles()
    permissions = sorted(list_permissions(), key=lambda item: item["id"])
    role_id = request.args.get("role_id", type=int) or (roles[0]["id"] if roles else None)
    current = get_role_permissions(role_id) if role_id else []
    assigned = {row["id"] for row in current}
    role_name = next((r["role_name"] for r in roles if r["id"] == role_id), None)
    role_summaries = []
    for role in roles:
        role_perms = get_role_permissions(role["id"])
        role_summaries.append({
            "id": role["id"],
            "role_name": role["role_name"],
            "count": len(role_perms),
            "permissions": [row["name"] for row in role_perms],
        })
    return render_template(
        "roles.html",
        roles=roles,
        permissions=permissions,
        assigned_permissions=assigned,
        selected_role_id=role_id,
        selected_role_name=role_name,
        role_summaries=role_summaries,
    )


def save_role_permissions_page() -> str:
    role_id_raw = request.form.get("role_id", "").strip()
    selected_permissions = request.form.getlist("permissions")
    try:
        role_id = int(role_id_raw)
    except ValueError:
        flash("Invalid role selected.")
        return redirect(url_for("admin.roles"))

    try:
        permission_ids = sorted({int(pid) for pid in selected_permissions})
    except ValueError:
        flash("Invalid permission selection.")
        return redirect(url_for("admin.roles", role_id=role_id))

    set_role_permissions(role_id, permission_ids)
    with db_cursor(dictionary=False) as (_, cursor):
        log_action(
            f"Updated permissions for role #{role_id}",
            user_id=session["user_id"], ip_address=request.remote_addr,
            target_table="roles", target_id=role_id,
        )
    create_notification(
        session["user_id"], "Role permissions were updated.",
        pref_key="role_changes", email_subject="Role Permissions Updated",
        email_body="Role permissions were updated successfully.",
    )
    flash("Role permissions saved successfully")
    return redirect(url_for("admin.roles", role_id=role_id))


def backup_restore_page() -> str:
    backups = list_backup_files()
    return render_template("backup_restore.html", backups=backups)


def download_backup_page(filename: str) -> str:
    safe_name = secure_filename(filename)
    if safe_name != filename or not (
        safe_name.startswith("backup_") or safe_name.startswith("restore_") or safe_name.startswith("pre_restore_")
    ):
        flash("Invalid backup file.")
        return redirect(url_for("admin.backup_restore"))
    filepath = os.path.join(Config.BACKUP_DIR, safe_name)
    if not os.path.exists(filepath):
        flash("Backup file not found.")
        return redirect(url_for("admin.backup_restore"))
    return send_file(filepath, as_attachment=True, download_name=safe_name)


def _generate_temporary_password(length: int = 12) -> str:
    token = secrets.token_urlsafe(length)
    candidate = "".join(ch for ch in token if ch.isalnum())[: max(length - 2, 8)]
    return f"{candidate}9A"
