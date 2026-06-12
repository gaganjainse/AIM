from __future__ import annotations

from flask import Response, render_template, request, session

from repositories.report_repository import all_student_attendance_summary, get_attendance_threshold, low_attendance_exists, export_log
from utils.notifications import create_notification


def report_page():
    threshold = get_attendance_threshold()
    records = all_student_attendance_summary()

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

    if any(r["percentage"] < threshold for r in records) and not low_attendance_exists(session["user_id"], "Low attendance warning"):
        create_notification(
            session["user_id"],
            "Low attendance warning",
            pref_key="low_attendance",
            email_subject="Low Attendance Warning",
            email_body=f"At least one student is below the attendance threshold of {threshold:.0f}%.",
        )

    return render_template("report.html", records=records, threshold=threshold)


def export_report_csv():
    records = all_student_attendance_summary()
    export_log(session["user_id"], request.remote_addr)

    def generate():
        yield "Roll No.,First Name,Last Name,Present Days,Absent Days,Leave Days,Total Days,Percentage\n"
        for r in records:
            percentage = 0 if r["total_days"] == 0 else round((r["present_days"] / r["total_days"]) * 100, 2)
            yield f"{r['roll']},{r['first_name']},{r['last_name']},{r['present_days']},{r['absent_days']},{r['leave_days']},{r['total_days']},{percentage}\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=attendance_report.csv"})
