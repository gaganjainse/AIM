from __future__ import annotations

from flask import Blueprint

from routes.auth import login_required
from services.calendar_service import attendance_events_json, calendar_page

calendar_bp = Blueprint("calendar", __name__)


@calendar_bp.route("/calendar")
@login_required
def calendar() -> str:
    return calendar_page()


@calendar_bp.route("/attendance_events")
@login_required
def attendance_events() -> str:
    return attendance_events_json()
