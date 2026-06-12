"""
AIM Demo Data Seeder
====================
Seeds the database with realistic demo students, teachers, and 30 days of attendance data.

Usage:
    python demo/seed_demo_data.py              # Seed all demo data
    python demo/seed_demo_data.py --students   # Seed only students
    python demo/seed_demo_data.py --attendance # Seed only attendance
    python demo/seed_demo_data.py --users      # Seed only users
    python demo/seed_demo_data.py --reset      # Clear all data first

Requirements:
    - MySQL running with the attendance_db schema loaded
    - .env file with DB credentials configured
"""
from __future__ import annotations

import argparse
import os
import random
import secrets
import string
import sys
from datetime import date, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


# ── Sample Data ──────────────────────────────────────────────────────────────

DEMO_STUDENTS = [
    # CS-2026 Batch
    ("CS-2026-001", "Aarav", "Sharma"), ("CS-2026-002", "Vivaan", "Patel"),
    ("CS-2026-003", "Aditya", "Singh"), ("CS-2026-004", "Vihaan", "Kumar"),
    ("CS-2026-005", "Arjun", "Gupta"), ("CS-2026-006", "Sai", "Reddy"),
    ("CS-2026-007", "Reyansh", "Verma"), ("CS-2026-008", "Ayaan", "Malhotra"),
    ("CS-2026-009", "Krishna", "Joshi"), ("CS-2026-010", "Ishaan", "Shah"),
    # CS-2025 Batch
    ("CS-2025-001", "Ananya", "Rao"), ("CS-2025-002", "Diya", "Menon"),
    ("CS-2025-003", "Myra", "Nair"), ("CS-2025-004", "Sara", "Pillai"),
    ("CS-2025-005", "Aanya", "Desai"), ("CS-2025-006", "Ira", "Kulkarni"),
    ("CS-2025-007", "Meera", "Hegde"), ("CS-2025-008", "Priya", "Bhat"),
    ("CS-2025-009", "Riya", "Iyer"), ("CS-2025-010", "Nisha", "Raman"),
    # EE-2026 Batch
    ("EE-2026-001", "Rohan", "Mishra"), ("EE-2026-002", "Karan", "Agarwal"),
    ("EE-2026-003", "Rahul", "Trivedi"), ("EE-2026-004", "Nikhil", "Saxena"),
    ("EE-2026-005", "Deepak", "Chatterjee"),
    # ME-2026 Batch
    ("ME-2026-001", "Amit", "Banerjee"), ("ME-2026-002", "Suresh", "Das"),
    ("ME-2026-003", "Pranav", "Ghosh"), ("ME-2026-004", "Gaurav", "Sen"),
    ("ME-2026-005", "Manish", "Pandey"),
]

DEMO_TEACHERS = [
    ("prof_sharma", "Dr. Rajesh", "sharma@university.edu", "Computer Science"),
    ("prof_patel", "Dr. Priya", "patel@university.edu", "Electronics"),
    ("prof_kumar", "Dr. Amit", "kumar@university.edu", "Mechanical"),
    ("prof_reddy", "Dr. Sunita", "reddy@university.edu", "Mathematics"),
]

ATTENDANCE_WEIGHTS = [("Present", 78), ("Absent", 14), ("Leave", 8)]


def _get_connection():
    import mysql.connector
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "attendance_db"),
        autocommit=False,
    )


def seed_students(conn) -> list[tuple[int, str]]:
    """Insert demo students. Returns list of (id, roll) tuples."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students")
    if cur.fetchone()[0] > 0:
        print("  Students already seeded, skipping...")
        cur.execute("SELECT id, roll FROM students")
        return cur.fetchall()

    for roll, first, last in DEMO_STUDENTS:
        cur.execute(
            "INSERT IGNORE INTO students (roll, first_name, last_name) VALUES (%s, %s, %s)",
            (roll, first, last),
        )
    conn.commit()
    cur.execute("SELECT id, roll FROM students")
    results = cur.fetchall()
    cur.close()
    print(f"  ✅ Seeded {len(results)} students")
    return results


def seed_teacher_users(conn) -> None:
    """Insert demo teacher users."""
    from argon2 import PasswordHasher
    ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=4)
    default_pw = ph.hash("Teacher@123")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE id > 1")
    if cur.fetchone()[0] > 0:
        print("  Teacher users already seeded, skipping...")
        cur.close()
        return

    # Get teacher role id
    cur.execute("SELECT id FROM roles WHERE role_name = 'teacher'")
    role_row = cur.fetchone()
    if not role_row:
        print("  ❌ Teacher role not found. Make sure schema.sql was loaded.")
        cur.close()
        return
    role_id = role_row[0]

    for username, full_name, email, dept in DEMO_TEACHERS:
        cur.execute(
            "INSERT IGNORE INTO users (username, password, email, email_notifications, theme, records_per_page) "
            "VALUES (%s, %s, %s, 1, 'light', 10)",
            (username, default_pw, email),
        )
        user_id = cur.lastrowid
        if user_id:
            cur.execute("INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (%s, %s)", (user_id, role_id))
            cur.execute("INSERT IGNORE INTO user_notification_settings (user_id) VALUES (%s)", (user_id,))

    conn.commit()
    cur.close()
    print(f"  ✅ Seeded {len(DEMO_TEACHERS)} teacher users")


def seed_attendance(conn, students: list[tuple[int, str]]) -> int:
    """Generate 30 days of realistic attendance data. Returns count of records inserted."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM attendance")
    existing = cur.fetchone()[0]

    statuses, weights = zip(*ATTENDANCE_WEIGHTS)
    total_inserted = 0
    today = date.today()

    for day_offset in range(30):
        target_date = today - timedelta(days=day_offset)
        # Skip weekends
        if target_date.weekday() >= 5:
            continue

        for student_id, roll in students:
            status = random.choices(statuses, weights=weights, k=1)[0]
            cur.execute(
                """
                INSERT INTO attendance (student_id, date, status)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE status = VALUES(status)
                """,
                (student_id, str(target_date), status),
            )
            total_inserted += 1

    conn.commit()
    cur.close()
    new_total = existing + total_inserted
    print(f"  ✅ Seeded {total_inserted} attendance records (total: {new_total})")
    return total_inserted


def seed_settings(conn) -> None:
    """Ensure demo-friendly system settings."""
    cur = conn.cursor()
    demo_settings = {
        "system_name": "AIM — University Attendance System",
        "attendance_limit": "75",
        "login_tagline": "Track attendance without the clutter",
        "year": "2025-26",
        "teacher_calendar_policy": "current_week_only",
        "semester_start_date": "2025-07-01",
        "semester_end_date": "2025-12-31",
        "backup_retention_days": "30",
        "max_login_attempts": "5",
        "login_lock_minutes": "15",
    }
    for key, value in demo_settings.items():
        cur.execute(
            """
            INSERT INTO settings (setting_name, setting_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            """,
            (key, value),
        )
    conn.commit()
    cur.close()
    print("  ✅ Demo settings configured")


def reset_data(conn) -> None:
    """Clear all demo data (preserves admin user)."""
    cur = conn.cursor()
    cur.execute("DELETE FROM attendance")
    cur.execute("DELETE FROM notifications")
    cur.execute("DELETE FROM logs")
    cur.execute("DELETE FROM user_notification_settings WHERE user_id > 1")
    cur.execute("DELETE FROM user_roles WHERE user_id > 1")
    cur.execute("DELETE FROM users WHERE id > 1")
    cur.execute("DELETE FROM students")
    conn.commit()
    cur.close()
    print("  ✅ All demo data cleared")


def main():
    parser = argparse.ArgumentParser(description="Seed AIM demo data")
    parser.add_argument("--students", action="store_true", help="Seed only students")
    parser.add_argument("--attendance", action="store_true", help="Seed only attendance")
    parser.add_argument("--users", action="store_true", help="Seed only teacher users")
    parser.add_argument("--reset", action="store_true", help="Clear all data first")
    args = parser.parse_args()

    print("🎓 AIM Demo Data Seeder")
    print("=" * 50)

    try:
        conn = _get_connection()
    except Exception as e:
        print(f"❌ Cannot connect to database: {e}")
        print("   Make sure MySQL is running and .env is configured.")
        sys.exit(1)

    try:
        if args.reset:
            reset_data(conn)

        if args.students:
            seed_students(conn)
        elif args.attendance:
            cur = conn.cursor()
            cur.execute("SELECT id, roll FROM students")
            students = cur.fetchall()
            cur.close()
            if not students:
                print("  ❌ No students found. Run without --attendance first to seed students.")
            else:
                seed_attendance(conn, students)
        elif args.users:
            seed_teacher_users(conn)
        else:
            # Seed everything
            students = seed_students(conn)
            seed_teacher_users(conn)
            seed_attendance(conn, students)
            seed_settings(conn)

        print()
        print("=" * 50)
        print("✅ Demo data seeding complete!")
        print()
        print("Default login credentials:")
        print("  Admin:   admin / admin123!")
        for username, full_name, email, dept in DEMO_TEACHERS:
            print(f"  Teacher: {username} / Teacher@123")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
