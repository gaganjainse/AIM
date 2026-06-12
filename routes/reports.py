from __future__ import annotations

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
