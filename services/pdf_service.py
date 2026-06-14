"""PDF report generation service for AIM application."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from flask import current_app

logger = logging.getLogger(__name__)


def generate_attendance_pdf(records: list, threshold: float, title: str = "Attendance Report") -> bytes:
    """Generate a PDF attendance report.
    
    Args:
        records: List of student attendance records
        threshold: Attendance threshold percentage
        title: Report title
        
    Returns:
        PDF file content as bytes
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        logger.warning("weasyprint not installed, falling back to HTML")
        return _generate_html_pdf_fallback(records, threshold, title)
    
    html_content = _build_report_html(records, threshold, title)
    
    try:
        pdf = HTML(string=html_content, base_url="").write_pdf()
        return pdf
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        return _generate_html_pdf_fallback(records, threshold, title)


def _build_report_html(records: list, threshold: float, title: str) -> str:
    """Build HTML content for the PDF report."""
    today = date.today().strftime("%B %d, %Y")
    now = datetime.now().strftime("%I:%M %p")
    
    total_students = len(records)
    good_count = sum(1 for r in records if r.get("color") == "success")
    average_count = sum(1 for r in records if r.get("color") == "warning")
    low_count = sum(1 for r in records if r.get("color") == "danger")
    
    rows_html = ""
    for r in records:
        pct = r.get("percentage", 0)
        color_class = r.get("color", "secondary")
        label = r.get("label", "N/A")
        rows_html += f"""
        <tr>
            <td>{r.get("roll", "")}</td>
            <td>{r.get("first_name", "")} {r.get("last_name", "")}</td>
            <td>{r.get("present_days", 0)}</td>
            <td>{r.get("absent_days", 0)}</td>
            <td>{r.get("leave_days", 0)}</td>
            <td>{r.get("total_days", 0)}</td>
            <td>{pct}%</td>
            <td><span class="badge bg-{color_class}">{label}</span></td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            @page {{ size: A4 landscape; margin: 1cm; }}
            body {{ font-family: Arial, sans-serif; font-size: 10pt; color: #333; }}
            h1 {{ color: #1a365d; font-size: 18pt; margin-bottom: 5px; }}
            .subtitle {{ color: #666; font-size: 10pt; margin-bottom: 20px; }}
            .summary {{ display: flex; gap: 15px; margin-bottom: 20px; }}
            .stat-box {{ background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 10px 15px; text-align: center; }}
            .stat-value {{ font-size: 16pt; font-weight: bold; color: #2d3748; }}
            .stat-label {{ font-size: 8pt; color: #718096; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th {{ background: #2d3748; color: white; padding: 8px 6px; text-align: left; font-size: 9pt; }}
            td {{ padding: 6px; border-bottom: 1px solid #e2e8f0; font-size: 9pt; }}
            tr:nth-child(even) {{ background: #f7fafc; }}
            .badge {{ padding: 2px 8px; border-radius: 3px; font-size: 8pt; color: white; }}
            .badge-success {{ background: #38a169; }}
            .badge-warning {{ background: #d69e2e; }}
            .badge-danger {{ background: #e53e3e; }}
            .footer {{ margin-top: 20px; font-size: 8pt; color: #a0aec0; text-align: center; }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <div class="subtitle">Generated on {today} at {now} | Threshold: {threshold}%</div>
        
        <div class="summary">
            <div class="stat-box">
                <div class="stat-value">{total_students}</div>
                <div class="stat-label">Total Students</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #38a169;">{good_count}</div>
                <div class="stat-label">Good</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #d69e2e;">{average_count}</div>
                <div class="stat-label">Average</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #e53e3e;">{low_count}</div>
                <div class="stat-label">Low</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Roll No.</th>
                    <th>Name</th>
                    <th>Present</th>
                    <th>Absent</th>
                    <th>Leave</th>
                    <th>Total</th>
                    <th>%</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        
        <div class="footer">
            AIM — Attendance Information Manager &copy; {date.today().year}
        </div>
    </body>
    </html>
    """
    return html


def _generate_html_pdf_fallback(records: list, threshold: float, title: str) -> bytes:
    """Generate HTML report as fallback when weasyprint is not available."""
    html = _build_report_html(records, threshold, title)
    return html.encode("utf-8")
