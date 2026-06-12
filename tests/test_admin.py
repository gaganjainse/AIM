"""Tests for admin services — user management, roles, settings, backup."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


def _csrf(client) -> str:
    """Get a CSRF token from the session."""
    with client.session_transaction() as sess:
        from app import create_app
        import secrets
        token = secrets.token_urlsafe(32)
        sess["_csrf_token"] = token
    return token


class TestUserManagement:
    def test_users_page_requires_admin(self, client) -> None:
        response = client.get("/users")
        assert response.status_code in (302, 403)

    def test_add_user_requires_manage_users(self, client) -> None:
        token = _csrf(client)
        response = client.post("/add_user", data={
            "username": "newuser",
            "password": "TestPass1!",
            "role_id": "2",
            "csrf_token": token,
        })
        assert response.status_code in (302, 403)

    def test_delete_user_requires_manage_users(self, client) -> None:
        token = _csrf(client)
        response = client.post("/delete_user/1", data={"csrf_token": token})
        assert response.status_code in (302, 403)

    def test_reset_password_requires_manage_users(self, client) -> None:
        token = _csrf(client)
        response = client.post("/reset_password/1", data={"csrf_token": token})
        assert response.status_code in (302, 403)


class TestRoleManagement:
    def test_roles_page_requires_admin(self, client) -> None:
        response = client.get("/roles")
        assert response.status_code in (302, 403)

    def test_save_role_permissions_requires_admin(self, client) -> None:
        token = _csrf(client)
        response = client.post("/roles", data={
            "role_id": "1",
            "permissions": ["1"],
            "csrf_token": token,
        })
        assert response.status_code in (302, 403)


class TestSettingsManagement:
    def test_settings_page_requires_admin(self, client) -> None:
        response = client.get("/settings")
        assert response.status_code in (302, 403)

    def test_update_settings_requires_admin(self, client) -> None:
        token = _csrf(client)
        response = client.post("/settings", data={
            "system_name": "Test System",
            "attendance_limit": "75",
            "csrf_token": token,
        })
        assert response.status_code in (302, 403)

    def test_restore_defaults_requires_admin(self, client) -> None:
        token = _csrf(client)
        response = client.post("/restore_defaults", data={"csrf_token": token})
        assert response.status_code in (302, 403)


class TestBackupRestore:
    def test_backup_page_requires_admin(self, client) -> None:
        response = client.get("/backup_restore")
        assert response.status_code in (302, 403)

    def test_backup_database_requires_admin(self, client) -> None:
        token = _csrf(client)
        response = client.post("/backup", data={"csrf_token": token})
        assert response.status_code in (302, 403)

    def test_restore_backup_requires_admin(self, client) -> None:
        token = _csrf(client)
        response = client.post("/restore_backup", data={"csrf_token": token})
        assert response.status_code in (302, 403)


class TestLogManagement:
    def test_logs_page_requires_admin(self, client) -> None:
        response = client.get("/logs")
        assert response.status_code in (302, 403)

    def test_clear_logs_requires_admin(self, client) -> None:
        token = _csrf(client)
        response = client.post("/clear_logs", data={"csrf_token": token})
        assert response.status_code in (302, 403)


class TestNotificationManagement:
    def test_mark_notifications_read_requires_login(self, client) -> None:
        token = _csrf(client)
        response = client.post("/mark_notifications_read", data={"csrf_token": token})
        assert response.status_code in (302, 403)


class TestPasswordGeneration:
    def test_temporary_password_generation(self) -> None:
        from services.admin_service import _generate_temporary_password
        pwd = _generate_temporary_password()
        assert len(pwd) >= 8
        assert any(c.isdigit() for c in pwd)
        assert any(c.isupper() for c in pwd)

    def test_temporary_password_uniqueness(self) -> None:
        from services.admin_service import _generate_temporary_password
        passwords = {_generate_temporary_password() for _ in range(10)}
        assert len(passwords) > 1


class TestInputValidation:
    def test_username_validation(self) -> None:
        from services.auth_service import valid_username
        assert valid_username("admin") is True
        assert valid_username("ab") is False

    def test_year_format_validation(self) -> None:
        import re
        pattern = r"\d{4}-\d{2}"
        assert re.fullmatch(pattern, "2026-27")
        assert re.fullmatch(pattern, "2026-01") is not None
        assert re.fullmatch(pattern, "2026") is None

    def test_date_format_validation(self) -> None:
        from datetime import datetime
        datetime.strptime("2026-01-01", "%Y-%m-%d")
        with pytest.raises(ValueError):
            datetime.strptime("not-a-date", "%Y-%m-%d")
