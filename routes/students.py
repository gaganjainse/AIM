from __future__ import annotations

import re

from flask import Blueprint, flash, redirect, request, url_for

from routes.auth import login_required
from routes.permissions import has_permission, permission_required
from services.student_service import (
    add_student as add_student_service,
    import_students_csv as import_students_csv_service,
    delete_student_page,
    edit_student_page,
    student_chart_page,
    student_profile_page,
    students_page,
    update_student_page,
)

students_bp = Blueprint("students", __name__)


@students_bp.route("/students")
@login_required
def students() -> str:
    return students_page()


@students_bp.route("/add_student", methods=["POST"])
@login_required
@permission_required("manage_students")
def add_student() -> str:
    return add_student_service()


@students_bp.route("/update_student/<int:id>", methods=["POST"])
@login_required
@permission_required("manage_students")
def update_student(id: int) -> str:
    return update_student_page(id)


@students_bp.route("/edit_student/<int:id>")
@login_required
@permission_required("manage_students")
def edit_student(id: int) -> str:
    return edit_student_page(id)


@students_bp.route("/delete_student/<int:id>", methods=["POST"])
@login_required
@permission_required("manage_students")
def delete_student(id: int) -> str:
    return delete_student_page(id)


@students_bp.route("/student/<int:id>")
@login_required
def student_profile(id: int) -> str:
    return student_profile_page(id)


@students_bp.route("/student_chart/<int:id>")
@login_required
def student_chart(id: int) -> str:
    return student_chart_page(id)


@students_bp.route("/import_students", methods=["POST"])
@login_required
@permission_required("manage_students")
def import_students() -> str:
    file_storage = request.files.get("csv_file")
    if not file_storage or not file_storage.filename:
        flash("No file selected.", "warning")
        return redirect(url_for("students.students"))

    file_storage.seek(0, 2)
    file_size = file_storage.tell()
    file_storage.seek(0)
    if file_size > 2 * 1024 * 1024:
        flash("File too large. Maximum size is 2MB.", "danger")
        return redirect(url_for("students.students"))

    imported, updated, error = import_students_csv_service(file_storage)
    if error:
        flash(error, "danger")
    else:
        flash(f"Imported {imported} new students and updated {updated} existing records.", "success")
    return redirect(url_for("students.students"))
