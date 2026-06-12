from __future__ import annotations

from datetime import date, timedelta

from flask import render_template, session

from repositories.dashboard_repository import (
    all_students_minimal,
    attendance_today_count,
    missing_attendance_notice_exists,
    monthly_progress,
    attendance_for_date,
    daily_totals,
    recent_attendance,
    students_by_status,
    today_summary,
    total_students,
)
from utils.notifications import create_notification


def dashboard_page():
    today = date.today()
    summary = today_summary(today)
    present = summary["present"]
    absent = summary["absent"]
    leave = summary["leave"]
    records_today = present + absent + leave
    attendance_rate = round((present / records_today) * 100, 1) if records_today else 0.0

    yesterday = today - timedelta(days=1)
    yesterday_summary = daily_totals(yesterday)
    yesterday_present = yesterday_summary.get("present") or 0
    yesterday_absent = yesterday_summary.get("absent") or 0
    yesterday_leave = yesterday_summary.get("leave_count") or 0
    yesterday_records_total = yesterday_present + yesterday_absent + yesterday_leave
    yesterday_rate = round((yesterday_present / yesterday_records_total) * 100, 1) if yesterday_records_total else 0.0

    if attendance_today_count(today) == 0 and not missing_attendance_notice_exists(session["user_id"], today):
        create_notification(
            session["user_id"],
            "Attendance not marked today",
            pref_key="system_alerts",
            email_subject="Attendance Missing Today",
            email_body="No attendance has been marked for today yet.",
        )

    return render_template(
        "dashboard.html",
        total_students=total_students(),
        present=present,
        absent=absent,
        leave=leave,
        attendance_rate=attendance_rate,
        months=monthly_progress(),
        recent_attendance=recent_attendance(),
        all_students=all_students_minimal(),
        present_students=students_by_status(today, "Present"),
        absent_students=students_by_status(today, "Absent"),
        leave_students=students_by_status(today, "Leave"),
        yesterday_date=yesterday,
        yesterday_date_label=yesterday.strftime("%d %b %Y"),
        yesterday_present=yesterday_present,
        yesterday_absent=yesterday_absent,
        yesterday_leave=yesterday_leave,
        yesterday_records_total=yesterday_records_total,
        yesterday_rate=yesterday_rate,
        yesterday_records=attendance_for_date(yesterday, limit=8),
    )
