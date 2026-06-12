"""Attendance page routes."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, request, url_for

from routes.auth import login_required
from routes.permissions import permission_required
from services.attendance_service import attendance_events_json, attendance_page, import_attendance_csv

attendance_bp = Blueprint("attendance", __name__)


@attendance_bp.route("/attendance", methods=["GET", "POST"])
@login_required
@permission_required("mark_attendance")
def attendance() -> str:
    return attendance_page()


@attendance_bp.route("/attendance/import", methods=["POST"])
@login_required
@permission_required("edit_old_attendance")
def import_attendance() -> str:
    file_storage = request.files.get("csv_file")
    if not file_storage or not file_storage.filename:
        flash("No file selected.", "warning")
        return redirect(url_for("attendance.attendance"))

    file_storage.seek(0, 2)
    file_size = file_storage.tell()
    file_storage.seek(0)
    if file_size > 2 * 1024 * 1024:
        flash("File too large. Maximum size is 2MB.", "danger")
        return redirect(url_for("attendance.attendance"))

    imported, updated, skipped, error = import_attendance_csv(file_storage)
    if error:
        flash(error, "danger")
    else:
        flash(f"Imported {imported} new rows, updated {updated} rows and skipped {skipped} rows.", "success")
    return redirect(url_for("attendance.attendance"))
