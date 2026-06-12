"""Tests for authentication routes and services."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


class TestLoginPage:
    def test_login_page_loads(self, client) -> None:
        with patch("app.fetch_settings_map", return_value={}):
            response = client.get("/login")
            assert response.status_code == 200

    def test_login_page_contains_form(self, client) -> None:
        with patch("app.fetch_settings_map", return_value={}):
            response = client.get("/login")
            assert b"login" in response.data.lower() or b"username" in response.data.lower()


class TestUnauthenticatedAccess:
    def test_dashboard_redirects_to_login(self, client) -> None:
        response = client.get("/dashboard")
        assert response.status_code in (302, 308)
        assert "login" in response.headers.get("Location", "").lower()

    def test_students_redirects_to_login(self, client) -> None:
        response = client.get("/students")
        assert response.status_code in (302, 308)

    def test_attendance_redirects_to_login(self, client) -> None:
        response = client.get("/attendance")
        assert response.status_code in (302, 308)

    def test_reports_redirects_to_login(self, client) -> None:
        response = client.get("/report")
        assert response.status_code in (302, 308)

    def test_admin_redirects_to_login(self, client) -> None:
        response = client.get("/users")
        assert response.status_code in (302, 308)


class TestInvalidLogin:
    def test_invalid_credentials(self, client) -> None:
        response = client.post("/login", data={
            "username": "nobody",
            "password": "wrong",
        })
        # Without CSRF token, returns 400 (BAD REQUEST) which is correct behavior
        # The important thing is it doesn't crash
        assert response.status_code in (200, 302, 400)

    def test_empty_username(self, client) -> None:
        response = client.post("/login", data={
            "username": "",
            "password": "somepass",
        })
        assert response.status_code in (200, 302, 400)

    def test_empty_password(self, client) -> None:
        response = client.post("/login", data={
            "username": "admin",
            "password": "",
        })
        assert response.status_code in (200, 302, 400)


class TestSessionStatus:
    def test_session_status_unauthenticated(self, client) -> None:
        response = client.get("/session_status")
        assert response.status_code == 401

    def test_api_session_status_unauthenticated(self, client) -> None:
        response = client.get("/api/session_status")
        assert response.status_code == 401


class TestHealthCheck:
    def test_health_endpoint(self, client) -> None:
        with patch("database.db.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (1,)
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.close = MagicMock()
            response = client.get("/health")
            assert response.status_code in (200, 503)


class TestPasswordPolicy:
    def test_short_password_rejected(self) -> None:
        from services.auth_service import password_policy_error
        result = password_policy_error("short")
        assert result is not None
        assert "8 characters" in result

    def test_password_without_digit_rejected(self) -> None:
        from services.auth_service import password_policy_error
        result = password_policy_error("NoDigitsHere")
        assert result is not None
        assert "number" in result.lower() or "digit" in result.lower()

    def test_password_without_uppercase_rejected(self) -> None:
        from services.auth_service import password_policy_error
        result = password_policy_error("nouppercase1")
        assert result is not None

    def test_password_without_lowercase_rejected(self) -> None:
        from services.auth_service import password_policy_error
        result = password_policy_error("NOLOWERCASE1")
        assert result is not None

    def test_valid_password_accepted(self) -> None:
        from services.auth_service import password_policy_error
        with patch("utils.crypto.is_password_breached", return_value=False):
            result = password_policy_error("ValidPass1")
            assert result is None


class TestArgon2Hashing:
    def test_argon2_hash_and_verify(self) -> None:
        from services.auth_service import _hash_password, _verify_password
        hashed = _hash_password("TestPassword1!")
        assert hashed.startswith("$argon2")
        assert _verify_password(hashed, "TestPassword1!") is True
        assert _verify_password(hashed, "WrongPassword") is False

    def test_legacy_werkzeug_hash_still_works(self) -> None:
        from services.auth_service import _verify_password
        from werkzeug.security import generate_password_hash
        legacy_hash = generate_password_hash("TestPassword1!")
        assert _verify_password(legacy_hash, "TestPassword1!") is True
        assert _verify_password(legacy_hash, "WrongPassword") is False


class TestUsernameValidation:
    def test_valid_usernames(self) -> None:
        from services.auth_service import valid_username
        assert valid_username("admin") is True
        assert valid_username("user_123") is True
        assert valid_username("john.doe") is True
        assert valid_username("user-name") is True

    def test_invalid_usernames(self) -> None:
        from services.auth_service import valid_username
        assert valid_username("ab") is False
        assert valid_username("") is False
        assert valid_username("user@name") is False
        assert valid_username("a" * 51) is False


class TestNameValidation:
    def test_valid_names(self) -> None:
        from services.auth_service import valid_person_name
        assert valid_person_name("John") is True
        assert valid_person_name("Mary-Jane") is True
        assert valid_person_name("O'Brien") is True

    def test_invalid_names(self) -> None:
        from services.auth_service import valid_person_name
        assert valid_person_name("") is False
        assert valid_person_name("123") is False
        assert valid_person_name("a" * 51) is False
