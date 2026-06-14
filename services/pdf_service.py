"""PDF report generation service for AIM application."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def generate_attendance_pdf(
    records: List[Dict[str, Any]],
    threshold: float,
    title: str = "Attendance Report",
) -> bytes:
    """Generate a PDF attendance report.
    
    Args:
        records: List of student attendance records
        threshold: Attendance threshold percentage
        title: Report title
        
    Returns:
        PDF file content as bytes (or HTML if weasyprint not available)
    """
    html_content = _build_report_html(records, threshold, title)
    
    try:
        from weasyprint import HTML
        pdf = HTML(string=html_content, base_url="").write_pdf()
        return pdf
    except ImportError:
        logger.warning("weasyprint not installed, returning HTML")
        return html_content.encode("utf-8")
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        return html_content.encode("utf-8")


def _build_report_html(records: List[Dict[str, Any]], threshold: float, title: str) -> str:
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
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
@page {{ size: A4 landscape; margin: 1cm; }}
body {{ font-family: Arial, sans-serif; font-size: 10pt; color: #333; }}
h1 {{ color: #1a365d; font-size: 18pt; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
th {{ background: #2d3748; color: white; padding: 8px 6px; text-align: left; font-size: 9pt; }}
td {{ padding: 6px; border-bottom: 1px solid #e2e8f0; font-size: 9pt; }}
tr:nth-child(even) {{ background: #f7fafc; }}
.badge {{ padding: 2px 8px; border-radius: 3px; font-size: 8pt; color: white; }}
.badge-success {{ background: #38a169; }} .badge-warning {{ background: #d69e2e; }} .badge-danger {{ background: #e53e3e; }}
</style></head>
<body>
<h1>{title}</h1>
<p>Generated on {today} at {now} | Threshold: {threshold}%</p>
<p>Total: {total_students} | Good: {good_count} | Average: {average_count} | Low: {low_count}</p>
<table><thead><tr>
<th>Roll</th><th>Name</th><th>Present</th><th>Absent</th><th>Leave</th><th>Total</th><th>%</th><th>Status</th>
</tr></thead><tbody>{rows_html}</tbody></table>
</body></html>"""
    return html
