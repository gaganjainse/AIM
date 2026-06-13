from __future__ import annotations

import csv
import io
import re

from flask import flash, redirect, render_template, request, session, url_for

from repositories.student_repository import (
    create_student,
    delete_student,
    get_records_per_page_setting,
    get_student,
    get_student_attendance_records,
    get_student_name,
    get_student_profile_stats,
    list_students,
    student_exists_by_roll,
    update_student,
)
from routes.permissions import has_permission
from utils.notifications import create_notification
from utils.logger import log_action

ROLL_RE = re.compile(r'^[A-Za-z0-9-]{3,20}$')
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s'.-]{0,49}$")


def _validate_student(roll, first_name, last_name):
    if not ROLL_RE.fullmatch(roll or ''):
        return 'Roll number must be 3-20 characters using letters, numbers, or dash.'
    if not NAME_RE.fullmatch(first_name or ''):
        return 'First name is invalid.'
    if not NAME_RE.fullmatch(last_name or ''):
        return 'Last name is invalid.'
    return None


def students_page():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    per_page = int(session.get('records_per_page') or get_records_per_page_setting())
    total_students, rows = list_students(page, per_page, q or None)
    total_pages = max((total_students + per_page - 1) // per_page, 1)
    return render_template(
        'students.html',
        students=rows,
        page=page,
        total_pages=total_pages,
        q=q,
        can_manage_students=has_permission('manage_students'),
    )


def import_students_csv(file_storage):
    if not file_storage or not file_storage.filename:
        return 0, 0, 'Choose a CSV file to import.'

    if not file_storage.filename.lower().endswith('.csv'):
        return 0, 0, 'Only CSV files are allowed.'

    raw = file_storage.stream.read()
    try:
        stream = io.StringIO(raw.decode('utf-8-sig'))
    except Exception:
        return 0, 0, 'Unable to read the CSV file.'

    reader = csv.DictReader(stream)
    required = {'roll', 'first_name', 'last_name'}
    if not reader.fieldnames or not required.issubset({(h or '').strip().lower() for h in reader.fieldnames}):
        return 0, 0, 'CSV must contain roll, first_name and last_name columns.'

    staged: dict[str, tuple[str, str, str]] = {}
    skipped = 0
    for row in reader:
        roll = (row.get('roll') or row.get('Roll') or '').strip()
        first_name = (row.get('first_name') or row.get('First Name') or row.get('firstName') or '').strip()
        last_name = (row.get('last_name') or row.get('Last Name') or row.get('lastName') or '').strip()
        if not roll or not first_name or not last_name:
            skipped += 1
            continue
        error = _validate_student(roll, first_name, last_name)
        if error:
            skipped += 1
            continue
        staged[roll] = (roll, first_name, last_name)

    if not staged:
        return 0, 0, 'No valid student rows were found.'

    from repositories.db_utils import db_cursor, fetch_all

    existing_rolls = {row['roll'] for row in fetch_all('SELECT roll FROM students')}
    payload = []
    imported = 0
    updated = 0
    for roll, first_name, last_name in staged.values():
        if roll in existing_rolls:
            updated += 1
        else:
            imported += 1
        payload.append((roll, first_name, last_name))

    with db_cursor(dictionary=False) as (_, cursor):
        cursor.executemany(
            '''
            INSERT INTO students (roll, first_name, last_name)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE first_name=VALUES(first_name), last_name=VALUES(last_name)
            ''',
            payload,
        )

    return imported, updated, None


def add_student():
    roll = request.form.get('roll', '').strip()
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()

    error = _validate_student(roll, first_name, last_name)
    if error:
        flash(error)
        return redirect(url_for('students.students'))

    if student_exists_by_roll(roll):
        flash('Roll number already exists.')
        return redirect(url_for('students.students'))

    create_student(roll, first_name, last_name)
    log_action(f'Added student {roll}', user_id=session['user_id'], ip_address=request.remote_addr, target_table='students')
    create_notification(
        session['user_id'],
        f'New student {roll} added',
        pref_key='new_student',
        email_subject='New Student Added',
        email_body=f'Student {roll} - {first_name} {last_name} was added to the system.',
    )
    flash('Student added successfully')
    return redirect(url_for('students.students'))


def update_student_page(student_id: int):
    roll = request.form.get('roll', '').strip()
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()

    error = _validate_student(roll, first_name, last_name)
    if error:
        flash(error)
        return redirect(url_for('students.students'))

    if student_exists_by_roll(roll, student_id):
        flash('Roll number already exists.')
        return redirect(url_for('students.students'))

    update_student(student_id, roll, first_name, last_name)
    log_action(f'Updated student {roll}', user_id=session['user_id'], ip_address=request.remote_addr, target_table='students', target_id=student_id)
    flash('Student updated successfully')
    return redirect(url_for('students.students'))


def edit_student_page(student_id: int):
    student = get_student(student_id)
    return render_template('edit_student.html', student=student)


def delete_student_page(student_id: int):
    student = get_student_name(student_id)
    if not student:
        flash('Student not found.')
        return redirect(url_for('students.students'))
    delete_student(student_id)
    log_action(f'Deleted student {student["roll"]}', user_id=session['user_id'], ip_address=request.remote_addr, target_table='students', target_id=student_id)
    flash('Student deleted successfully')
    return redirect(url_for('students.students'))


def student_profile_page(student_id: int):
    student = get_student(student_id)
    if not student:
        flash('Student not found.')
        return redirect(url_for('students.students'))
    stats = get_student_profile_stats(student_id)
    return render_template('student_profile.html', student=student, stats=stats)


def student_chart_page(student_id: int):
    student = get_student_name(student_id)
    if not student:
        flash('Student not found.')
        return redirect(url_for('students.students'))
    records = get_student_attendance_records(student_id)
    dates = [str(r['date']) for r in records]
    values = [2 if r['status'] == 'Present' else 1 if r['status'] == 'Leave' else 0 for r in records]
    status_labels = [r['status'] for r in records]
    return render_template(
        'student_chart.html',
        dates=dates,
        values=values,
        status_labels=status_labels,
        student_id=student_id,
        student=student,
    )
