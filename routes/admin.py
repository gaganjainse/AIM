from __future__ import annotations

from flask import Blueprint, request
from typing import Optional

from routes.auth import login_required
from routes.permissions import permission_required
from services.admin_service import (
    add_user as add_user_service,
    backup_database_page,
    backup_restore_page,
    download_backup_page,
    restore_database_page,
    restore_defaults_page,
    roles_page,
    save_role_permissions_page,
    delete_user_page,
    logs_page,
    clear_logs_page,
    mark_notifications_read_page,
    reset_password_page,
    settings_page,
    users_page,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users")
@login_required
@permission_required("manage_users")
def users() -> str:
    return users_page()


@admin_bp.route("/add_user", methods=["POST"])
@login_required
@permission_required("manage_users")
def add_user() -> str:
    return add_user_service()


@admin_bp.route("/delete_user/<int:id>", methods=["POST"])
@login_required
@permission_required("manage_users")
def delete_user(id: int) -> str:
    return delete_user_page(id)


@admin_bp.route("/reset_password/<int:id>", methods=["POST"])
@login_required
@permission_required("manage_users")
def reset_password(id: int) -> str:
    return reset_password_page(id)


@admin_bp.route("/logs")
@login_required
@permission_required("manage_users")
def logs() -> str:
    return logs_page()


@admin_bp.route("/roles", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def roles() -> str:
    if request.method == "POST":
        return save_role_permissions_page()
    return roles_page()


@admin_bp.route("/backup_restore")
@login_required
@permission_required("manage_users")
def backup_restore() -> str:
    return backup_restore_page()


@admin_bp.route("/backup_download/<path:filename>")
@login_required
@permission_required("manage_users")
def backup_download(filename: str) -> str:
    return download_backup_page(filename)


@admin_bp.route("/backup", methods=["POST"])
@login_required
@permission_required("manage_users")
def backup_database() -> str:
    return backup_database_page()


@admin_bp.route("/clear_logs", methods=["POST"])
@login_required
@permission_required("manage_users")
def clear_logs() -> str:
    return clear_logs_page()


@admin_bp.route("/restore_backup", methods=["POST"])
@login_required
@permission_required("manage_users")
def restore_backup() -> str:
    return restore_database_page()


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def settings() -> str:
    return settings_page()


@admin_bp.route("/restore_defaults", methods=["POST"])
@login_required
@permission_required("manage_users")
def restore_defaults() -> str:
    return restore_defaults_page()


@admin_bp.route("/mark_notifications_read", methods=["POST"])
@login_required
def mark_notifications_read() -> str:
    return mark_notifications_read_page()
