from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for

from services.auth_service import (
    account_page,
    change_password as change_password_service,
    change_password_page,
    login_required_session_check,
    login_user,
    logout_other_sessions as logout_other_sessions_service,
    logout_user,
    preferences_page,
    password_policy_error,
    session_status_response,
    toggle_theme as toggle_theme_service,
    update_account_preferences as update_account_preferences_service,
    update_notification_preferences as update_notification_preferences_service,
    valid_person_name,
    valid_username,
)

auth_bp = Blueprint("auth", __name__)


def login_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not login_required_session_check():
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/session_status", methods=["GET"])
def session_status() -> tuple[dict, int]:
    payload, status = session_status_response()
    return jsonify(payload), status


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> str:
    return login_user()


@auth_bp.route("/logout", methods=["POST"])
def logout() -> str:
    return logout_user()


@auth_bp.route("/toggle_theme", methods=["POST"])
@login_required
def toggle_theme() -> str:
    return toggle_theme_service()


@auth_bp.route("/account")
@login_required
def account() -> str:
    return account_page()


@auth_bp.route("/logout_other_sessions", methods=["POST"])
@login_required
def logout_other_sessions() -> str:
    return logout_other_sessions_service()


@auth_bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password() -> str:
    if request.method == "POST":
        return change_password_service()
    return change_password_page()


@auth_bp.route("/preferences")
@login_required
def preferences() -> str:
    return preferences_page()


@auth_bp.route("/update_preferences", methods=["POST"])
@login_required
def update_preferences() -> str:
    return update_account_preferences_service()


@auth_bp.route("/update_notification_settings", methods=["POST"])
@login_required
def update_notification_settings() -> str:
    return update_notification_preferences_service()
