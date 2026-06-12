from __future__ import annotations

import csv
import io
from datetime import date, datetime

from flask import flash, redirect, render_template, request, session, url_for

from repositories.attendance_repository import (
    attendance_count_for_date,
    attendance_exists,
    attendance_exists_notification,
    attendance_events,
    daily_totals,
    get_attendance_for_date,
    get_student_id_by_roll,
    list_students,
    monthly_averages_for_year,
    recent_attendance,
    save_attendance,
    students_by_status_for_date,
)
from routes.permissions import has_permission, teacher_calendar_policy_label, teacher_calendar_scope_label, teacher_edit_window
from utils.notifications import create_notification
from utils.logger import log_action


def attendance_page():
    today = date.today()
    selected_date = request.args.get('date') or str(today)
    teacher_start, teacher_end, _ = teacher_edit_window(today)

    if session.get('role') != 'admin':
        try:
            requested = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            requested = today
        if requested < teacher_start or requested > teacher_end:
            selected_date = str(today)
        else:
            selected_date = str(requested)

    if request.method == 'POST':
        selected_date = request.form.get('attendance_date', str(today))
        try:
            selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid attendance date.')
            return redirect(url_for('attendance.attendance'))

        teacher_start, teacher_end, _ = teacher_edit_window(today)
        if session.get('role') != 'admin' and (selected_date_obj < teacher_start or selected_date_obj > teacher_end):
            flash(f'Teachers can edit attendance only within {teacher_calendar_policy_label().lower()} up to today.')
            return redirect(url_for('calendar.calendar'))

        allowed_status = {'Present', 'Absent', 'Leave'}
        for student_id, status in request.form.items():
            if student_id in {'attendance_date', 'csrf_token'}:
                continue
            if status not in allowed_status:
                continue
            try:
                student_id_int = int(student_id)
            except ValueError:
                continue
            save_attendance(student_id_int, selected_date, status)

        from repositories.db_utils import db_cursor
        with db_cursor(dictionary=False) as (_, cursor):
            log_action(f'Marked attendance for {selected_date}', user_id=session['user_id'], ip_address=request.remote_addr, target_table='attendance')
        create_notification(
            session['user_id'],
            f'Attendance saved for {selected_date}',
            pref_key='attendance_saved',
            email_subject='Attendance Saved',
            email_body=f'Attendance was saved successfully for {selected_date}.',
        )
        flash(f'Attendance saved for {selected_date}')

    students = list_students()
    attendance_dict = get_attendance_for_date(selected_date)
    selected_date_obj = date.fromisoformat(selected_date)
    can_edit_selected_date = session.get('role') == 'admin' or (teacher_start <= selected_date_obj <= teacher_end)
    return render_template(
        'attendance.html',
        students=students,
        selected_date=selected_date,
        attendance_dict=attendance_dict,
        can_edit_old_attendance=can_edit_selected_date,
        teacher_policy_label=teacher_calendar_policy_label(),
        teacher_policy_scope=teacher_calendar_scope_label(),
        can_import_attendance=has_permission('edit_old_attendance') or session.get('role') == 'admin',
    )


def import_attendance_csv(file_storage):
    """Import attendance rows from a CSV file while respecting permission windows."""
    if not file_storage or not file_storage.filename:
        return 0, 0, 0, 'Choose a CSV file to import.'

    if not file_storage.filename.lower().endswith('.csv'):
        return 0, 0, 0, 'Only CSV files are allowed.'

    raw = file_storage.stream.read()
    try:
        stream = io.StringIO(raw.decode('utf-8-sig'))
    except Exception:
        return 0, 0, 0, 'Unable to read the CSV file.'

    reader = csv.DictReader(stream)
    required = {'roll', 'date', 'status'}
    if not reader.fieldnames or not required.issubset({(h or '').strip().lower() for h in reader.fieldnames}):
        return 0, 0, 0, 'CSV must contain roll, date and status columns.'

    allowed_status = {'Present', 'Absent', 'Leave'}
    today = date.today()
    teacher_start, teacher_end, _ = teacher_edit_window(today)
    admin_mode = session.get('role') == 'admin' or has_permission('edit_old_attendance')

    staged: dict[tuple[str, str], str] = {}
    skipped = 0
    for row in reader:
        roll = (row.get('roll') or row.get('Roll') or '').strip()
        attendance_date = (row.get('date') or row.get('Date') or '').strip()
        status = (row.get('status') or row.get('Status') or '').strip().title()

        if not roll or not attendance_date or status not in allowed_status:
            skipped += 1
            continue

        try:
            parsed = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        except ValueError:
            skipped += 1
            continue

        if not admin_mode and (parsed < teacher_start or parsed > teacher_end):
            skipped += 1
            continue

        staged[(roll, attendance_date)] = status

    if not staged:
        return 0, 0, skipped, 'No attendance rows were imported.'

    from repositories.db_utils import db_cursor, fetch_all

    roll_map = {row['roll']: row['id'] for row in fetch_all('SELECT id, roll FROM students')}
    row_map: dict[tuple[int, str], str] = {}
    student_ids = set()
    dates = set()
    for (roll, attendance_date), status in staged.items():
        student_id = roll_map.get(roll)
        if not student_id:
            skipped += 1
            continue
        row_map[(student_id, attendance_date)] = status
        student_ids.add(student_id)
        dates.add(attendance_date)

    if not row_map:
        return 0, 0, skipped, 'No attendance rows were imported.'

    existing_pairs = set()
    date_list = sorted(dates)
    student_list = sorted(student_ids)
    if date_list and student_list:
        date_chunk_size = 50
        student_chunk_size = 200
        for i in range(0, len(date_list), date_chunk_size):
            date_chunk = date_list[i:i + date_chunk_size]
            date_placeholders = ','.join(['%s'] * len(date_chunk))
            for j in range(0, len(student_list), student_chunk_size):
                student_chunk = student_list[j:j + student_chunk_size]
                student_placeholders = ','.join(['%s'] * len(student_chunk))
                query = (
                    f'SELECT student_id, date FROM attendance '
                    f'WHERE date IN ({date_placeholders}) AND student_id IN ({student_placeholders})'
                )
                params = tuple(date_chunk) + tuple(student_chunk)
                for row in fetch_all(query, params):
                    existing_pairs.add((row['student_id'], str(row['date'])))

    imported = 0
    updated = 0
    payload = []
    for key, status in row_map.items():
        if key in existing_pairs:
            updated += 1
        else:
            imported += 1
        payload.append((key[0], key[1], status))

    with db_cursor(dictionary=False) as (_, cursor):
        cursor.executemany(
            '''
            INSERT INTO attendance (student_id, date, status)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE status=VALUES(status)
            ''',
            payload,
        )

    log_action(
        f'Imported attendance CSV: {imported} new, {updated} updated, {skipped} skipped',
        user_id=session.get('user_id'),
        ip_address=request.remote_addr,
        target_table='attendance',
    )
    create_notification(
        session['user_id'],
        f'Attendance imported: {imported} new, {updated} updated',
        pref_key='attendance_updates',
        email_subject='Attendance Imported',
        email_body=f'Imported {imported} new attendance rows and updated {updated} existing rows from CSV.',
    )
    return imported, updated, skipped, None


def attendance_events_json():
    records = attendance_events()
    events = []
    for r in records:
        total = r['total'] or 0
        percent = 0 if not total else (r['present'] / total) * 100
        if percent >= 85:
            color = '#1cc88a'
        elif percent >= 60:
            color = '#f6c23e'
        else:
            color = '#e74a3b'
        events.append({
            'title': f"P:{r['present']} A:{r['absent']} L:{r['leave_count']} Count:{round(percent)}%",
            'start': str(r['date']),
            'color': color,
        })
    return events
