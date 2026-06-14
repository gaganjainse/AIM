from __future__ import annotations

import random
from datetime import date
from typing import Any, Dict, List, Tuple, Union

from flask import Blueprint, jsonify, request, session

from routes.auth import login_required
from routes.permissions import permission_required
from services.attendance_service import attendance_events_json
from services.auth_service import session_status_response
from repositories.attendance_repository import list_students, save_attendance
from database.db import get_pool_stats
from services.cache_service import invalidate_all_cache
from utils.logger import log_action

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/session_status", methods=["GET"])
def session_status() -> Tuple[Dict[str, Any], int]:
    """
    Get current session status.
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Session is valid
        schema:
          type: object
          properties:
            authenticated:
              type: boolean
            user:
              type: string
            role:
              type: string
      401:
        description: Not authenticated
    """
    payload, status = session_status_response()
    return jsonify(payload), status


@api_bp.route("/health", methods=["GET"])
def health() -> Tuple[Dict[str, Any], int]:
    """
    Health check endpoint.
    ---
    tags:
      - System
    responses:
      200:
        description: System is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
    """
    return jsonify({"status": "ok"}), 200


@api_bp.route("/attendance_events", methods=["GET"])
@login_required
def attendance_events() -> str:
    """
    Get attendance events for the calendar.
    ---
    tags:
      - Attendance
    security:
      - session: []
    responses:
      200:
        description: List of attendance events
        schema:
          type: object
          properties:
            events:
              type: array
              items:
                type: object
    """
    return jsonify({"events": attendance_events_json()})


@api_bp.route("/attendance/randomize", methods=["POST"])
@login_required
@permission_required("mark_attendance")
def randomize_attendance() -> Tuple[Dict[str, Any], int]:
    """
    Generate random demo attendance data.
    ---
    tags:
      - Attendance
    security:
      - session: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            date:
              type: string
              format: date
              example: "2026-01-15"
    responses:
      200:
        description: Random attendance generated
        schema:
          type: object
          properties:
            ok:
              type: boolean
            date:
              type: string
            counts:
              type: object
            total:
              type: integer
      404:
        description: No students found
    """
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


@api_bp.route("/pool_stats", methods=["GET"])
@login_required
def pool_stats() -> Tuple[Dict[str, Any], int]:
    """
    Get database connection pool statistics.
    ---
    tags:
      - System
      - Monitoring
    security:
      - session: []
    responses:
      200:
        description: Pool statistics
        schema:
          type: object
          properties:
            ok:
              type: boolean
            pool:
              type: object
              properties:
                pool_name:
                  type: string
                pool_size:
                  type: integer
                connections_created:
                  type: integer
                connections_failed:
                  type: integer
    """
    stats = get_pool_stats()
    return jsonify({"ok": True, "pool": stats})


@api_bp.route("/cache/invalidate", methods=["POST"])
@login_required
def invalidate_cache() -> Tuple[Dict[str, Any], int]:
    """
    Invalidate all cache entries. Admin only.
    ---
    tags:
      - System
      - Admin
    security:
      - session: []
    responses:
      200:
        description: Cache invalidated
      403:
        description: Admin access required
    """
    if session.get("role") != "admin":
        return jsonify({"ok": False, "message": "Admin access required"}), 403
    
    invalidate_all_cache()
    return jsonify({"ok": True, "message": "Cache invalidated"})
