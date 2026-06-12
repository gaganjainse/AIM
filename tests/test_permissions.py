"""Tests for permission system — RBAC, role defaults, edge cases."""
from __future__ import annotations

from datetime import date
import pytest
from unittest.mock import patch, MagicMock


class TestRoleDefaultPermissions:
    def test_teacher_default_permissions(self) -> None:
        from routes.permissions import ROLE_DEFAULT_PERMISSIONS
        teacher_perms = ROLE_DEFAULT_PERMISSIONS.get("teacher", set())
        assert "mark_attendance" in teacher_perms
        assert "view_reports" in teacher_perms
        assert "export_reports" in teacher_perms
        assert "manage_users" not in teacher_perms

    def test_admin_has_all_permissions(self) -> None:
        from routes.permissions import has_permission
        with patch("routes.permissions.session", {"role": "admin", "user_id": 1}):
            assert has_permission("manage_users") is True
            assert has_permission("mark_attendance") is True
            assert has_permission("any_permission") is True


class TestPermissionCheck:
    def test_no_user_id_returns_false(self) -> None:
        from routes.permissions import has_permission
        with patch("routes.permissions.session", {"role": "teacher"}):
            assert has_permission("manage_users") is False

    def test_unknown_role_returns_false(self) -> None:
        from routes.permissions import has_permission
        with patch("routes.permissions.session", {"role": "unknown", "user_id": 1}):
            with patch("routes.permissions.user_has_permission", return_value=False):
                assert has_permission("mark_attendance") is False


class TestPolicyNormalization:
    def test_valid_policies(self) -> None:
        from routes.permissions import normalize_teacher_policy
        assert normalize_teacher_policy("current_week_only") == "current_week_only"
        assert normalize_teacher_policy("Current month only") == "current_month_only"
        assert normalize_teacher_policy("current semester only") == "current_semester_only"

    def test_invalid_policy_defaults(self) -> None:
        from routes.permissions import normalize_teacher_policy
        assert normalize_teacher_policy("invalid") == "current_week_only"
        assert normalize_teacher_policy(None) == "current_week_only"
        assert normalize_teacher_policy("") == "current_week_only"


class TestPolicyLabels:
    def test_policy_labels(self) -> None:
        from routes.permissions import _POLICY_LABELS, _SCOPE_LABELS
        assert _POLICY_LABELS["current_week_only"] == "Current week only"
        assert _SCOPE_LABELS["current_week_only"] == "current week"


class TestTeacherEditWindow:
    def test_week_window_starts_monday(self) -> None:
        from routes.permissions import teacher_edit_window
        # Thursday Jan 15, 2026
        thursday = date(2026, 1, 15)
        start, end, policy = teacher_edit_window(thursday)
        assert start.weekday() == 0  # Monday

    def test_month_window_starts_first(self) -> None:
        from routes.permissions import teacher_edit_window, normalize_teacher_policy
        with patch("routes.permissions.get_setting", return_value="current_month_only"):
            mid_month = date(2026, 1, 15)
            start, end, policy = teacher_edit_window(mid_month)
            assert start.day == 1

    def test_window_never_exceeds_today(self) -> None:
        from routes.permissions import teacher_edit_window
        today = date(2026, 1, 15)
        start, end, _ = teacher_edit_window(today)
        assert end <= today
        assert start <= end
