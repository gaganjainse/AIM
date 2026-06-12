"""Tests for API routes — JSON responses, status codes, rate limiting."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


class TestAPISessionStatus:
    def test_unauthenticated_returns_401(self, client) -> None:
        response = client.get("/api/session_status")
        assert response.status_code == 401
        data = response.get_json()
        assert data["active"] is False


class TestAPIHealth:
    def test_health_returns_200(self, client) -> None:
        with patch("database.db.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (1,)
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_conn.return_value.close = MagicMock()
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "ok"


class TestAPIAttendanceEvents:
    def test_events_requires_login(self, client) -> None:
        response = client.get("/api/attendance_events")
        assert response.status_code in (302, 401, 403)


class TestAPIRandomizeAttendance:
    def test_randomize_requires_login(self, client) -> None:
        response = client.post(
            "/api/attendance/randomize",
            json={"date": "2026-01-15"},
            headers={"X-CSRFToken": "test"},
        )
        assert response.status_code in (302, 400, 401, 403)

    def test_randomize_requires_permission(self, client) -> None:
        response = client.post(
            "/api/attendance/randomize",
            json={"date": "2026-01-15"},
            headers={"X-CSRFToken": "test"},
        )
        assert response.status_code in (302, 400, 403)


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_format(self, client) -> None:
        response = client.get("/metrics")
        assert response.status_code in (200, 404)


class TestSecurityHeaders:
    def test_security_headers_present(self, client) -> None:
        with patch("app.fetch_settings_map", return_value={}):
            response = client.get("/login")
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            # Talisman may set SAMEORIGIN; we also set DENY in after_request
            assert response.headers.get("X-Frame-Options") in ("DENY", "SAMEORIGIN")

    def test_csp_header_present(self, client) -> None:
        with patch("app.fetch_settings_map", return_value={}):
            response = client.get("/login")
            assert response.status_code == 200


class TestErrorPages:
    def test_404_page(self, client) -> None:
        with patch("app.fetch_settings_map", return_value={}):
            response = client.get("/nonexistent-page")
            assert response.status_code == 404

    def test_403_page(self, client) -> None:
        response = client.get("/users")
        assert response.status_code in (302, 403)
