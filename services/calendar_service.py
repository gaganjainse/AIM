from __future__ import annotations

from datetime import date, timedelta

from flask import jsonify, render_template, session

from repositories.calendar_repository import attendance_events
from routes.permissions import teacher_calendar_policy_label, teacher_calendar_scope_label, teacher_edit_window


def calendar_page():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    policy_start, policy_end, _ = teacher_edit_window(today)
    return render_template(
        "calendar.html",
        today=str(today),
        week_start=str(week_start),
        week_end=str(week_end),
        policy_start=str(policy_start),
        policy_end=str(policy_end),
        teacher_policy_label=teacher_calendar_policy_label(),
        teacher_policy_scope=teacher_calendar_scope_label(),
        is_teacher=session.get("role") != "admin",
    )


def attendance_events_json():
    records = attendance_events()
    events = []
    for r in records:
        total = r["total"] or 0
        percent = 0 if not total else (r["present"] / total) * 100
        if percent >= 85:
            color = "#1cc88a"
        elif percent >= 60:
            color = "#f6c23e"
        else:
            color = "#e74a3b"
        events.append({"title": f"P:{r['present']} A:{r['absent']} L:{r['leave_count']} Count:{round(percent)}%", "start": str(r['date']), "color": color})
    return jsonify(events)
