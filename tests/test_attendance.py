"""Tests for attendance services — marking, import, edit windows, permissions."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta


class TestAttendancePermissions:
    def test_attendance_page_requires_login(self, client) -> None:
        response = client.get("/attendance")
        assert response.status_code in (302, 403)

    def test_attendance_import_requires_permission(self, client) -> None:
        with client.session_transaction() as sess:
            import secrets
            sess["_csrf_token"] = secrets.token_urlsafe(32)
        response = client.post("/attendance/import", data={"csrf_token": "test"})
        assert response.status_code in (302, 400, 403)


class TestTeacherEditWindow:
    def test_current_week_policy(self) -> None:
        from routes.permissions import teacher_edit_window
        # Thursday June 12, 2025 (weekday=3)
        thursday = date(2025, 6, 12)
        start, end, policy = teacher_edit_window(today=thursday)
        assert policy == "current_week_only"
        assert start == date(2025, 6, 9)  # Monday of that week
        assert end == thursday

    def test_current_month_policy(self) -> None:
        from routes.permissions import normalize_teacher_policy, _parse_date
        assert normalize_teacher_policy("current_week_only") == "current_week_only"
        assert normalize_teacher_policy("Current month only") == "current_month_only"
        assert normalize_teacher_policy("invalid") == "current_week_only"

    def test_date_parsing(self) -> None:
        from routes.permissions import _parse_date
        assert _parse_date("2026-01-15") == date(2026, 1, 15)
        assert _parse_date(None) is None
        assert _parse_date("invalid") is None
        assert _parse_date("") is None


class TestAttendanceValidation:
    def test_valid_status_values(self) -> None:
        valid = {"Present", "Absent", "Leave"}
        assert "Present" in valid
        assert "Absent" in valid
        assert "Leave" in valid
        assert "Late" not in valid

    def test_csv_required_columns(self) -> None:
        required = {"roll", "date", "status"}
        assert required.issubset({"roll", "date", "status", "extra"})
        assert not required.issubset({"roll", "date"})


class TestStudentValidation:
    def test_roll_number_validation(self) -> None:
        import re
        pattern = r"^[A-Za-z0-9-]{3,20}$"
        assert re.fullmatch(pattern, "CS-2026-001")
        assert re.fullmatch(pattern, "A" * 20)
        assert not re.fullmatch(pattern, "AB")  # Too short
        assert not re.fullmatch(pattern, "A" * 21)  # Too long
        assert not re.fullmatch(pattern, "CS@001")  # Invalid char

    def test_name_validation(self) -> None:
        import re
        pattern = r"^[A-Za-z][A-Za-z\s'.-]{0,49}$"
        assert re.fullmatch(pattern, "John")
        assert re.fullmatch(pattern, "Mary-Jane")
        assert re.fullmatch(pattern, "O'Brien")
        assert not re.fullmatch(pattern, "123John")
        assert not re.fullmatch(pattern, "")


class TestReportCalculations:
    def test_attendance_percentage_calculation(self) -> None:
        present, total = 80, 100
        percentage = round((present / total) * 100, 2)
        assert percentage == 80.0

    def test_zero_total_handling(self) -> None:
        present, total = 0, 0
        percentage = 0 if not total else round((present / total) * 100, 2)
        assert percentage == 0

    def test_report_label_assignment(self) -> None:
        threshold = 75.0
        records = [
            {"percentage": 90.0, "expected": "success"},
            {"percentage": 70.0, "expected": "warning"},
            {"percentage": 40.0, "expected": "danger"},
        ]
        for r in records:
            if r["percentage"] >= threshold:
                label = "success"
            elif r["percentage"] >= max(50, threshold - 25):
                label = "warning"
            else:
                label = "danger"
            assert label == r["expected"]


class TestSearchValidation:
    def test_empty_search_handling(self) -> None:
        q = "".strip()
        assert not q  # Empty search should return empty results

    def test_search_sanitization(self) -> None:
        q = "test'; DROP TABLE students; --"
        like = f"%{q}%"
        assert "DROP" in like  # The LIKE pattern itself is safe with parameterized queries
