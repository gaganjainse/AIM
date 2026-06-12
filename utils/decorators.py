"""Shared decorators to avoid cross-layer circular imports."""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import abort, redirect, session, url_for


def login_required(f: Callable) -> Callable:
    """Verify the current session is authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from services.auth_service import login_required_session_check
        if not login_required_session_check():
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function
