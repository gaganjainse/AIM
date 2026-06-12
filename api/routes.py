from __future__ import annotations

import random
from datetime import date

from flask import Blueprint, jsonify, request, session

from routes.auth import login_required
from routes.permissions import permission_required
from services.attendance_service import attendance_events_json
from services.auth_service import session_status_response
from repositories.attendance_repository import list_students, save_attendance
from utils.logger import log_action

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/session_status", methods=["GET"])
def session_status() -> tuple[dict, int]:
    payload, status = session_status_response()
    return jsonify(payload), status


@api_bp.route("/health", methods=["GET"])
def health() -> tuple[dict, int]:
    return jsonify({"status": "ok"}), 200


@api_bp.route("/attendance_events", methods=["GET"])
@login_required
def attendance_events() -> str:
    return jsonify({"events": attendance_events_json()})


@api_bp.route("/attendance/randomize", methods=["POST"])
@login_required
@permission_required("mark_attendance")
def randomize_attendance() -> tuple[dict, int]:
    """Generate random demo attendance. Weights: 80% Present, 12% Absent, 8% Leave."""
    target_date = request.json.get("date") if request.is_json else None
    if not target_date:
        target_date = str(date.today())

    weights = [("Present", 80), ("Absent", 12), ("Leave", 8)]
    statuses, w = zip(*weights)

    students = list_students()
    if not students:
        return jsonify({"ok": False, "message": "No students found."}), 404

    results = {"Present": 0, "Absent": 0, "Leave": 0}
    for student in students:
        chosen = random.choices(statuses, weights=w, k=1)[0]
        save_attendance(student["id"], target_date, chosen)
        results[chosen] += 1

    log_action(
        f"Generated random attendance for {target_date}",
        user_id=session["user_id"],
        ip_address=request.remote_addr,
        target_table="attendance",
    )

    return jsonify({
        "ok": True,
        "date": target_date,
        "counts": results,
        "total": len(students),
        "message": (
            f"Generated attendance for {len(students)} students "
            f"({results['Present']} present, {results['Absent']} absent, "
            f"{results['Leave']} leave)."
        ),
    })
