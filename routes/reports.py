from __future__ import annotations
from typing import Any
from datetime import date

from flask import Blueprint

from routes.auth import login_required
from routes.permissions import permission_required
from services.report_service import export_report_csv, report_page

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/report")
@login_required
@permission_required("view_reports")
def report() -> str:
    return report_page()


@reports_bp.route("/export_report")
@login_required
@permission_required("export_reports")
def export_report() -> str:
    return export_report_csv()


@reports_bp.route("/reports/export/pdf", methods=["GET"])
@login_required
def export_report_pdf() -> Any:
    """Export attendance report as PDF."""
    from flask import Response, session
    from repositories.report_repository import all_student_attendance_summary, get_attendance_threshold, export_log
    from services.pdf_service import generate_attendance_pdf
    from utils.notifications import create_notification
    
    threshold = get_attendance_threshold()
    records = all_student_attendance_summary()
    export_log(session["user_id"], "pdf_export")
    
    for r in records:
        if r["total_days"] == 0:
            r["percentage"] = 0
        else:
            r["percentage"] = round((r["present_days"] / r["total_days"]) * 100, 2)
        if r["percentage"] >= threshold:
            r["color"] = "success"
            r["label"] = "Good"
        elif r["percentage"] >= max(50, threshold - 25):
            r["color"] = "warning"
            r["label"] = "Average"
        else:
            r["color"] = "danger"
            r["label"] = "Low"
    
    pdf_content = generate_attendance_pdf(records, threshold)
    
    create_notification(
        session["user_id"],
        "PDF report exported",
        pref_key="report_export",
    )
    
    filename = f"attendance_report_{date.today().isoformat()}.pdf"
    return Response(
        pdf_content,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
